from host_provider.credentials.base import CredentialBase, CredentialAdd


class CredentialAWS(CredentialBase):

    @property
    def keyname(self):
        return self.content['keyname']

    @property
    def region(self):
        return self.content['region']

    def template_to(self, engine):
        return self.content['templates'][engine]

    @property
    def security_group_ids(self):
        return [sg['id'] for sg in self.content['security_groups']]

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
    def _zones_field(self):
        return self.subnets

    def before_create_host(self, group):
        self._zone = self._get_zone(group)

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
    def is_valid(cls, content):
        mim_of_subnets = int(content.get('mimOfSubnets', 0))
        subnets = content.get('subnets', {})
        active_subnets = len(list(filter(
            lambda k, : subnets[k].get('active'),
            content.get('subnets', [])
        )))

        if active_subnets < mim_of_subnets:
            return False, "Must be {} active subnets at least".format(
                mim_of_subnets
            )

        return True, ""
