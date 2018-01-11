from host_provider.providers.base import ProviderBase


class FakeProvider(ProviderBase):

    @classmethod
    def get_provider(cls):
        return "ProviderForTests"

    def build_client(self):
        return "FakeClient"

    def build_credential(self):
        return "FakeCredential"
