from collections import namedtuple
from host_provider.credentials.base import CredentialMongoDB, CredentialAdd


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


class CredentialFakeDB(CredentialMongoDB):

    @property
    def collection(self):
        if not self._collection:
            self._collection = FakeMongoDB()
        return self._collection

    @property
    def content(self):
        return self._content


class CredentialAddFake(CredentialFakeDB, CredentialAdd):

    def is_valid(self):
        if "fake" not in self.content:
            return False, "Should have fake field"
        return True, None
