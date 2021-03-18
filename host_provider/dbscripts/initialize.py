from peewee import MySQLDatabase
from host_provider.settings import MYSQL_PARAMS
from host_provider.settings import LOGGING_LEVEL
from host_provider.models import Host, IP
import logging

logging.basicConfig(level=LOGGING_LEVEL)
mysql_db = MySQLDatabase(**MYSQL_PARAMS)


def try_create_table(model):
    mysql_db.get_conn()
    try:
        logging.info('Creating {} table'.format(model))
        mysql_db.create_tables([model])
    except Exception as e:
        logging.error(e)


def main():
    try_create_table(Host)
    try_create_table(IP)

if __name__ == "__main__":
    main()
