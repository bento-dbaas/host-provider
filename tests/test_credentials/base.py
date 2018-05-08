from collections import OrderedDict
from unittest import TestCase
from unittest.mock import patch
from host_provider.settings import MONGODB_HOST, MONGODB_PORT, MONGODB_USER, \
    MONGODB_PWD
from host_provider.credentials.base import CredentialAdd, CredentialBase
from tests.test_credentials import CredentialAddFake, CredentialBaseFake, \
    FakeMongoDB


PROVIDER = "fake"
ENVIRONMENT = "dev"
ENGINE = "redis"
FAKE_CERT_PATH = "/path/to/certs/"
GROUP = "fake-group"


class TestBaseProvider(TestCase):

    def tearDown(self):
        FakeMongoDB.clear()

    def test_credential_add_not_implemented_methods(self):
        credential = CredentialAdd(PROVIDER, ENVIRONMENT, "")
        self.assertRaises(NotImplementedError, credential.is_valid)

    def test_base_content(self):
        credential_add = CredentialAddFake(
            PROVIDER, ENVIRONMENT, {"fake": "info"}
        )
        credential_add.save()
        __import__('ipdb').set_trace()
        credential = CredentialBaseFake(PROVIDER, ENVIRONMENT, ENGINE)
        self.assertIsNone(credential._content)
        self.assertEqual(credential.content, credential._content)
        self.assertIsNotNone(credential.content)

    def test_base_content_empty(self):
        credential = CredentialBaseFake(PROVIDER, ENVIRONMENT + "-new", ENGINE)
        self.assertIsNone(credential._content)
        self.assertRaises(NotImplementedError, credential.get_content)

    def test_after_before_create_methods(self):
        credential = CredentialBaseFake(PROVIDER, ENVIRONMENT, ENGINE)
        self.assertIsNone(credential.before_create_host(GROUP))
        self.assertIsNone(credential.after_create_host(GROUP))

    @patch('host_provider.credentials.base.MongoClient')
    def test_mongo_db_connection(self, mongo_client):
        credential = CredentialBase(PROVIDER, ENVIRONMENT, ENGINE)
        self.assertIsNotNone(credential.credential)
        mongo_client.assert_called_once_with(
            host=MONGODB_HOST, port=MONGODB_PORT,
            username=MONGODB_USER, password=MONGODB_PWD,
            document_class=OrderedDict
        )

    @patch('host_provider.credentials.base.CredentialAdd.credential')
    def test_delete(self, credential):
        env = "env"
        provider = "fake"
        CredentialAdd(provider, env, {}).delete()
        credential.delete_one.assert_called_once_with({
            "environment": env, "provider": provider
        })
