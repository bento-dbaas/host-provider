from host_provider.credentials.base import CredentialAdd, CredentialBase


class CredentialK8s(CredentialBase):

    # This data should be in credential database
    PORTS = {
        "k8s-aws": {
            "mongodb_4_2_3": [27017]
        }
    }
    CONFIGURATION_FILES = {
            "mongodb_4_2_3": "mongodb.conf"

    }

    @property
    def ports(self):
        return self.PORTS[self.environment][self.engine]

    @property
    def configuration_file(self):
        return self.CONFIGURATION_FILES[self.engine]

    @property
    def _zones_field(self):
        return {}


class CredentialAddK8s(CredentialAdd):

    @classmethod
    def is_valid(cls, content):
        return True, ""
