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
from analysis.one_euro_filter import OneEuroFilter
import time


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

    # Per-axis breakdown of what made this frame suspicious. Tracked
    # separately (rather than only as the blended `suspicious` flag) so the
    # temporal window can hold each axis to its own threshold — see
    # TemporalConfig's PITCH_/YAW_/ROLL_ ratios.
    yaw_suspicious:     bool = False
    pitch_suspicious:   bool = False
    roll_suspicious:    bool = False
    dropout_suspicious: bool = False


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
        self._yaw_filter   = OneEuroFilter(HeadPoseConfig.FILTER_MIN_CUTOFF,
                                           HeadPoseConfig.FILTER_BETA,
                                           HeadPoseConfig.FILTER_D_CUTOFF)
        self._pitch_filter = OneEuroFilter(HeadPoseConfig.FILTER_MIN_CUTOFF,
                                           HeadPoseConfig.FILTER_BETA,
                                           HeadPoseConfig.FILTER_D_CUTOFF)
        self._roll_filter  = OneEuroFilter(HeadPoseConfig.FILTER_MIN_CUTOFF,
                                           HeadPoseConfig.FILTER_BETA,
                                           HeadPoseConfig.FILTER_D_CUTOFF)
        self._ready_at = time.time() + CalibrationConfig.POST_CALIBRATION_GRACE_SECONDS

        # Last successfully tracked normalized pose, used to decide whether a
        # subsequent tracking dropout should count as suspicious (see
        # _dropout_follows_suspicious_direction). None until the first face
        # is seen, so dropout before any successful track never counts.
        self._last_valid_yaw = None
        self._last_valid_pitch = None

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
            # A lost face is a signal, but a DIRECTIONAL one. MediaPipe's
            # mesh breaks during steep downward tilt and turning away — the
            # behavior we want to catch — but equally when someone simply
            # leans back and looks UP, which we do not. Since we cannot see
            # why tracking was lost, the last valid pose decides: if the
            # examinee was already heading down or sideways, the dropout
            # continues that movement and counts. Facing forward or tilting
            # up, it does not. Dropout also carries its own (stricter)
            # sliding-window threshold, so it must persist notably longer
            # than a real pose deviation before escalating risk.
            counts = self._dropout_follows_suspicious_direction()
            reason = ("No face detected — continuing suspicious head movement"
                      if counts else
                      "No face detected — no prior suspicious direction")
            return NormalizedPose(
                success=False,
                suspicious=counts,
                dropout_suspicious=counts,
                reason=reason,
            )

        scale_ratio = self._compute_scale_ratio(head_result.scale)
        drifted = abs(scale_ratio - 1.0) > CalibrationConfig.SCALE_DRIFT_TOLERANCE

        n_yaw   = self._wrap_delta(head_result.yaw   - self._baseline.yaw)
        n_pitch = self._wrap_delta(head_result.pitch - self._baseline.pitch)
        n_roll  = self._wrap_delta(head_result.roll  - self._baseline.roll)
        n_yaw, n_pitch, n_roll = self._smooth(n_yaw, n_pitch, n_roll)
        in_grace_period = time.time() < self._ready_at

        yaw_susp = pitch_susp = roll_susp = False

        if drifted:
            # Distance from camera changed too much since calibration —
            # the baseline (and therefore these normalized angles) can no
            # longer be trusted. Suppress suspicion rather than risk a
            # false positive; surface a clear recalibration prompt instead.
            direction = "closer" if scale_ratio > 1.0 else "farther"
            reason = (f"Moved {direction} from camera "
                      f"({scale_ratio:.0%} of calibrated distance) — "
                      f"press R to recalibrate")
        elif in_grace_period:
            reason = "Settling after calibration..."
        else:
            yaw_susp, pitch_susp, roll_susp, reason = self._analyse(
                n_yaw, n_pitch, n_roll)

        # Remember this pose so a later tracking dropout can tell which
        # direction the examinee was heading when the face was lost. Only
        # recorded while the baseline is trustworthy — a drifted reading
        # would give the dropout check a misleading direction.
        if not drifted:
            self._last_valid_yaw = n_yaw
            self._last_valid_pitch = n_pitch

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
            suspicious=(yaw_susp or pitch_susp or roll_susp),
            reason=reason,
            yaw_suspicious=yaw_susp,
            pitch_suspicious=pitch_susp,
            roll_suspicious=roll_susp,
        )

    def _dropout_follows_suspicious_direction(self) -> bool:
        """
        Decide whether a tracking dropout should count as suspicious, based
        on the last pose seen before the face was lost.

        Counts only if the examinee was already heading DOWN or SIDEWAYS —
        the directions consistent with looking at something off-screen. A
        forward-facing or upward-tilted last pose does not count, which is
        what stops "leaning back and looking up" from escalating to HIGH.

        Returns False when no face has been tracked yet this session, so
        dropout before the first successful track is never counted.
        """
        if self._last_valid_yaw is None or self._last_valid_pitch is None:
            return False

        fraction = HeadPoseConfig.DROPOUT_CONTEXT_FRACTION
        heading_down = self._last_valid_pitch > HeadPoseConfig.PITCH_THRESHOLD * fraction
        heading_sideways = abs(self._last_valid_yaw) > HeadPoseConfig.YAW_THRESHOLD * fraction
        return heading_down or heading_sideways
        
    
    def _smooth(self, yaw, pitch, roll):
        """One-Euro filter over normalized angles — damps landmark jitter
        when still while staying responsive to fast, real head turns."""
        return (self._yaw_filter(yaw),
                self._pitch_filter(pitch),
                self._roll_filter(roll))
    

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_delta(delta: float) -> float:
        """
        Wrap an angle difference into [-180, +180].

        cv2.decomposeProjectionMatrix returns Euler angles on a circular
        range, and with this 3D face model the resting pitch lands near
        -160 degrees — only ~20 degrees from the -180/+180 seam. Tilting the
        head up far enough pushes the raw value across that seam, where it
        reappears as +178. Plain subtraction then reports
        178 - (-160) = +338 degrees, which sails past PITCH_THRESHOLD and is
        reported as "Looking down" — the system reads a raised head as a
        lowered one and escalates to HIGH.

        Wrapping maps that +338 back to -22, i.e. "looking up by 22 degrees",
        which correctly fails the downward check. Applied to all three axes
        since any of them can cross their seam.
        """
        return (delta + 180.0) % 360.0 - 180.0

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

        Returns:
            (yaw_suspicious, pitch_suspicious, roll_suspicious, reason)
            Each axis is reported separately so the temporal window can hold
            it to its own threshold rather than blending all three together.
        """
        reasons = []

        yaw_susp = abs(yaw) > HeadPoseConfig.YAW_THRESHOLD
        if yaw_susp:
            direction = "left" if yaw < 0 else "right"
            reasons.append(f"Head turned {direction} ({yaw:+.1f}° from baseline)")

        pitch_susp = pitch > HeadPoseConfig.PITCH_THRESHOLD
        if pitch_susp:
            reasons.append(f"Looking down ({pitch:+.1f}° from baseline)")

        roll_susp = abs(roll) > HeadPoseConfig.ROLL_THRESHOLD
        if roll_susp:
            reasons.append(f"Head tilted ({roll:+.1f}° from baseline)")

        reason = " | ".join(reasons) if reasons else "Normal"
        return yaw_susp, pitch_susp, roll_susp, reason