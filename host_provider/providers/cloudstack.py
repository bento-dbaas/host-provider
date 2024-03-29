from os import getenv
from collections import namedtuple
from libcloud.compute.types import Provider
from requests.exceptions import ConnectionError
from host_provider.providers.base import ProviderBase
from host_provider.credentials.cloudstack import CredentialCloudStack, \
    CredentialAddCloudStack
import logging
from host_provider.models import Host


if bool(int(getenv('VERIFY_SSL_CERT', '0'))):
    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = False


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

    @property
    def create_attempts(self):
        return len(self.credential.zones)

    @classmethod
    def get_provider(cls):
        return Provider.CLOUDSTACK

    def get_cs_node(self, host):
        return self.client.ex_get_node(
            host.identifier,
            self.BasicInfo(self.credential.project)
        )

    def get_network_from(self, host):
        all_network_of_project = self.client.ex_list_networks(
            self.BasicInfo(self.credential.project)
        )
        cs_node = self.get_cs_node(host)
        host_network_id = cs_node.extra['nics:'][0]['networkid']

        for network in all_network_of_project:
            if network.id == host_network_id:
                return network

    def fqdn(self, host):
        try:
            cs_node = self.get_cs_node(host)
            network = self.get_network_from(host)
        except ConnectionError:
            return ''
        if not network:
            return ''
        return "{}.{}".format(cs_node.name, network.extra['network_domain'])

    def build_credential(self):
        return CredentialCloudStack(
            self.get_provider(), self.environment, self.engine
        )

    def get_host_by_name_and_zone(self, name, zone):
        try:
            project = self.BasicInfo(self.credential.project)
            zone = self.BasicInfo(zone)
            nodes = self.client.list_nodes(project=project, location=zone)
            list_by_name = list(filter(lambda n: n is not None, [n if name in n.name else None for n in nodes]))
            # list_by_zone = list(filter(lambda z: z is not None, [z if zone in z.extra.get('zone_id') else None for z in list_by_name]))
            return list_by_name
        except Exception as error:
            logging.error("Error in list host {}".format(error))
            return []

    def _create_host(self, cpu, memory, name, *args, **kw):
        networks = [
            self.BasicInfo(network) for network in self.credential.networks
        ]

        project = self.credential.project
        if project:
            project = self.BasicInfo(project)

        params = dict(
            name=name,
            size=self.BasicInfo(self.credential.offering_to(int(cpu), memory)),
            image=self.BasicInfo(self.credential.template),
            location=self.BasicInfo(self.credential.zone),
            networks=networks,
            project=project
        )
        logging.info("Creating VM with params {}".format(params))

        node = self.get_host_by_name_and_zone(name, self.credential.zone)
        if len(node) > 0:
            return node[0]
        else:
            return self.client.create_node(
                name=name,
                size=self.BasicInfo(self.credential.offering_to(int(cpu), memory)),
                image=self.BasicInfo(self.credential.template),
                location=self.BasicInfo(self.credential.zone),
                networks=networks,
                project=project
            )

    def get_credential_add(self):
        return CredentialAddCloudStack

    def start(self, host):
        node = self.BasicInfo(host.identifier)
        return self.client.ex_start(node)

    def stop(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.ex_stop(node)

    def _destroy(self, identifier):
        node = self.BasicInfo(identifier)
        return self.client.destroy_node(node)

    def _all_node_destroyed(self, group):
        self.credential.remove_last_used_for(group)

    def _restore(self, host, engine, *args, **kw):
        node = self.BasicInfo(host.identifier)

        if engine is None:
            template = self.credential.template
        else:
            template = self.credential.template_to(engine)

        template = self.BasicInfo(template)

        return self.client.ex_restore(node, template)

    def resize(self, host, cpus, memory):
        node = self.BasicInfo(host.identifier)
        offering = self.BasicInfo(self.credential.offering_to(int(cpus), memory))

        return self.client.ex_change_node_size(node, offering)

    def create_host_object(self, provider, payload, env,
                           created_host_metadata, *args, **kw):
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
