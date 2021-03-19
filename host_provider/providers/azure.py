from collections import namedtuple
from requests.status_codes import codes as response_created
import os
import json
import re
from collections import OrderedDict
from contextlib import suppress
from host_provider.credentials.azure import CredentialAddAzure, CredentialAzure
from host_provider.common.azure import AzureConnection
from host_provider.models import Host
from host_provider.providers import ProviderBase
from host_provider.settings import HOST_ORIGIN_TAG
from libcloud.compute.types import Provider
from host_provider.clients.team import TeamClient
from pathlib import Path


class OperationNotAllowed(Exception):
    pass


class DeployVmError(Exception):
    pass


class OfferingNotFoundError(Exception):
    pass


class InvalidParameterError(Exception):
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

        return az.conn_cls(self.credential.access_id,
                           self.credential.secret_key,
                           tenant_id=self.credential.tenant_id,
                           subscription_id=self.credential.subscription_id)

    def get_node(self, node_id):
        pass

    def _parse_image(self, name, size, gallery='myGallery', image='mssql_2019_0_0', version='1.0.0'):
        sql_dict = OrderedDict()
        templates = JsonTemplates()
        pw = self.credential.init_password
        region = self.credential.region

        image_id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/galleries/%s/images/%s/versions/%s' \
                   % (self.credential.subscription_id, self.credential.resource_group, gallery, image, version)

        network_id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s' \
                     % (self.credential.subscription_id, self.credential.resource_group, name)

        osProfile = {'adminUsername': 'dbaas', 'computerName': name, 'adminPassword': pw}

        try:
            for file in templates.list_files(version):
                file_name = file.name.split('.json')[0]
                if file_name == 'sql':
                    sql_dict = templates.load_json(file.as_posix())
                    sql_dict['properties']['hardwareProfile']['vmSize'] = size
                    sql_dict['properties']['storageProfile']['imageReference']['id'] = image_id
                    sql_dict['properties']['storageProfile']['osDisk']['name'] = name
                    sql_dict['properties']['osProfile'] = osProfile
                    sql_dict['properties']['networkProfile']['networkInterfaces'][0]['id'] = network_id
                    sql_dict['location'] = region
            return sql_dict
        except Exception as error:
            raise Exception("Template parse error: {}" % error)

    def offering_to(self, cpu, memory, api_version='2020-12-01'):

        base_url = self.credential.endpoint
        action = "subscriptions/%s/providers/Microsoft.Compute/locations/%s/vmSizes?api-version=%s" \
                 % (self.credential.subscription_id, self.credential.region, api_version)

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

    def _parse_nic(self, name, vnet, subnet, version='1.0.0'):
        nic_dict = OrderedDict()
        id = '/subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualNetworks/%s/subnets/%s' \
             % (self.credential.subscription_id, self.credential.resource_group, vnet, subnet)

        region = self.credential.region
        templates = JsonTemplates()
        try:
            for file in templates.list_files(version):
                file_name = file.name.split('.json')[0]
                if file_name == 'nic':
                    nic_dict = templates.load_json(file.as_posix())
                    config = nic_dict['properties']['ipConfigurations']
                    for nic in config:
                        nic['name'] = name
                        nic['properties']['subnet']['id'] = id
                    nic_dict['properties']['ipConfigurations'] = config
                    nic_dict['location'] = region
            return nic_dict
        except Exception as error:
            raise Exception("Template not found error")

    def create_nic(self, name, api_version='2020-07-01'):
        subnet = self.credential.get_next_zone_from(self.credential.subnets)
        vnet = self.credential.subnets.get(subnet)['name']
        base_url = self.credential.endpoint
        action = 'subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/networkInterfaces/%s?api-version=%s' \
                 % (self.credential.subscription_id, self.credential.resource_group, name, api_version)
        nic = self._parse_nic(name, vnet, subnet)

        payload = json.dumps(nic)
        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("PUT", action, body=payload, headers=header)
        resp = self.azClient.connection.getresponse()

        return resp

    def get_network(self, api_version='2020-07-01'):
        subnet = self.credential.get_next_zone_from(self.credential.subnets)
        vnet = self.credential.subnets.get(subnet)['name']
        base_url = self.credential.endpoint

        action = "subscriptions/%s/resourceGroups/%s/providers/Microsoft.Network/virtualNetworks/%s?api-version=%s" \
                 % (self.credential.subscription_id, self.credential.resource_group, vnet, api_version)

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
                "Network {} not found".format(vnet)
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

    def create_host_object(self, provider, payload, env, created_host_metadata, static_ip_id, **kw):
        nic = created_host_metadata.get('nic', '')
        vm = created_host_metadata.get('vm', '')

        configs = [conf for conf in nic['properties']['ipConfigurations']]
        primaryIPAddress = [i['properties']['privateIPAddress'] for i in configs][0]
        identifier = vm['properties']['vmId']

        address = primaryIPAddress
        host = Host(
            name=payload['name'], group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=identifier, address=address,
            zone=provider.credential._zone
        )
        host.save()

        return host

    def _list_vm(self, name, only_status=True, api_version='2020-12-01'):
        status_only = 'false' if not only_status else 'true'
        base_url = self.credential.endpoint

        action = "subscriptions/%s/providers/Microsoft.Compute/virtualMachines/?api-version=%s&statusOnly=%s" \
                 % (self.credential.subscription_id, api_version, status_only)

        header = {}
        self.get_azure_connection()
        self.azClient.connect(base_url=base_url)
        self.azClient.add_default_headers(header)
        self.azClient.connection.request("GET", action, headers=header)
        resp = self.azClient.connection.getresponse()

        return resp.json()

    def deploy_vm(self, name, size, api_version='2020-12-01'):
        response_metadata = OrderedDict()

        vms = self._list_vm(name).get('value', [])
        has_name = lambda _vms, name: [i for i in _vms if i.get('name', '') == name]

        if any(has_name(vms, name)):
            raise DeployVmError('Already exists: %s' % name)

        size_name = size['name']
        nic_metadata = self.create_nic(name)
        template = self._parse_image(name, size_name)

        if nic_metadata.status_code in [response_created.CREATED]:
            response_metadata['nic'] = nic_metadata.json()
            base_url = self.credential.endpoint
            action = 'subscriptions/%s/resourceGroups/%s/providers/Microsoft.Compute/virtualMachines/%s?api-version=%s' \
                     % (self.credential.subscription_id, self.credential.resource_group, name, api_version)

            payload = json.dumps(template)

            header = {}
            self.get_azure_connection()
            self.azClient.connect(base_url=base_url)
            self.azClient.add_default_headers(header)
            self.azClient.connection.request("PUT", action, body=payload, headers=header)
            vm_metadata = self.azClient.connection.getresponse()
            result = vm_metadata.json()

            error = 'error'
            for key, value in result.items():
                if error in key:
                    error = result.get(error)
                    with suppress(KeyError):
                        action = nic_metadata.request.url
                        header = {}
                        self.get_azure_connection()
                        self.azClient.connect(base_url=action)
                        self.azClient.add_default_headers(header)
                        self.azClient.connection.request('DELETE', action, headers=header)
                        resp = self.azClient.connection.getresponse()
                        if nic_metadata.status_code in [response_created.OK, response_created.ACCEPTED]:
                            response_metadata['nic'] = resp.json()

                    with suppress(ValueError):
                        code, message, target = [item for item in error.items()]
                        if 'OperationNotAllowed' in code:
                            raise OperationNotAllowed('OperationNotAllowed: code: %s, message: %s, target: %s' % (
                                code[1], message[1], target[1]))

            response_metadata['vm'] = result
            return response_metadata

        return None

    def _create_host(self, cpu, memory, name, *args, **kw):
        name = re.sub('[^A-Za-z0-9]+', '', str(name))
        if len(name) <= 15 and not name.isnumeric():
            name = name
        else:
            raise InvalidParameterError('InvalidParameterError: %s' % name)

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
