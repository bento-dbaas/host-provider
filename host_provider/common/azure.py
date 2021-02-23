from msal import ConfidentialClientApplication
from msal import SerializableTokenCache
from host_provider.credentials.azure import CredentialAzure
from host_provider.providers.azure import AzureProvider


class AzureClientApplication(object):
    __credential_cls = CredentialAzure
    __cache_cls = SerializableTokenCache

    def __init__(self, scopes=None):
        self.scopes = scopes
        self._credentials = None
        self.provider = "azure_arm"
        self.environment = "dev"
        self.engine = "mssql"
        if not self.scopes:
            self.scopes = "https://management.azure.com/.default"
    
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


