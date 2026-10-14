"""
=============================================================================
monitoring/evidence_capture.py — Evidence Capture
Online Assessment Monitoring System
Holy Angel University — School of Computing

Handles automatic screenshot capture when a HIGH RISK event occurs.
Includes a cooldown so the system doesn't spam screenshots every frame
while the examinee remains in a high-risk state.
=============================================================================
"""

import os
import glob
import time
import clock
import cv2
import numpy as np
from datetime import datetime
from config import DatabaseConfig, OutputConfig, RetentionConfig


class EvidenceCapture:
    """
    Captures and saves screenshots as evidence when triggered.

    Usage:
        capture = EvidenceCapture()
        path = capture.try_capture(frame, risk_level="HIGH")
        if path:
            print("Saved:", path)
    """

    def __init__(self, output_dir: str = None, cooldown_seconds: int = None):
        self._output_dir = output_dir or OutputConfig.SCREENSHOT_DIR
        self._cooldown    = cooldown_seconds or OutputConfig.SCREENSHOT_COOLDOWN
        self._last_capture_time = 0.0
        self._capture_count = 0

        # Cloud upload context — set via set_context() once the session's
        # exam/professor is known. Screenshots still save locally even if
        # this is never called (uploader stays None); only the *returned
        # path* changes from a local path to a Storage object path.
        self._session_uid = None
        self._professor_uid = None
        self._uploader = None

        self._ensure_output_dir()
        self._purge_expired_local_copies()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_context(self, session_uid: str, professor_uid: str | None,
                    uploader=None) -> None:
        """
        Wire in the current session's identity and (optionally) a
        FirebaseStorageUploader, so subsequent captures upload to the
        cloud instead of staying local-only. Call once at session start,
        after the exam code (if any) has been resolved.

        Args:
            session_uid:   This session's unique ID (SessionReport.session_uid)
            professor_uid: Owning professor's UID, or None if the session
                           proceeded without a valid exam code (screenshots
                           upload under "_unassigned/" in that case)
            uploader:      A FirebaseStorageUploader, or None to keep
                           screenshots local-only (e.g. DatabaseConfig.ENABLE_DB
                           is False)
        """
        self._session_uid = session_uid
        self._professor_uid = professor_uid
        self._uploader = uploader

    def try_capture(self, frame: np.ndarray, risk_level: str) -> str | None:
        """
        Attempt to capture a screenshot if conditions are met.

        Only captures when:
          - risk_level is "HIGH"
          - the cooldown period has elapsed since the last capture

        Args:
            frame:      Current OpenCV BGR frame
            risk_level: Current risk classification ("LOW"/"MODERATE"/"HIGH")

        Returns:
            File path of the saved screenshot, or None if not captured
        """
        if risk_level != "HIGH":
            return None

        now = clock.now()
        if (now - self._last_capture_time) < self._cooldown:
            return None  # Still in cooldown period

        path = self._save_screenshot(frame)
        self._last_capture_time = now
        self._capture_count += 1
        return path

    @property
    def capture_count(self) -> int:
        """Total number of screenshots captured this session."""
        return self._capture_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_output_dir(self) -> None:
        """Create the evidence directory if it doesn't already exist."""
        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir)
            print(f"[EvidenceCapture] Created directory: {self._output_dir}/")

    def _purge_expired_local_copies(self) -> None:
        """
        Delete local evidence screenshots older than
        RetentionConfig.EVIDENCE_RETENTION_DAYS. After a successful upload
        the local copy is already gone, so this only catches copies left
        behind by failed uploads or runs without a database.
        """
        folder = os.path.basename(os.path.normpath(self._output_dir))
        if folder in RetentionConfig.PROTECTED_DIRS:
            print(f"[EvidenceCapture][WARN] Not purging protected folder "
                  f"{self._output_dir}/ — see RetentionConfig.PROTECTED_DIRS.")
            return

        cutoff = time.time() - RetentionConfig.EVIDENCE_RETENTION_DAYS * 86400
        removed = 0
        for path in glob.glob(os.path.join(self._output_dir, "high_risk_*.jpg")):
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        if removed:
            print(f"[EvidenceCapture] Retention: deleted {removed} local screenshot(s) "
                  f"older than {RetentionConfig.EVIDENCE_RETENTION_DAYS} days.")

    def _save_screenshot(self, frame: np.ndarray) -> str:
        """
        Write the frame to disk with a timestamped filename, then upload it
        to Firebase Storage if a context/uploader has been set (see
        set_context()). Once the upload succeeds the local copy is deleted
        (RetentionConfig.DELETE_LOCAL_AFTER_UPLOAD), so the only copy is the
        access-controlled one in Storage. If the upload fails, the local copy
        is kept as a fallback until the retention purge removes it.

        Returns:
            The Storage object path if upload succeeded, otherwise the
            local filesystem path (unchanged legacy behavior when no
            uploader is configured, or if the upload itself fails).
        """
        timestamp = datetime.fromtimestamp(clock.now()).strftime("%Y%m%d_%H%M%S")
        filename  = f"high_risk_{timestamp}.jpg"
        filepath  = os.path.join(self._output_dir, filename)

        cv2.imwrite(filepath, frame)
        print(f"[EvidenceCapture] HIGH RISK — screenshot saved: {filepath}")

        if self._uploader is None:
            return filepath

        owner = self._professor_uid or "_unassigned"
        dest_path = f"{DatabaseConfig.EVIDENCE_STORAGE_PREFIX}/{owner}/{self._session_uid}/{filename}"
        try:
            # upload()'s return value is the source of truth, not dest_path
            # itself — the Firebase uploader always returns it unchanged,
            # but the local PHP backend computes its own final path
            # server-side (see connection/local_backend.py::
            # LocalStorageUploader.upload's docstring), which can differ.
            stored_path = self._uploader.upload(filepath, dest_path)
            print(f"[EvidenceCapture] Uploaded to Storage: {stored_path}")
            if RetentionConfig.DELETE_LOCAL_AFTER_UPLOAD:
                os.remove(filepath)
            return stored_path
        except Exception as exc:
            print(f"[EvidenceCapture][WARN] Storage upload failed ({exc}). "
                  f"Local copy is still intact: {filepath}")
            return filepath
