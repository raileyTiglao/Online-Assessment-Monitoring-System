"""
=============================================================================
connection/seed_emulator.py — Seed the Firebase Local Emulator Suite
Online Assessment Monitoring System
Holy Angel University — School of Computing

Populates the Auth/Firestore/Storage emulators with one professor account,
one admin account, one exam, one session with mixed MODERATE/HIGH fake
events, and a dummy screenshot upload — enough to develop/test the
dashboard against realistic data without a real webcam session or a real
Firebase project.

Sets the emulator env vars itself (a "demo-" prefixed project ID needs no
real credentials) BEFORE initializing firebase_admin, so this script can
never accidentally write to production even if you forgot to export them
yourself.

Prerequisites:
    firebase emulators:start   (run from the repo root, in another terminal)

Usage (run as a module, from the repo root — same reason as
bootstrap_admin.py, config.py must be importable):
    py -3.11 -m connection.seed_emulator
=============================================================================
"""

import os

DEMO_PROJECT_ID = "demo-oams"
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
# NOTE: FIREBASE_STORAGE_EMULATOR_HOST is a Node.js/Firebase-CLI convention
# that the Python google-cloud-storage client (which firebase_admin.storage
# uses under the hood) does NOT recognize — without STORAGE_EMULATOR_HOST
# set, upload_from_filename() silently targets the real
# storage.googleapis.com instead of the local emulator.
os.environ.setdefault("STORAGE_EMULATOR_HOST", "http://127.0.0.1:9199")
os.environ.setdefault("GCLOUD_PROJECT", DEMO_PROJECT_ID)
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", DEMO_PROJECT_ID)

import tempfile
from datetime import datetime, timedelta, timezone

import google.auth.credentials
import firebase_admin
from firebase_admin import auth, credentials, firestore, storage


class _EmulatorCredential(credentials.Base):
    """
    firebase_admin.initialize_app() always wants a credentials.Base
    instance, and credentials.ApplicationDefault() eagerly resolves real
    Google Cloud credentials at init time (google.auth.default()) even
    when every actual call will hit an emulator — it fails immediately on
    a machine with no gcloud login configured, which is exactly this
    machine. AnonymousCredentials satisfies the interface without ever
    touching a real auth provider; the emulators don't check them anyway.
    """

    def get_credential(self):
        return google.auth.credentials.AnonymousCredentials()

PROFESSOR_EMAIL = "professor@example.hau.edu.ph"
ADMIN_EMAIL = "admin@example.hau.edu.ph"
DEMO_PASSWORD = "password123"


def init_app() -> None:
    if not firebase_admin._apps:
        firebase_admin.initialize_app(
            _EmulatorCredential(),
            {"projectId": DEMO_PROJECT_ID, "storageBucket": f"{DEMO_PROJECT_ID}.appspot.com"},
        )


def get_or_create_user(email: str, password: str, display_name: str):
    try:
        return auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return auth.create_user(email=email, password=password, display_name=display_name)


def seed_users(db):
    professor = get_or_create_user(PROFESSOR_EMAIL, DEMO_PASSWORD, "Dr. Jane Dela Cruz")
    auth.set_custom_user_claims(professor.uid, {"role": "professor"})
    db.collection("users").document(professor.uid).set({
        "email": professor.email,
        "displayName": professor.display_name,
        "role": "professor",
        "active": True,
        "createdAt": datetime.now(timezone.utc),
        "createdBy": "seed_emulator",
    })

    admin_user = get_or_create_user(ADMIN_EMAIL, DEMO_PASSWORD, "System Admin")
    auth.set_custom_user_claims(admin_user.uid, {"role": "admin"})
    db.collection("users").document(admin_user.uid).set({
        "email": admin_user.email,
        "displayName": admin_user.display_name,
        "role": "admin",
        "active": True,
        "createdAt": datetime.now(timezone.utc),
        "createdBy": "seed_emulator",
    })

    print(f"[seed_emulator] Professor: {PROFESSOR_EMAIL} / {DEMO_PASSWORD}")
    print(f"[seed_emulator] Admin:     {ADMIN_EMAIL} / {DEMO_PASSWORD}")
    return professor.uid, admin_user.uid


def seed_exam(db, professor_uid: str) -> str:
    code = "EXAM-DEMO1"
    db.collection("exams").document(code).set({
        "code": code,
        "title": "Physics Midterm (seeded)",
        "professorUid": professor_uid,
        "professorEmail": PROFESSOR_EMAIL,
        "createdAt": datetime.now(timezone.utc),
        "active": True,
    })
    print(f"[seed_emulator] Exam code: {code}")
    return code


def seed_dummy_screenshot(session_uid: str, professor_uid: str) -> str:
    """
    A tiny valid JPEG (solid gray square) so ScreenshotViewer has something
    real to getDownloadURL() during dashboard development — the actual
    pixel content doesn't matter.
    """
    import numpy as np
    import cv2

    dest_path = f"evidence/{professor_uid}/{session_uid}/high_risk_seeded.jpg"
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        frame = np.full((360, 640, 3), 128, dtype=np.uint8)
        cv2.putText(frame, "SEEDED SCREENSHOT", (140, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imwrite(tmp.name, frame)
        bucket = storage.bucket()
        blob = bucket.blob(dest_path)
        blob.upload_from_filename(tmp.name)

    print(f"[seed_emulator] Uploaded dummy screenshot: {dest_path}")
    return dest_path


def seed_session(db, professor_uid: str, exam_code: str):
    session_uid = "sess_seeded_demo_0001"
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=12)

    screenshot_path = seed_dummy_screenshot(session_uid, professor_uid)

    events = [
        {
            "timestamp": (start + timedelta(minutes=3)).isoformat(),
            "risk_level": "MODERATE",
            "yaw": 18.4, "pitch": -6.2, "roll": 3.1,
            "device_detected": False,
            "behavioral_indicator": "Head turned right (+18.4° from baseline)",
            "trigger": "Suspicious head pose 42% of window",
            "screenshot_path": None,
        },
        {
            "timestamp": (start + timedelta(minutes=7)).isoformat(),
            "risk_level": "HIGH",
            "yaw": 34.7, "pitch": -14.9, "roll": 5.0,
            "device_detected": True,
            "behavioral_indicator": "Looking down (-14.9° from baseline)",
            "trigger": "Dual-modal: device + suspicious head pose co-occurred 58% of window",
            "screenshot_path": screenshot_path,
        },
        {
            "timestamp": (start + timedelta(minutes=9, seconds=30)).isoformat(),
            "risk_level": "MODERATE",
            "yaw": -20.1, "pitch": -3.0, "roll": -2.2,
            "device_detected": False,
            "behavioral_indicator": "Head turned left (-20.1° from baseline)",
            "trigger": "Suspicious head pose 37% of window",
            "screenshot_path": None,
        },
    ]

    document = {
        "session_start": start.isoformat(),
        "session_end": now.isoformat(),
        "calibration_baseline": {"yaw": 1.2, "pitch": -0.8, "roll": 0.4, "sample_count": 42},
        "total_flagged_events": len(events),
        "high_risk_count": sum(1 for e in events if e["risk_level"] == "HIGH"),
        "moderate_risk_count": sum(1 for e in events if e["risk_level"] == "MODERATE"),
        "events": events,
        "exam_code": exam_code,
        "professor_uid": professor_uid,
        "exam_title": "Physics Midterm (seeded)",
        "session_uid": session_uid,
        "examinee_label": None,
    }

    db.collection("sessions").document(session_uid).set(document)
    print(f"[seed_emulator] Session: {session_uid} "
          f"({document['high_risk_count']} HIGH, {document['moderate_risk_count']} MODERATE)")


def main() -> None:
    init_app()
    db = firestore.client()

    professor_uid, _admin_uid = seed_users(db)
    exam_code = seed_exam(db, professor_uid)
    seed_session(db, professor_uid, exam_code)

    print("\n[seed_emulator] Done. Start the dashboard (npm run dev) and sign in as "
          f"{PROFESSOR_EMAIL} / {DEMO_PASSWORD} or {ADMIN_EMAIL} / {DEMO_PASSWORD}.")


if __name__ == "__main__":
    main()
