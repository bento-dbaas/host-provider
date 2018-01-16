from datetime import datetime
from peewee import MySQLDatabase, Model, DateTimeField, CharField, \
    PrimaryKeyField, IntegerField
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


def initialize_database():
    mysql_db.get_conn()
    mysql_db.create_tables([Host])
