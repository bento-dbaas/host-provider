from collections import namedtuple
from host_provider.credentials.base import CredentialMongoDB, CredentialAdd, CredentialBase


class FakeMongoDB(object):

    metadata = []
    ids = [0]

    def insert_one(self, data):
        if "raise" in data:
            raise Exception("Wrong values")

        InsertInfo = namedtuple("InsertInfo", "inserted_id")

        self.metadata.append(data)
        new_id = self.ids[-1] + 1
        self.ids.append(new_id)
        return InsertInfo(inserted_id=new_id)

    def find_one(self, filter):
        for line in self.metadata:
            for key, value in filter.items():
                if line.get(key, None) == value:
                    return line
        return None

    @classmethod
    def clear(cls):
        cls.metadata = []


class CredentialFakeDB(CredentialMongoDB):

    @property
    def credential(self):
        if not self._collection_credential:
            self._collection_credential = FakeMongoDB()
        return self._collection_credential


class CredentialBaseFake(CredentialFakeDB, CredentialBase):
    pass


class CredentialAddFake(CredentialFakeDB, CredentialAdd):

    def is_valid(self):
        if "fake" not in self.content:
            return False, "Should have fake field"
        return True, None
