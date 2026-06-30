"""
=============================================================================
analysis/temporal.py — Sliding Window Temporal Analyzer
Online Assessment Monitoring System
Holy Angel University — School of Computing

Aggregates per-frame signals (device detection + suspicious head pose)
over a sliding window of recent frames. This filters out incidental,
momentary signals and surfaces only sustained behavioral patterns,
consistent with the study's conceptual framework.
=============================================================================
"""

from collections import deque
from dataclasses import dataclass
from config import TemporalConfig


@dataclass
class TemporalSnapshot:
    """
    Aggregated state of the sliding window at a single point in time.

    Attributes:
        device_count: Frames in the window with a device detected
        head_count:   Frames in the window with suspicious head pose
        both_count:   Frames where BOTH signals co-occurred
        window_size:  Total frames currently held in the window
    """
    device_count: int
    head_count:   int
    both_count:   int
    window_size:  int


class TemporalAnalyzer:
    """
    Tracks recent per-frame signals in a fixed-size sliding window and
    reports aggregated counts used for risk classification.

    Usage:
        analyzer = TemporalAnalyzer()
        analyzer.update(device_detected=True, head_suspicious=False)
        snapshot = analyzer.get_snapshot()
    """

    def __init__(self, window_size: int = None):
        self.window_size = window_size or TemporalConfig.WINDOW_SIZE
        # Each entry is a tuple: (device_detected: bool, head_suspicious: bool)
        self._window = deque(maxlen=self.window_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, device_detected: bool, head_suspicious: bool) -> None:
        """
        Push the current frame's signals into the sliding window.
        Oldest frame is automatically dropped once window_size is exceeded.
        """
        self._window.append((device_detected, head_suspicious))

    def get_snapshot(self) -> TemporalSnapshot:
        """
        Compute aggregated counts across all frames currently in the window.

        Returns:
            TemporalSnapshot with device_count, head_count, both_count
        """
        if not self._window:
            return TemporalSnapshot(0, 0, 0, 0)

        device_count = sum(1 for device, _ in self._window if device)
        head_count   = sum(1 for _, head in self._window if head)
        both_count   = sum(1 for device, head in self._window if device and head)

        return TemporalSnapshot(
            device_count=device_count,
            head_count=head_count,
            both_count=both_count,
            window_size=len(self._window),
        )

    def reset(self) -> None:
        """Clear the sliding window (e.g. when starting a new session)."""
        self._window.clear()

    def is_full(self) -> bool:
        """True once the window has reached its configured maximum size."""
        return len(self._window) == self.window_size
