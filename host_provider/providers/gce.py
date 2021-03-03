import logging
from time import sleep
import googleapiclient.discovery
from google.oauth2 import service_account

from host_provider.credentials.gce import CredentialGce, CredentialAddGce
from host_provider.providers.base import ProviderBase
from host_provider.models import Host, IP


LOG = logging.getLogger(__name__)


class WrongStatusError(Exception):
    pass


class StaticIPNotFoundError(Exception):
    pass


class GceProvider(ProviderBase):

    def build_client(self):
        service_account_data = self.credential.content['service_account']
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')
        credentials = service_account.Credentials.from_service_account_info(
            service_account_data
        )
        return googleapiclient.discovery.build(
            'compute', 'v1', credentials=credentials
        )

    @classmethod
    def get_provider(cls):
        return "gce"

    def get_static_ip_by_name(self, name):
        return IP.get(name=name)

    def build_credential(self):
        return CredentialGce(
            self.get_provider(), self.environment, self.engine
        )

    def get_credential_add(self):
        return CredentialAddGce

    def start(self, host):
        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        self.client.instances().start(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        self.wait_status_of_instance(instance_name, status='RUNNING')

    def stop(self, identifier):
        host = Host.get(identifier=identifier)

        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        self.client.instances().stop(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        self.wait_status_of_instance(
            instance_name, status='TERMINATED'
        )

    @property
    def disk_image_link(self):
        image_response = self.client.images().get(
            project=self.credential.project,
            image=self.credential.template_to(self.engine),
        ).execute()

        return image_response['selfLink']

    def _create_host(self, cpu, memory, name, *args, **kw):

        offering = self.credential.offering_to(int(cpu), memory)
        zone = self.credential.zone
        static_ip_id = kw.get('static_ip_id')
        if not static_ip_id:
            raise StaticIPNotFoundError(
                'The id of static IP must be provided'
            )
        static_ip = self.get_static_ip_by_name(static_ip_id)

        machine_type = "zones/{}/machineTypes/{}".format(zone, offering)

        network_interface = {
            'subnetwork': self.credential.subnetwork,
            'aliasIpRanges': [],
            'networkIP': static_ip.address
        }

        config = {
            'name': name,
            'machineType': machine_type,

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': self.disk_image_link,
                    }
                }
            ],

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [network_interface],

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write'
                ]
            }],

        }

        instance = self.client.instances().insert(
            project=self.credential.project,
            zone=zone,
            body=config
        ).execute()
        return instance

    def _destroy(self, identifier):
        host = Host.get(identifier=identifier)
        return self.client.instances().delete(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name
        ).execute()

    def create_static_ip(self, group, ip_name):
        self.credential.before_create_host(group)
        self.client.addresses().insert(
            project=self.credential.project,
            region=self.credential.region,
            body={
                'subnetwork': self.credential.subnetwork,
                'addressType': 'INTERNAL',
                'name': ip_name
            }
        ).execute()

        self.wait_status_of_static_ip(ip_name, status="RESERVED")
        ip_metadata = self.get_internal_static_ip(ip_name)

        ip = IP(
            name=ip_name,
            group=group,
            address=ip_metadata['address']
        )
        ip.save()

        return ip

    def destroy_static_ip(self, ip_name):
        self.client.addresses().delete(
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        ).execute()

    def clean(self, name):
        pass

    def configure(self, name, group, configuration):
        pass

    def resize(self, host, cpus, memory):
        offering = self.credential.offering_to(int(cpus), memory)
        machine_type = "zones/{}/machineTypes/{}".format(host.zone, offering)
        config = {
            'machineType': machine_type,
        }
        return self.client.instances().setMachineType(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name,
            body=config
        ).execute()

    def _is_ready(self, host):
        pass

    def associate_ip_with_host(self, host, static_ip_id):
        ip = self.get_static_ip_by_name(static_ip_id)
        ip.host = host
        ip.save()

    def create_host_object(self, provider, payload, env,
                           created_host_metadata, static_ip_id, **kw):

        zone = provider.credential.zone
        instance_name = payload['name']

        self.wait_status_of_instance(instance_name, status='RUNNING')

        instance = self.get_instance(instance_name)
        address = instance['networkInterfaces'][0]['networkIP']

        host = Host(
            name=payload['name'], group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=created_host_metadata['id'], address=address,
            zone=zone
        )
        host.save()
        return host

    def get_instance(self, instance_name, execute_request=True):
        request = self.client.instances().get(
            project=self.credential.project,
            zone=self.credential.zone,
            instance=instance_name
        )
        if execute_request:
            return request.execute()
        return request

    def get_internal_static_ip(self, ip_name, execute_request=True):
        request = self.client.addresses().get(
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        )
        if execute_request:
            return request.execute()
        return request

    def wait_status_of_static_ip(self, address_name, status):

        request = self.get_internal_static_ip(
            address_name,
            execute_request=False
        )

        return self._wait_status_of(
            request,
            status,
            required_fields=['address']
        )

    def wait_status_of_instance(self, instance_name, status):
        request = self.get_instance(
            instance_name,
            execute_request=False
        )

        return self._wait_status_of(request, status)

    def _wait_status_of(self, request, status, required_fields=None):
        """
        Wait resource get specific status through
        status param.
        u can pass `required_fields`
        required_fields is a array with field name.
        When u pass fields name, we will wait this field
        exists in response resource.
        Ex. required_fields=['age', 'name']
        """

        def resource_has_required_fields(resource, required_fields):
            for field_name in required_fields:
                if field_name not in resource:
                    return False
            return True

        if required_fields is None:
            required_fields = []
        attempts = 1
        while attempts <= 60:

            resource = request.execute()
            resource_status = resource['status']
            if (resource_status == status and
                    resource_has_required_fields(resource, required_fields)):
                return True

            attempts += 1
            sleep(5)

        err_msg = "It was expected status: {} got: {}.".format(
            status, resource_status
        )
        if required_fields:
            err_msg += (" And It expected required fields: {} "
                        "the resource has this fields: {}").format(
                            required_fields, resource.keys()
                        )
        raise WrongStatusError(err_msg)
