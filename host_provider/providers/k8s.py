from jinja2 import Environment, PackageLoader
from yaml import safe_load
import logging
from kubernetes.client import Configuration, ApiClient, AppsV1beta1Api, CoreV1Api
from host_provider.models import Host
from host_provider.credentials.k8s import CredentialK8s, CredentialAddK8s
from host_provider.providers.base import ProviderBase


LOG = logging.getLogger(__name__)


class K8sClient(AppsV1beta1Api, CoreV1Api):
    pass


class K8sProvider(ProviderBase):

    @staticmethod
    def render_to_string(path, template_context):
        env = Environment(
            loader=PackageLoader('host_provider', 'templates/k8s/yamls/')
        )
        template = env.get_template(path)
        return template.render(**template_context)

    def yaml_file(self, path, context):
        yaml_file = self.render_to_string(path, context)
        return safe_load(yaml_file)

    def build_client(self):
        configuration = Configuration()
        configuration.api_key['authorization'] = "Bearer {}".format(self.auth_info['K8S-Token'])
        configuration.host = self.auth_info['K8S-Endpoint']
        configuration.verify_ssl = self._verify_ssl
        api_client = ApiClient(configuration)
        return K8sClient(api_client)

    @property
    def _verify_ssl(self):
        verify_ssl = self.auth_info.get("K8S-Verify-Ssl", 'false')
        return verify_ssl != 'false' and verify_ssl != 0

    @classmethod
    def get_provider(cls):
        return "k8s"

    def build_credential(self):
        return CredentialK8s(
            self.get_provider(), self.environment, self.engine
        )

    def get_credential_add(self):
        return CredentialAddK8s

    def start(self, identifier):
        # TODO
        pass

    def stop(self, identifier):
        # TODO
        pass

    def _build_stateful_set(self, cpu, memory, name, group, port, volume_name):
        context = {
            'STATEFULSET_NAME': name,
            'POD_NAME': name,
            'LABEL_NAME': group,
            'SERVICE_NAME': f'service-{name}',
            'INIT_CONTAINER_CREATE_CONFIG_COMMANDS': (
                'cp /mnt/config-map/{config_file} /data; chown mongodb:mongodb /data/{config_file}'.format(
                    config_file=self.credential.configuration_file,
                )
            ),
            'CONFIG_MAP_MOUNT_PATH': '/mnt/config-map',
            'IMAGE_NAME': self.credential.image_name,
            'IMAGE_TAG': self.credential.image_version,
            'CONTAINER_PORT': port,
            'VOLUME_NAME': 'data-volume',
            'VOLUME_PATH_ROOT': '/data',
            'VOLUME_PATH_DB': '/data/db',
            'VOLUME_PATH_CONFIGDB': '/data/configdb',
            'CPU': cpu * 1000,
            'CPU_LIMIT': cpu * 1000,
            'MEMORY': memory,
            'MEMORY_LIMIT': memory,
            'VOLUME_CLAIM_NAME': volume_name,
            'CONFIG_MAP_NAME': f"configmap-{name}",
            'DATABASE_CONFIG_FULL_PATH': f"/data/{self.credential.configuration_file}",
            'CONFIG_FILE_NAME': self.credential.configuration_file,
            'DATABASE_LOG_DIR': "/data/logs",
            'DATABASE_LOG_FULL_PATH': f"/data/logs/{self.credential.log_file}"
        }
        return self.yaml_file('statefulset.yaml', context)

    def _create_host(self, cpu, memory, name, *args, **kw):
        yaml = self._build_stateful_set(cpu, memory, name, kw["group"], kw["port"], kw["volume_name"])
        return self.client.create_namespaced_stateful_set(
            self.auth_info.get('K8S-Namespace', 'default'), yaml
        )

    def create_host_object(self, provider, payload, env, created_host_metadata):
        host = Host(
            name=f"{created_host_metadata.metadata.name}-0", group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=created_host_metadata.metadata.name,
            address=created_host_metadata.metadata.name, zone=''
        )
        host.save()
        return host

    def _destroy(self, identifier):
        self.client.delete_namespaced_stateful_set(
            identifier,
            self.auth_info.get('K8S-Namespace', 'default'),
            orphan_dependents=False
        )

    def prepare(self, name, group, engine, ports):
        context = {
            'SERVICE_NAME': name,
            'LABEL_NAME': group,
            'PORTS': ports,
        }
        self.client.create_namespaced_service(
            self.auth_info.get('K8S-Namespace', 'default'),
            self.yaml_file('service.yaml', context)
        )

    def clean(self, name):
        self.client.delete_namespaced_service(
            name,
            self.auth_info.get('K8S-Namespace', 'default'),
        )

    def configure(self, name, group, configuration):
        context = {
            'CONFIG_MAP_NAME': f"configmap-{name}",
            'CONFIG_MAP_LABEL': group,
            'CONFIG_FILE_NAME': self.credential.configuration_file,
            'CONFIG_CONTENT': 'config_content'
        }
        yaml_file = self.yaml_file('config_map.yaml', context)
        yaml_file['data'][self.credential.configuration_file] = configuration
        self.client.create_namespaced_config_map(
            self.auth_info.get('K8S-Namespace', 'default'),
            yaml_file
        )

    def remove_configuration(self, name):
        self.client.delete_namespaced_config_map(
            f"configmap-{name}",
            self.auth_info.get('K8S-Namespace', 'default'),
        )

    def resize(self, host, cpus, memory):
        namespace = self.auth_info.get('K8S-Namespace', 'default')
        pod_data = self.client.read_namespaced_pod_status(
            host.name, namespace,
        )
        volume_name = pod_data.spec.volumes[0].persistent_volume_claim.claim_name
        volume_name = volume_name.replace(namespace + ":", "")
        pod_port = pod_data.spec.containers[0].ports[0].container_port
        yaml = self._build_stateful_set(
            cpus, memory, host.identifier, host.group, pod_port, volume_name
        )
        stateful = self.client.replace_namespaced_stateful_set(
            host.identifier, namespace, yaml,
        )
        # Force redeploy
        self.client.delete_namespaced_pod(
            host.name, namespace
        )
        return stateful

    def _is_ready(self, host):
        pod_data = self.client.read_namespaced_pod_status(
            host.name, self.auth_info.get('K8S-Namespace', 'default'),
        )
        for status_data in pod_data.status.conditions:
            if status_data.type == 'Ready':
                if status_data.status == 'True':
                    return True
                return False

    def _refresh_metadata(self, host):
        pod_metadata = self.client.read_namespaced_pod(
            host.name, self.auth_info.get('K8S-Namespace', 'default'),
        )
        host.address = pod_metadata.status.pod_ip
