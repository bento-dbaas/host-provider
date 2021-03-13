from collections import namedtuple
import os
import json
import re
from host_provider.credentials.azure import CredentialAddAzure, CredentialAzure
from host_provider.common.azure import AzureConnection
from host_provider.models import Host
from host_provider.providers import ProviderBase
from host_provider.settings import HOST_ORIGIN_TAG
from libcloud.compute.types import Provider
from host_provider.clients.team import TeamClient
from pathlib import Path


class DeployVmError(Exception):
    def __init__(*args, **kwargs):
        pass


class OfferingNotFoundError(Exception):
    pass


class InvalidParameterError(Exception):
    def __init__(*args, **kwargs):
        pass


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

    def _parse_image(self, name, size, gallery='myGallery', image='mssql_2019_0_0', version='1.0.0'):
        templates = JsonTemplates()
        pw = self.credential.init_password

        image_id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/galleries/%s/images/%s/versions/%s' \
            %( self.credential.subscription_id, self.credential.resource_group, gallery, image, version )
        
        network_id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s' \
            %( self.credential.subscription_id, self.credential.resource_group, name )

        osProfile = {'adminUsername': 'dbaas', 'computerName': name, 'adminPassword': pw}

        for file in templates.list_files(version):
            file_name = file.name.split('.json')[0]
            if file_name == 'sql':
                sql_dict = templates.load_json(file.as_posix())
                sql_dict['properties']['hardwareProfile']['vmSize'] = size
                sql_dict['properties']['storageProfile']['imageReference']['id'] = image_id
                sql_dict['properties']['storageProfile']['osDisk']['name'] = name
                sql_dict['properties']['osProfile'] = osProfile
                sql_dict['properties']['networkProfile']['networkInterfaces'][0]['id'] = network_id
        return sql_dict

    def offering_to(self, cpu, memory, api_version='2020-12-01'):

        base_url = self.credential.endpoint
        action = "subscriptions/%s/providers/Microsoft.Compute/locations/%s/vmSizes?api-version=%s" \
            %(self.credential.subscription_id, self.credential.region, api_version)

        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("GET", action, headers=header)
        resp = self.azClient.connection.getresponse()

        if resp.status_code == 200:
            offerings = resp.json()['value']

            for offering in offerings:
                if offering.get('memoryInMB') == memory and offering.get('numberOfCores') == cpu:
                    return offering

        raise OfferingNotFoundError(
            "Offering with {} cpu and {} of memory not found.".format(cpu, memory)
        )

    def _parse_nic(self, name, vnet, subnet):
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
        nic = self._parse_nic(name, vnet, subnet)

        payload = json.dumps(nic)
        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("PUT", action, body=payload, headers=header)
        resp = self.azClient.connection.getresponse()
        
        if resp.status_code == 200 or resp.status_code == 201:
            return resp
        
        return None

    def get_network(self, api_version='2020-07-01'):
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

    def deploy_vm(self, name, size, api_version='2020-12-01'):
        try:
            size_name = size['name']
            nic = self.create_nic(name)
            template = self._parse_image(name, size_name)
            
            if nic is not None:
                base_url = self.credential.endpoint
                action = 'subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s?api-version=%s' \
                    %(self.credential.subscription_id, self.credential.resource_group, name, api_version)

                payload = json.dumps(template)
                
                header = {}
                self.get_azure_connection()
                self.azClient.connect(base_url=base_url)
                self.azClient.add_default_headers(header)
                self.azClient.connection.request("PUT", action, body=payload, headers=header)
                resp = self.azClient.connection.getresponse()
            
        except DeployVmError as err:
            raise DeployVmError("OperationNotAllowed: %s" % (err))

        finally:
            return resp

    def _create_host(self, cpu, memory, name, *args, **kw):
        name = re.sub('[^A-Za-z0-9]+', '', str(name))
        if len(name) <= 15 and not name.isnumeric():
            name = name
        else:
            raise InvalidParameterError('InvalidParameterError: %s' % (name))

        vmSize = self.offering_to(int(cpu), int(memory))

        return self.deploy_vm(name, vmSize)

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

