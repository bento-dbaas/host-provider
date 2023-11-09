from time import sleep
from collections import namedtuple
from libcloud.compute.types import Provider
from host_provider.providers.base import ProviderBase
from host_provider.credentials.aws import CredentialAWS, \
    CredentialAddAWS
from host_provider.settings import (HTTP_PROXY,
                                    HTTPS_PROXY)
from host_provider.settings import TEAM_API_URL
from dbaas_base_provider.team import TeamClient


class OfferingNotFoundError(Exception):
    pass


class NodeNotFounfError(Exception):
    pass


class WrongStateError(Exception):
    pass


class AWSProxyNotSet(Exception):
    pass


class AWSProvider(ProviderBase):
    BasicInfo = namedtuple("EC2BasicInfo", "id")

    def get_node(self, node_id):
        try:
            return self.client.list_nodes(ex_node_ids=[node_id])[0]
        except IndexError:
            raise NodeNotFounfError("Node with id {} not found".format(node_id))

    def build_client(self):
        AwsClient = self.get_driver()

        if HTTP_PROXY is None:
            raise AWSProxyNotSet("Env HTTP_PROXY is empty, please set proxy")

        client = AwsClient(
            key=self.credential.access_id,
            secret=self.credential.secret_key,
            region=self.credential.region,
            **{'proxy_url': HTTP_PROXY} if HTTP_PROXY else {}
        )

        if HTTP_PROXY:
            client.connection.connection.session.proxies.update({
                'https': HTTPS_PROXY
            })

        return client

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

    def _create_host(self, cpu, memory, name, *args, **kw):
        team_name = kw.get('team_name')
        infra_name = kw.get('group')
        database_name = kw.get('database_name')
        team_labels = self.get_team(team_name, infra_name, database_name)
        return self.client.create_node(
            name=name,
            image=self.BasicInfo(self.credential.template_to(self.engine)),
            size=self.offering_to(int(cpu), int(memory)),
            ex_keyname=self.credential.keyname,
            ex_security_group_ids=self.credential.security_group_ids,
            ex_subnet=self.BasicInfo(self.credential.zone),
            ex_metadata=team_labels
        )

    def get_credential_add(self):
        return CredentialAddAWS

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
        node = self.BasicInfo(host.identifier)
        resp = self.client.ex_start_node(node)
        self.wait_state(host.identifier, 'running')
        return resp


    def stop(self, identifier):
        node = self.BasicInfo(identifier)
        resp = self.client.ex_stop_node(node)
        self.wait_state(identifier, 'stopped')
        return resp

    def _destroy(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.destroy_node(node)

    def _all_node_destroyed(self, group):
        self.credential.remove_last_used_for(group)

    def resize(self, host, cpus, memory):
        node = self.get_node(host.identifier)
        offering = self.offering_to(int(cpus), int(memory))

        return self.client.ex_change_node_size(node, offering)
