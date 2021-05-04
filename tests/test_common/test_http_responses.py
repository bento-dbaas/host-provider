from unittest import TestCase
import requests
import requests_mock
from host_provider.common.http import Connection, JsonResponse, ProviderConnection, ResponseError


class ResponseClassesTests(TestCase):
    def setUp(self):
        self.mock_connection = ProviderConnection(host='mock.com', port=80)

    def test_JsonResponse_class_success(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text='{"foo": "bar"}')
            response_obj = requests.get('mock://test.com/')
            response = JsonResponse(response=response_obj,
                                    connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, {'foo': 'bar'})

    def test_JsonResponse_class_malformed_response(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text='{"foo": "bar"')
            response_obj = requests.get('mock://test.com/')
            try:
                JsonResponse(response=response_obj,
                             connection=self.mock_connection)
            except ResponseError:
                pass
            else:
                self.fail('Exception was not thrown')

    def test_JsonResponse_class_zero_length_body_strip(self):
        with requests_mock.mock() as m:
            m.register_uri('GET', 'mock://test.com/', text=' ')
            response_obj = requests.get('mock://test.com/')
            response = JsonResponse(response=response_obj,
                                    connection=self.mock_connection)

        parsed = response.parse_body()
        self.assertEqual(parsed, '')