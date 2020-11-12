from host_provider.credentials.base import CredentialBase, CredentialAdd
from host_provider.models import Host


class CredentialCloudStack(CredentialBase):

    def __init__(self, provider, environment, engine):
        super(CredentialCloudStack, self).__init__(provider, environment, engine)
        self._zone_increment = 0

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
        return self.content['offerings']['{}c{}m'.format(cpu, memory)]['id']

    def template_to(self, engine):
        return self.content['templates'][engine]

    @property
    def template(self):
        templates = self.content['templates']
        return templates[self.engine]

    @property
    def _zones_field(self):
        return self.content['zones']

    @property
    def already_tried_all_zones(self):
        return self._zone_increment >= len(self.zones)

    def _used_all_available_zones(self, used_zones):
        return len(used_zones) >= len(self.zones)

    @staticmethod
    def _zone_already_used(zone, used_zones):
        return zone in used_zones

    def before_create_host(self, group):
        used_zones = set([host.zone for host in Host.filter(group=group)])
        while True:
            if self.already_tried_all_zones:
                raise Exception("No zone available")
            zone = self._get_zone(group)
            if self._used_all_available_zones(used_zones):
                break
            if not self._zone_already_used(zone, used_zones):
                break
            self._zone_increment += 1
        self._zone_increment += 1
        self._zone = zone

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
        return self.db["cloudstack_zones_last"]

    def exist_node(self, group):
        return self.collection_last.find_one({
            "group": group, "environment": self.environment
        })

    def last_used_zone(self):
        return self.collection_last.find_one({
            "latestUsed": True, "environment": self.environment
        })

    def _get_zone(self, group):
        exist = self.exist_node(group)
        if exist:
            return self.get_next_zone_from(exist["zone"], self._zone_increment)

        latest_used = self.last_used_zone()
        if latest_used:
            return self.get_next_zone_from(latest_used["zone"], self._zone_increment)

        zones = list(self.zones.keys())
        return self.get_next_zone_from(zones[0], self._zone_increment)

    @property
    def networks(self):
        zone = self.content['zones'][self.zone]
        if 'networks' not in zone:
            raise NotImplementedError(
                "Not network to zone {}".format(self.zone)
            )

        return [net['networkId'] for net in zone['networks'][self.engine]]

    @property
    def project(self):
        if 'projectid' in self.content:
            return self.content['projectid']

    @property
    def secure(self):
        return self.content.get('secure', False)


class CredentialAddCloudStack(CredentialAdd):

    @classmethod
    def is_valid(cls, content):
        mim_of_zones = int(content.get('mimOfZones', 0))
        zones = content.get('zones', {})
        active_zones = len(list(filter(
            lambda k, : zones[k].get('active'),
            content.get('zones', [])
        )))

        if active_zones < mim_of_zones:
            return False, "Must be {} active zones at least".format(
                mim_of_zones
            )

        return True, ""
