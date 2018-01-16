from host_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialCloudStack(CredentialBase):

    @property
    def endpoint(self):
        return self.content['endpoint']

    @property
    def api_key(self):
        return self.content['api_key']

    @property
    def secret_key(self):
        return self.content['secret_key']

    def offering_to(self, cpu, memory):
        return self.content['offerings']['{}c{}m'.format(cpu, memory)]

    @property
    def template(self):
        return self.content[self.engine]['template']

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

    @property
    def collection_last(self):
        return self.db["cloudstack_zones_last"]

    def exist_node(self, group):
        return self.collection_last.find_one({
            "group": group, "environment": self.environment
        })

    def last_used_zone(self):
        return self.collection_last.find_one({
            "latestUsed": True, "environment": self.environment
        })

    def get_next_zone_from(self, zone_name):
        zones = list(self.content['zones'].keys())
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

        return list(self.content['zones'].keys())[0]

    @property
    def networks(self):
        zone = self.content['zones'][self.zone]
        if 'networks' in zone:
            return zone['networks'][self.engine]
        raise NotImplementedError("Not network to zone {}".format(self.zone))

    @property
    def project(self):
        if 'projectid' in self.content:
            return self.content['projectid']

    @property
    def secure(self):
        return self.content['secure']


class CredentialAddCloudStack(CredentialAdd):

    @classmethod
    def is_valid(self):
        # TODO Create validation here
        return True, ""
