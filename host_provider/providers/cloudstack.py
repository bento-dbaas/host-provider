from collections import namedtuple
from libcloud.compute.types import Provider
from host_provider.providers.base import ProviderBase
from host_provider.credentials.cloudstack import CredentialCloudStack, \
    CredentialAddCloudStack
import logging


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

    def _create_host(self, cpu, memory, name, *args, **kw):
        networks = [
            self.BasicInfo(network) for network in self.credential.networks
        ]

        project = self.credential.project
        if project:
            project = self.BasicInfo(project)

        params = dict(
            name=name,
            size=self.BasicInfo(self.credential.offering_to(cpu, memory)),
            image=self.BasicInfo(self.credential.template),
            location=self.BasicInfo(self.credential.zone),
            networks=networks,
            project=project
        )
        logging.error("Creating VM with params {}".format(params))
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

    def start(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.ex_start(node)

    def stop(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.ex_stop(node)

    def _destroy(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.destroy_node(node)

    def _all_node_destroyed(self, group):
        self.credential.remove_last_used_for(group)

    def restore(self, identifier, engine=None):
        node = self.BasicInfo(identifier)

        if engine is None:
            template = self.credential.template
        else:
            template = self.credential.template_to(engine)

        template = self.BasicInfo(template)

        return self.client.ex_restore(node, template)

    def resize(self, identifier, cpus, memory):
        node = self.BasicInfo(identifier)
        offering = self.BasicInfo(self.credential.offering_to(cpus, memory))

        return self.client.ex_change_node_size(node, offering)
