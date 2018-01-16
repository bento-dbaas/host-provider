from unittest import TestCase
from unittest.mock import Mock, patch
from host_provider.credentials.cloudstack import CredentialCloudStack, \
    CredentialAddCloudStack
from host_provider.providers.cloudstack import CloudStackProvider


ENVIRONMENT = "dev"
ENGINE = "redis"


class TestCloudStackProvider(TestCase):

    def setUp(self):
        self.credential = CredentialCloudStack(
            CloudStackProvider.get_provider(), ENVIRONMENT, ENGINE
        )
        self.credential_add = CredentialAddCloudStack(
            CloudStackProvider.get_provider(), ENVIRONMENT, ENGINE
        )

    def test_add_is_valid(self):
        success, error = self.credential_add.is_valid()
        self.assertTrue(success)
        self.assertEqual(error, "")

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.get_content'
    )
    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.zone'
    )
    def test_error_no_network(self, zone, content):
        content.return_value = {"zones": {"zone1": {}}}
        zone.__get__ = Mock(return_value="zone1")

        def call_networks():
            _ = self.credential.networks

        self.assertRaises(NotImplementedError, call_networks)
