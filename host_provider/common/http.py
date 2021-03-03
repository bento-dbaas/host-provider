import copy
import json
from urllib.parse import urlencode, urlparse, urljoin

import requests


__all__ = [
    'ProviderConnection',
    'Connection',
    'Response',
    'RawResponse',
    'JsonResponse'
]

ALLOW_REDIRECTS = 1


class ConnectionError(Exception):
    def __init__(*args, **kwargs):
        print(f"Connection Error:{args} / {kwargs}")
        pass


class ResponseError(Exception):
    def __init__(*args, **kwargs):
        print(f"Response Error:{args} / {kwargs}")
        pass


class BaseProviderConnection(object):
    session = None

    proxy_scheme = None
    proxy_host = None
    proxy_port = None

    proxy_username = None
    proxy_password = None

    http_proxy_used = False

    ca_cert = None

    def __init__(self):
        self.session = requests.Session()


class ProviderConnection(BaseProviderConnection):
    timeout = None
    host = None
    response = None

    def __init__(self, host, port, secure=None, **kwargs):
        scheme = 'https' if secure is not None and secure else 'http'
        self.host = '{0}://{1}{2}'.format( 'https' if port == 443 else scheme, host, ":{0}".format(port) if port not in (80, 443) else "" )

        BaseProviderConnection.__init__(self)
        self.session.timeout = kwargs.get('timeout', 60)

    def request(self, method, url, body=None, headers=None, raw=False, stream=False):
        url = urljoin(self.host, url)
        headers = self._normalize_headers(headers=headers)

        self.response = self.session.request(
            method=method.lower(),
            url=url,
            data=body,
            headers=headers,
            allow_redirects=ALLOW_REDIRECTS,
            stream=stream
        )

    def prepared_request(self, method, url, body=None, headers=None, raw=False, stream=False):

        headers = self._normalize_headers(headers=headers)
        req = requests.Request(method, ''.join([self.host, url]), data=body, headers=headers)

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

    def connect(self):
        pass


class Response(object):

    status = None
    headers = {}
    body = None
    object = None
    error = None
    connection = None

    def __init__(self, response, connection):
        self.connection = connection

        self.headers = self.lowercase_keys(dict(response.headers))
        self.error = response.reason
        self.status = response.status_code
        self.request = response.request
        self.iter_content = response.iter_content     

        self.body = response.text.strip() \
            if response.text is not None and hasattr(response.text, 'strip') \
            else ''

        if not self.success():
            raise ResponseError(code=self.status, message=self.parse_error(), headers=self.headers)

        self.object = self.parse_body()

    def parse_body(self):
        return self.body if self.body is not None else ''

    def parse_error(self):
        return self.body

    def success(self):
        return self.status in [requests.codes.ok, requests.codes.created, requests.codes.accepted]
    
    def lowercase_keys(self, dictionary):
        return dict(((k.lower(), v) for k, v in dictionary.items()))


class RawResponse(Response):
    connection = None
    status = None
    headers = {}
    body = None
    object = None

    def __init__(self, connection, response=None):
        self._status = None
        self._response = None
        self._headers = {}
        self._error = None
        self._reason = None
        self.connection = connection
        if response is not None:
            self.headers = self.lowercase_keys(dict(response.headers))
            self.error = response.reason
            self.status = response.status_code
            self.request = response.request
            self.iter_content = response.iter_content

    def success(self):
        return self.status in [requests.codes.ok, requests.codes.created, requests.codes.accepted]

    @property
    def response(self):
        if not self._response:
            response = self.connection.connection.getresponse()
            self._response = response
            if not self.success():
                self.parse_error()
        return self._response

    @property
    def body(self):
        return self.response.body

    @property
    def reason(self):
        if not self._reason:
            self._reason = self.response.reason
        return self._reason


class JsonResponse(Response):

    def parse_body(self):
        if len(self.body) == 0:
            return self.body
        try:
            body = json.loads(self.body)
        except Exception as error:
            raise ResponseError(error)

        return body


class Connection(object):
    connection = None
    conn_cls = ProviderConnection
    response_cls = Response
    rawResponse_cls = RawResponse
    host = ''
    port = 443
    timeout = None
    secure = 1

    def __init__(self, secure=True, host=None, port=None, url=None, timeout=None, proxy_url=None):
        self.secure = secure and 1 or 0
        self.context = {}

        self.request_path = ''

        if host:
            self.host = host

        if port is not None:
            self.port = port
        else:
            if self.secure == 1:
                self.port = 443
            else:
                self.port = 80

        if url:
            (self.host, self.port, self.secure,
             self.request_path) = self._tuple_from_url(url)

        self.timeout = timeout or self.timeout
        self.proxy_url = proxy_url

    def _tuple_from_url(self, url):
        secure = 1
        port = None
        (scheme, netloc, request_path, param,
         query, fragment) = urlparse(url)

        if scheme not in ['http', 'https']:
            raise ConnectionError('Invalid scheme: %s in url %s' % (scheme, url))

        if scheme == "http":
            secure = 0

        if ":" in netloc:
            netloc, port = netloc.rsplit(":")
            port = int(port)

        if not port:
            if scheme == "http":
                port = 80
            else:
                port = 443

        host = netloc
        port = int(port)

        return (host, port, secure, request_path)

    def set_context(self, context):
        if not isinstance(context, dict):
            raise TypeError('needs to be a dictionary')
        self.context = context

    def reset_context(self):
        self.context = {}

    @property
    def version(self):
        return '2.0'

    def connect(self, host=None, port=None, base_url=None, **kwargs):
        connection = None
        secure = self.secure

        if getattr(self, 'base_url', None) and base_url is None:
            (host, port, secure, request_path) = self._tuple_from_url(getattr(self, 'base_url'))

        elif base_url is not None:
            (host, port, secure, request_path) = self._tuple_from_url(base_url)

        else:
            host = host or self.host
            port = port or self.port

        port = int(port)

        if not hasattr(kwargs, 'host'):
            kwargs.update({'host': host})

        if not hasattr(kwargs, 'port'):
            kwargs.update({'port': port})

        if not hasattr(kwargs, 'secure'):
            kwargs.update({'secure': self.secure})

        if self.timeout:
            kwargs.update({'timeout': self.timeout})

        connection = self.conn_cls(**kwargs)

        self.connection = connection

    def request(self, action, params=None, data=None, headers=None, method='GET', raw=False, stream=False):

        if params is None:
            params = {}
        else:
            params = copy.copy(params)

        if headers is None:
            headers = {}
        else:
            headers = copy.copy(headers)

        self.action = action
        self.method = method
        self.data = data

        params = self.add_default_params(params)

        headers = self.add_default_headers(headers)
        headers.update({'Accept-Encoding': 'gzip,deflate'})

        port = int(self.port)

        if port not in (80, 443):
            headers.update({'Host': "%s:%d" % (self.host, port)})
        else:
            headers.update({'Host': self.host})

        if data:
            data = self.encode_data(data)

        if params:
            if '?' in action:
                url = '&'.join((action, urlencode(params, doseq=True)))
            else:
                url = '?'.join((action, urlencode(params, doseq=True)))
        else:
            url = action

        if self.connection is None:
            self.connect()

        try:
            if raw:
                self.connection.prepared_request( method=method, url=url, body=data, headers=headers, raw=raw, stream=stream)
            else:
                self.connection.request(method=method, url=url, body=data, headers=headers, stream=stream)
        except Exception as error:
            raise ResponseError(error)

        if raw:
            response_cls = self.rawResponse_cls
            kwargs = {'connection': self, 'response': self.connection.getresponse()}
        else:
            response_cls = self.response_cls
            kwargs = {'connection': self, 'response': self.connection.getresponse()}

        try:
           response = response_cls(**kwargs)
        finally:
           self.reset_context()

        return response

    def add_default_params(self, params):
        return params
    
    def add_default_headers(self, headers):
        return headers

    def encode_data(self, data):
        return json.dumps(data)