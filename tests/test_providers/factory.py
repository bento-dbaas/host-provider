from unittest import TestCase
from host_provider.providers import get_provider_to
from . import FakeProvider


class TestFactory(TestCase):

    def test_no_provider(self):
        self.assertRaises(
            NotImplementedError, get_provider_to, "fake"
        )

    def test_have_provider(self):
        provider = get_provider_to(FakeProvider.get_provider())
        self.assertEqual(provider.__name__, FakeProvider.__name__)
