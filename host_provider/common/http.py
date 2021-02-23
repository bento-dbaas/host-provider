import requests
from requests.auth import AuthBase
from host_provider.common.azure import AzureClientApplication
from host_provider.settings import HTTP_AZURE_PROXY


__all__ = [
    'BaseConnection',
    'Connection'
]

ALLOW_REDIRECTS = 1


class AzureClientApplicationException(Exception):
    pass


class AzureAccessToken(AuthBase):

    def __init__(self, token=None):
        self.token = token

    def get_or_update_token(self):
        if self.token == None:
            try:
                self.token = AzureClientApplication.token()
            except Exception as ex:
                raise AzureClientApplicationException(ex)
        self.client = client_cls

    def __call__(self, req):
        req.headers["Authorization"] = f"{self.token}"
        return req


class BaseConnection(object):
    session = None
    self.token = None

    def __init__(self):
        self.session = requests.Session()


class Connection(BaseConnection):
    client_cls = AzureClientApplication
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

    def get_token_from_client(self, *kwargs):
        client = self.client_cls()
        try:
            token = client.get_token()
        except Exception as ex:
            raise AzureClientApplicationException(ex)
        self.token = token

    def add_default_headers(self, headers):
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = "Bearer %s" % self.access_token

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
            stream=stream,
            verify=self.verification
        )

    def prepared_request(self, method, url, body=None,
                         headers=None, raw=False, stream=False):
        headers = self._normalize_headers(headers=headers)

        req = requests.Request(method, ''.join([self.host, url]),
                               data=body, headers=headers)

        prepped = self.session.prepare_request(req)

        prepped.body = body

        self.response = self.session.send(
            prepped,
            stream=raw)

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
