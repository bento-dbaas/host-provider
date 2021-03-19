from unittest import TestCase
from mock import MagicMock, patch, PropertyMock
from libcloud.compute.types import Provider
from host_provider.providers import AzureProvider
from host_provider.credentials.azure import CredentialAddAzure

ENVIRONMENT = "dev"
ENGINE = "mssql"


@patch(
    'host_provider.providers.azure.HOST_ORIGIN_TAG',
    new=str('dbaas')
)
class AzureTestCase(TestCase):

    def setUp(self):
        self.provider = AzureProvider(ENVIRONMENT, ENGINE)
        self.provider.wait_state = MagicMock()

    def test_provider_name(self):
        self.assertEqual(Provider.AZURE_ARM, self.provider.get_provider())

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddAzure
        )
