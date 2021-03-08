from collections import namedtuple


FAKE_CREDENTIAL = {
    "api_key": "Fake-123",
    "mimOfZones": "1",
    "secret_key": "Fake-456",
    "endpoint": "http://cloudstack.internal.com/client/api",
    "secure": False,
    "projectid": "myprojectid",
    "zones": {
        "zone1": {
            "networks": {'redis': [
                {"networkId": "net1", "name": "net_name1"},
                {"networkId": "net2", "name": "net_name2"}]
            },
            "active": True
        }
    },
    "offerings": {
        "1c1024m": {"id": "offering1", "name": "offering_name1"},
        "2c2048m": {"id": "offering2", "name": "offering_name2"}
    },
    "templates": {
        "redis": "template-redis-1"
    }
}

FAKE_CS_NODE_EXTRA = {
    'haenable': 'True',
    'zone_id': 'dd74a65f-5754-48be-b092-61558221101e',
    'zone_name': 'CMAH08BE',
    'key_name': None,
    'password': None,
    'image_id': 'c8455f2b-d93b-4fed-8fe7-fb5cd21a1e1e',
    'image_name': 'mysql-5725-fox-2019-10-22',
    'template_display_text': None,
    'password_enabled': 'False',
    'size_id': 'b01f23d7-0d9d-4301-baa8-cae408216d2e',
    'size_name': 'c1m1',
    'root_device_id': '0',
    'root_device_type': 'ROOT',
    'hypervisor': 'XenServer',
    'project': 'DBaaS_Homolog',
    'project_id': '445d0dd6-12af-4a11-984a-68dc5ebc68ca',
    'nics:': [{
        'id': '47a8c94d-9d45-4f6e-8e1c-63929e8e7977',
        'networkid': 'fake_network_id_b',
        'networkname': 'fake_network_b',
        'netmask': '255.255.255.0',
        'gateway': '10.224.77.1',
        'ipaddress': '10.224.77.220',
        'isolationuri': 'vlan://1287',
        'broadcasturi': 'vlan://1287',
        'traffictype': 'Guest',
        'type': 'Shared',
        'isdefault': True,
        'macaddress': '1e:00:76:00:17:16',
        'secondaryip': [],
        'extradhcpoption': []
    }],
    'security_group': [],
    'affinity_group': [],
    'ip_addresses': [],
    'ip_forwarding_rules': [],
    'port_forwarding_rules': [],
    'created': '2019-09-25T16:04:31-0300',
    'tags': {}
}
FAKE_NODE_OBJ = namedtuple('FakeNodeObj', 'id name extra')
FAKE_CS_NODE = FAKE_NODE_OBJ(
    'fake_node_id', 'fake_node_name', FAKE_CS_NODE_EXTRA
)

FAKE_NETWORK_OBJ = namedtuple('FakeNetworkObj', 'id name extra')
FAKE_NETWORK_A = FAKE_NETWORK_OBJ(
    'fake_network_id_a',
    'fake_network_a',
    {'network_domain': 'fake_network_domain_a.globoi.com'}
)
FAKE_NETWORK_B = FAKE_NETWORK_OBJ(
    'fake_network_id_b',
    'fake_network_b',
    {'network_domain': 'fake_network_domain_b.globoi.com'}
)
FAKE_NETWORK_C = FAKE_NETWORK_OBJ(
    'fake_network_id_c',
    'fake_network_c',
    {'network_domain': 'fake_network_domain_c.globoi.com'}
)
FAKE_EX_LIST_NETWORKS = [FAKE_NETWORK_A, FAKE_NETWORK_B, FAKE_NETWORK_C]

FAKE_HOST = namedtuple('FakeHost', 'id identifier name')('fake_id', 'fake_identifier', 'fake_name')