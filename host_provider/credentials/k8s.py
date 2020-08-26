from host_provider.credentials.base import CredentialBase


class CredentialK8s(CredentialBase):

    @property
    def kube_config_path(self):
        return self.content['kube_config_path']

    @property
    def kube_config_content(self):
        return self.content['kube_config_content']


class CredentialAddK8s(CredentialBase):

    @classmethod
    def is_valid(cls, content):

        return True, ""
