from host_provider.credentials.base import CredentialAdd, CredentialBase


class CredentialK8s(CredentialBase):

    @property
    def _zones_field(self):
        return {}


class CredentialAddK8s(CredentialAdd):

    @classmethod
    def is_valid(cls, content):
        return True, ""
