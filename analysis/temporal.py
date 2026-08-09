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
        head_ratio:   Fraction of the window's time during which ANY pose
                      axis was suspicious — the blended signal, kept for
                      dual-modal classification and display
        both_ratio:   Fraction of the window's time during which BOTH
                      device and head-pose signals were active simultaneously
        yaw_ratio:    Fraction during which yaw alone exceeded threshold
        pitch_ratio:  Fraction during which pitch alone exceeded threshold
        roll_ratio:   Fraction during which roll alone exceeded threshold
        dropout_ratio: Fraction during which face tracking was lost AND that
                       loss followed a suspicious direction of movement
        window_seconds: Actual time span currently covered by the window
                         (may be less than the configured target early
                         in a session, before the window fills up)
        sample_count: Number of frame samples currently held

    The per-axis ratios exist because the axes have very different noise
    floors — see the threshold rationale in TemporalConfig. Collapsing them
    into head_ratio alone forced one threshold to serve signals that need
    quite different sensitivities.
    """
    device_ratio:   float
    head_ratio:     float
    both_ratio:     float
    window_seconds: float
    sample_count:   int
    yaw_ratio:      float = 0.0
    pitch_ratio:    float = 0.0
    roll_ratio:     float = 0.0
    dropout_ratio:  float = 0.0
    gaze_ratio:     float = 0.0


class TemporalAnalyzer:
    """
    Tracks recent per-frame signals in a fixed-DURATION sliding window
    and reports aggregated time ratios used for risk classification.

    Each update() call is timestamped. Entries older than
    TemporalConfig.WINDOW_SECONDS are automatically dropped, so the
    window always reflects "the last N seconds" regardless of FPS.

    Usage:
        analyzer = TemporalAnalyzer()
        analyzer.update(device_detected=True, pitch_suspicious=True)
        snapshot = analyzer.get_snapshot()
    """

    def __init__(self, window_seconds: float = None):
        self.window_seconds = window_seconds or TemporalConfig.WINDOW_SECONDS
        # Each entry: (timestamp, device_detected, yaw_susp, pitch_susp,
        #              roll_susp, dropout_susp)
        self._entries = deque(maxlen=TemporalConfig.MAX_WINDOW_ENTRIES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, device_detected: bool, yaw_suspicious: bool = False,
               pitch_suspicious: bool = False, roll_suspicious: bool = False,
               dropout_suspicious: bool = False,
               gaze_suspicious: bool = False) -> None:
        """
        Record the current frame's signals with a timestamp, then prune
        any entries that have fallen outside the configured time window.

        Each pose axis is stored separately so it can be aggregated against
        its own threshold; the blended "any axis" signal is derived at
        snapshot time rather than stored.
        """
        now = time.time()
        self._entries.append((now, device_detected, yaw_suspicious,
                              pitch_suspicious, roll_suspicious,
                              dropout_suspicious, gaze_suspicious))
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
        yaw_duration = 0.0
        pitch_duration = 0.0
        roll_duration = 0.0
        dropout_duration = 0.0
        gaze_duration = 0.0

        entries = list(self._entries)
        for i in range(1, len(entries)):
            (t_prev, device_prev, yaw_prev, pitch_prev,
             roll_prev, dropout_prev, gaze_prev) = entries[i - 1]
            t_curr = entries[i][0]
            dt = t_curr - t_prev
            if dt <= 0:
                continue

            # "Head suspicious" for dual-modal purposes means any pose axis,
            # a directionally-consistent tracking dropout, or off-baseline gaze.
            head_prev = (yaw_prev or pitch_prev or roll_prev
                         or dropout_prev or gaze_prev)

            total_duration += dt
            if device_prev:
                device_duration += dt
            if head_prev:
                head_duration += dt
            if device_prev and head_prev:
                both_duration += dt
            if yaw_prev:
                yaw_duration += dt
            if pitch_prev:
                pitch_duration += dt
            if roll_prev:
                roll_duration += dt
            if dropout_prev:
                dropout_duration += dt
            if gaze_prev:
                gaze_duration += dt

        if total_duration <= 0:
            return TemporalSnapshot(0.0, 0.0, 0.0, 0.0, len(entries))

        # Divide by the CONFIGURED window, not the span actually buffered.
        #
        # Dividing by the buffered span made a ratio mean "fraction of
        # however much history happens to exist", so the same behaviour
        # crossed a threshold much sooner when the window was still filling:
        # 2.5s of downward tilt inside 3.5s of history reads as 71%, clearing
        # a 67% bar that is supposed to represent 4 seconds. Sessions were
        # therefore most trigger-happy in the moments right after start-up
        # and after every recalibration — exactly when an examinee is still
        # settling.
        #
        # Against the configured window the same 2.5s reads as 42%, so a
        # threshold expressed as a fraction now corresponds to a fixed number
        # of seconds regardless of how long the session has been running.
        # max() guards the case where pruning briefly leaves slightly more
        # than a full window buffered, which would otherwise allow a ratio
        # above 1.0.
        denominator = max(total_duration, self.window_seconds)

        return TemporalSnapshot(
            device_ratio=device_duration / denominator,
            head_ratio=head_duration / denominator,
            both_ratio=both_duration / denominator,
            # Reported as the span actually held, which is what the overlay
            # shows as "Window: x.xs / Ns" — a fill indicator, not the
            # denominator used above.
            window_seconds=total_duration,
            sample_count=len(entries),
            yaw_ratio=yaw_duration / denominator,
            pitch_ratio=pitch_duration / denominator,
            roll_ratio=roll_duration / denominator,
            dropout_ratio=dropout_duration / denominator,
            gaze_ratio=gaze_duration / denominator,
        )

    def reset(self) -> None:
        """Clear the sliding window (e.g. when starting a new session)."""
        self._entries.clear()

    def get_onset_timestamp(self, require_device: bool = False,
                            axis: str = None) -> float | None:
        """
        Scan the current window from oldest to newest and return the
        timestamp of the first frame that satisfies the given condition:

            require_device=True:  first frame where BOTH device detection
                                   AND head suspicion were active
                                   (dual-modal onset)
            axis="pitch"/"yaw"/"roll"/"dropout":
                                  first frame where THAT specific signal
                                  was active — lets evidence capture pull
                                  the frame where the actual triggering
                                  behavior began, not merely where any
                                  suspicion started
            neither:              first frame where any head suspicion
                                   was active

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
        # "device"/"device_immediate" map to the device flag rather than a
        # pose axis, so a device-triggered HIGH captures the frame where the
        # device first appeared instead of the first frame of any unrelated
        # head movement that happened to be earlier in the window.
        axis_index = {"yaw": 2, "pitch": 3, "roll": 4,
                      "dropout": 5, "gaze": 6,
                      "device": 1, "device_immediate": 1}.get(axis)

        for entry in self._entries:
            timestamp, device = entry[0], entry[1]
            head = entry[2] or entry[3] or entry[4] or entry[5] or entry[6]

            if require_device:
                if device and head:
                    return timestamp
            elif axis_index is not None:
                if entry[axis_index]:
                    return timestamp
            elif head:
                return timestamp
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune(self, now: float) -> None:
        """Drop entries older than the configured window duration."""
        cutoff = now - self.window_seconds
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()