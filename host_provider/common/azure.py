from requests.auth import AuthBase
from host_provider.common.http import Connection
from host_provider.credentials.azure import CredentialAzure
from host_provider.providers.azure import AzureProvider
from msal import ConfidentialClientApplication, SerializableTokenCache


class AzureClientApplicationException(Exception):
    pass


class AzureClientApplication(object):
    __credential_cls = CredentialAzure
    __cache_cls = SerializableTokenCache

    def __init__(self, engine="mssql", provider="azure_arm", **kwargs):
        self.engine = engine
        self.provider = provider
        self.environment = kwargs.get("environment", "dev")
        self.scopes = kwargs.get("scopes", "https://management.azure.com/.default")
        self._credentials = None
    
    @property
    def scopes(self):
        return self.scopes

    @scopes.setter
    def scopes(self, scope):
        self.scopes = scope

    def _build_credentials(self, provider=None, environment=None, engine=None):
        if not provider:
            provider = self.provider
        if not environment:
            environment = self.environment
        if not engine:
            engine = self.engine
        if not self._credentials:
            self._credentials = self.__credential_cls(provider, environment, engine)
        return self._credentials

    def __build_msal_app(self, url=None):
        if not url:
            url = "https://login.microsoftonline.com/"
        credentials = self._build_credentials()
        client_id = credentials.access_id
        client_credential = credentials.secret_key
        authority = str(url + credentials.tenant_id)
        return ConfidentialClientApplication(
            client_id, authority=authority, client_credential=client_credential
        )

    @classmethod
    def token(cls, scopes=None):
        if not scopes:
            scopes = cls.scopes
        app = self.__build_msal_app()
        return app.acquire_token_for_client(scopes=scopes)


class AzureAuth(AuthBase):

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


class AzureConnection(Connection):
    client_cls = AzureClientApplication
    response_cls = Response

    def add_default_headers(self, headers):
        headers['Content-Type'] = "application/json"
        headers['Authorization'] = "Bearer %s" % self.access_token
        return headers     

    def get_token_from_client(self):
        client = self.client_cls()
        try:
            token = client.get_token()
        except Exception as ex:
            raise AzureClientApplicationException(ex)
        self.access_token = token
        return self.access_token

    def connect(self, **kwargs):
        pass