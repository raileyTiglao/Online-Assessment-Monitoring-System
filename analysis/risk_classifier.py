"""
=============================================================================
analysis/risk_classifier.py — Graduated Risk Classification
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts an aggregated TemporalSnapshot into one of three risk levels,
matching the study's three-tier framework:

  LOW      — No sustained suspicious signals
  MODERATE — Either device OR head pose sustained alone (ambiguous)
  HIGH     — Two possible triggers:
               1. Both signals co-occur persistently (dual-modal, strongest)
               2. Head pose alone sustained beyond the stricter solo threshold
                  (captures prolonged downward gaze without a visible device)

Classification is based on TIME-WEIGHTED RATIOS (fraction of the recent
window during which a signal was active) rather than raw frame counts,
so the thresholds behave consistently regardless of actual FPS.

RiskResult.trigger_type identifies WHICH condition fired, so callers
(e.g. evidence capture) know whether to look up the onset of the
dual-modal co-occurrence or the head-only sustained period when
retrieving a representative frame from the frame buffer.
=============================================================================
"""

from dataclasses import dataclass
from config import TemporalConfig
from analysis.temporal import TemporalSnapshot


@dataclass
class RiskResult:
    """
    Output of a risk classification decision.

    Attributes:
        level:        "LOW", "MODERATE", or "HIGH"
        snapshot:     The TemporalSnapshot the decision was based on
        escalated:    True if this call increased the risk level versus the
                      previous classification (used to trigger event logging)
        trigger:      Human-readable string describing what caused the level
        trigger_type: Machine-readable category of what fired:
                      "dual_modal" | "head_only" | "device_only" |
                      "head_moderate" | "none"
    """
    level:        str
    snapshot:     TemporalSnapshot
    escalated:    bool = False
    trigger:      str  = ""
    trigger_type: str  = "none"


class RiskClassifier:
    """
    Applies the study's three-tier risk classification rules to a
    TemporalSnapshot, using time-weighted activation ratios.

    HIGH risk has two independent trigger paths:
      - Dual-modal:      both device AND head pose co-occur >= HIGH_TRIGGER_RATIO
      - Per-axis:        any single axis (pitch/yaw/roll/dropout) sustained
                         past its OWN threshold — captures e.g. prolonged
                         downward gaze with no visible device

    Usage:
        classifier = RiskClassifier()
        result = classifier.classify(snapshot)
        print(result.level, result.trigger, result.trigger_type)
    """

    # Risk levels ordered lowest to highest, used to detect escalation
    _LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    # Per-axis rules, checked in order. Each entry is:
    #   (snapshot attribute, HIGH ratio, MODERATE ratio,
    #    human-readable label, trigger_type stem)
    # Ordered most- to least-specific so the reported trigger names the
    # behavior that actually drove the escalation.
    _AXIS_RULES = (
        ("pitch_ratio",   "PITCH_HIGH_RATIO",   "PITCH_MODERATE_RATIO",
         "Sustained downward tilt",   "pitch"),
        ("yaw_ratio",     "YAW_HIGH_RATIO",     "YAW_MODERATE_RATIO",
         "Sustained sideways turn",   "yaw"),
        ("roll_ratio",    "ROLL_HIGH_RATIO",    "ROLL_MODERATE_RATIO",
         "Sustained head tilt",       "roll"),
        ("dropout_ratio", "DROPOUT_HIGH_RATIO", "DROPOUT_MODERATE_RATIO",
         "Face tracking lost while turned away", "dropout"),
        ("gaze_ratio",    "GAZE_HIGH_RATIO",    "GAZE_MODERATE_RATIO",
         "Eyes directed away from screen", "gaze"),
    )

    def __init__(self):
        self._moderate_ratio = TemporalConfig.MODERATE_TRIGGER_RATIO
        self._high_ratio     = TemporalConfig.HIGH_TRIGGER_RATIO
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, snapshot: TemporalSnapshot) -> RiskResult:
        """
        Classify risk level based on the aggregated temporal snapshot.

        Rules (checked in order of severity):
            HIGH (dual-modal):    both_ratio >= HIGH_TRIGGER_RATIO
            HIGH (per-axis):      pitch/yaw/roll/dropout ratio >= that
                                   axis's own HIGH threshold
            MODERATE:             device_ratio >= MODERATE_TRIGGER_RATIO, or
                                   any axis >= its own MODERATE threshold
            LOW:                  otherwise

        Args:
            snapshot: Current TemporalSnapshot from the TemporalAnalyzer

        Returns:
            RiskResult with level, escalation flag, trigger description,
            and trigger_type for downstream evidence lookup
        """
        level, trigger, trigger_type = self._determine_level(snapshot)
        escalated = self._LEVEL_ORDER[level] > self._LEVEL_ORDER[self._last_level]
        self._last_level = level

        return RiskResult(
            level=level,
            snapshot=snapshot,
            escalated=escalated,
            trigger=trigger,
            trigger_type=trigger_type,
        )

    def reset(self) -> None:
        """Reset internal escalation tracking (e.g. for a new session)."""
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_level(self, snapshot: TemporalSnapshot) -> tuple:
        """
        Pure decision logic returning (level, trigger_description, trigger_type).
        Isolated for easy unit testing.

        Each pose axis is evaluated against its OWN thresholds rather than a
        single shared one, because the axes differ substantially in how noisy
        they are (see TemporalConfig). All HIGH conditions are checked before
        any MODERATE condition, so a quiet-but-decisive signal is never
        masked by a noisier one sitting at a lower level.
        """
        # --- HIGH: dual-modal (device + head pose co-occurring) ---
        if snapshot.both_ratio >= self._high_ratio:
            trigger = (f"Dual-modal: device + suspicious head pose "
                       f"co-occurred {snapshot.both_ratio:.0%} of window")
            return "HIGH", trigger, "dual_modal"

        # --- HIGH: any single axis sustained past its own threshold ---
        for attr, high_name, _, label, stem in self._AXIS_RULES:
            ratio = getattr(snapshot, attr)
            high_threshold = getattr(TemporalConfig, high_name)
            if ratio >= high_threshold:
                trigger = (f"{label}: active {ratio:.0%} of window "
                           f"(threshold {high_threshold:.0%})")
                return "HIGH", trigger, f"{stem}_only"

        # --- MODERATE: device alone ---
        if snapshot.device_ratio >= self._moderate_ratio:
            trigger = (f"Device detected {snapshot.device_ratio:.0%} of window")
            return "MODERATE", trigger, "device_only"

        # --- MODERATE: any single axis past its own moderate threshold ---
        for attr, _, moderate_name, label, stem in self._AXIS_RULES:
            ratio = getattr(snapshot, attr)
            moderate_threshold = getattr(TemporalConfig, moderate_name)
            if ratio >= moderate_threshold:
                trigger = (f"{label}: active {ratio:.0%} of window "
                           f"(threshold {moderate_threshold:.0%})")
                return "MODERATE", trigger, f"{stem}_moderate"

        return "LOW", "No sustained suspicious signals", "none"