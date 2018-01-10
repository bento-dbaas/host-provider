from collections import namedtuple
from libcloud.compute.types import Provider
from host_provider.providers.base import ProviderBase
from host_provider.settings import credentials


class CloudStackProvider(ProviderBase):
    BasicInfo = namedtuple("CloudStackBasicInfo", "id")

    def build_client(self):
        CloudStackClient = self.get_driver()
        return CloudStackClient(
            key=self.credential.api_key,
            secret=self.credential.secret_key,
            url=self.credential.endpoint,
            secure=self.credential.secure
        )

    def build_credential(self):
        return Credential(self.environment, self.engine)

    @staticmethod
    def get_provider():
        return Provider.CLOUDSTACK

    def create_host(self, cpu, memory, name):
        BasicInfo = namedtuple("CloudStackBasicInfo", "id")
        return self.client.create_node(
            name=name,
            size=BasicInfo(self.credential.offering_to(cpu, memory)),
            image=BasicInfo(self.credential.template),
            location=BasicInfo(self.credential.zone),
            networks=[BasicInfo(self.credential.networks)],
            project=BasicInfo(self.credential.project)
        )


class Credential(object):

    def __init__(self, environment, engine):
        self.environment = environment
        self.engine = engine
        self.env_data = credentials[self.environment]
        self.engine_data = self.env_data[self.engine]

    @property
    def endpoint(self):
        return self.env_data['endpoint']

    @property
    def api_key(self):
        return self.env_data['api_key']

    @property
    def secret_key(self):
        return self.env_data['secret_key']

    def offering_to(self, cpu, memory):
        return self.env_data['offerings']['{}c{}m'.format(cpu, memory)]

    @property
    def template(self):
        return self.engine_data['template']

    @property
    def zone(self):
        return list(self.env_data['zones'].keys())[0]

    @property
    def networks(self):
        zone = self.env_data['zones'][self.zone]
        if 'networks' in zone:
            return zone['networks'][0]
        return None

    @property
    def extra(self):
        return self.env_data['extra']

    @property
    def project(self):
        return self.env_data['extra']['projectid']

    @property
    def secure(self):
        return self.env_data['secure']
