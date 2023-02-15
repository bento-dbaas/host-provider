from libcloud.compute.providers import get_driver
from libcloud import security
from host_provider.models import Host
from dbaas_base_provider.baseProvider import BaseProvider
from host_provider.settings import LIBCLOUD_CA_CERTS_PATH

from dbaas_base_provider.log import log_this


class ProviderBase(BaseProvider):

    provider_type = "host_provider"

    def __init__(self, environment, engine, auth_info=None):
        super(ProviderBase, self).__init__(
            environment,
            engine=engine,
            auth_info=None
        )

        if LIBCLOUD_CA_CERTS_PATH is not None:
            security.CA_CERTS_PATH = LIBCLOUD_CA_CERTS_PATH
            if security.CA_CERTS_PATH == "":
                security.CA_CERTS_PATH = None

    def get_driver(self):
        return get_driver(self.get_provider())

    def get_host_ids(self, group_id):
        host_ids = Host.filter(group=group_id).select(Host.identifier)
        return [x.identifier for x in host_ids]

    def get_host_names(self, group_id):
        host_names = Host.filter(group=group_id).select(Host.name)
        return [x.name for x in host_names]

    @property
    def create_attempts(self):
        return 1

    @property
    def engine_name(self):
        return self.engine.split("_")[0]

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

    def update_host_metadata(self, identifier):
        self._update_host_metadata(identifier)

    def _update_host_metadata(self, identifier):
        pass

    def clean(self, name):
        pass

    def refresh_metadata(self, host):
        self._refresh_metadata(host)
        host.save()

    def _create_host(self, cpu, memory, name, *args, **kw):
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

    def restore(self, host, engine, *args, **kw):
        self._restore(host, engine, *args, **kw)

    def _restore(self, host, engine, *args, **kw):
        raise NotImplementedError

    def create_service_account(self, name):
        return self._create_service_account(name)

    def _create_service_account(self, name):
        pass

    def destroy_service_account(self, service_account):
        return self._destroy_service_account(service_account)

    def _destroy_service_account(self, service_account):
        pass

    def sa_set_role(self, service_account):
        return self._sa_set_role(service_account)

    def _sa_set_role(self, service_account):
        pass

    def update_team_labels(self, host, team_name):
        return self._update_team_labels(host, team_name)

    def _update_team_labels(self, host, team_name):
        pass
