from collections import OrderedDict
from pymongo import MongoClient
from host_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD


class CredentialMongoDB(object):

    def __init__(self, provider, environment):
        self.provider = provider
        self.environment = environment
        self._db = None
        self._collection_credential = None
        self._content = None

    @property
    def db(self):
        if not self._db:
            client = MongoClient(
                host=MONGODB_HOST, port=MONGODB_PORT,
                username=MONGODB_USER, password=MONGODB_PWD,
                document_class=OrderedDict
            )
            self._db = client[MONGODB_DB]

        return self._db

    @property
    def credential(self):
        if not self._collection_credential:
            self._collection_credential = self.db["credential"]
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

    def before_create_host(self, group):
        pass

    def after_create_host(self, group):
        pass


class CredentialAdd(CredentialMongoDB):

    def __init__(self, provider, environment, content):
        super(CredentialAdd, self).__init__(provider, environment)
        self._content = content

    def save(self):
        return self.credential.find_one_and_update(
            {
                'provider': self.provider,
                'environment': self.environment
            },
            {'$set': {
                'provider': self.provider,
                'environment': self.environment, **self.content
            }},
            upsert=True
        )

    def delete(self):
        return self.credential.delete_one({
            'provider': self.provider, 'environment': self.environment
        })

    def is_valid(self):
        raise NotImplementedError
