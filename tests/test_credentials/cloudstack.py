from unittest import TestCase
from unittest.mock import Mock, patch
from host_provider.credentials.cloudstack import CredentialCloudStack, \
    CredentialAddCloudStack
from host_provider.providers.cloudstack import CloudStackProvider
from tests.test_credentials.base import FakeMongoDB


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
        self.fake_mongo = FakeMongoDB()

    def tearDown(self):
        self.fake_mongo.clear()

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

    def test_zone(self):
        self.credential._zone = "fake_zone"
        self.assertEqual(self.credential.zone, self.credential._zone)

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.collection_last'
    )
    def test_remove_last_used_for(self, collection_last):
        self.credential.remove_last_used_for("fake_group")
        collection_last.delete_one.assert_called_once_with({
            "environment": self.credential.environment, "group": "fake_group"
        })

    def test_collection_last(self):
        self.credential._db = {"cloudstack_zones_last": "mocked_test"}
        self.assertEqual(self.credential.collection_last, "mocked_test")

    def _force_content(self):
        self.credential._content = {
            "zones": {
                "first": [1, 2],
                "second": [3, 4],
                "third": [5, 6],
            }
        }

    def test_get_next_zone_from(self):
        self._force_content()
        self.assertEqual(self.credential.get_next_zone_from("first"), "second")
        self.assertEqual(self.credential.get_next_zone_from("second"), "third")
        self.assertEqual(self.credential.get_next_zone_from("third"), "first")

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.collection_last'
    )
    def test_get_zone_environment(self, last_collection):
        self._force_content()
        self.fake_mongo.metadata.append({
            "latestUsed": True,
            "environment": self.credential.environment,
            "zone": "second"
        })
        last_collection.find_one = self.fake_mongo.find_one
        self.assertEqual(self.credential._get_zone("new_group"), "third")

    @patch(
        'host_provider.providers.cloudstack.CredentialCloudStack.collection_last'
    )
    def test_get_zone_infra(self, last_collection):
        self._force_content()
        self.fake_mongo.metadata.append({
            "group": "fake_group",
            "environment": self.credential.environment,
            "zone": "first"
        })
        last_collection.find_one = self.fake_mongo.find_one
        self.assertEqual(self.credential._get_zone("fake_group"), "second")
