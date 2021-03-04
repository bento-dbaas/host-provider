from peewee import MySQLDatabase
from host_provider.settings import MYSQL_PARAMS
from host_provider.settings import LOGGING_LEVEL
from host_provider.models import Host, IP
import logging

logging.basicConfig(level=LOGGING_LEVEL)
mysql_db = MySQLDatabase(**MYSQL_PARAMS)

def main():
    mysql_db.get_conn()


if __name__ == "__main__":
    main()