from unittest import TestCase
from unittest.mock import patch
from libcloud import security
from host_provider.providers.base import ProviderBase
from host_provider.providers import base
from tests.test_providers import FakeProvider


ENVIRONMENT = "dev"
ENGINE = "redis"
FAKE_CERT_PATH = "/path/to/certs/"


class TestBaseProvider(TestCase):

    def test_init_data(self):
        provider = ProviderBase(ENVIRONMENT, ENGINE)
        self.assertEqual(provider.environment, ENVIRONMENT)
        self.assertEqual(provider.engine, ENGINE)
        self.assertIsNone(provider._client)
        self.assertIsNone(provider._credential)

    def test_not_implemented_methods(self):
        provider = ProviderBase(ENVIRONMENT, ENGINE)
        self.assertRaises(NotImplementedError, provider.build_credential)
        self.assertRaises(NotImplementedError, provider.build_client)
        self.assertRaises(NotImplementedError, provider.get_provider)
        self.assertRaises(NotImplementedError, provider.create_host, 0, 0, "")

    def test_build_client(self):
        provider = FakeProvider(ENVIRONMENT, ENGINE)
        self.assertIsNone(provider._client)
        self.assertEqual(provider.client, provider.build_client())
        self.assertIsNotNone(provider._client)

    def test_build_credential(self):
        provider = FakeProvider(ENVIRONMENT, ENGINE)
        self.assertIsNone(provider._credential)
        self.assertEqual(provider.credential, provider.build_credential())
        self.assertIsNotNone(provider._credential)

    @patch("host_provider.providers.base.get_driver", return_value="Fake")
    def test_get_driver(self, get_driver):
        provider = FakeProvider(ENVIRONMENT, ENGINE)
        self.assertEqual(provider.get_driver(), "Fake")

    def test_security_cert_path(self):
        base.LIBCLOUD_CA_CERTS_PATH = FAKE_CERT_PATH
        self.assertNotEqual(security.CA_CERTS_PATH, FAKE_CERT_PATH)
        ProviderBase(ENVIRONMENT, ENGINE)
        self.assertEqual(security.CA_CERTS_PATH, FAKE_CERT_PATH)

    def test_security_cert_path_empty(self):
        base.LIBCLOUD_CA_CERTS_PATH = ""
        self.assertNotEqual(security.CA_CERTS_PATH, "")
        ProviderBase(ENVIRONMENT, ENGINE)
        self.assertIsNone(security.CA_CERTS_PATH, None)


