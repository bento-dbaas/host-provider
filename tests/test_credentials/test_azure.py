from unittest import TestCase

from host_provider.credentials.azure import CredentialAddAzure, CredentialAzure
from host_provider.providers.azure import AzureProvider
from uuid import uuid4 as UUID

ARM_CLIENT_ID = UUID().hex
ARM_CLIENT_SECRET = UUID().hex
SUBSCRIPTION_ID = UUID().hex
TENANT_ID = UUID().hex

ENVIRONMENT = "dev"
ENGINE = "mssql"


class TestAzureProvider(TestCase):
    def setUp(self):
        self.credential     = CredentialAzure(AzureProvider.get_provider(), ENVIRONMENT, ENGINE)
        self.credential_add = CredentialAddAzure(AzureProvider.get_provider(), ENVIRONMENT, ENGINE)

    def test_add_is_valid(self):
        success, error = self.credential_add.is_valid({})
        self.assertTrue(success)
        self.assertEqual(error, "")