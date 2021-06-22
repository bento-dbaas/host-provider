from unittest.mock import patch, MagicMock, PropertyMock

from peewee import DoesNotExist
from googleapiclient.errors import HttpError

from .base import GCPBaseTestCase
from .fakes.gce import (FAKE_GCE_CREDENTIAL,
                        FAKE_STATIC_IP,
                        FAKE_GOOGLE_RESPONSE_STATIC_IP)
from .fakes.base import FAKE_ENGINE, FAKE_HOST, FAKE_TAGS
from host_provider.providers.gce import StaticIPNotFoundError, WrongStatusError


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class StartVMTestCase(GCPBaseTestCase):

    def test_call_client_params(self, client_mock, wait_op):
        start_mock = client_mock().instances().start
        self.provider.start(self.host)
        self.assertTrue(wait_op.called)
        self.assertTrue(start_mock.called)
        start_params = start_mock.call_args[1]
        self.assertEqual(start_params['project'], 'fake_project')
        self.assertEqual(start_params['instance'], 'fake_host_name')
        self.assertEqual(start_params['zone'], 'fake_host_zone')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class StopVMTestCase(GCPBaseTestCase):

    @patch('host_provider.models.Host.get',
           new=MagicMock(return_value=FAKE_HOST))
    def test_call_client_params(self, client_mock, wait_op):
        stop_mock = client_mock().instances().stop
        self.provider.stop('fake_identifier')

        self.assertTrue(wait_op.called)
        self.assertTrue(stop_mock.called)
        stop_params = stop_mock.call_args[1]
        self.assertEqual(stop_params['project'], 'fake_project')
        self.assertEqual(stop_params['instance'], 'fake_host_name')
        self.assertEqual(stop_params['zone'], 'fake_host_zone')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class StopVMEdgeCasesTestCase(GCPBaseTestCase):

    def test_host_not_found(self, client_mock, wait_op):
        with self.assertRaises(DoesNotExist):
            self.provider.stop('fake_identifier')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
@patch('host_provider.providers.gce.GceProvider.get_static_ip_by_name',
       new=MagicMock(return_value=FAKE_STATIC_IP))
@patch('host_provider.providers.gce.GceProvider.disk_image_link',
       new=PropertyMock(return_value='fake_disk_image_link'))
@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation',
       new=MagicMock(return_value={'status': 'READY'}))
@patch('host_provider.clients.team.TeamClient.make_tags',
       new=MagicMock(return_value={'cliente': 'x'}))
class CreateHostTestCase(GCPBaseTestCase):

    def test_static_ip_not_found(self, client_mock, wait_op):
        with self.assertRaises(StaticIPNotFoundError):
            self.provider._create_host(2, 1024, 'fake_name')

    def test_call_client_params(self, client_mock, wait_op):
        self.provider.credential._zone = 'fake_zone_1'
        insert_mock = client_mock().instances().insert
        self.provider._create_host(
            2, 1024, 'fake_name', static_ip_id='fake_static_ip_id'
        )

        self.assertTrue(wait_op.called)
        self.assertTrue(insert_mock.called)
        insert_params = insert_mock.call_args[1]
        self.assertEqual(insert_params['project'], 'fake_project')
        self.assertEqual(insert_params['zone'], 'fake_zone_1')
        self.assertTrue(isinstance(insert_params['body'], dict))
        self.assertEqual(insert_params['body']['name'], 'fake_name')
        self.assertEqual(
            insert_params['body']['machineType'],
            'zones/fake_zone_1/machineTypes/fake_offering_2c1024m'
        )
        self.assertEqual(
            (insert_params['body']['disks'][0]
             ['initializeParams']['sourceImage']),
            'fake_disk_image_link'
        )
        network_interface_config = (
            insert_params['body']['networkInterfaces'][0]
        )
        self.assertEqual(
            network_interface_config['subnetwork'], 'fake/sub/network'
        )
        self.assertEqual(
            network_interface_config['networkIP'], 'fake_address'
        )

    def test_create_host_with_specific_zone(self, client_mock, wait_op):
        self.provider.credential._zone = 'fake_zone_1'
        insert_mock = client_mock().instances().insert
        self.provider._create_host(
            2, 1024, 'fake_name',
            static_ip_id='fake_static_ip_id',
            zone='another_fake_zone'
        )
        self.assertTrue(insert_mock.called)
        insert_params = insert_mock.call_args[1]
        self.assertEqual(insert_params['zone'], 'another_fake_zone')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.IP')
@patch('host_provider.providers.gce.GceProvider.get_internal_static_ip',
       new=MagicMock(return_value=FAKE_GOOGLE_RESPONSE_STATIC_IP))
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class CreateStaticIPTestCase(GCPBaseTestCase):

    def test_call_client_params(self, client_mock, model_ip_mock, wait_op):
        insert_mock = client_mock().addresses().insert
        self.provider.create_static_ip('fake_group', 'fake_ip_name')
        self.assertTrue(wait_op.called)
        self.assertTrue(insert_mock.called)
        insert_params = insert_mock.call_args[1]
        self.assertEqual(insert_params['project'], 'fake_project')
        self.assertEqual(insert_params['region'], 'fake_region')
        self.assertDictEqual(
            insert_params['body'],
            {
                'subnetwork': 'fake/sub/network',
                'addressType': 'INTERNAL',
                'name': 'fake_ip_name'
            }
        )

    def test_model_ip_called(self, client_mock,
                             model_ip_mock, wait_op):
        self.provider.create_static_ip('fake_group', 'fake_ip_name')

        self.assertTrue(model_ip_mock.called)
        model_ip_params = model_ip_mock.call_args[1]
        self.assertEqual(model_ip_params['name'], 'fake_ip_name')
        self.assertEqual(model_ip_params['group'], 'fake_group')
        self.assertEqual(model_ip_params['address'], 'fake_address')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class DestroyStaticIPTestCase(GCPBaseTestCase):

    def test_call_client_params(self, client_mock, wait_op):
        delete_mock = client_mock().addresses().delete
        self.provider.destroy_static_ip('fake_ip_name')
        self.assertTrue(wait_op.called)
        self.assertTrue(delete_mock.called)
        delete_params = delete_mock.call_args[1]
        self.assertEqual(delete_params['project'], 'fake_project')
        self.assertEqual(delete_params['region'], 'fake_region')
        self.assertEqual(delete_params['address'], 'fake_ip_name')


@patch('dbaas_base_provider.baseProvider.BaseProvider.wait_operation')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class DestroyVMTestCase(GCPBaseTestCase):

    def test_host_not_found(self, client_mock, wait_op):
        with self.assertRaises(DoesNotExist):
            self.provider._destroy('fake_identifier')

    @patch('host_provider.models.Host.get',
           new=MagicMock(return_value=FAKE_HOST))
    def test_call_client_params(self, client_mock, wait_op):
        delete_mock = client_mock().instances().delete
        self.provider._destroy('fake_identifier')
        self.assertTrue(wait_op.called)
        self.assertTrue(delete_mock.called)
        delete_params = delete_mock.call_args[1]
        self.assertEqual(delete_params['project'], 'fake_project')
        self.assertEqual(delete_params['instance'], 'fake_host_name')
        self.assertEqual(delete_params['zone'], 'fake_host_zone')


@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class ResizeTestCase(GCPBaseTestCase):

    def test_call_client_params(self, client_mock):
        self.provider.credential._zone = 'fake_zone_1'
        set_machine_type_mock = client_mock().instances().setMachineType
        self.provider.resize(FAKE_HOST, 2, 4096)

        self.assertTrue(set_machine_type_mock.called)
        set_machine_type_params = set_machine_type_mock.call_args[1]
        self.assertEqual(set_machine_type_params['project'], 'fake_project')
        self.assertEqual(set_machine_type_params['zone'], 'fake_host_zone')
        self.assertTrue(isinstance(set_machine_type_params['body'], dict))
        self.assertEqual(
            set_machine_type_params['body']['machineType'],
            'zones/fake_host_zone/machineTypes/fake_offering_2c4096m'
        )


@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class GetInstanceTestCase(GCPBaseTestCase):

    def test_call_params(self, client_mock):
        get_instance_mock = client_mock().instances().get
        self.provider.get_instance('fake_instance_name', 'fake_zone')

        self.assertTrue(get_instance_mock.called)
        get_instance_params = get_instance_mock.call_args[1]
        self.assertEqual(get_instance_params['project'], 'fake_project')
        self.assertEqual(get_instance_params['zone'], 'fake_zone')
        self.assertEqual(get_instance_params['instance'], 'fake_instance_name')

    def test_execute_request_when_configured_to(self, client_mock):
        get_mock = client_mock().instances().get
        execute_mock = get_mock().execute
        self.provider.get_instance(
            'fake_instance_name',
            'fake_zone',
            execute_request=True
        )

        self.assertTrue(get_mock.called)
        self.assertTrue(execute_mock.called)

    def test_not_execute_request_when_configured_to(self, client_mock):
        get_mock = client_mock().instances().get
        execute_mock = get_mock().execute
        self.provider.get_instance(
            'fake_instance_name',
            'fake_zone',
            execute_request=False
        )

        self.assertTrue(get_mock.called)
        self.assertFalse(execute_mock.called)


@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class GetInternalStaticIPTestCase(GCPBaseTestCase):

    def test_call_params(self, client_mock):
        get_static_ip_mock = client_mock().addresses().get
        self.provider.get_internal_static_ip('fake_ip_name')

        self.assertTrue(get_static_ip_mock.called)
        get_static_ip_params = get_static_ip_mock.call_args[1]
        self.assertEqual(get_static_ip_params['project'], 'fake_project')
        self.assertEqual(get_static_ip_params['region'], 'fake_region')
        self.assertEqual(
            get_static_ip_params['address'], 'fake_ip_name'
        )

    def test_execute_request_when_configured_to(self, client_mock):
        get_mock = client_mock().addresses().get
        execute_mock = get_mock().execute
        self.provider.get_internal_static_ip(
            'fake_ip_name',
            execute_request=True
        )

        self.assertTrue(get_mock.called)
        self.assertTrue(execute_mock.called)

    def test_not_execute_request_when_configured_to(self, client_mock):
        get_mock = client_mock().addresses().get
        execute_mock = get_mock().execute
        self.provider.get_internal_static_ip(
            'fake_ip_name',
            execute_request=False
        )

        self.assertTrue(get_mock.called)
        self.assertFalse(execute_mock.called)


# @patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class WaitStatusOfTestCase(GCPBaseTestCase):

    def setUp(self):
        super(WaitStatusOfTestCase, self).setUp()
        self.provider.WAIT_ATTEMPTS = 3
        self.provider.WAIT_TIME = 0
        self.fake_request = MagicMock()
        self.fake_request.execute.return_value = {
            'status': 'READY',
            'age': 99,
            'color': 'black'
        }


@patch('host_provider.providers.gce.GceProvider._destroy')
@patch('host_provider.providers.gce.GceProvider._create_host')
@patch('host_provider.providers.gce.GceProvider.get_instance')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
@patch('host_provider.providers.gce.GceProvider.get_static_ip_by_host_id',
       new=MagicMock(return_value=FAKE_STATIC_IP))
class RestoreTestCase(GCPBaseTestCase):

    def setUp(self):
        super(RestoreTestCase, self).setUp()
        fake_resp = type('FakeResp', (object,), {'status': 404})
        fake_content = MagicMock(spec=bytes)
        self.fake_http_error = HttpError(fake_resp, fake_content)

    def test_call_destroy_when_not_recreating(self, client_mock,
                                              get_instance_mock,
                                              create_host_mock,
                                              destroy_host_mock):

        get_instance_mock.side_effect = self.fake_http_error
        self.provider.restore(FAKE_HOST, FAKE_ENGINE)

        self.assertTrue(destroy_host_mock.called)

    def test_dont_call_destroy_when_recreating(self, client_mock,
                                               get_instance_mock,
                                               create_host_mock,
                                               destroy_host_mock):

        get_instance_mock.side_effect = self.fake_http_error
        FAKE_HOST.recreating = True
        self.provider.restore(FAKE_HOST, FAKE_ENGINE)

        self.assertFalse(destroy_host_mock.called)
