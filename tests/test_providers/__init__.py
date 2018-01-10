from host_provider.providers.base import ProviderBase


class FakeProvider(ProviderBase):

    @staticmethod
    def get_provider():
        return "ProviderForTests"

    def build_client(self):
        return "FakeClient"

    def build_credential(self):
        return "FakeCredential"
