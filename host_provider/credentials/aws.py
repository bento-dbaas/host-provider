from host_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialAWS(CredentialBase):


    @property
    def region(self):
        return self.content['region']

    def template_to(self, engine):
        return self.content['templates'][engine]

    @property
    def security_group_id(self):
        return self.content['security_group_id']

    @property
    def access_id(self):
        return self.content['access_id']

    @property
    def secret_key(self):
        return self.content['secret_key']

    @property
    def subnets(self):
        return self.content['subnets']

    @property
    def zones(self):
        all_zones = self.subnets
        filtered_zones = {}
        for zone_key in all_zones.keys():
            zone_val = all_zones[zone_key]
            if zone_val['active'] == True:
                filtered_zones[zone_key] = zone_val

        return filtered_zones

    @property
    def zone(self):
        return self._zone

    def before_create_host(self, group):
        self._zone = self._get_zone(group)

    def after_create_host(self, group):
        existing = self.exist_node(group)
        if not existing:
            self.collection_last.update_one(
                {"latestUsed": True, "environment": self.environment},
                {"$set": {"zone": self.zone}}, upsert=True
            )

        self.collection_last.update(
            {"group": group, "environment": self.environment},
            {"$set": {"zone": self.zone}}, upsert=True
        )

    def remove_last_used_for(self, group):
        self.collection_last.delete_one({
            "environment": self.environment, "group": group
        })

    @property
    def collection_last(self):
        return self.db["ec2_zones_last"]

    def exist_node(self, group):
        return self.collection_last.find_one({
            "group": group, "environment": self.environment
        })

    def last_used_zone(self):
        return self.collection_last.find_one({
            "latestUsed": True, "environment": self.environment
        })

    def get_next_zone_from(self, zone_name):
        zones = list(self.zones.keys())
        base_index = zones.index(zone_name)

        next_index = base_index + 1
        if next_index >= len(zones):
            next_index = 0

        return zones[next_index]

    def _get_zone(self, group):
        exist = self.exist_node(group)
        if exist:
            return self.get_next_zone_from(exist["zone"])

        latest_used = self.last_used_zone()
        if latest_used:
            return self.get_next_zone_from(latest_used["zone"])

        resp = list(self.zones.keys())
        return resp[0]


class CredentialAddAWS(CredentialAdd):

    @classmethod
    def is_valid(self):
        # TODO Create validation here
        return True, ""
