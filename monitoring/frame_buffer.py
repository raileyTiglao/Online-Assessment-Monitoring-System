"""
=============================================================================
monitoring/frame_buffer.py — Rolling Frame Buffer
Online Assessment Monitoring System
Holy Angel University — School of Computing

Keeps a short rolling history of recent frames so that when a HIGH risk
event is confirmed, the system can retrieve the frame from the moment the
sustained suspicious behavior actually BEGAN, rather than the current
frame at the moment the temporal window finished accumulating enough
evidence to escalate.

Without this, evidence screenshots tend to capture the examinee already
back to a normal pose — escalation is intentionally delayed by the
sliding window (to avoid flagging on momentary movements), so by the
time HIGH risk fires, the triggering behavior itself may have ended.
=============================================================================
"""

import time
import cv2
import numpy as np
from collections import deque
from typing import Optional


class FrameBuffer:
    """
    Stores (timestamp, frame) pairs for a configurable duration and can
    retrieve the frame closest to a target timestamp.

    Frames are downscaled before storage to keep memory usage reasonable
    over several seconds of buffered video — evidence screenshots don't
    need full webcam resolution.

    Usage:
        buffer = FrameBuffer(max_age_seconds=5.0)
        buffer.add(frame)                          # call every processed frame
        onset_frame = buffer.get_frame_near(onset_timestamp)
    """

    def __init__(self, max_age_seconds: float, store_width: Optional[int] = 640):
        self._max_age = max_age_seconds
        self._store_width = store_width
        self._entries: deque = deque()   # entries of (timestamp, frame)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, frame: np.ndarray) -> None:
        """Store a (possibly downscaled) copy of the current frame with a timestamp."""
        now = time.time()
        stored = self._downscale(frame)
        self._entries.append((now, stored))
        self._prune(now)

    def get_frame_near(self, target_timestamp: float) -> Optional[np.ndarray]:
        """
        Return the buffered frame whose timestamp is closest to
        target_timestamp.

        Args:
            target_timestamp: The wall-clock time to search for

        Returns:
            The closest matching frame, or None if the buffer is empty
        """
        if not self._entries:
            return None

        closest_entry = min(self._entries, key=lambda entry: abs(entry[0] - target_timestamp))
        return closest_entry[1]

    def reset(self) -> None:
        """Clear all buffered frames (e.g. when starting a new session)."""
        self._entries.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _downscale(self, frame: np.ndarray) -> np.ndarray:
        """Resize the frame down to store_width before buffering, if configured."""
        if self._store_width is None:
            return frame.copy()

        h, w = frame.shape[:2]
        if w <= self._store_width:
            return frame.copy()

        scale = self._store_width / float(w)
        new_h = int(h * scale)
        return cv2.resize(frame, (self._store_width, new_h), interpolation=cv2.INTER_AREA)

    def _prune(self, now: float) -> None:
        """Drop entries older than the configured max age."""
        cutoff = now - self._max_age
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()