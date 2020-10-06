from host_provider.credentials.base import CredentialAdd, CredentialBase


class CredentialK8s(CredentialBase):

    # This data should be in credential database
    CONFIGURATION_FILES = {
            "mongodb_4_2_3": "mongodb.conf"
    }
    LOG_FILES = {
            "mongodb_4_2_3": "mongodb.log"
    }
    IMAGE_NAMES = {
            "mongodb_4_2_3": "mongo"
    }
    IMAGE_VERSIONS = {
            "mongodb_4_2_3": "4.2"
    }

    @property
    def configuration_file(self):
        return self.CONFIGURATION_FILES[self.engine]

    @property
    def log_file(self):
        return self.LOG_FILES[self.engine]

    @property
    def image_name(self):
        return self.IMAGE_NAMES[self.engine]

    @property
    def image_version(self):
        return self.IMAGE_VERSIONS[self.engine]

    @property
    def _zones_field(self):
        return {}


class CredentialAddK8s(CredentialAdd):

    @classmethod
    def is_valid(cls, content):
        return True, ""
