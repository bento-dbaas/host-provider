from os import getenv


LIBCLOUD_CA_CERTS_PATH = getenv("LIBCLOUD_CA_CERTS_PATH", None)


MONGODB_HOST = getenv("MONGODB_HOST", "127.0.0.1")
MONGODB_PORT = getenv("MONGODB_PORT", 27017)
MONGODB_DB = getenv("MONGODB_DB", "host_provider")
MONGODB_USER = getenv("MONGODB_USER", None)
MONGODB_PWD = getenv("MONGODB_PWD", None)


MYSQL_HOST = getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = getenv("MYSQL_PORT", 3306)
MYSQL_DB = getenv("MYSQL_DB", "host_provider")
MYSQL_USER = getenv("MYSQL_USER", "root")
MYSQL_PWD = getenv("MYSQL_PWD", "")

MYSQL_PARAMS = {"database": MYSQL_DB, "host": MYSQL_HOST, "port": MYSQL_PORT}
if MYSQL_USER:
    MYSQL_PARAMS["user"] = MYSQL_USER
    MYSQL_PARAMS["password"] = MYSQL_PWD
