"""
=============================================================================
analysis/risk_classifier.py — Graduated Risk Classification
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts an aggregated TemporalSnapshot into one of three risk levels:

  LOW      — No sustained suspicious signals
  MODERATE — Either device OR head pose sustained alone (ambiguous)
  HIGH     — Two possible triggers:
               1. Both signals co-occur persistently (dual-modal)
               2. Head pose alone sustained beyond stricter solo threshold
                  (captures prolonged downward gaze without visible device)
=============================================================================
"""

from dataclasses import dataclass, field
from config import TemporalConfig
from analysis.temporal import TemporalSnapshot


@dataclass
class RiskResult:
    """
    Output of a single risk classification decision.

    Attributes:
        level:     "LOW", "MODERATE", or "HIGH"
        snapshot:  The TemporalSnapshot the decision was based on
        escalated: True if risk level increased versus the previous call
        trigger:   Human-readable string describing what caused the level
    """
    level:     str
    snapshot:  TemporalSnapshot
    escalated: bool = False
    trigger:   str  = ""


class RiskClassifier:
    """
    Applies the study's three-tier risk classification rules to a
    TemporalSnapshot using time-weighted activation ratios.

    Usage:
        classifier = RiskClassifier()
        result = classifier.classify(snapshot)
        print(result.level)
        print(result.trigger)
    """

    _LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    def __init__(self):
        self._moderate_ratio = TemporalConfig.MODERATE_TRIGGER_RATIO
        self._high_ratio     = TemporalConfig.HIGH_TRIGGER_RATIO
        self._head_only_high = TemporalConfig.HEAD_ONLY_HIGH_RATIO
        self._last_level     = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, snapshot: TemporalSnapshot) -> RiskResult:
        """
        Classify risk level from the temporal snapshot.

        Rules (checked in order of severity):
            HIGH (dual-modal):  both_ratio  >= HIGH_TRIGGER_RATIO
            HIGH (head-only):   head_ratio  >= HEAD_ONLY_HIGH_RATIO
            MODERATE:           device_ratio or head_ratio >= MODERATE_TRIGGER_RATIO
            LOW:                otherwise

        Returns:
            RiskResult with level, escalation flag, and trigger description
        """
        level, trigger = self._determine_level(snapshot)
        escalated = self._LEVEL_ORDER[level] > self._LEVEL_ORDER[self._last_level]
        self._last_level = level

        return RiskResult(
            level=level,
            snapshot=snapshot,
            escalated=escalated,
            trigger=trigger,
        )

    def reset(self) -> None:
        """Reset escalation tracking for a new session."""
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_level(self, snapshot: TemporalSnapshot) -> tuple:
        """
        Pure decision logic — returns (level, trigger_description).
        Kept separate for easy unit testing.
        """

        # HIGH — dual modal: device + head pose co-occurring
        if snapshot.both_ratio >= self._high_ratio:
            trigger = (
                f"Dual-modal: device + suspicious head pose "
                f"co-occurred {snapshot.both_ratio:.0%} of window"
            )
            return "HIGH", trigger

        # HIGH — head pose only: sustained gaze deviation alone
        if snapshot.head_ratio >= self._head_only_high:
            trigger = (
                f"Sustained head pose: suspicious orientation active "
                f"{snapshot.head_ratio:.0%} of window "
                f"(threshold {self._head_only_high:.0%})"
            )
            return "HIGH", trigger

        # MODERATE — device signal alone
        if snapshot.device_ratio >= self._moderate_ratio:
            trigger = (
                f"Device detected {snapshot.device_ratio:.0%} of window"
            )
            return "MODERATE", trigger

        # MODERATE — head pose signal alone
        if snapshot.head_ratio >= self._moderate_ratio:
            trigger = (
                f"Suspicious head pose {snapshot.head_ratio:.0%} of window"
            )
            return "MODERATE", trigger

        return "LOW", "No sustained suspicious signals"