from os import getenv


LIBCLOUD_CA_CERTS_PATH = getenv("LIBCLOUD_CA_CERTS_PATH", None)


MONGODB_HOST = getenv("MONGODB_HOST", "127.0.0.1")
MONGODB_PORT = getenv("MONGODB_PORT", 27017)
MONGODB_DB = getenv("MONGODB_DB", "host_provider")
MONGODB_USER = getenv("MONGODB_USER", None)
MONGODB_PWD = getenv("MONGODB_PWD", None)
