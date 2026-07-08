"""
=============================================================================
analysis/temporal.py — Sliding Window Temporal Analyzer
Online Assessment Monitoring System
Holy Angel University — School of Computing

Aggregates per-frame signals (device detection + suspicious head pose)
over a TIME-based sliding window of recent frames. This filters out
incidental, momentary signals and surfaces only sustained behavioral
patterns, consistent with the study's conceptual framework.

Using a time window (seconds) rather than a fixed frame count keeps
behavior consistent regardless of actual achieved FPS — important since
inference speed varies by machine (CPU vs GPU) and detection frame-skip
settings.
=============================================================================
"""

import time
from collections import deque
from dataclasses import dataclass
from config import TemporalConfig


@dataclass
class TemporalSnapshot:
    """
    Aggregated state of the sliding window at a single point in time.

    Attributes:
        device_ratio: Fraction (0.0-1.0) of the window's time duration
                      during which a device was detected
        head_ratio:   Fraction of the window's time during which head
                      pose was suspicious
        both_ratio:   Fraction of the window's time during which BOTH
                      signals were active simultaneously
        window_seconds: Actual time span currently covered by the window
                         (may be less than the configured target early
                         in a session, before the window fills up)
        sample_count: Number of frame samples currently held
    """
    device_ratio:   float
    head_ratio:     float
    both_ratio:     float
    window_seconds: float
    sample_count:   int


class TemporalAnalyzer:
    """
    Tracks recent per-frame signals in a fixed-DURATION sliding window
    and reports aggregated time ratios used for risk classification.

    Each update() call is timestamped. Entries older than
    TemporalConfig.WINDOW_SECONDS are automatically dropped, so the
    window always reflects "the last N seconds" regardless of FPS.

    Usage:
        analyzer = TemporalAnalyzer()
        analyzer.update(device_detected=True, head_suspicious=False)
        snapshot = analyzer.get_snapshot()
    """

    def __init__(self, window_seconds: float = None):
        self.window_seconds = window_seconds or TemporalConfig.WINDOW_SECONDS
        # Each entry: (timestamp: float, device_detected: bool, head_suspicious: bool)
        self._entries = deque(maxlen=TemporalConfig.MAX_WINDOW_ENTRIES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, device_detected: bool, head_suspicious: bool) -> None:
        """
        Record the current frame's signals with a timestamp, then prune
        any entries that have fallen outside the configured time window.
        """
        now = time.time()
        self._entries.append((now, device_detected, head_suspicious))
        self._prune(now)

    def get_snapshot(self) -> TemporalSnapshot:
        """
        Compute time-weighted ratios across all frames currently in the
        window. Ratios are based on elapsed wall-clock time between
        consecutive samples, so they remain meaningful even if FPS
        fluctuates within the window.

        Returns:
            TemporalSnapshot with device_ratio, head_ratio, both_ratio
        """
        if len(self._entries) < 2:
            # Not enough data yet to compute a meaningful duration
            sample_count = len(self._entries)
            return TemporalSnapshot(0.0, 0.0, 0.0, 0.0, sample_count)

        total_duration = 0.0
        device_duration = 0.0
        head_duration = 0.0
        both_duration = 0.0

        entries = list(self._entries)
        for i in range(1, len(entries)):
            t_prev, device_prev, head_prev = entries[i - 1]
            t_curr, _, _ = entries[i]
            dt = t_curr - t_prev
            if dt <= 0:
                continue

            total_duration += dt
            if device_prev:
                device_duration += dt
            if head_prev:
                head_duration += dt
            if device_prev and head_prev:
                both_duration += dt

        if total_duration <= 0:
            return TemporalSnapshot(0.0, 0.0, 0.0, 0.0, len(entries))

        return TemporalSnapshot(
            device_ratio=device_duration / total_duration,
            head_ratio=head_duration / total_duration,
            both_ratio=both_duration / total_duration,
            window_seconds=total_duration,
            sample_count=len(entries),
        )

    def reset(self) -> None:
        """Clear the sliding window (e.g. when starting a new session)."""
        self._entries.clear()

    def get_onset_timestamp(self, require_device: bool) -> float | None:
        """
        Scan the current window from oldest to newest and return the
        timestamp of the first frame that satisfies the given condition:

            require_device=True:  first frame where BOTH device detection
                                   AND head suspicion were active
                                   (dual-modal onset)
            require_device=False: first frame where head suspicion alone
                                   was active (head-only onset)

        This locates the moment sustained suspicious behavior actually
        BEGAN, rather than the moment the window finished accumulating
        enough evidence to escalate risk (which is necessarily later, by
        design of the sliding-window approach). Used by evidence capture
        to retrieve a representative frame instead of whatever frame is
        current at the moment of escalation, which may already show the
        examinee back to normal behavior.

        Returns:
            The onset timestamp, or None if no matching frame is found
            in the current window (shouldn't normally happen if the
            corresponding risk level has already been triggered).
        """
        for timestamp, device, head in self._entries:
            if require_device:
                if device and head:
                    return timestamp
            else:
                if head:
                    return timestamp
        return None

    def is_warmed_up(self) -> bool:
        """
        True once the window has accumulated close to its full configured
        duration. Useful to avoid premature risk classification right at
        session start, before enough history exists.
        """
        if len(self._entries) < 2:
            return False
        oldest_time = self._entries[0][0]
        newest_time = self._entries[-1][0]
        return (newest_time - oldest_time) >= (self.window_seconds * 0.8)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune(self, now: float) -> None:
        """Drop entries older than the configured window duration."""
        cutoff = now - self.window_seconds
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()