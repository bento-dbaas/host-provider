from unittest import TestCase, mock
from host_provider.main import app
from bson import json_util, ObjectId
import json


class TestRules(TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @mock.patch('host_provider.credentials.cloudstack.CredentialCloudStack.credential')  # noqa
    def test_get_all_credentials(self, mock_credential):
        mock_credential.find.return_value = [
            {'_id': ObjectId('1af05448560a70b7cead056d'),
                'provider': 'cloudstack'},
            {'_id': ObjectId('2af05448560a70b7cead0564'), 'provider': 'aws'},
                ]
        resp = self.app.get('/cloudstack/credentials')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(json.loads(resp.data.decode("utf-8"))), 2)

    @mock.patch('host_provider.credentials.cloudstack.CredentialCloudStack.credential')  # noqa
    def test_get_credential(self, mock_credential):
        mock_credential.find_one.return_value = {
            '_id': ObjectId('5af05448560a70b7cead056d'),
            'provider': 'cloudstack'
        }
        resp = self.app.get('/cloudstack/credential/5af05448560a70b7cead056d')

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(mock_credential.find_one.called)
        self.assertDictEqual(
            mock_credential.find_one.call_args[0][0],
            {'_id': ObjectId('5af05448560a70b7cead056d')}
        )

    @mock.patch('host_provider.credentials.cloudstack.CredentialCloudStack.credential')  # noqa
    def test_update_credential(self, mock_credential):
        mock_credential.update.return_value = {
            "nMatched": 1, "nUpserted": 0, "nModified": 1
        }
        resp = self.app.put(
            '/cloudstack/credential/5af05448560a70b7cead056d',
            data=json.dumps({'fake': 1}),
            content_type='application/json'
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(mock_credential.update.called)
        self.assertEqual(
            mock_credential.update.call_args[0][0],
            {'_id': ObjectId('5af05448560a70b7cead056d')}
        )
        self.assertDictEqual(
            mock_credential.update.call_args[0][1],
            {'fake': 1}
        )
