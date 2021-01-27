import logging

import googleapiclient.discovery
from google.oauth2 import service_account

from host_provider.credentials.gce import CredentialGce, CredentialAddGce
from host_provider.providers.base import ProviderBase


LOG = logging.getLogger(__name__)


class GceProvider(ProviderBase):

    def build_client(self):
        service_account_data = self.credential.content['service_account']
        service_account_data['private_key'] = service_account_data[
            'private_key'
        ].replace('\\n', '\n')
        credentials = service_account.Credentials.from_service_account_info(
            service_account_data
        )
        credentials
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
        pass

    def stop(self, identifier):
        pass

    def _create_host(self, cpu, memory, name, *args, **kw):
        image_response = self.client.images().getFromFamily(
            project='debian-cloud', family='debian-9'
        ).execute()
        source_disk_image = image_response['selfLink']
        offering = self.credential.offering_to(int(cpu), memory)
        zone = self.credential.zone
    # Configure the machine
        machine_type = "zones/{}/machineTypes/{}".format(zone, offering)
        # startup_script = open(
        #     os.path.join(
        #         os.path.dirname(__file__), 'startup-script.sh'), 'r').read()
        # image_url = "http://storage.googleapis.com/gce-demo-input/photo.jpg"
        # image_caption = "Ready for dessert?"

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

            # Metadata is readable from the instance and allows you to
            # pass configuration from deployment scripts to instances.
            # 'metadata': {
            #     'items': [{
            #         # Startup script is automatically executed by the
            #         # instance upon startup.
            #         'key': 'startup-script',
            #         'value': startup_script
            #     }, {
            #         'key': 'url',
            #         'value': image_url
            #     }, {
            #         'key': 'text',
            #         'value': image_caption
            #     }, {
            #         'key': 'bucket',
            #         'value': bucket
            #     }]
            # }
        }
        self.credential.zone
        return self.client.instances().insert(
            project=self.credential.project,
            zone=zone,
            body=config
        ).execute()

    def _destroy(self, name):
        return self.client.instances().delete(
            project=self.credential.project,
            zone=self.credential.zone,
            instance=name
        ).execute()

    def clean(self, name):
        pass

    def configure(self, name, group, configuration):
        pass

    def resize(self, host, cpus, memory):
        pass

    def _is_ready(self, host):
        pass
