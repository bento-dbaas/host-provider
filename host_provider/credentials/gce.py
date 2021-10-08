from host_provider.credentials.base import CredentialAdd, CredentialBase


class CredentialGce(CredentialBase):
    @property
    def project(self):
        return self.content['project']

    @property
    def availability_zones(self):
        return self.content['availability_zones']

    @property
    def region(self):
        return self.content['region']

    @property
    def scopes(self):
        return self.content['scopes']

    @property
    def subnetwork(self):
        return self.content['subnetwork']

    @property
    def vm_service_account(self):
        return self.content['vm_service_account']

    @property
    def network_tag(self):
        return self.content['network_tag']

    @property
    def template_project(self):
        return self.content['template_project']

    @property
    def _zones_field(self):
        return self.availability_zones

    def before_create_host(self, group):
        self._zone = self._get_zone(group)

    def template_to(self, engine):
        return self.content['templates'][engine]

    @property
    def collection_last(self):
        return self.db["gcp_zones_last"]

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
            return self.get_next_zone_from(exist["zone"])

        latest_used = self.last_used_zone()
        if latest_used:
            return self.get_next_zone_from(latest_used["zone"])

        resp = list(self.zones.keys())
        return resp[0]

    @property
    def pubsub(self):
        return self.content['pubsub']

    @property
    def roles(self):
        return self.content['roles']


class CredentialAddGce(CredentialAdd):

    @classmethod
    def is_valid(cls, content):
        return True, ""
