from unittest import TestCase
import requests
import requests_mock
from host_provider.common.http import Connection, JsonResponse, RawResponse, ProviderConnection, ResponseError


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

    def test_RawResponse_class_read_method(self):

        TEST_DATA = '1234abcd'

        conn = Connection(host='mock.com', port=80, secure=False)
        conn.connect()

        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'http://mock.com/raw_data', text=TEST_DATA,
                           headers={'test': 'value'})
            response = conn.request('/raw_data', raw=True)
        data = response.response.read()
        self.assertEqual(data, TEST_DATA)

        header_value = response.response.getheader('test')
        self.assertEqual(header_value, 'value')

        headers = response.response.getheaders()
        self.assertEqual(headers, [('test', 'value')])

        self.assertEqual(response.response.status, 200)