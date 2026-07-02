"""
=============================================================================
analysis/calibration.py — Head Pose Calibration
Online Assessment Monitoring System
Holy Angel University — School of Computing

Runs a short calibration phase before monitoring begins, during which the
examinee's natural resting head orientation (yaw, pitch, roll) is sampled
and averaged into a baseline. All subsequent suspicion checks are made
against this baseline rather than absolute camera-relative angles, so
examinees seated off-center, above, or below the webcam are treated fairly.
=============================================================================
"""

import time
import statistics
from dataclasses import dataclass
from config import CalibrationConfig


@dataclass
class CalibrationBaseline:
    """
    The examinee's natural resting head orientation, averaged over the
    calibration period. Used to normalize all later pose readings.

    Attributes:
        yaw, pitch, roll: Average camera-relative angles (degrees) during
                           the calibration window
        sample_count:      Number of face samples the average is based on
    """
    yaw: float
    pitch: float
    roll: float
    sample_count: int


class Calibrator:
    """
    Collects head pose samples for a fixed duration and computes the
    average orientation as a baseline.

    Usage:
        calibrator = Calibrator()
        calibrator.start()
        while not calibrator.is_complete():
            ... estimate raw pose for the current frame ...
            calibrator.add_sample(yaw, pitch, roll)
        baseline = calibrator.compute_baseline()
    """

    def __init__(self, duration_seconds: float = None):
        self.duration = duration_seconds or CalibrationConfig.DURATION_SECONDS
        self._start_time = None
        self._yaw_samples = []
        self._pitch_samples = []
        self._roll_samples = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin (or restart) the calibration timer and clear samples."""
        self._start_time = time.time()
        self._yaw_samples.clear()
        self._pitch_samples.clear()
        self._roll_samples.clear()

    def add_sample(self, yaw: float, pitch: float, roll: float) -> None:
        """Record one frame's raw head pose reading during calibration."""
        if self._start_time is None:
            self.start()
        self._yaw_samples.append(yaw)
        self._pitch_samples.append(pitch)
        self._roll_samples.append(roll)

    def is_complete(self) -> bool:
        """True once the calibration duration has elapsed."""
        if self._start_time is None:
            return False
        return self.elapsed_seconds() >= self.duration

    def elapsed_seconds(self) -> float:
        """Seconds elapsed since calibration started."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def remaining_seconds(self) -> float:
        """Seconds left until calibration completes."""
        return max(0.0, self.duration - self.elapsed_seconds())

    def progress_ratio(self) -> float:
        """Calibration progress from 0.0 (just started) to 1.0 (complete)."""
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed_seconds() / self.duration)

    @property
    def sample_count(self) -> int:
        """Number of valid face samples collected so far."""
        return len(self._yaw_samples)

    def compute_baseline(self) -> CalibrationBaseline:
        """
        Average all collected samples into a CalibrationBaseline.

        Falls back to a zero baseline (i.e. no normalization applied) if
        no samples were collected — e.g. if the examinee's face was never
        detected during the calibration window.
        """
        if len(self._yaw_samples) < CalibrationConfig.MIN_SAMPLES:
            print(f"[Calibrator] WARNING: Only {len(self._yaw_samples)} samples "
                  f"collected (minimum recommended: {CalibrationConfig.MIN_SAMPLES}). "
                  f"Baseline may be unreliable.")

        if not self._yaw_samples:
            print("[Calibrator] WARNING: No face detected during calibration — "
                  "baseline defaults to 0,0,0 (no normalization will be applied).")
            return CalibrationBaseline(yaw=0.0, pitch=0.0, roll=0.0, sample_count=0)

        return CalibrationBaseline(
            yaw=statistics.mean(self._yaw_samples),
            pitch=statistics.mean(self._pitch_samples),
            roll=statistics.mean(self._roll_samples),
            sample_count=len(self._yaw_samples),
        )