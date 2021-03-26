import json
import time
from urllib.parse import urlencode

from host_provider.common.http import Connection, ProviderConnection, JsonResponse
from host_provider.credentials.azure import CredentialAzure


class AzureConnection(Connection):
    credential_cls = CredentialAzure
    conn_cls = ProviderConnection
    response_cls = JsonResponse

    def __init__(self, engine=None, provider='azure_arm', env='dev'):
        self.engine = engine
        self.provider = provider
        self.environment = env
        self.__login_host = None
        self.__key = None
        self.__secret = None
        self.__tenant_id = None
        self.__login_resource = None
        self.__subscription_id = None
        self.__endpoint = None

    @property
    def subscription_id(self):
        return self.__subscription_id

    @subscription_id.setter
    def subscription_id(self, subscription_id):
        self.__subscription_id = subscription_id

    @property
    def key(self):
        return self.__key

    @key.setter
    def key(self, key):
        self.__key = key

    @property
    def secret(self):
        return self.__secret

    @secret.setter
    def secret(self, secret):
        self.__secret = secret

    @property
    def tenant_id(self):
        return self.__tenant_id

    @tenant_id.setter
    def tenant_id(self, tenant_id):
        self.__tenant_id = tenant_id

    @property
    def login_host(self):
        return self.__login_host

    @login_host.setter
    def login_host(self, host):
        self.__login_host = host

    @property
    def endpoint(self):
        return self.__endpoint

    @endpoint.setter
    def endpoint(self, endpoint):
        self.__endpoint = endpoint

    @property
    def login_resource(self):
        return self.__login_resource
    
    @login_resource.setter
    def login_resource(self, login_resource):
        self.__login_resource = login_resource
        
    def _build_credentials(self):
        credentials = self.credential_cls(self.provider, self.environment, self.engine)
        self.key = credentials.access_id
        self.secret = credentials.secret_key
        self.tenant_id = credentials.tenant_id
        self.subscription_id = credentials.subscription_id
        self.login_resource = credentials.endpoint['scope']
        self.login_host = credentials.endpoint['login']
        self.endpoint = credentials.endpoint['api']
        return credentials

    def get_token_from_credentials(self):
        self._build_credentials()
        conn = self.conn_cls(self.login_host, 443, timeout=self.timeout)
        conn.connect()
        params = urlencode({
            "grant_type": "client_credentials",
            "client_id": self.key,
            "client_secret": self.secret,
            "scope": self.login_resource
        })
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        conn.request("POST", "/%s/oauth2/v2.0/token" % self.tenant_id, params, headers)
        resp = self.response_cls(conn.getresponse(), conn)
        self.access_token = resp.object["access_token"]
        self.expires_in = resp.object["expires_in"]

    def add_default_headers(self, headers):
        headers['Content-Type'] = "application/json"
        headers['Authorization'] = "Bearer %s" % self.access_token
        return headers
    
    def encode_data(self, data):
        return json.dumps(data)
    
    def connect(self, **kwargs):
        self.get_token_from_credentials()
        return super(AzureConnection, self).connect(**kwargs)

    def request(self, action, params=None, data=None, headers=None, method='GET', raw=False):
        if (time.time() + 300) >= int(self.expires_in):
            self.get_token_from_credentials()

        return super(AzureConnection, self).request(action, params=params, data=data, headers=headers, method=method, raw=raw)
