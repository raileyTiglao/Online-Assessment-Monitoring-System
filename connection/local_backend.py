"""
=============================================================================
connection/local_backend.py — Local PHP/MySQL Backend Client (XAMPP)
Online Assessment Monitoring System
Holy Angel University — School of Computing

No-billing alternative to connection/firebase_db.py + firebase_storage.py,
talking to the PHP backend in php_backend/ over plain HTTP instead of
Firestore/Storage. Every class here mirrors the Firebase equivalent's
method signature exactly (LocalExamRepository.get_exam, LocalStorageUploader
.upload, LocalSessionRepository.save_report) so main.py only needs to
choose which classes to construct — the rest of its logic (exam lookup,
screenshot capture, session save) is identical regardless of backend.
=============================================================================
"""

from pathlib import Path

import requests

from config import LocalBackendConfig


class LocalBackendClient:
    """Holds the base URL + API key shared by all local-backend requests."""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or LocalBackendConfig.BASE_URL).rstrip("/")
        self.api_key = api_key or LocalBackendConfig.API_KEY
        print(f"[LocalBackendClient] Using backend at: {self.base_url}")

    def close(self) -> None:
        """No persistent connection to release — kept for interface parity
        with FirebaseClient, whose callers close it unconditionally."""
        pass

    def _headers(self, **extra) -> dict:
        return {"X-Api-Key": self.api_key, **extra}


class LocalExamRepository:
    """Mirrors connection.firebase_db.ExamRepository.get_exam()."""

    def __init__(self, client: LocalBackendClient):
        self._client = client

    def get_exam(self, code: str) -> dict | None:
        """
        Look up an exam by its code via api/resolve_exam_code.php.

        Returns a dict with Firebase-style key names (professorUid, title)
        even though the PHP endpoint returns professorId — so main.py's
        calling code doesn't need to know which backend is active.
        """
        resp = requests.get(
            f"{self._client.base_url}/api/resolve_exam_code.php",
            headers=self._client._headers(),
            params={"code": code},
            timeout=10,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        return {"professorUid": data["professorId"], "title": data["title"]}


class LocalStorageUploader:
    """Mirrors connection.firebase_storage.FirebaseStorageUploader.upload()."""

    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = (base_url or LocalBackendConfig.BASE_URL).rstrip("/")
        self.api_key = api_key or LocalBackendConfig.API_KEY

    def upload(self, local_path: str, dest_path: str) -> str:
        """
        Upload a local file via api/upload_evidence.php.

        Args:
            local_path: Path to the file on disk
            dest_path:  The path EvidenceCapture already constructed, in
                        the form "<prefix>/<owner>/<session_uid>/<filename>"
                        (see monitoring/evidence_capture.py). owner and
                        session_uid are pulled back out of it here since
                        the PHP endpoint wants them as separate form
                        fields, not a pre-built path — the endpoint
                        derives its own storage path server-side.

        Returns:
            The server-confirmed relative path (PHP sanitizes the
            filename, so this may differ slightly from dest_path) —
            source of truth is what the server actually saved, same
            principle as trusting a database's generated ID over a
            client-guessed one.
        """
        parts = dest_path.split("/")
        owner, session_uid, filename = parts[-3], parts[-2], parts[-1]
        professor_id = "" if owner == "_unassigned" else owner

        with open(local_path, "rb") as f:
            resp = requests.post(
                f"{self.base_url}/api/upload_evidence.php",
                headers={"X-Api-Key": self.api_key},
                files={"file": (filename, f, "image/jpeg")},
                data={"session_id": session_uid, "professor_id": professor_id},
                timeout=15,
            )
        resp.raise_for_status()
        return resp.json()["path"]


class LocalSessionRepository:
    """Mirrors connection.firebase_db.FirestoreSessionRepository.save_report()."""

    def __init__(self, client: LocalBackendClient):
        self._client = client

    def save_report(self, report: dict, session_uid: str,
                    examinee_label: str = None) -> str:
        """POST the full report dict to api/save_session.php."""
        document = dict(report)
        document["session_uid"] = session_uid
        document["examinee_label"] = examinee_label

        resp = requests.post(
            f"{self._client.base_url}/api/save_session.php",
            headers=self._client._headers(**{"Content-Type": "application/json"}),
            json=document,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["session_id"]
