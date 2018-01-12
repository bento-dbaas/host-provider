from collections import namedtuple
from libcloud.compute.types import Provider
from host_provider.providers.base import ProviderBase
from host_provider.credentials.cloudstack import CredentialCloudStack, CredentialAddCloudStack


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

    @classmethod
    def get_provider(cls):
        return Provider.CLOUDSTACK

    def build_credential(self):
        return CredentialCloudStack(
            self.get_provider(), self.environment, self.engine
        )

    def create_host(self, cpu, memory, name):
        networks = [
            self.BasicInfo(network) for network in self.credential.networks
        ]

        project = self.credential.project
        if project:
            project = self.BasicInfo(project)

        return self.client.create_node(
            name=name,
            size=self.BasicInfo(self.credential.offering_to(cpu, memory)),
            image=self.BasicInfo(self.credential.template),
            location=self.BasicInfo(self.credential.zone),
            networks=networks,
            project=project
        )

    def get_credential_add(self):
        return CredentialAddCloudStack

