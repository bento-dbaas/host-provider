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
