from os import getenv
import re
import json
import logging


LIBCLOUD_CA_CERTS_PATH = getenv("LIBCLOUD_CA_CERTS_PATH", None)

MONGODB_HOST = getenv("MONGODB_HOST", "127.0.0.1")
MONGODB_PORT = int(getenv("MONGODB_PORT", 27017))
MONGODB_DB = getenv("MONGODB_DB", "host_provider")
MONGODB_USER = getenv("MONGODB_USER", None)
MONGODB_PWD = getenv("MONGODB_PWD", None)
MONGO_ENDPOINT = getenv("DBAAS_MONGODB_ENDPOINT", None)


MYSQL_HOST = getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(getenv("MYSQL_PORT", 3306))
MYSQL_DB = getenv("MYSQL_DB", "host_provider")
MYSQL_USER = getenv("MYSQL_USER", "root")
MYSQL_PWD = getenv("MYSQL_PWD", "")
DBAAS_MYSQL_ENDPOINT = getenv("DBAAS_MYSQL_ENDPOINT")

if DBAAS_MYSQL_ENDPOINT:
    matched_string = re.search(
        'mysql://(.*):(.*)@(.*):(\d+)/(.*)', DBAAS_MYSQL_ENDPOINT
    )
    if matched_string:
        MYSQL_USER, MYSQL_PWD, MYSQL_HOST, MYSQL_PORT, MYSQL_DB  = matched_string.groups()
        MYSQL_PORT = int(MYSQL_PORT)


MYSQL_PARAMS = {"database": MYSQL_DB, "host": MYSQL_HOST, "port": MYSQL_PORT}
if MYSQL_USER:
    MYSQL_PARAMS["user"] = MYSQL_USER
    MYSQL_PARAMS["password"] = MYSQL_PWD

APP_USERNAME = getenv("APP_USERNAME", None)
APP_PASSWORD = getenv("APP_PASSWORD", None)
HTTP_PROXY = getenv("DBAAS_HTTP_PROXY", None)
HTTPS_PROXY = getenv("DBAAS_HTTPS_PROXY", None)

TEAM_API_URL = getenv("TEAM_API_URL", None)
DBAAS_TEAM_API_URL = getenv("DBAAS_TEAM_API_URL", None)
USER_DBAAS_API = getenv("USER_DBAAS_API", "user")
PASSWORD_DBAAS_API = getenv("PASSWORD_DBAAS_API", "password")

LOGGING_LEVEL = int(getenv('LOGGING_LEVEL', logging.INFO))
SENTRY_DSN = getenv("SENTRY_DSN", None)
