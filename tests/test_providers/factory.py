from unittest import TestCase
from host_provider.providers import factory
from host_provider.providers.base import ProviderBase


class TestFactory(TestCase):

    def test_no_provider(self):
        self.assertRaises(
            NotImplementedError, factory, "fake", "", ""
        )

    def test_have_provider(self):
        provider = factory(FakeProvider.get_provider(), "", "")
        self.assertIsInstance(provider, FakeProvider)


class FakeProvider(ProviderBase):

    @staticmethod
    def get_provider():
        return "ProviderForTests"

