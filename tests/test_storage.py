import unittest
from attendance import occurrence_id
from storage import save_records, load_records, COLLECTION, IMPORTS


class Snapshot:
    def __init__(self, data): self.data = data
    def to_dict(self): return dict(self.data)


class Document:
    def __init__(self, store, key):
        self.store, self.key, self.id = store, key, key.split('/')[-1]
    def set(self, data, merge=False):
        self.store[self.key] = dict(self.store.get(self.key, {}) if merge else {}, **data)


class Collection:
    def __init__(self, store, name): self.store, self.name = store, name
    def document(self, identity=None):
        if identity is None:
            identity = 'import-' + str(len(self.store))
        return Document(self.store, self.name + '/' + identity)
    def stream(self):
        return [Snapshot(data) for key, data in self.store.items() if key.startswith(self.name + '/')]


class Batch:
    def __init__(self, client): self.client, self.writes = client, []
    def set(self, ref, data, merge=False): self.writes.append((ref, data, merge))
    def commit(self):
        self.client.commits += 1
        if self.client.fail_on == self.client.commits:
            raise RuntimeError('Connection interrupted')
        for ref, data, merge in self.writes:
            ref.set(data, merge)


class Client:
    def __init__(self, store, fail_on=None): self.store, self.fail_on, self.commits = store, fail_on, 0
    def collection(self, name): return Collection(self.store, name)
    def batch(self): return Batch(self)


def row(index=0):
    record = {'person_id':f'ats:{index}', 'ats_id':str(index), 'name':'Test Employee',
        'date':'2026-09-01', 'status':'No Show', 'district':'Polk'}
    record['id'] = occurrence_id(record)
    return record


class StorageTests(unittest.TestCase):
    def test_reconnect_and_reimport_keep_history_without_duplicates(self):
        backing_store = {}
        first = Client(backing_store)
        save_records(first, [row()], import_info={'filename':'test.xlsx'})
        second = Client(backing_store)
        loaded = load_records(second)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]['person_id'], 'ats:0')
        # Preserve follow-up fields not in the imported workbook.
        backing_store[COLLECTION + '/' + row()['id']]['addressed'] = True
        save_records(second, [row()])
        self.assertEqual(len(load_records(Client(backing_store))), 1)
        self.assertTrue(load_records(second)[0]['addressed'])
        self.assertEqual(len(list(second.collection(IMPORTS).stream())), 2)

    def test_interrupted_batch_keeps_committed_history_and_can_resume(self):
        backing_store = {}
        progress = []
        records = [row(i) for i in range(401)]
        with self.assertRaises(RuntimeError):
            save_records(Client(backing_store, fail_on=2), records, progress.append)
        self.assertEqual(progress, [400])
        self.assertEqual(len(load_records(Client(backing_store))), 400)
        log = list(Client(backing_store).collection(IMPORTS).stream())[0].to_dict()
        self.assertEqual(log['saved_records'], 400)
        self.assertEqual(log['status'], 'interrupted')
        save_records(Client(backing_store), records)
        self.assertEqual(len(load_records(Client(backing_store))), 401)

    def test_other_counties_rejected_before_writing(self):
        backing_store = {}
        record = dict(row(), district='HCPS')
        with self.assertRaises(ValueError): save_records(Client(backing_store), [record])
        self.assertEqual(backing_store, {})
