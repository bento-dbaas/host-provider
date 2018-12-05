from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock
from libcloud.compute.types import Provider
from libcloud.compute.drivers.ec2 import EC2NodeDriver
from host_provider.providers.aws import AWSProvider, OfferingNotFoundError
from host_provider.credentials.aws import CredentialAddAWS
from .fakes.ec2 import LIST_SIZES, FAKE_TAGS, FAKE_CREDENTIAL


ENVIRONMENT = "dev"
ENGINE = "redis"


@patch(
    'host_provider.providers.aws.HOST_ORIGIN_TAG',
    new=str('dbaas')
)
class TestCredentialAWS(TestCase):

    def setUp(self):
        self.provider = AWSProvider(ENVIRONMENT, ENGINE)
        self.provider.wait_state = MagicMock()

    def test_provider_name(self):
        self.assertEqual(Provider.EC2, self.provider.get_provider())

    def test_get_credential_add(self):
        self.assertEqual(
            self.provider.get_credential_add(), CredentialAddAWS
        )

    def test_validate_credential(self):
        invalid_content = deepcopy(FAKE_CREDENTIAL)
        invalid_content.update({'mimOfSubnets': "3"})

        success, error = self.provider.credential_add(invalid_content)

        self.assertFalse(success)
        self.assertEqual(error, "Must be 3 active subnets at least")


    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    def test_build_client(self, content):
        self.build_credential_content(content)
        self.assertEqual(
            type(self.provider.build_client()), EC2NodeDriver
        )

    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.list_sizes',
        new=MagicMock(return_value=LIST_SIZES)
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.zone'
    )
    @patch(
        'host_provider.credentials.aws.CredentialAWS.collection_last'
    )
    @patch(
        'host_provider.providers.aws.TeamClient.API_URL',
        new=None
    )
    def test_create_host_without_environment_of_teams(
        self, collection_last, zone, create_node, credential_content
    ):

        self.create_host_tests(collection_last, create_node, credential_content, zone)

    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.list_sizes',
        new=MagicMock(return_value=LIST_SIZES)
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.zone'
    )
    @patch(
        'host_provider.credentials.aws.CredentialAWS.collection_last'
    )
    def test_create_host_without_teams(self, collection_last, zone, create_node, credential_content):
        self.create_host_tests(collection_last, create_node, credential_content, zone)

    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.list_sizes',
        new=MagicMock(return_value=LIST_SIZES)
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.create_node'
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.zone'
    )
    @patch(
        'host_provider.credentials.aws.CredentialAWS.collection_last'
    )
    @patch(
        'host_provider.providers.aws.TeamClient.make_tags',
        new=MagicMock(return_value=FAKE_TAGS)
    )
    def test_create_host_with_teams(self, collection_last, zone, create_node, credential_content):
        self.create_host_tests(collection_last, create_node, credential_content, zone, has_tags=True)

    def build_credential_content(self, content, **kwargs):
        values = deepcopy(FAKE_CREDENTIAL)
        values.update(kwargs)
        content.return_value = values

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content',
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.list_sizes',
        return_value=LIST_SIZES
    )
    def test_offering(self, sizes_mock, content):
        self.build_credential_content(content)
        result = self.provider.offering_to(cpu=1, memory=512)

        self.assertEqual(1, result.id)
        self.assertEqual(1, result.extra['cpu'])
        self.assertEqual(512, result.ram)

        result = self.provider.offering_to(cpu=2, memory=1024)

        self.assertEqual(3, result.id)
        self.assertEqual(2, result.extra['cpu'])
        self.assertEqual(1024, result.ram)

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content',
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.list_sizes',
        return_value=LIST_SIZES
    )
    def test_offering_not_found(self, sizes_mock, content):
        self.build_credential_content(content)
        with self.assertRaises(OfferingNotFoundError):
            result = self.provider.offering_to(cpu=99, memory=999)

    def create_host_tests(
        self, collection_last, create_node, content, zone, **kwargs
    ):
        collection_last.find_one.return_value = []
        self.build_credential_content(content, **kwargs)

        zone = "fake_subnet_id_2"

        name = "infra-01-123456"
        group = "infra123456"
        self.provider.create_host(1, 1024, name, group, zone)

        project = content.return_value.get("projectid", None)
        if project:
            project = self.provider.BasicInfo(id=project)

        networks = [
            self.provider.BasicInfo("net1"), self.provider.BasicInfo("net2")
        ]

        expected_tags = FAKE_TAGS if kwargs.get('has_tags') else {}
        expected_tags.update({
            'origin': 'dbaas',
            'infra_name': group,
            'engine': 'redis'
        })
        create_node.assert_called_once_with(
            name=name,
            image=self.provider.BasicInfo('fake_so_image_id'),
            ex_keyname='elesbom',
            size=LIST_SIZES[1],
            ex_security_group_ids=['fake_security_group_id'],
            ex_subnet=self.provider.BasicInfo('fake_subnet_id_2'),
            ex_metadata=expected_tags
        )

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver',
        #'libcloud.compute.drivers.ec2.EC2NodeDriver.ex_start_node',
    )
    def test_start(self, node_driver, content):
        self.build_credential_content(content)
        identifier = "fake-uuid-ec2-stac"
        self.provider.start(identifier)
        node_driver().ex_start_node.assert_called_once_with(self.provider.BasicInfo(identifier))

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.ex_stop_node',
    )
    def test_stop(self, ex_stop, content):
        self.build_credential_content(content)
        identifier = "fake-uuid-ec2-stac"
        self.provider.stop(identifier)
        ex_stop.assert_called_once_with(self.provider.BasicInfo(identifier))

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'libcloud.compute.drivers.ec2.EC2NodeDriver.destroy_node',
    )
    def test_destroy_aws(self, destroy_node, content):
        self.build_credential_content(content)
        identifier = "fake-uuid-cloud-stac"
        self.provider._destroy(identifier)
        destroy_node.assert_called_once_with(
            self.provider.BasicInfo(identifier)
        )

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'host_provider.providers.aws.CredentialAWS.collection_last'
    )
    def test_all_nodes_deleted(self, collection_last, content):
        self.build_credential_content(content)
        group = "fake123456"
        self.provider._all_node_destroyed(group)
        collection_last.delete_one.assert_called_once_with({
            "environment": self.provider.credential.environment, "group": group
        })

    @patch(
        'host_provider.providers.aws.CredentialAWS.get_content'
    )
    @patch(
        'host_provider.providers.aws.AWSProvider._destroy'
    )
    @patch(
        'host_provider.providers.aws.AWSProvider._all_node_destroyed'
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
