from peewee import MySQLDatabase
from playhouse.migrate import migrate, MySQLMigrator
from peewee import BooleanField
from host_provider.settings import MYSQL_PARAMS
from host_provider.settings import LOGGING_LEVEL
import logging

logging.basicConfig(level=LOGGING_LEVEL)
mysql_db = MySQLDatabase(**MYSQL_PARAMS)
migrator = MySQLMigrator(mysql_db)


def main():

    try:
        logging.info("Add 'status' column on 'Host' table")
        recreating_field = BooleanField(default=False)
        migrate(migrator.add_column('host', 'recreating', recreating_field))
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    main()
