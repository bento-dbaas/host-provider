import logging
import httplib2
import google_auth_httplib2

from time import sleep
import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from host_provider.settings import HTTP_PROXY
from host_provider.credentials.gce import CredentialGce, CredentialAddGce
from host_provider.providers.base import ProviderBase
from host_provider.models import Host, IP


LOG = logging.getLogger(__name__)


class WrongStatusError(Exception):
    pass


class StaticIPNotFoundError(Exception):
    pass


class GceProvider(ProviderBase):
    WAIT_ATTEMPTS = 60
    WAIT_TIME = 5

    def build_client(self):
        service_account_data = self.credential.content['service_account']
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')

        credentials = service_account.Credentials.from_service_account_info(
            service_account_data,
            scopes=self.credential.scopes
        )

        if HTTP_PROXY:
            _, host, port = HTTP_PROXY.split(':')
            try:
                port = int(port)
            except ValueError:
                raise EnvironmentError('HTTP_PROXY incorrect format')

            proxied_http = httplib2.Http(proxy_info=httplib2.ProxyInfo(
                httplib2.socks.PROXY_TYPE_HTTP,
                host.replace('//', ''),
                port
            ))

            authorized_http = google_auth_httplib2.AuthorizedHttp(
                                credentials,
                                http=proxied_http)

            service = googleapiclient.discovery.build(
                        'compute',
                        'v1',
                        http=authorized_http)
        else:
            service = googleapiclient.discovery.build(
                'compute',
                'v1',
                credentials=credentials,
            )

        return service

    @classmethod
    def get_provider(cls):
        return "gce"

    def get_static_ip_by_name(self, name):
        return IP.get(name=name)

    def get_static_ip_by_host_id(self, host_id):
        return IP.get(host_id=host_id)

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

        start = self.client.instances().start(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        return self.wait_operation(
            operation=start.get('name'),
            zone=zone
        )

    def stop(self, identifier):
        host = Host.get(identifier=identifier)

        project = self.credential.project
        zone = host.zone
        instance_name = host.name

        stop = self.client.instances().stop(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

        return self.wait_operation(
            operation=stop.get('name'),
            zone=zone
        )

    @property
    def disk_image_link(self):
        image_response = self.client.images().get(
            project=self.credential.project,
            image=self.credential.template_to(self.engine),
        ).execute()

        return image_response['selfLink']

    def get_machine_type(self, offering, zone):
        return "zones/{}/machineTypes/{}".format(
            zone,
            offering
        )

    def _create_host(self, cpu, memory, name, zone=None, *args, **kw):

        offering = self.credential.offering_to(int(cpu), memory)
        static_ip_id = kw.get('static_ip_id')
        zone = zone or self.credential.zone

        if not static_ip_id:
            raise StaticIPNotFoundError(
                'The id of static IP must be provided'
            )
        static_ip = self.get_static_ip_by_name(static_ip_id)

        network_interface = {
            'subnetwork': self.credential.subnetwork,
            'aliasIpRanges': [],
            'networkIP': static_ip.address
        }

        config = {
            'name': name,
            'machineType': self.get_machine_type(offering, zone),

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

        self.wait_operation(
            operation=instance.get('name'),
            zone=zone
        )

        return instance

    def _destroy(self, identifier):
        host = Host.get(identifier=identifier)
        destroy = self.client.instances().delete(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name
        ).execute()

        return self.wait_operation(
            operation=destroy.get('name'),
            zone=host.zone
        )

    def create_static_ip(self, group, ip_name):
        self.credential.before_create_host(group)
        address = self.client.addresses().insert(
            project=self.credential.project,
            region=self.credential.region,
            body={
                'subnetwork': self.credential.subnetwork,
                'addressType': 'INTERNAL',
                'name': ip_name
            }
        ).execute()

        self.wait_operation(
            operation=address.get('name'),
            region=self.credential.region
        )

        ip_metadata = self.get_internal_static_ip(ip_name)

        ip = IP(
            name=ip_name,
            group=group,
            address=ip_metadata['address']
        )
        ip.save()

        return ip

    def destroy_static_ip(self, ip_name):
        del_addr = self.client.addresses().delete(
            project=self.credential.project,
            region=self.credential.region,
            address=ip_name
        ).execute()

        self.wait_operation(
            operation=del_addr.get('name'),
            region=self.credential.region
        )

    def clean(self, name):
        pass

    def configure(self, name, group, configuration):
        pass

    def resize(self, host, cpus, memory):
        offering = self.credential.offering_to(int(cpus), memory)
        return self.client.instances().setMachineType(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name,
            body={
                'machineType': self.get_machine_type(
                    offering, host.zone
                ),
            }
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

        instance = self.get_instance(instance_name, zone)
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

    def get_instance(self, instance_name, zone, execute_request=True):
        request = self.client.instances().get(
            project=self.credential.project,
            zone=zone,
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

    def restore(self, host, engine=None):

        if engine:
            self.engine = engine
        # import ipdb; ipdb.set_trace()
        if host.recreating is False:
            self._destroy(identifier=host.identifier)
            host.recreating = True
            host.save()

        created_host_metadata = self._create_host(
            cpu=host.cpu,
            memory=host.memory,
            name=host.name,
            static_ip_id=self.get_static_ip_by_host_id(host.id).name,
            zone=host.zone
        )

        host.identifier = created_host_metadata['id']
        host.recreating = False
        host.save()
