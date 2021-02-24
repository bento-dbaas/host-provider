from collections import namedtuple


FAKE_GCE_CREDENTIAL = {
    "_id": "fake_id",
    "provider": "gce",
    "service_account": {
        "type": "service_account",
        "project_id": "fake_project_id",
        "private_key_id": "fake_private_key_id",
        "private_key": "fake_private_key",
        "client_email": "fake_client_email",
        "client_id": "fake_client_id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": (
            "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": ""
    },
    "environment": "fake_env",
    "offerings": {
        "2c1024m": {
            "id": "e2-micro",
            "name": "micro instance"
        },
        "2c2048m": {
            "id": "e2-small",
            "name": "small instance"
        },
        "2c4096m": {
            "id": "e2-medium",
            "name": "medium instance"
        }
    },
    "project": "fake_project",
    "availability_zones": {
        "fake_zone_1": {
            "active": True,
            "id": "fake_zone_1",
            "name": "fake_zone_1"
        }
    },
    "subnetwork": "fake/sub/network",
    "templates": {
        "mongodb_3_4_1": "fake_template_mongo_3_4_1",
        "mongodb_4_0_3": "fake_template_mongo_4_0_3",
        "mongodb_4_2_3": "fake_template_mongo_4_2_3"
    },
    "region": "fake_region"
}

FAKE_HOST_OBJ = namedtuple('FakeHostObj', 'id name zone identifier')
FAKE_HOST = FAKE_HOST_OBJ(
    'fake_id', 'fake_host_name', 'fake_zone', 'fake_identifier'
)
