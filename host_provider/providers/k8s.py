from os import getenv
from host_provider.providers.base import ProviderBase
from host_provider.credentials.k8s import CredentialK8s, \
    CredentialAddK8s
import jinja2
import yaml
import logging
from kubernetes import client, config
from host_provider.models import Host
from time import sleep


LOG = logging.getLogger(__name__)


if bool(int(getenv('VERIFY_SSL_CERT', '0'))):
    import libcloud.security
    libcloud.security.VERIFY_SSL_CERT = False


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

    def build_client(self, api_name='AppsV1beta1Api'):
        config.load_kube_config(
            self.credential.kube_config_path
        )

        conf = client.configuration.Configuration()
        conf.verify_ssl = False

        return getattr(client, api_name)(client.ApiClient(conf))

    @classmethod
    def get_provider(cls):
        return "k8s"

    def build_credential(self):
        return CredentialK8s(
            self.get_provider(), self.environment, self.engine
        )

    def create_host(self, *args, **kw):
        return self.client.create_namespaced_stateful_set(
            kw.get('namespace', 'default'),
            self.yaml_file(kw['yaml_context'])
        )

    def get_credential_add(self):
        return CredentialAddK8s

    def destroy(self, identifier, *args, **kw):
        self.client.delete_namespaced_stateful_set(
            identifier,
            kw.get('namespace', 'default'),
            orphan_dependents=False
        )

    def wait_pod_ready(self, pod_name, namespace):
        core_v1_client = self.build_client(
            api_name='CoreV1Api'
        )
        for attempt in range(self.retries):
            pod_data = core_v1_client.read_namespaced_pod_status(
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
            LOG.info("Wating %i seconds to try again..." % (self.interval))
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
