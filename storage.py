"""Storage isolated from the workbook parser; unrelated subparty data is untouched."""
import firebase_admin
from firebase_admin import credentials, firestore

COLLECTION = 'polkcounty_incidents'


def connect(config):
    if config.get('project_id') != 'subparty':
        raise ValueError('Firebase project must be subparty.')
    try:
        app = firebase_admin.get_app('polkcounty')
    except ValueError:
        app = firebase_admin.initialize_app(credentials.Certificate(dict(config)), name='polkcounty')
    return firestore.client(app)


def load_records(client):
    return [doc.to_dict() for doc in client.collection(COLLECTION).stream()]


def save_records(client, records, progress=None):
    """Idempotent merges preserve follow-up information on reimport."""
    saved = 0
    for offset in range(0, len(records), 400):
        chunk = records[offset:offset + 400]
        batch = client.batch()
        for record in chunk:
            payload = dict(record, updated_at=firestore.SERVER_TIMESTAMP)
            batch.set(client.collection(COLLECTION).document(record['id']), payload, merge=True)
        batch.commit()
        saved += len(chunk)
        if progress:
            progress(saved)
    return saved
