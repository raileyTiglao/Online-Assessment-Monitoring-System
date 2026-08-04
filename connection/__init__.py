"""connection package — session report persistence (local PHP/MySQL or Firebase)."""

from .firebase_db import FirebaseClient, FirestoreSessionRepository, ExamRepository
from .firebase_storage import FirebaseStorageUploader
from .local_backend import (
    LocalBackendClient, LocalSessionRepository, LocalExamRepository,
    LocalStorageUploader,
)

__all__ = [
    "FirebaseClient", "FirestoreSessionRepository", "ExamRepository",
    "FirebaseStorageUploader",
    "LocalBackendClient", "LocalSessionRepository", "LocalExamRepository",
    "LocalStorageUploader",
]
