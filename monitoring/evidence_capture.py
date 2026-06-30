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
import time
import cv2
import numpy as np
from datetime import datetime
from config import OutputConfig


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

        self._ensure_output_dir()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        now = time.time()
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

    def _save_screenshot(self, frame: np.ndarray) -> str:
        """Write the frame to disk with a timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"high_risk_{timestamp}.jpg"
        filepath  = os.path.join(self._output_dir, filename)

        cv2.imwrite(filepath, frame)
        print(f"[EvidenceCapture] HIGH RISK — screenshot saved: {filepath}")
        return filepath
