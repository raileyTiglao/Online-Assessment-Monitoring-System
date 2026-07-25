"""connection/firebase_db.py — Firebase (Firestore) connection + session persistence."""

import firebase_admin
from firebase_admin import credentials, firestore
from config import DatabaseConfig


class FirebaseClient:
    """Owns the Firebase Admin SDK app + Firestore client."""

    def __init__(self, credentials_path: str = None):
        self._credentials_path = credentials_path or DatabaseConfig.FIREBASE_CREDENTIALS_PATH

        if not firebase_admin._apps:
            cred = credentials.Certificate(self._credentials_path)
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()
        print(f"[FirebaseClient] Connected using credentials: {self._credentials_path}")

    def close(self) -> None:
        """No persistent connection to release — kept for interface parity
        with callers that close their DB client unconditionally."""
        pass


class FirestoreSessionRepository:
    """Maps SessionReport data onto a Firestore collection, one document per session."""

    def __init__(self, client: FirebaseClient):
        self._db = client.db

    def save_report(self, report: dict, session_uid: str,
                    examinee_label: str = None) -> str:
        """
        Persist a full report dict (same shape as session_report.json) as a
        single document, keyed by session_uid. The nested "events" list is
        stored as-is — Firestore supports nested arrays/maps within a
        document, and a session's flagged-event count stays well under the
        per-document size limit.
        """
        document = dict(report)
        document["session_uid"] = session_uid
        document["examinee_label"] = examinee_label

        self._db.collection(DatabaseConfig.FIRESTORE_COLLECTION) \
            .document(session_uid).set(document)

        return session_uid
