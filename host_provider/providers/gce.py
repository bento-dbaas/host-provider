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
        #credentials
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

        image_response = self.client.images().get(
            project=self.credential.project,
            image=self.credential.template_to(self.engine),
        ).execute()

        source_disk_image = image_response['selfLink']
        offering = self.credential.offering_to(int(cpu), memory)
        zone = self.credential.zone

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
        pass

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


        '''
    provider: <host_provider.providers.gce.GceProvider object at 0x11313a4e0> payload: {'engine': 'mongodb_4_2_3', 'group': 'test01161222692366', 'name': 'test01-01-161222692366', 'database_name': 'test01', 'memory': 1024, 'team_name': 'dbaas', 'cpu': 1.0}
    env: gcp-lab
    created_host_metadata: {'id': '5945271361285200033', 'name': 'operation-1612228173282-5ba501f90bb86-d03f8a4a-f909a27a', 'zone': 'https://www.googleapis.com/compute/v1/projects/gglobo-dbaas-dev-dev-qa/zones/southamerica-east1-a', 'operationType': 'insert', 'targetLink': 'https://www.googleapis.com/compute/v1/projects/gglobo-dbaas-dev-dev-qa/zones/southamerica-east1-a/instances/test01-01-161222692366', 'targetId': '1333087839616047266', 'status': 'RUNNING', 'user': '398728514298-compute@developer.gserviceaccount.com', 'progress': 0, 'insertTime': '2021-02-01T17:09:34.432-08:00', 'startTime': '2021-02-01T17:09:34.435-08:00', 'selfLink': 'https://www.googleapis.com/compute/v1/projects/gglobo-dbaas-dev-dev-qa/zones/southamerica-east1-a/operations/operation-1612228173282-5ba501f90bb86-d03f8a4a-f909a27a', 'kind': 'compute#operation'}
    '''


        '''
        address = created_host_metadata.private_ips[0]
        host = Host(
            name=payload['name'], group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=created_host_metadata.id, address=address,
            zone=provider.credential._zone
        )
        host.save()
        return host
        '''
