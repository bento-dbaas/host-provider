import logging
from time import sleep
import googleapiclient.discovery
from google.oauth2 import service_account

from host_provider.credentials.gce import CredentialGce, CredentialAddGce
from host_provider.providers.base import ProviderBase
from host_provider.models import Host


LOG = logging.getLogger(__name__)

class WrongStatusError(Exception):
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

    def build_credential(self):
        return CredentialGce(
            self.get_provider(), self.environment, self.engine
        )

    def get_credential_add(self):
        return CredentialAddGce

    def start(self, host):
        return self.client.instances().start(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name
        ).execute()

    def stop(self, identifier):
        host = Host.get(identifier=identifier)
        return self.client.instances().stop(
            project=self.credential.project,
            zone=host.zone,
            instance=host.name
        ).execute()

    def _create_host(self, cpu, memory, name, *args, **kw):

        image_response = self.client.images().get(
            project=self.credential.project,
            image=self.credential.template_to(self.engine),
        ).execute()

        source_disk_image = image_response['selfLink']
        offering = self.credential.offering_to(int(cpu), memory)
        zone = self.credential.zone

        machine_type = "zones/{}/machineTypes/{}".format(zone, offering)

        config = {
            'name': name,
            'machineType': machine_type,

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': source_disk_image,
                    }
                }
            ],

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [{
                "subnetwork": self.credential.content['subnetwork'],
                "accessConfigs": [
                    {
                        "kind": "compute#accessConfig",
                        "name": "External NAT",
                        "type": "ONE_TO_ONE_NAT",
                        "networkTier": "STANDARD"
                    }
                ],
                "aliasIpRanges": []
            }],

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write'
                ]
            }],

        }

        #self.credential.zone
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

    def create_host_object(self, provider, payload, env,
                           created_host_metadata):

        project = provider.credential.project
        zone = provider.credential._zone
        instance_name = payload['name']

        self.wait_status(project, zone, instance_name, status='RUNNING')

        instance = self.get_instance(project, zone, instance_name)
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

    def get_instance(self, project, zone, instance_name):
        return self.client.instances().get(
            project=project,
            zone=zone,
            instance=instance_name
        ).execute()

    def wait_status(self, project, zone, instance_name, status):
        attempts = 1
        while attempts <= 15:

            instance = self.get_instance(project, zone, instance_name)
            vm_status = instance['status']
            if vm_status == status:
                return True

            attempts += 1
            sleep(5)

        raise WrongStatusError(
            "It was expected status: {} got: {}".format(state, vm_status)
        )

