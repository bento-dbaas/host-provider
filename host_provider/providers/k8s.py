import jinja2
import yaml
import logging
from kubernetes.client import Configuration, ApiClient, AppsV1beta1Api, CoreV1Api
from host_provider.models import Host
from host_provider.credentials.k8s import CredentialK8s, CredentialAddK8s
from host_provider.providers.base import ProviderBase


LOG = logging.getLogger(__name__)


class K8sClient(AppsV1beta1Api, CoreV1Api):
    pass


class K8sProvider(ProviderBase):

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

    def _is_ready(self, host):
        ## This -0 should be removed, future work
        pod_data = self.client.read_namespaced_pod_status(
            host.name + "-0", self.auth_info.get('K8S-Namespace', 'default'),
        )
        for status_data in pod_data.status.conditions:
            if status_data.type == 'Ready':
                if status_data.status == 'True':
                    return True
                return False

    def _refresh_metadata(self, host):
        ## This -0 should be removed, future work
        pod_metadata = self.client.read_namespaced_pod(
            host.name + "-0", self.auth_info.get('K8S-Namespace', 'default'),
        )
        host.address = pod_metadata.status.pod_ip

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
