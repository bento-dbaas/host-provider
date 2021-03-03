from copy import deepcopy
from datetime import datetime
from peewee import MySQLDatabase, Model, DateTimeField, CharField, \
    PrimaryKeyField, IntegerField, ForeignKeyField
from host_provider.settings import MYSQL_PARAMS


mysql_db = MySQLDatabase(**MYSQL_PARAMS)


class BaseModel(Model):

    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField()

    class Meta:
        database = mysql_db

    def save(self, force_insert=False, only=None):
        self.updated_at = datetime.now()
        super(BaseModel, self).save(force_insert, only)


class Host(BaseModel):
    id = PrimaryKeyField()
    name = CharField()
    group = CharField()
    engine = CharField()
    environment = CharField()
    cpu = IntegerField()
    memory = IntegerField()
    provider = CharField()
    identifier = CharField()
    address = CharField()
    zone = CharField(null=True)

    @property
    def to_dict(self):
        my_data = deepcopy(self._data)
        if 'password' in my_data:
            my_data.pop('password')
        my_data['zone_id'] = self.zone
        my_data['zone'] = self.credential.zone_by_id(self.zone)
        return my_data

    @property
    def credential(self):
        from host_provider.providers import get_provider_to
        provider_cls = get_provider_to(self.provider)
        provider = provider_cls(self.environment, self.engine, None)
        return provider.credential


class IP(BaseModel):
    id = PrimaryKeyField()
    name = CharField()
    group = CharField()
    host = ForeignKeyField(Host, null=True, on_delete='SET NULL')
    address = CharField()

    @property
    def to_dict(self):
        return self._data


def initialize_database():
    mysql_db.get_conn()
    mysql_db.create_tables([Host, IP])
