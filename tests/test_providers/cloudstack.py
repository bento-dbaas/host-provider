from unittest import TestCase
from unittest.mock import Mock, patch
from libcloud.compute.types import Provider
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver
from host_provider.providers.cloudstack import CloudStackProvider
from host_provider.credentials.cloudstack import CredentialAddCloudStack


ENVIRONMENT = "dev"
ENGINE = "redis"


class TestBaseCredential(TestCase):

    def setUp(self):
        self.provider = CloudStackProvider(ENVIRONMENT, ENGINE)

    def test_provider_name(self):
        self.assertEqual(Provider.CLOUDSTACK, self.provider.get_provider())

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddCloudStack
        )

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
    @patch(
        'host_provider.credentials.cloudstack.CredentialCloudStack.collection_last'
    )
    def test_create_host(self, collection_last, zone, create_node, credential_content):
        self.create_host_tests(collection_last, create_node, credential_content, zone)

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'libcloud.compute.drivers.cloudstack.CloudStackNodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.zone'
    )
    @patch(
        'host_provider.credentials.cloudstack.CredentialCloudStack.collection_last'
    )
    def test_create_host_with_project(
        self, collection_last, zone, create_node, credential_content
    ):
        self.create_host_tests(
            collection_last, create_node, credential_content, zone,
            projectid="myprojectid"
        )

    def build_credential_content(self, content, **kwargs):
        values = {
            "api_key": "Fake-123",
            "secret_key": "Fake-456",
            "endpoint": "http://cloudstack.internal.com/client/api",
            "secure": False,
            "projectid": "myprojectid",
            "zones": {
                "zone1": {"networks": {'redis': [
                    {"networkId": "net1", "name": "net_name1"},
                    {"networkId": "net2", "name": "net_name2"}]
                }}
            },
            "offerings": {
                "1c1024m": {"id": "offering1", "name": "offering_name1"},
                "2c2048m": {"id": "offering2", "name": "offering_name2"}
            },
            "templates": {
                "redis": "template-redis-1"
            }
        }
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
        self.provider.create_host(1, 1024, name, group)

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
        identifier = "fake-uuid-cloud-stac"
        self.provider.start(identifier)
        ex_start.assert_called_once_with(self.provider.BasicInfo(identifier))

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
    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.collection_last'
    )
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
    @patch(
        'host_provider.providers.cloudstack.CloudStackProvider._all_node_destroyed'
    )
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
