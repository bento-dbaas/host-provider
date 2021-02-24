from unittest.mock import patch, MagicMock

from .base import GCPBaseTestCase
from .fakes.gce import FAKE_HOST, FAKE_GCE_CREDENTIAL


@patch('host_provider.providers.gce.GceProvider.wait_status_of_instance')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class StartVMTestCase(GCPBaseTestCase):

    def test_call_client_params(self, client_mock, wait_status_mock):
        start_mock = client_mock().instances().start
        self.provider.start(self.host)

        self.assertTrue(start_mock.called)
        start_params = start_mock.call_args[1]
        self.assertEqual(start_params['project'], 'fake_project')
        self.assertEqual(start_params['instance'], 'fake_host_name')
        self.assertEqual(start_params['zone'], 'fake_zone')

    def test_wait_status(self, client_mock, wait_status_mock):
        self.provider.start(self.host)

        self.assertTrue(wait_status_mock.called)
        wait_status_params = wait_status_mock.call_args
        self.assertEqual(wait_status_params[0][0], 'fake_host_name')
        self.assertEqual(wait_status_params[1]['status'], 'RUNNING')


@patch('host_provider.providers.gce.GceProvider.wait_status_of_instance')
@patch('host_provider.providers.gce.GceProvider.build_client')
@patch('host_provider.providers.gce.CredentialGce.get_content',
       new=MagicMock(return_value=FAKE_GCE_CREDENTIAL))
class StopVMTestCase(GCPBaseTestCase):

    @patch('host_provider.models.Host.get',
           new=MagicMock(return_value=FAKE_HOST))
    def test_call_client_params(self, client_mock, wait_status_mock):
        stop_mock = client_mock().instances().stop
        self.provider.stop(self.host)

        self.assertTrue(stop_mock.called)
        stop_params = stop_mock.call_args[1]
        self.assertEqual(stop_params['project'], 'fake_project')
        self.assertEqual(stop_params['instance'], 'fake_host_name')
        self.assertEqual(stop_params['zone'], 'fake_zone')

    @patch('host_provider.models.Host.get',
           new=MagicMock(return_value=FAKE_HOST))
    def test_wait_status(self, client_mock, wait_status_mock):
        self.provider.stop(self.host)

        self.assertTrue(wait_status_mock.called)
        wait_status_params = wait_status_mock.call_args
        self.assertEqual(wait_status_params[0][0], 'fake_host_name')
        self.assertEqual(wait_status_params[1]['status'], 'TERMINATED')
