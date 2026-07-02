"""
=============================================================================
analysis/head_pose_normalizer.py — Baseline-Relative Pose Normalization
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts raw head pose angles into baseline-relative ("normalized") angles
using the CalibrationBaseline captured at session start, then applies the
suspicion thresholds from HeadPoseConfig to the normalized values instead
of absolute camera-relative angles.

This keeps the system fair for examinees who naturally sit off-center,
above, or below the webcam — only DEVIATION from their own resting pose
is treated as suspicious, not their static position.
=============================================================================
"""

from dataclasses import dataclass
from config import HeadPoseConfig
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
                                use these for ALL behavioral decisions
        suspicious:            True if any normalized angle exceeds threshold
        reason:                Human-readable description of what triggered it
    """
    success:    bool
    raw_yaw:    float = 0.0
    raw_pitch:  float = 0.0
    raw_roll:   float = 0.0
    yaw:        float = 0.0
    pitch:      float = 0.0
    roll:       float = 0.0
    suspicious: bool  = False
    reason:     str   = "No face detected"


class HeadPoseNormalizer:
    """
    Applies a CalibrationBaseline to raw HeadPoseResult readings and
    evaluates suspicion against the examinee's own natural resting pose,
    rather than fixed camera-relative angles.

    Usage:
        normalizer = HeadPoseNormalizer(baseline)
        normalized = normalizer.normalize(head_result)
        print(normalized.yaw, normalized.suspicious)
    """

    def __init__(self, baseline: CalibrationBaseline):
        self._baseline = baseline

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, head_result: HeadPoseResult) -> NormalizedPose:
        """
        Subtract the calibration baseline from the raw pose reading and
        check the resulting deviation against configured thresholds.

        Args:
            head_result: Raw HeadPoseResult from HeadPoseEstimator.estimate()

        Returns:
            NormalizedPose with baseline-relative angles and suspicion flag
        """
        if not head_result.success:
            return NormalizedPose(success=False)

        n_yaw   = head_result.yaw   - self._baseline.yaw
        n_pitch = head_result.pitch - self._baseline.pitch
        n_roll  = head_result.roll  - self._baseline.roll

        suspicious, reason = self._analyse(n_yaw, n_pitch, n_roll)

        return NormalizedPose(
            success=True,
            raw_yaw=head_result.yaw,
            raw_pitch=head_result.pitch,
            raw_roll=head_result.roll,
            yaw=round(n_yaw, 2),
            pitch=round(n_pitch, 2),
            roll=round(n_roll, 2),
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

    def _analyse(self, yaw: float, pitch: float, roll: float) -> tuple:
        """
        Compare baseline-relative angles against the configured thresholds.
        Same threshold values as before (HeadPoseConfig), now applied to
        deviation from the examinee's own natural pose instead of absolute
        camera-relative angles.
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