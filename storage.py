"""Firestore retains attendance independently of Streamlit sessions/deployments."""
import firebase_admin
from firebase_admin import credentials, firestore
from attendance import occurrence_id, is_polk, STATUSES

COLLECTION = 'polkcounty_incidents'
IMPORTS = 'polkcounty_imports'
METADATA = 'polkcounty_metadata'


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


def load_imports(client):
    logs = client.collection(IMPORTS).order_by('started_at', direction=firestore.Query.DESCENDING).limit(25).stream()
    return [doc.to_dict() for doc in logs]


def save_records(client, records, progress=None, import_info=None):
    """Atomic batches include durable progress; repeat uploads reuse incident IDs."""
    for record in records:
        if not is_polk(record.get('district')) or record.get('status') not in STATUSES:
            raise ValueError('Only valid Polk County incidents can be stored.')
        if record.get('id') != occurrence_id(record):
            raise ValueError('Invalid incident identity.')
    if not records:
        return 0
    log = client.collection(IMPORTS).document()
    log.set(dict(import_info or {}, started_at=firestore.SERVER_TIMESTAMP,
                 status='in_progress', total_records=len(records), saved_records=0))
    saved = 0
    try:
        for offset in range(0, len(records), 400):
            chunk = records[offset:offset + 400]
            batch = client.batch()
            for record in chunk:
                payload = dict(record, updated_at=firestore.SERVER_TIMESTAMP, last_import_id=log.id)
                batch.set(client.collection(COLLECTION).document(record['id']), payload, merge=True)
            finished = offset + len(chunk) == len(records)
            batch.set(log, {'saved_records': saved + len(chunk),
                           'status': 'completed' if finished else 'in_progress',
                           'updated_at': firestore.SERVER_TIMESTAMP}, merge=True)
            if finished:
                batch.set(client.collection(METADATA).document('app'), {
                    'district': 'Polk County', 'schema_version': 1,
                    'last_successful_import': firestore.SERVER_TIMESTAMP,
                    'last_import_id': log.id}, merge=True)
            batch.commit()
            saved += len(chunk)
            if progress:
                progress(saved)
    except Exception:
        # Never mask the original failure if writing the failure log also fails.
        try:
            log.set({'status': 'interrupted', 'updated_at': firestore.SERVER_TIMESTAMP}, merge=True)
        except Exception:
            pass
        raise
    return saved
