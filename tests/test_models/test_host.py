from unittest import TestCase
from host_provider.models import Host


class PropertiesTestCase(TestCase):

    def setUp(self):
        self.host = Host()
        self.host._data = {
            'id': 11,
            'name': 'fake_name'
        }

    def return_normal_fields(self):
        """
            Test when password field does no exist, return all other fields
            without error.
        """

        my_dict = self.to_dict
        self.assertIn('id', my_dict)
        self.assertIn('name', my_dict)

    def exclude_password(self):

        self.host._data['password'] = 123

        my_dict = self.to_dict
        self.assertIn('id', my_dict)
        self.assertIn('name', my_dict)
        self.assertNotIn('password', my_dict)
