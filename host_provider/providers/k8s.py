from host_provider.providers.base import ProviderBase
from host_provider.credentials.k8s import CredentialK8s, \
    CredentialAddK8s
import jinja2
import yaml
import logging
from kubernetes.client import Configuration, ApiClient, CoreV1Api
from host_provider.models import Host
from time import sleep


LOG = logging.getLogger(__name__)


class K8sProvider(ProviderBase):
    retries = 30
    interval = 10

    def render_to_string(self, template_contenxt):
        env = jinja2.Environment(
            loader=jinja2.PackageLoader('host_provider', 'templates')
        )
        template = env.get_template('k8s/yamls/statefulset.yaml')
        return template.render(**template_contenxt)

    def yaml_file(self, context):
        yaml_file = self.render_to_string(
            context
        )
        return yaml.safe_load(yaml_file)

    def build_client(self):
        configuration = Configuration()
        configuration.api_key['authorization'] = "Bearer {}".format(self.auth_info['K8S-Token'])
        configuration.host = self.auth_info['K8S-Endpoint']
        configuration.verify_ssl = self._verify_ssl
        api_client = ApiClient(configuration)
        return CoreV1Api(api_client)

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

    def create_host(self, *args, **kw):
        return self.client.create_namespaced_stateful_set(
            self.auth_info.get('K8S-Namespace', 'default'),
            self.yaml_file(kw['yaml_context'])
        )

    def get_credential_add(self):
        return CredentialAddK8s

    def destroy(self, identifier, *args, **kw):
        self.client.delete_namespaced_stateful_set(
            identifier,
            self.auth_info.get('K8S-Namespace', 'default'),
            orphan_dependents=False
        )

    def wait_pod_ready(self, pod_name, namespace):
        for attempt in range(self.retries):
            pod_data = self.client.read_namespaced_pod_status(
                pod_name, namespace
            )
            for status_data in pod_data.status.conditions:
                if status_data.type == 'Ready':
                    if status_data.status == 'True':
                        return True
            if attempt == self.retries - 1:
                LOG.error("Maximum number of login attempts.")
                raise EnvironmentError('POD {} is not ready'.format(
                    pod_name
                ))

            LOG.warning("Pod {} not ready.".format(pod_name))
            LOG.info("Wating {} seconds to try again...".format(self.interval))
            sleep(self.interval)

    def create_host_object(self, provider, payload, env,
                           created_host_metadata):
        host = Host(
            name=payload['name'], group=payload['group'],
            engine=payload['engine'], environment=env, cpu=payload['cpu'],
            memory=payload['memory'], provider=provider.credential.provider,
            identifier=created_host_metadata.metadata.name,
            address=created_host_metadata.metadata.name, zone=''
        )
        host.save()
        return host
