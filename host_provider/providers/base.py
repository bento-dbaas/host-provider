from libcloud.compute.providers import get_driver
from libcloud import security
from host_provider.models import Host
from host_provider.settings import LIBCLOUD_CA_CERTS_PATH


class ProviderBase(object):

    def __init__(self, environment, engine, auth_info=None):
        self.environment = environment
        self.engine = engine
        self._client = None
        self._credential = None
        self.auth_info = auth_info

        if LIBCLOUD_CA_CERTS_PATH is not None:
            security.CA_CERTS_PATH = LIBCLOUD_CA_CERTS_PATH
            if security.CA_CERTS_PATH == "":
                security.CA_CERTS_PATH = None

    def get_driver(self):
        return get_driver(self.get_provider())

    @property
    def create_attempts(self):
        return 1

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

        is_valid, error = credential.is_valid(content)
        if not is_valid:
            return False, error

        try:
            insert = credential.save()
        except Exception as e:
            return False, str(e)
        else:
            return True, insert and insert.get('_id')

    def prepare(self, name, group, engine, ports):
        pass

    def configure(self, name, group, configuration):
        pass

    def remove_configuration(self, host):
        pass

    def create_host(self, cpu, memory, name, group, zone, *args, **kw):
        kw.update({'group': group})
        self.credential.before_create_host(group)
        if zone:
            self.credential.zone = zone
        result = self._create_host(cpu, memory, name, *args, **kw)
        self.credential.after_create_host(group)
        return result

    def get_status(self, host):
        is_ready, version_id = self._is_ready(host)
        if is_ready:
            return "READY", version_id
        return "NOT READY", None

    def destroy(self, group, identifier):
        self._destroy(identifier)
        quantity = len(Host.filter(group=group))
        if quantity:
            self._all_node_destroyed(group)

    def clean(self, name):
        pass

    def refresh_metadata(self, host):
        self._refresh_metadata(host)
        host.save()

    @classmethod
    def get_provider(cls):
        raise NotImplementedError

    def build_client(self):
        raise NotImplementedError

    def _create_host(self, cpu, memory, name, *args, **kw):
        raise NotImplementedError

    def build_credential(self):
        raise NotImplementedError

    def get_credential_add(self):
        raise NotImplementedError

    def start(self, host):
        raise NotImplementedError

    def stop(self, identifier):
        raise NotImplementedError

    def _destroy(self, identifier):
        raise NotImplementedError

    def _all_node_destroyed(self, group):
        pass

    def _is_ready(self, host):
        raise NotImplementedError

    def _refresh_metadata(self, host):
        pass

    def create_static_ip(self, *args, **kw):
        pass

    def destroy_static_ip(self, *args, **kw):
        pass

    def associate_ip_with_host(self, *args, **kw):
        pass

    def create_host_object(self, *args, **kw):
        raise NotImplementedError
