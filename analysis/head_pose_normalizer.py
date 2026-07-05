"""
=============================================================================
analysis/head_pose_normalizer.py — Baseline-Relative Pose Normalization
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts raw head pose angles into baseline-relative ("normalized") angles
using the CalibrationBaseline captured at session start, then applies the
suspicion thresholds from HeadPoseConfig to the normalized values instead
of absolute camera-relative angles.

DISTANCE DRIFT DETECTION:
Monocular head pose estimation (solvePnP with an approximated camera
matrix and a generic 3D face model) carries systematic error that changes
with the examinee's distance from the camera. If the examinee moves
significantly closer/farther after calibration, the calibrated baseline
no longer accurately represents "normal," and normalized angles can
falsely appear suspicious. This module detects that condition via the
change in face scale (inter-eye pixel distance) relative to the
calibration baseline, and suppresses suspicion checks while drifted
rather than risk a false positive — surfacing a "recalibration
recommended" state instead.
=============================================================================
"""

from dataclasses import dataclass
from config import HeadPoseConfig, CalibrationConfig
from detection.head_pose import HeadPoseResult
from analysis.calibration import CalibrationBaseline


@dataclass
class NormalizedPose:
    """
    Baseline-relative head pose reading for a single frame.

    Attributes:
        success:               False if no face was detected this frame
        raw_yaw/pitch/roll:    Original camera-relative angles (degrees)
        yaw/pitch/roll:        Baseline-relative angles (degrees) —
                                use these for behavioral decisions
        scale_ratio:           current_scale / baseline_scale (1.0 = same
                                distance as calibration)
        drifted:               True if scale_ratio deviates beyond the
                                configured tolerance — normalized angles
                                are unreliable in this state
        suspicious:            True if any normalized angle exceeds threshold
                                (always False while drifted, to avoid false
                                positives from an invalidated baseline)
        reason:                Human-readable description of what triggered
                                suspicion, OR a drift warning if drifted
    """
    success:     bool
    raw_yaw:     float = 0.0
    raw_pitch:   float = 0.0
    raw_roll:    float = 0.0
    yaw:         float = 0.0
    pitch:       float = 0.0
    roll:        float = 0.0
    scale_ratio: float = 1.0
    drifted:     bool  = False
    suspicious:  bool  = False
    reason:      str   = "No face detected"


class HeadPoseNormalizer:
    """
    Applies a CalibrationBaseline to raw HeadPoseResult readings, detects
    distance drift, and evaluates suspicion against the examinee's own
    natural resting pose — but only while the examinee remains at
    approximately the same distance from the camera as during calibration.

    Usage:
        normalizer = HeadPoseNormalizer(baseline)
        normalized = normalizer.normalize(head_result)
        print(normalized.yaw, normalized.suspicious, normalized.drifted)
    """

    def __init__(self, baseline: CalibrationBaseline):
        self._baseline = baseline

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, head_result: HeadPoseResult) -> NormalizedPose:
        """
        Subtract the calibration baseline from the raw pose reading,
        check for distance drift, and evaluate suspicion accordingly.

        Args:
            head_result: Raw HeadPoseResult from HeadPoseEstimator.estimate()

        Returns:
            NormalizedPose with baseline-relative angles, drift status,
            and suspicion flag
        """
        if not head_result.success:
            return NormalizedPose(success=False)

        scale_ratio = self._compute_scale_ratio(head_result.scale)
        drifted = abs(scale_ratio - 1.0) > CalibrationConfig.SCALE_DRIFT_TOLERANCE

        n_yaw   = head_result.yaw   - self._baseline.yaw
        n_pitch = head_result.pitch - self._baseline.pitch
        n_roll  = head_result.roll  - self._baseline.roll

        if drifted:
            # Distance from camera changed too much since calibration —
            # the baseline (and therefore these normalized angles) can no
            # longer be trusted. Suppress suspicion rather than risk a
            # false positive; surface a clear recalibration prompt instead.
            suspicious = False
            direction = "closer" if scale_ratio > 1.0 else "farther"
            reason = (f"Moved {direction} from camera "
                      f"({scale_ratio:.0%} of calibrated distance) — "
                      f"press R to recalibrate")
        else:
            suspicious, reason = self._analyse(n_yaw, n_pitch, n_roll)

        return NormalizedPose(
            success=True,
            raw_yaw=head_result.yaw,
            raw_pitch=head_result.pitch,
            raw_roll=head_result.roll,
            yaw=round(n_yaw, 2),
            pitch=round(n_pitch, 2),
            roll=round(n_roll, 2),
            scale_ratio=round(scale_ratio, 3),
            drifted=drifted,
            suspicious=suspicious,
            reason=reason,
        )

    @property
    def baseline(self) -> CalibrationBaseline:
        """The CalibrationBaseline this normalizer is using."""
        return self._baseline

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_scale_ratio(self, current_scale: float) -> float:
        """
        Ratio of current face scale to calibrated baseline scale.
        1.0 = same distance as calibration; >1.0 = closer; <1.0 = farther.
        Guards against division by zero if baseline scale wasn't captured
        (e.g. calibration had no valid samples).
        """
        if self._baseline.scale <= 0 or current_scale <= 0:
            return 1.0
        return current_scale / self._baseline.scale

    def _analyse(self, yaw: float, pitch: float, roll: float) -> tuple:
        """
        Compare baseline-relative angles against the configured thresholds.
        Only called when NOT drifted — i.e. the examinee is at approximately
        the same distance from the camera as during calibration, so the
        baseline is still valid.
        """
        reasons = []

        if abs(yaw) > HeadPoseConfig.YAW_THRESHOLD:
            direction = "left" if yaw < 0 else "right"
            reasons.append(f"Head turned {direction} ({yaw:+.1f}° from baseline)")

        if pitch < -HeadPoseConfig.PITCH_THRESHOLD:
            reasons.append(f"Looking down ({pitch:+.1f}° from baseline)")

        if abs(roll) > HeadPoseConfig.ROLL_THRESHOLD:
            reasons.append(f"Head tilted ({roll:+.1f}° from baseline)")

        if reasons:
            return True, " | ".join(reasons)
        return False, "Normal"