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
      - Head-pose-only:  head pose alone >= HEAD_ONLY_HIGH_RATIO
                         (captures sustained downward gaze without visible device)

    Usage:
        classifier = RiskClassifier()
        result = classifier.classify(snapshot)
        print(result.level, result.trigger, result.trigger_type)
    """

    # Risk levels ordered lowest to highest, used to detect escalation
    _LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    def __init__(self):
        self._moderate_ratio = TemporalConfig.MODERATE_TRIGGER_RATIO
        self._high_ratio     = TemporalConfig.HIGH_TRIGGER_RATIO
        self._head_only_high = TemporalConfig.HEAD_ONLY_HIGH_RATIO
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, snapshot: TemporalSnapshot) -> RiskResult:
        """
        Classify risk level based on the aggregated temporal snapshot.

        Rules (checked in order of severity):
            HIGH (dual-modal):    both_ratio >= HIGH_TRIGGER_RATIO
            HIGH (head-only):     head_ratio >= HEAD_ONLY_HIGH_RATIO
            MODERATE:             device_ratio or head_ratio >= MODERATE_TRIGGER_RATIO
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
        """
        # --- HIGH: dual-modal (device + head pose co-occurring) ---
        if snapshot.both_ratio >= self._high_ratio:
            trigger = (f"Dual-modal: device + suspicious head pose "
                       f"co-occurred {snapshot.both_ratio:.0%} of window")
            return "HIGH", trigger, "dual_modal"

        # --- HIGH: head-pose-only (sustained gaze deviation alone) ---
        if snapshot.head_ratio >= self._head_only_high:
            trigger = (f"Sustained head pose: suspicious orientation "
                       f"active {snapshot.head_ratio:.0%} of window "
                       f"(threshold {self._head_only_high:.0%})")
            return "HIGH", trigger, "head_only"

        # --- MODERATE: either signal alone, less sustained ---
        if snapshot.device_ratio >= self._moderate_ratio:
            trigger = (f"Device detected {snapshot.device_ratio:.0%} of window")
            return "MODERATE", trigger, "device_only"

        if snapshot.head_ratio >= self._moderate_ratio:
            trigger = (f"Suspicious head pose {snapshot.head_ratio:.0%} of window")
            return "MODERATE", trigger, "head_moderate"

        return "LOW", "No sustained suspicious signals", "none"