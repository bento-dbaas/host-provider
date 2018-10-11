from collections import OrderedDict
from pymongo import MongoClient, ReturnDocument
from host_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD, MONGO_ENDPOINT


class CredentialMongoDB(object):

    def __init__(self, provider, environment):
        self.provider = provider
        self.environment = environment
        self._db = None
        self._collection_credential = None
        self._content = None

    @property
    def db(self):
        if not self._db:
            params = {'document_class': OrderedDict}
            if MONGO_ENDPOINT is None:
                params.update({
                    'host': MONGODB_HOST, 'port': MONGODB_PORT,
                    'username': MONGODB_USER, 'password': MONGODB_PWD
                })
                client = MongoClient(**params)
            else:
                client = MongoClient(MONGO_ENDPOINT, **params)
            self._db = client[MONGODB_DB]

        return self._db

    @property
    def credential(self):
        if not self._collection_credential:
            self._collection_credential = self.db["credential"]
        return self._collection_credential

    @property
    def content(self):
        return self._content


class CredentialBase(CredentialMongoDB):

    def __init__(self, provider, environment, engine):
        super(CredentialBase, self).__init__(provider, environment)
        self.engine = engine
        self._zone = None

    def get_content(self):
        content = self.credential.find_one({
            "provider": self.provider,
            "environment": self.environment,
        })
        if content:
            return content

        raise NotImplementedError("No {} credential for {}".format(
            self.provider, self.environment
        ))

    @property
    def content(self):
        if not self._content:
            self._content = self.get_content()
        return super(CredentialBase, self).content

    def before_create_host(self, group):
        pass

    def after_create_host(self, group):
        pass

    @property
    def _zones_field(self):
        raise NotImplementedError

    def __get_zones(self, **filters):
        all_zones = self._zones_field
        filtered_zones = {}
        for zone_key in all_zones.keys():
            zone_val = all_zones[zone_key]
            valid = True
            for key, value in filters.items():
                if zone_val[key] != value:
                    valid = False
                    break

            if valid:
                filtered_zones[zone_key] = zone_val

        return filtered_zones

    @property
    def all_zones(self):
        return self.__get_zones()

    @property
    def zones(self):
        return self.__get_zones(active=True)

    @property
    def zone(self):
        return self._zone

    @zone.setter
    def zone(self, zone):
        zones = list(self.__get_zones(name=zone).keys())
        self._zone = zones[0]

    def zone_by_id(self, zone_id):
        zones = self.__get_zones(id=zone_id)
        zone_id, values = zones.popitem()
        return values['name']


class CredentialAdd(CredentialMongoDB):

    def __init__(self, provider, environment, content):
        super(CredentialAdd, self).__init__(provider, environment)
        self._content = content

    def save(self):
        return self.credential.find_one_and_update(
            {
                'provider': self.provider,
                'environment': self.environment
            },
            {'$set': {
                'provider': self.provider,
                'environment': self.environment, **self.content
            }},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    def delete(self):
        return self.credential.delete_one({
            'provider': self.provider, 'environment': self.environment
        })

    def is_valid(self, content):
        raise NotImplementedError
