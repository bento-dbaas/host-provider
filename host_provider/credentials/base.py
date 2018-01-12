from pymongo import MongoClient
from host_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD


class CredentialMongoDB(object):

    def __init__(self, provider, environment):
        self.provider = provider
        self.environment = environment
        self._collection_credential = None
        self._content = None

    @property
    def credential(self):
        if not self._collection_credential:
            client = MongoClient(
                host=MONGODB_HOST, port=MONGODB_PORT,
                username=MONGODB_USER, password=MONGODB_PWD
            )
            db = client[MONGODB_DB]
            self._collection_credential = db["credential"]
        return self._collection_credential

    @property
    def content(self):
        return self._content


class CredentialBase(CredentialMongoDB):

    def __init__(self, provider, environment, engine):
        super(CredentialBase, self).__init__(provider, environment)
        self.engine = engine

    def get_content(self):
        content = self.credential.find_one({
            "provider": self.provider,
            "environment": self.environment,
        })
        if content:
            return content

        raise NotImplementedError("No {} credential for {}".format(
            self.provider, self.environment
        ))

    @property
    def content(self):
        if not self._content:
            self._content = self.get_content()
        return super(CredentialBase, self).content


class CredentialAdd(CredentialMongoDB):

    def __init__(self, provider, environment, content):
        super(CredentialAdd, self).__init__(provider, environment)
        self._content = content

    def save(self):
        return self.credential.insert_one({
            'provider': self.provider,
            'environment': self.environment, **self.content,
        })

    def is_valid(self):
        raise NotImplementedError
