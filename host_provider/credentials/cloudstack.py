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
    def create_attempts(self):
        return len(self.zones)

    def before_create_host(self, group):
        hosts = Host.filter(group=group)
        used_zones = (host.zone for host in hosts)
        available_zones = self.zones
        while True:
            self._zone_increment += 1
            zone = self._get_zone(group)
            if len(used_zones) >= len(available_zones):
                break
            if zone not in used_zones:
                break
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
        return self.get_next_zone_from(zones[-1], self._zone_increment)

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
