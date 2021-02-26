import requests
import json
from urllib.parse import urlparse
from host_provider.common.azure import AzureClientApplication

try:
    from host_provider.settings import HTTP_AZURE_PROXY
except ImportError:
    pass

__all__ = [
    'BaseConnection',
    'Connection'
]

ALLOW_REDIRECTS = 1


class BaseConnection(object):
    session = None
    response_cls = Response

    def __init__(self):
        self.session = requests.Session()


class Connection(BaseConnection):
    response = None

    def __init__(self, host, port, secure=None, **kwargs):
        scheme = 'https' if secure is not None and secure else 'http'
        self.host = '{0}://{1}{2}'.format(
            'https' if port == 443 else scheme,
            host,
            ":{0}".format(port) if port not in (80, 443) else ""
        )

        BaseConnection.__init__()
        self.session.timeout = kwargs.get('timeout', 60)

    def request(self, method, url, body=None, headers=None, raw=False,
                stream=False):
        url = urlparse.urljoin(self.host, url)
        headers = self._normalize_headers(headers=headers)

        self.response = self.session.request(
            method=method.lower(),
            url=url,
            data=body,
            headers=headers,
            allow_redirects=ALLOW_REDIRECTS,
            stream=stream
        )

    def prepared_request(self, method, url, body=None,
                         headers=None, raw=False, stream=False):
        headers = self._normalize_headers(headers=headers)

        req = requests.Request(method, ''.join([self.host, url]),
                               data=body, headers=headers)

        prepped = self.session.prepare_request(req)
        prepped.body = body
        self.response = self.session.send(prepped, stream=raw)

    def getresponse(self):
        return self.response

    @property
    def status(self):
        return self.response.status_code

    @property
    def reason(self):
        return None if self.response.status_code > 400 else self.response.text        

    def _normalize_headers(self, headers):
        headers = headers or {}

        for key, value in headers.items():
            if isinstance(value, (int, float)):
                headers[key] = str(value)

        return headers

    def connect(self, host=None, port=None, base_url=None, **kwargs):
        pass


class Response(object):
    object = None
    body = None
    headers = {}

    def __init__(self, connection, response=None):
        self.connection = connection
        self._response = response
        self.object = self.parse_body

    @property
    def body(self):
        return self._response.content

    def parse_body(self):
        body = json.loads(self.body)
        return self.body

    def get_token_from_response(self):
        return self._response['access_token']