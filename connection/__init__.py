"""connection package — Firebase/Firestore persistence for session reports."""

from .firebase_db import FirebaseClient, FirestoreSessionRepository

__all__ = ["FirebaseClient", "FirestoreSessionRepository"]
