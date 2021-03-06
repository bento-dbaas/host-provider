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
            "id": "fake_offering_2c1024m",
            "name": "micro instance"
        },
        "2c2048m": {
            "id": "fake_offering_2c2048m",
            "name": "small instance"
        },
        "2c4096m": {
            "id": "fake_offering_2c4096m",
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

FAKE_STATIC_IP_OBJ = namedtuple('FakeStaticIP', 'id name address')
FAKE_STATIC_IP = FAKE_STATIC_IP_OBJ(
    'fake_id', 'fake_ip_name', 'fake_address'
)

FAKE_GOOGLE_RESPONSE_STATIC_IP = {'address': 'fake_address'}
