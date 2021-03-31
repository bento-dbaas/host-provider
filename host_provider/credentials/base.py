from pymongo import MongoClient, ReturnDocument
from host_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD, MONGO_ENDPOINT

from dbaas_base_provider import BaseCredential


class CredentialMongoDB(BaseCredential):

    @property
    def provider_type(self):
        return 'host_provider'


    def __init__(self, provider, environment):
        super(CredentialMongoDB, self).__init__(
            provider,
            environment
        )
        self.MONGO_ENDPOINT = MONGO_ENDPOINT
        self.MONGODB_HOST = MONGODB_HOST
        self.MONGODB_USER = MONGODB_USER
        self.MONGODB_PORT = MONGODB_PORT
        self.MONGODB_PWD = MONGODB_PWD
        self.MONGODB_DB = MONGODB_DB


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

    def offering_to(self, cpu, memory):
        return self.content['offerings']['{}c{}m'.format(cpu, memory)]['id']

    def before_create_host(self, group):
        pass

    def after_create_host(self, group):
        existing = self.exist_node(group)
        if not existing:
            self.collection_last.update_one(
                {"latestUsed": True, "environment": self.environment},
                {"$set": {"zone": self.zone}}, upsert=True
            )

        self.collection_last.update(
            {"group": group, "environment": self.environment},
            {"$set": {"zone": self.zone}}, upsert=True
        )

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
        if not zone_id:
            return None
        zones = self.__get_zones(id=zone_id)
        zone_id, values = zones.popitem()
        return values['name']

    def get_next_zone_from(self, zone_name, increment=0):
        zones = list(self.zones.keys())
        try:
            base_index = zones.index(zone_name)
        except ValueError:
            next_index = increment
        else:
            next_index = base_index + increment + 1
            if next_index >= len(zones):
                next_index = next_index - len(zones)
        return zones[next_index]


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
