"""connection/firebase_storage.py — Firebase Storage evidence screenshot upload."""

import firebase_admin
from firebase_admin import storage
from config import DatabaseConfig


class FirebaseStorageUploader:
    """Uploads local evidence files to the project's default Storage bucket."""

    def __init__(self, bucket_name: str = None):
        self._bucket = storage.bucket(
            bucket_name or DatabaseConfig.STORAGE_BUCKET,
            app=firebase_admin.get_app(),
        )

    def upload(self, local_path: str, dest_path: str) -> str:
        """
        Upload a local file to dest_path within the bucket.

        Args:
            local_path: Path to the file on disk (e.g. a screenshot just
                        written by EvidenceCapture)
            dest_path:  Destination object path within the bucket, e.g.
                        "evidence/<professor_uid>/<session_uid>/<filename>.jpg"

        Returns:
            dest_path — the Storage object path (not a URL). The dashboard
            resolves a download URL client-side via getDownloadURL(), gated
            by storage.rules, rather than embedding a long-lived signed URL
            here.
        """
        blob = self._bucket.blob(dest_path)
        blob.upload_from_filename(local_path)
        return dest_path
