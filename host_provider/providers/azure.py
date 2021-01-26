from collections import namedtuple
from time import sleep
from host_provider.credentials.azure import CredentialAddAzure, CredentialAzure
from host_provider.models import Host
from host_provider.providers import ProviderBase
from host_provider.settings import HOST_ORIGIN_TAG
from libcloud.compute.types import Provider
import inspect


class AzureProvider(ProviderBase):
    BasicInfo = namedtuple("AzureBasicInfo", "id")

    @classmethod
    def get_provider(cls):
        return Provider.AZURE_ARM

    def build_client(self):
        AzureClient = self.get_driver()

        client = AzureClient(
            tenant_id=self.credential.tenant_id,
            subscription_id=self.credential.subscription_id,
            key=self.credential.access_id,
            secret=self.credential.secret_key,
            region=self.credential.region
        )
        return client

    def build_credential(self):
        return CredentialAzure(
            self.get_provider(), self.environment, self.engine
        )

    def get_node(self, node_id):
        if not node_id:
            raise ValueError
        nodes = self.client.list_nodes()
        if len(nodes) >= 1:
            for node in nodes:
                if node.get_uuid() == node_id:
                    return node
        return None    

    def offering_to(self, cpu, memory):
        offerings = self.client.list_sizes()

        for offering in offerings:
            if offering.ram == memory and offering.extra.get('numberOfCores') == cpu:
                return offering

        raise OfferingNotFoundError(
            "Offering with {} cpu and {} of memory not found.".format(cpu, memory)
        )

    def generate_tags(self, team_name, infra_name, database_name):
        tags = TeamClient.make_tags(team_name, self.engine)
        if HOST_ORIGIN_TAG:
            tags['origin'] = HOST_ORIGIN_TAG
        tags.update({
            'engine': self.engine_name,
            'infra_name': infra_name,
            'database_name': database_name or ''
        })
        return tags

    def create_host_object(self, provider, payload, env,
                           created_host_metadata):
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

    def _create_host(self, cpu, memory, name, *args, **kw):

        return client.created_node(
            name=name,
            image=self.BasicInfo(self.credential.template_to(self.engine)),
            size=self.offering_to(int(cpu), int(memory)),
            ex_keyname=self.credential.keyname,
            ex_security_group_ids=self.credential.security_group_ids,
            ex_subnet=self.BasicInfo(self.credential.zone),
            ex_metadata=self.generate_tags(
                team_name=kw.get('team_name'),
                infra_name=kw.get('group'),
                database_name=kw.get('database_name')
            )
        )

    def wait_state(self, identifier, state):
        attempts = 1
        while attempts <= 15:

            node = self.get_node(identifier)
            node_state = node.state
            if node_state == state:
                return True

            attempts += 1
            sleep(5)

        raise WrongStateError(
            "It was expected state: {} got: {}".format(state, node_state)
        )

    def start(self, host):
        node = self.get_node(host.identifier)
        resp = self.client.ex_start_node(node)
        self.wait_state(host.identifier, 'running')
        return resp

    def stop(self, identifier):
        node = self.get_node(identifier)
        resp = self.client.ex_stop_node(node)
        self.wait_state(identifier, 'stopped')
        return resp

    @property
    def engine_name(self):
        return self.engine.split('_')[0]

    def get_credential_add(self):
        return CredentialAddAzure

