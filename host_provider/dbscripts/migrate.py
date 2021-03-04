from peewee import MySQLDatabase
from playhouse.migrate import migrate, MySQLMigrator
from peewee import (
    DateTimeField,
    CharField,
    PrimaryKeyField,
    IntegerField,
    ForeignKeyField
)
from host_provider.settings import MYSQL_PARAMS
from host_provider.settings import LOGGING_LEVEL
from host_provider.models import Host, IP
import logging

logging.basicConfig(level=LOGGING_LEVEL)
mysql_db = MySQLDatabase(**MYSQL_PARAMS)
migrator = MySQLMigrator(mysql_db)

def main():

    try:
        logging.info("Add 'status' column on 'Host' table")
        status_field = IntegerField(null=True, default=1)
        migrate(migrator.add_column('Host', 'status', status_field))
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    main()