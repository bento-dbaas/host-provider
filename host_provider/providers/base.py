from libcloud.compute.providers import get_driver
from libcloud import security
from host_provider.settings import LIBCLOUD_CA_CERTS_PATH


class ProviderBase(object):

    def __init__(self, environment, engine):
        self.environment = environment
        self.engine = engine
        self._client = None
        self._credential = None

        if LIBCLOUD_CA_CERTS_PATH is not None:
            security.CA_CERTS_PATH = LIBCLOUD_CA_CERTS_PATH
            if security.CA_CERTS_PATH == "":
                security.CA_CERTS_PATH = None

    def get_driver(self):
        return get_driver(self.get_provider())

    @property
    def client(self):
        if not self._client:
            self._client = self.build_client()

        return self._client

    @property
    def credential(self):
        if not self._credential:
            self._credential = self.build_credential()

        return self._credential

    def credential_add(self, content):
        credential_cls = self.get_credential_add()
        credential = credential_cls(
            self.get_provider(), self.environment, content
        )

        is_valid, error = credential.is_valid()
        if not is_valid:
            return False, error

        try:
            insert = credential.save()
        except Exception as e:
            return False, str(e)
        else:
            return True, insert.inserted_id

    def create_host(self, cpu, memory, name, group):
        self.credential.before_create_host(group)
        result = self._create_host(cpu, memory, name)
        self.credential.after_create_host(group)
        return result

    @classmethod
    def get_provider(cls):
        raise NotImplementedError

    def build_client(self):
        raise NotImplementedError

    def _create_host(self, cpu, memory, name):
        raise NotImplementedError

    def build_credential(self):
        raise NotImplementedError

    def get_credential_add(self):
        raise NotImplementedError
