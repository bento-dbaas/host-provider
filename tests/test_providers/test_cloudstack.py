from unittest import TestCase
from copy import deepcopy
from unittest.mock import Mock, patch, MagicMock, PropertyMock

from libcloud.compute.types import Provider
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver
from requests.exceptions import ConnectionError

from host_provider.providers.cloudstack import CloudStackProvider
from host_provider.credentials.cloudstack import CredentialAddCloudStack
from .fakes.cloudstack import (FAKE_CREDENTIAL, FAKE_CS_NODE,
                               FAKE_EX_LIST_NETWORKS,
                               FAKE_HOST)
from .base import CloudStackBaseTestCase


ENVIRONMENT = "dev"
ENGINE = "redis"


@patch('libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.ex_get_node')
class CsHostDataTestCase(CloudStackBaseTestCase):
    def test_get_node_called(self, get_node_mock):
        self.provider.get_cs_node(self.host)
        self.assertTrue(get_node_mock.called)

    @patch('host_provider.credentials.cloudstack.CredentialCloudStack.project',
           new=PropertyMock(return_value='fake_project_id'))
    def test_get_node_params(self, get_node_mock):
        self.provider.get_cs_node(self.host)
        args = get_node_mock.call_args[0]
        self.assertEqual('fake_identifier', args[0])
        self.assertEqual(self.provider.BasicInfo('fake_project_id'), args[1])
        self.assertEqual('fake_project_id', args[1].id)


@patch(('libcloud.compute.drivers.cloudstack.CloudStackNodeDriver'
        '.ex_list_networks'), new=MagicMock(
            return_value=FAKE_EX_LIST_NETWORKS))
class GetNetworkFromTestCase(CloudStackBaseTestCase):
    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'), new=MagicMock(return_value=FAKE_CS_NODE))
    def test_find_network_b(self):
        network = self.provider.get_network_from(self.host)
        self.assertEqual(
            'fake_network_domain_b.globoi.com',
            network.extra['network_domain']
        )

    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'))
    def test_not_found(self, cs_host_mock):
        cs_node = deepcopy(FAKE_CS_NODE)
        cs_node.extra['nics:'][0].update({'networkid': 'fake_not_found'})
        cs_host_mock.return_value = cs_node
        network = self.provider.get_network_from(self.host)
        self.assertEqual(None, network)


class FqdnTestCase(CloudStackBaseTestCase):
    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'))
    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_network_from'))
    def test_get_cs_node_called(self, network_from_mock, cs_node_mock):
        self.provider.fqdn(MagicMock())
        self.assertTrue(network_from_mock.called)
        self.assertTrue(cs_node_mock.called)

    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'), new=MagicMock(return_value=FAKE_CS_NODE))
    @patch(('libcloud.compute.drivers.cloudstack.CloudStackNodeDriver'
            '.ex_list_networks'), new=MagicMock(
                return_value=FAKE_EX_LIST_NETWORKS))
    def test_fqdn(self):
        fqdn = self.provider.fqdn(self.host)
        self.assertEqual(
            'fake_node_name.fake_network_domain_b.globoi.com', fqdn
        )

    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'), return_value=FAKE_CS_NODE)
    @patch(('libcloud.compute.drivers.cloudstack.CloudStackNodeDriver'
            '.ex_list_networks'), new=MagicMock(
                return_value=FAKE_EX_LIST_NETWORKS))
    def test_fqdn_network_not_found(self, get_node_mock):
        cs_node = deepcopy(FAKE_CS_NODE)
        cs_node.extra['nics:'][0].update({'networkid': 'fake_not_found'})
        get_node_mock.return_value = cs_node
        fqdn = self.provider.fqdn(self.host)
        self.assertEqual('', fqdn)

    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '.get_cs_node'), return_value=FAKE_CS_NODE)
    @patch(('libcloud.compute.drivers.cloudstack.CloudStackNodeDriver'
            '.ex_list_networks'), new=MagicMock(
                return_value=FAKE_EX_LIST_NETWORKS))
    def test_fqdn_empty_when_connection_error(self, get_node_mock):
        get_node_mock.side_effect = ConnectionError
        try:
            fqdn = self.provider.fqdn(self.host)
        except ConnectionError:
            self.fail(
                ("provider.fqdn() raised ConnectionError unexpectedly!")
            )
        self.assertEqual('', fqdn)


class TestBaseCredential(TestCase):

    def setUp(self):
        self.provider = CloudStackProvider(ENVIRONMENT, ENGINE)

    def test_provider_name(self):
        self.assertEqual(Provider.CLOUDSTACK, self.provider.get_provider())

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddCloudStack
        )

    def test_validate_credential(self):
        invalid_content = deepcopy(FAKE_CREDENTIAL)
        invalid_content.update({'mimOfZones': "3"})

        success, error = self.provider.credential_add(invalid_content)

        self.assertFalse(success)
        self.assertEqual(error, "Must be 3 active zones at least")

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    def test_build_client(self, content):
        self.build_credential_content(content)
        self.assertEqual(
            type(self.provider.build_client()), CloudStackNodeDriver
        )

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.zone'
    )
    @patch(('host_provider.credentials.cloudstack.CredentialCloudStack'
            '.collection_last'))
    def test_create_host(self, collection_last, zone, create_node,
                         credential_content):
        self.create_host_tests(
            collection_last, create_node, credential_content, zone
        )

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.zone'
    )
    @patch(('host_provider.credentials.cloudstack.CredentialCloudStack'
           '.collection_last'))
    def test_create_host_with_project(
        self, collection_last, zone, create_node, credential_content
    ):
        self.create_host_tests(
            collection_last, create_node, credential_content, zone,
            projectid="myprojectid"
        )

    def build_credential_content(self, content, **kwargs):
        values = deepcopy(FAKE_CREDENTIAL)
        values.update(kwargs)
        content.return_value = values

    def create_host_tests(
        self, collection_last, create_node, content, zone, **kwargs
    ):
        collection_last.find_one.return_value = []
        self.build_credential_content(content, **kwargs)

        zone.__get__ = Mock(return_value="zone1")

        name = "infra-01-123456"
        group = "infra123456"
        self.provider.create_host(1, 1024, name, group, zone='zone1')

        project = content.return_value.get("projectid", None)
        if project:
            project = self.provider.BasicInfo(id=project)

        networks = [
            self.provider.BasicInfo("net1"), self.provider.BasicInfo("net2")
        ]

        create_node.assert_called_once_with(
            name=name,
            size=self.provider.BasicInfo("offering1"),
            image=self.provider.BasicInfo("template-redis-1"),
            location=self.provider.BasicInfo("zone1"),
            networks=networks, project=project
        )

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.ex_start'
    )
    def test_start(self, ex_start, content):
        self.build_credential_content(content)
        self.provider.start(FAKE_HOST)
        ex_start.assert_called_once_with(
            self.provider.BasicInfo('fake_identifier')
        )

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.ex_stop'
    )
    def test_stop(self, ex_stop, content):
        self.build_credential_content(content)
        identifier = "fake-uuid-cloud-stac"
        self.provider.stop(identifier)
        ex_stop.assert_called_once_with(self.provider.BasicInfo(identifier))

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.destroy_node'
    )
    def test_destroy_cloud_stack(self, destroy_node, content):
        self.build_credential_content(content)
        identifier = "fake-uuid-cloud-stac"
        self.provider._destroy(identifier)
        destroy_node.assert_called_once_with(
            self.provider.BasicInfo(identifier)
        )

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(('host_provider.providers.cloudstack.CredentialCloudStack'
           '.collection_last'))
    def test_all_nodes_deleted(self, collection_last, content):
        self.build_credential_content(content)
        group = "fake123456"
        self.provider._all_node_destroyed(group)
        collection_last.delete_one.assert_called_once_with({
            "environment": self.provider.credential.environment, "group": group
        })

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'host_provider.providers.cloudstack.CloudStackProvider._destroy'
    )
    @patch(('host_provider.providers.cloudstack.CloudStackProvider'
           '._all_node_destroyed'))
    @patch(
        'host_provider.providers.base.Host'
    )
    def test_destroy(self, host, all_node_destroyed, destroy, content):
        self.build_credential_content(content)
        host.filter.return_value = [1]

        group = "fake123456"
        identifier = "fake-uuid-cloud-stac"
        self.provider.destroy(group, identifier)
        host.filter.assert_called_once_with(group=group)
        destroy.assert_called_once_with(identifier)
        all_node_destroyed.assert_called_once_with(group)
