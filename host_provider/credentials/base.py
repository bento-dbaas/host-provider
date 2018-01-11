from pymongo import MongoClient
from host_provider.settings import MONGODB_DB, MONGODB_HOST, MONGODB_PORT, \
    MONGODB_USER, MONGODB_PWD


class CredentialConnection(object):

    def __init__(self, provider, environment):
        self.provider = provider
        self.environment = environment
        self._collection = None
        self._content = None

    @property
    def collection(self):
        if not self._collection:
            client = MongoClient(
                host=MONGODB_HOST, port=MONGODB_PORT,
                username=MONGODB_USER, password=MONGODB_PWD
            )
            db = client[MONGODB_DB]
            self._collection = db[self.provider]
        return self._collection

    @property
    def content(self):
        return self._content



class CredentialBase(CredentialConnection):

    def __init__(self, provider, environment, engine):
        super(CredentialBase, self).__init__(provider, environment)
        self.engine = engine

    def get_content(self):
        return self.collection.find_one({"environment": self.environment})

    @property
    def content(self):
        if not self._content:
            self._content = self.get_content()
        return super(CredentialBase, self).content


class CredentialAdd(CredentialConnection):

    def __init__(self, environment, content):
        super(CredentialAdd, self).__init__(environment)
        self._content = content

    def save(self):
        return self.collection.insert_one({
            'environment': self.environment, **self.content,
        })

    def is_valid(self):
        raise NotImplementedError
