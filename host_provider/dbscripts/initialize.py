from peewee import MySQLDatabase
from host_provider.settings import MYSQL_PARAMS
from host_provider.settings import LOGGING_LEVEL
from host_provider.models import Host, IP
import logging

logging.basicConfig(level=LOGGING_LEVEL)
mysql_db = MySQLDatabase(**MYSQL_PARAMS)

def main():
    mysql_db.get_conn()

    try:
        logging.info('Creating Host table')
        mysql_db.create_tables([Host])
    except Exception as e:
        logging.error(e)

    try:
        logging.info('Creating IP table')
        mysql_db.create_tables([IP])
    except Exception as e:
        logging.error(e)

if __name__ == "__main__":
    main()