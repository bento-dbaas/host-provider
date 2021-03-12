from collections import namedtuple
from time import sleep
import os
import json
from urllib.parse import urljoin
from host_provider.credentials.azure import CredentialAddAzure, CredentialAzure
from host_provider.common.azure import AzureConnection
from host_provider.models import Host
from host_provider.providers import ProviderBase
from host_provider.settings import HOST_ORIGIN_TAG
from libcloud.compute.types import Provider
from host_provider.clients.team import TeamClient
from pathlib import Path


class JsonTemplates(object):
    def __init__(self, path="host_provider/templates/azure/version/"):
        self.path = path
    
    def list_files(self, version):
        files_version = os.path.join(self.path, f"{version}/")
        files = [path for path in Path(files_version).rglob('*.json')]
        return files

    def load_json(self, json_file):
        data = None

        with open(json_file) as fp:
            data = json.load(fp)
        return data
    
    def dumps_json(self, obj):
        if isinstance(obj, dict):
            return json.dumps(obj)
        return None


class AzureProvider(ProviderBase):
    BasicInfo = namedtuple("AzureBasicInfo", "id")
    azClient = None
    connCls = AzureConnection

    @classmethod
    def get_provider(cls):
        return Provider.AZURE_ARM

    def build_client(self):
        AzureClient = self.get_driver()

        client = AzureClient(
            self.credential.tenant_id,
            self.credential.subscription_id,
            self.credential.access_id,
            self.credential.secret_key,
            region=self.credential.region
        )
        return client

    def build_credential(self):
        return CredentialAzure(
            self.get_provider(), self.environment, self.engine)

    def get_azure_connection(self):
        az = self.connCls()
        self.azClient = az

        return az.conn_cls(self.credential.access_id, \
            self.credential.secret_key, \
                tenant_id=self.credential.tenant_id, \
                    subscription_id=self.credential.subscription_id)

    def get_node(self, node_id):
        pass

    def get_image(self):

        templates = self.credential.template_to(self.engine)


    def offering_to(self, cpu, memory):
        pass

    def parse_nic(self, name, vnet, subnet):
        id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualNetworks/%s/subnets/%s' \
            %(self.credential.subscription_id, self.credential.resource_group, vnet, subnet)

        templates = JsonTemplates()
        for file in templates.list_files('1.0.0'):
            file_name = file.name.split('.json')[0]
            if file_name == 'nic':
                nic_dict = templates.load_json(file.as_posix())
                config = nic_dict['properties']['ipConfigurations']
                for nic in config:
                    nic['name'] = name
                    nic['properties']['subnet']['id'] = id
                nic_dict['properties']['ipConfigurations'] = config
        return nic_dict

    def create_nic(self, name, api_version='2020-07-01'):
        subnet = self.credential.get_next_zone_from(self.credential.subnets)
        vnet = self.credential.subnets.get(subnet)['name']
        base_url = self.credential.endpoint
        action = 'subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s?api-version=%s' \
            %(self.credential.subscription_id, self.credential.resource_group, name, api_version)
        nic = self.parse_nic(name, vnet, subnet)

        payload = json.dumps(nic)
        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("PUT", action, body=payload, headers=header)
        resp = self.azClient.connection.getresponse()
        
        if resp.status_code == 200 or resp.status_code == 201:
            return resp.json()
        
        return None

    def has_network(self, api_version='2020-07-01'):
        subnet = self.credential.get_next_zone_from(self.credential.subnets)
        vnet = self.credential.subnets.get(subnet)['name']
        base_url = self.credential.endpoint

        action = "subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualNetworks/%s?api-version=%s" \
            %(self.credential.subscription_id, self.credential.resource_group, vnet, api_version)

        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("GET", action, headers=header)
        resp = self.azClient.connection.getresponse()
        
        if resp.status_code == 200:
            return resp.json()

        else:
            raise Exception(
                "Network {} not found".format(name)
            )

    def deploy_vm(self, template_version):
        subnet = self.credential.get_next_zone_from(self.credential.subnets)
        template = JsonTemplates()
        pass

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
        pass

    def wait_state(self, identifier, state):
        pass

    def start(self, host):
        pass

    def stop(self, identifier):
        pass

    def _destroy(self, identifier):
        pass

    def _all_node_destroyed(self, group):
        self.credential.remove_last_used_for(group) 

    @property
    def engine_name(self):
        return self.engine.split('_')[0]

    def get_credential_add(self):
        return CredentialAddAzure

