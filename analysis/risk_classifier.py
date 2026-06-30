"""
=============================================================================
analysis/risk_classifier.py — Graduated Risk Classification
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts an aggregated TemporalSnapshot into one of three risk levels,
matching the study's three-tier framework:

  LOW      — No sustained suspicious signals
  MODERATE — Either device OR head pose sustained alone (ambiguous)
  HIGH     — Both signals co-occur persistently (strongest indicator)
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
        level:    "LOW", "MODERATE", or "HIGH"
        snapshot: The TemporalSnapshot the decision was based on
        escalated: True if this call increased the risk level versus the
                   previous classification (used to trigger event logging)
    """
    level:     str
    snapshot:  TemporalSnapshot
    escalated: bool = False


class RiskClassifier:
    """
    Applies the study's three-tier risk classification rules to a
    TemporalSnapshot.

    Usage:
        classifier = RiskClassifier()
        result = classifier.classify(snapshot)
        print(result.level)
    """

    # Risk levels ordered from lowest to highest, used to detect escalation
    _LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    def __init__(self):
        self._moderate_threshold = TemporalConfig.MODERATE_TRIGGER_FRAMES
        self._high_threshold     = TemporalConfig.HIGH_TRIGGER_FRAMES
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, snapshot: TemporalSnapshot) -> RiskResult:
        """
        Classify risk level based on the aggregated temporal snapshot.

        Rules:
            HIGH:     both_count >= HIGH_TRIGGER_FRAMES
            MODERATE: device_count or head_count >= MODERATE_TRIGGER_FRAMES
            LOW:      otherwise

        Args:
            snapshot: Current TemporalSnapshot from the TemporalAnalyzer

        Returns:
            RiskResult containing the level and whether it escalated
        """
        level = self._determine_level(snapshot)
        escalated = self._LEVEL_ORDER[level] > self._LEVEL_ORDER[self._last_level]
        self._last_level = level

        return RiskResult(level=level, snapshot=snapshot, escalated=escalated)

    def reset(self) -> None:
        """Reset internal escalation tracking (e.g. for a new session)."""
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _determine_level(self, snapshot: TemporalSnapshot) -> str:
        """Pure decision logic, isolated for easy unit testing."""
        if snapshot.both_count >= self._high_threshold:
            return "HIGH"

        if (snapshot.device_count >= self._moderate_threshold
                or snapshot.head_count >= self._moderate_threshold):
            return "MODERATE"

        return "LOW"
