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
        return list(self.content['zones'].keys())[0]

    @property
    def networks(self):
        zone = self.content['zones'][self.zone]
        if 'networks' in zone:
            return zone['networks']
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
