from collections import namedtuple
from libcloud.compute.types import Provider
from host_provider.providers.base import ProviderBase
from host_provider.credentials.aws import CredentialAWS, \
    CredentialAddAWS


class OfferingNotFoundError(Exception):
    pass


class AWSProvider(ProviderBase):
    BasicInfo = namedtuple("EC2BasicInfo", "id")

    def build_client(self):
        AwsClient = self.get_driver()

        return AwsClient(
            self.credential.access_id,
            self.credential.secret_key,
            self.credential.region
        )

    @classmethod
    def get_provider(cls):
        return Provider.EC2

    def build_credential(self):
        return CredentialAWS(
            self.get_provider(), self.environment, self.engine
        )

    def offering_to(self, cpu, memory):
        offerings = self.client.list_sizes()

        for offering in offerings:
            if offering.ram == memory and offering.extra.get('cpu') == cpu:
                return offering

        raise OfferingNotFoundError(
            "Offering with {} cpu and {} of memory not found.".format(cpu, memory)
        )

    def _create_host(self, cpu, memory, name):
        return self.client.create_node(
            name=name,
            image=self.BasicInfo(self.credential.image_id),
            size=self.offering_to(cpu, memory),
            ex_keyname='rafael.goncalves',
            ex_security_group_ids=[self.BasicInfo(self.credential.security_group_id)],
            ex_subnet=self.BasicInfo(self.credential.zone),
        )


    def get_credential_add(self):
        return CredentialAddAWS

    def start(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.ex_start_node(node)

    def stop(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.ex_stop_node(node)

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
