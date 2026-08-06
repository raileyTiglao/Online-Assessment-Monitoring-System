"""
=============================================================================
analysis/calibration.py — Head Pose Calibration
Online Assessment Monitoring System
Holy Angel University — School of Computing

Runs a short calibration phase before monitoring begins, during which the
examinee's natural resting head orientation (yaw, pitch, roll) AND face
scale (a proxy for distance-to-camera) are sampled and averaged into a
baseline. All subsequent suspicion checks are made against this baseline
rather than absolute camera-relative angles, so examinees seated
off-center, above, or below the webcam are treated fairly.

The scale baseline additionally allows the system to detect when the
examinee has moved significantly closer/farther from the camera after
calibration — a condition under which normalized angles become unreliable
(see analysis/head_pose_normalizer.py).
=============================================================================
"""

import math
import time
import statistics
from dataclasses import dataclass
from config import CalibrationConfig


@dataclass
class CalibrationBaseline:
    """
    The examinee's natural resting head orientation and face scale,
    averaged over the calibration period. Used to normalize all later
    pose readings and to detect distance drift.

    Attributes:
        yaw, pitch, roll: Average camera-relative angles (degrees) during
                           the calibration window
        scale:             Average inter-eye pixel distance during
                           calibration — reference distance-to-camera
        gaze_x, gaze_y:    Average iris offset (in eye-width units) while
                           the examinee looked naturally at their screen.
                           Later gaze readings are measured against this, so
                           no separate screen-corner calibration is needed.
        gaze_samples:      Number of frames the gaze baseline is based on
                           (lower than sample_count — blinks are excluded)
        sample_count:      Number of face samples the average is based on
    """
    yaw: float
    pitch: float
    roll: float
    scale: float
    sample_count: int
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    gaze_samples: int = 0


class Calibrator:
    """
    Collects head pose + scale samples for a fixed duration and computes
    the average as a baseline.

    Usage:
        calibrator = Calibrator()
        calibrator.start()
        while not calibrator.is_complete():
            ... estimate raw pose for the current frame ...
            calibrator.add_sample(yaw, pitch, roll, scale)
        baseline = calibrator.compute_baseline()
    """

    def __init__(self, duration_seconds: float = None):
        self.duration = duration_seconds or CalibrationConfig.DURATION_SECONDS
        self._start_time = None
        self._yaw_samples = []
        self._pitch_samples = []
        self._roll_samples = []
        self._scale_samples = []
        # Gaze is sampled separately because blink frames are skipped, so
        # there are generally fewer gaze samples than pose samples.
        self._gaze_x_samples = []
        self._gaze_y_samples = []
        # Live feedback for the calibration screen, updated per frame by
        # add_sample(): what the examinee should fix, and whether the
        # current frame is acceptable (drives the guide outline's colour).
        self.status = "Get into position"
        self.status_ok = False
        self._rejected_count = 0
        # Per-axis sample spread (degrees), filled in by compute_baseline().
        # Doubles as this examinee's own jitter measurement.
        self.stability = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin (or restart) the calibration timer and clear samples."""
        self._start_time = time.time()
        self._yaw_samples.clear()
        self._pitch_samples.clear()
        self._roll_samples.clear()
        self._scale_samples.clear()
        self._gaze_x_samples.clear()
        self._gaze_y_samples.clear()
        self.status = "Get into position"
        self.status_ok = False
        self._rejected_count = 0

    def add_sample(self, yaw: float, pitch: float, roll: float,
                   scale: float = 0.0, gaze_x: float = None,
                   gaze_y: float = None, face_center_x: float = None,
                   face_center_y: float = None,
                   face_scale_ratio: float = None) -> bool:
        """
        Record one calibration frame, if it passes validation.

        A calibration sample is only useful if the examinee was seated
        consistently AND facing the screen when it was taken — otherwise a
        bad position or a turned head silently becomes their definition of
        "normal" for the whole session.

        Pass gaze_x/gaze_y only for frames where the iris reading was valid
        (eyes open); omit them on blinks so an occluded iris cannot skew the
        neutral-gaze baseline. The face_* arguments are optional; when
        omitted, position checking is skipped (orientation is still checked).

        Returns:
            True if the sample was accepted. When False, `status` explains
            why, for display on the calibration screen.
        """
        if self._start_time is None:
            self.start()
        if self.elapsed_seconds() < CalibrationConfig.SETTLE_SECONDS:
            self.status = "Settling..."
            self.status_ok = False
            return False

        ok, reason = self._validate(yaw, roll, face_center_x,
                                    face_center_y, face_scale_ratio)
        self.status = reason
        self.status_ok = ok

        if not ok and CalibrationConfig.ENFORCE_POSITION_GUIDE:
            self._rejected_count += 1
            return False

        self._yaw_samples.append(yaw)
        self._pitch_samples.append(pitch)
        self._roll_samples.append(roll)
        self._scale_samples.append(scale)
        if gaze_x is not None and gaze_y is not None:
            self._gaze_x_samples.append(gaze_x)
            self._gaze_y_samples.append(gaze_y)
        return True

    def _validate(self, yaw, roll, cx, cy, scale_ratio) -> tuple:
        """
        Check a frame against the positioning guide and the orientation
        limits, returning (ok, human-readable reason).

        Checks run position-first, then orientation, so the message shown
        addresses whatever the examinee needs to fix first — telling someone
        to straighten their head is useless if they're not in frame yet.
        """
        cfg = CalibrationConfig

        if cx is not None and cy is not None:
            target_x, target_y = cfg.GUIDE_HEAD_CENTER
            if math.hypot(cx - target_x, cy - target_y) > cfg.GUIDE_HEAD_TOLERANCE:
                return False, "Center your head in the outline"

        if scale_ratio is not None and scale_ratio > 0:
            if scale_ratio < cfg.GUIDE_SCALE_MIN:
                return False, "Move closer to the camera"
            if scale_ratio > cfg.GUIDE_SCALE_MAX:
                return False, "Move back from the camera"

        # Yaw/roll only — see the note in CalibrationConfig on why pitch is
        # deliberately not gated here.
        if abs(yaw) > cfg.ORIENTATION_YAW_TOLERANCE:
            return False, "Face the screen directly (head turned)"
        if abs(roll) > cfg.ORIENTATION_ROLL_TOLERANCE:
            return False, "Straighten your head (tilted to one side)"

        return True, "Hold still — looking good"

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
            return CalibrationBaseline(yaw=0.0, pitch=0.0, roll=0.0,
                                        scale=0.0, sample_count=0)

        if self._rejected_count:
            print(f"[Calibrator] {self._rejected_count} frame(s) discarded "
                  f"(out of position or not facing the screen).")

        self._report_stability()

        # A gaze baseline needs enough open-eye frames to be meaningful; if
        # too few survived (heavy blinking, poor lighting, glasses glare),
        # fall back to zero so gaze is measured against a centred iris
        # rather than against a baseline built from a handful of frames.
        has_gaze = len(self._gaze_x_samples) >= CalibrationConfig.MIN_SAMPLES
        if not has_gaze and self._gaze_x_samples:
            print(f"[Calibrator] WARNING: Only {len(self._gaze_x_samples)} valid "
                  f"gaze samples (eyes open) — gaze baseline defaults to centred.")

        return CalibrationBaseline(
            yaw=statistics.median(self._yaw_samples),
            pitch=statistics.median(self._pitch_samples),
            roll=statistics.median(self._roll_samples),
            scale=statistics.median(self._scale_samples),
            sample_count=len(self._yaw_samples),
            gaze_x=statistics.median(self._gaze_x_samples) if has_gaze else 0.0,
            gaze_y=statistics.median(self._gaze_y_samples) if has_gaze else 0.0,
            gaze_samples=len(self._gaze_x_samples),
        )

    def _report_stability(self) -> None:
        """
        Warn if the examinee was moving throughout calibration.

        The baseline is the median of these samples — if they were spread
        widely, that median represents no pose the examinee actually held,
        and every later measurement is relative to a fiction. Better to say
        so and offer a recalibration than to proceed quietly.

        Reported per axis, since a large spread on one axis alone (e.g.
        fidgeting side-to-side) is diagnostic in a way an overall figure
        would hide.
        """
        if len(self._yaw_samples) < 3:
            return   # stdev needs at least a few points to mean anything

        spreads = {
            "yaw":   statistics.stdev(self._yaw_samples),
            "pitch": statistics.stdev(self._pitch_samples),
            "roll":  statistics.stdev(self._roll_samples),
        }
        self.stability = spreads

        unstable = {k: v for k, v in spreads.items()
                    if v > CalibrationConfig.STABILITY_WARN_DEGREES}
        detail = "  ".join(f"{k}={v:.1f}deg" for k, v in spreads.items())

        if unstable:
            axes = ", ".join(unstable)
            print(f"[Calibrator] WARNING: Unstable calibration — movement on "
                  f"{axes} exceeded {CalibrationConfig.STABILITY_WARN_DEGREES:.0f}deg "
                  f"spread ({detail}). Baseline may be unreliable; press R to "
                  f"recalibrate while sitting still.")
        else:
            print(f"[Calibrator] Stability OK ({detail}).")