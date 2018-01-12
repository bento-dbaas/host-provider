from unittest import TestCase
from unittest.mock import patch
from libcloud import security
from host_provider.providers.base import ProviderBase
from host_provider.providers import base
from tests.test_providers import FakeProvider
from tests.test_credentials import FakeMongoDB


ENVIRONMENT = "dev"
ENGINE = "redis"
FAKE_CERT_PATH = "/path/to/certs/"


class TestBaseProvider(TestCase):

    def tearDown(self):
        FakeMongoDB.clear()

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
        self.assertRaises(NotImplementedError, provider.get_credential_add)

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

    def test_add_credential_success(self):
        self._add_credential({"fake": "info"}, True)

    def test_add_credential_invalid(self):
        self._add_credential({"wrong": "info"}, False)

    def test_add_credential_database_error(self):
        self._add_credential({"raise": "info", "fake": "info"}, False)

    def _add_credential(self, content, success_expected):
        provider = FakeProvider(ENVIRONMENT, ENGINE)

        full_data = {
            "environment": ENVIRONMENT,
            "provider": provider.get_provider()
        }
        full_data.update(content)
        self.assertNotIn(full_data, FakeMongoDB.metadata)

        latest = FakeMongoDB.ids[-1]
        success, inserted_id = provider.credential_add(content)

        if success_expected:
            self.assertTrue(success)
            self.assertIn(full_data, FakeMongoDB.metadata)
            self.assertEqual(FakeMongoDB.ids[-1], inserted_id)
        else:
            self.assertFalse(success)
            self.assertIsInstance(inserted_id, str)
            self.assertNotIn(full_data, FakeMongoDB.metadata)
            self.assertEqual(FakeMongoDB.ids[-1], latest)

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
