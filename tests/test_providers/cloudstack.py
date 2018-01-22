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
                "zone1": {"networks": {'redis': ["net1", "net2"]}}
            },
            "offerings": {
                "1c1024m": "offering1",
                "2c2048m": "offering2",
            },
            "redis": {
                "template": "template-redis-1"
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
