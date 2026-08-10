"""
=============================================================================
analysis/risk_classifier.py — Graduated Risk Classification
Online Assessment Monitoring System
Holy Angel University — School of Computing

Converts an aggregated TemporalSnapshot into one of three risk levels,
matching the study's three-tier framework (paper, p.9):

  LOW      — No sustained suspicious signals
  MODERATE — Either device OR head pose sustained alone (ambiguous)
  HIGH     — Two conditions:
               1. Both signals co-occur persistently (dual-modal, per paper)
               2. Repeated suspicious-movement episodes (persistence across
                  discontinuous episodes rather than one continuous window
                  — not in the paper's text, but the same "persistent"
                  principle applied to a pattern the paper's continuous-
                  window test structurally can't see; see docs/logs.md
                  2026-08-10)

Single-axis head pose (pitch/yaw/roll/dropout/gaze) sustained alone, and a
device detected alone, now cap at MODERATE — matching the paper. Demoted
2026-08-10; previously each could reach HIGH independently. See
docs/logs.md for the reasoning (single-axis noise measured to exceed
deliberate-glance signal; device-alone HIGH tied risk severity to detector
precision with no corroboration).

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
from config import TemporalConfig, RepetitionConfig
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
      - Repetition:      repeated suspicious-movement episodes (see module
                         docstring)

    Usage:
        classifier = RiskClassifier()
        result = classifier.classify(snapshot)
        print(result.level, result.trigger, result.trigger_type)
    """

    # Risk levels ordered lowest to highest, used to detect escalation
    _LEVEL_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2}

    # Per-axis MODERATE rules, checked in order. Each entry is:
    #   (snapshot attribute, MODERATE ratio, human-readable label,
    #    trigger_type stem)
    # Axes no longer have an independent HIGH threshold — demoted 2026-08-10
    # to match the paper (a single axis alone now caps at MODERATE; HIGH
    # requires dual-modal or repetition). The corresponding *_HIGH_RATIO
    # config values still exist but are unused by this classifier.
    _AXIS_RULES = (
        ("pitch_ratio",   "PITCH_MODERATE_RATIO",
         "Sustained downward tilt",   "pitch"),
        ("yaw_ratio",     "YAW_MODERATE_RATIO",
         "Sustained sideways turn",   "yaw"),
        ("roll_ratio",    "ROLL_MODERATE_RATIO",
         "Sustained head tilt",       "roll"),
        ("dropout_ratio", "DROPOUT_MODERATE_RATIO",
         "Face tracking lost while turned away", "dropout"),
        ("gaze_ratio",    "GAZE_MODERATE_RATIO",
         "Eyes directed away from screen", "gaze"),
    )

    def __init__(self):
        self._moderate_ratio = TemporalConfig.MODERATE_TRIGGER_RATIO
        self._high_ratio     = TemporalConfig.HIGH_TRIGGER_RATIO
        self._last_level = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, snapshot: TemporalSnapshot,
                 repetition_count: int = 0) -> RiskResult:
        """
        Classify risk level based on the aggregated temporal snapshot.

        Rules (checked in order of severity):
            HIGH (dual-modal):    both_ratio >= HIGH_TRIGGER_RATIO
            HIGH (repetition):    repetition_count >= HIGH_COUNT
            MODERATE:             device_ratio >= MODERATE_TRIGGER_RATIO,
                                   any axis >= its own MODERATE threshold, or
                                   repetition_count >= MODERATE_COUNT
            LOW:                  otherwise

        Single-axis head pose and device-alone no longer reach HIGH — see
        module docstring, "Demoted 2026-08-10".

        Args:
            snapshot:         Current TemporalSnapshot from the TemporalAnalyzer
            repetition_count: Separate suspicious-movement episodes counted
                              by RepetitionAnalyzer over its own, much longer
                              window. An episode is any excursion past a
                              threshold on ANY signal — head turn, downward
                              tilt, head tilt, gaze, or tracking loss — and
                              back. Catches repeated brief movements, which
                              the ratio thresholds are structurally unable to
                              see, since each ends before it can accumulate.

        Returns:
            RiskResult with level, escalation flag, trigger description,
            and trigger_type for downstream evidence lookup
        """
        level, trigger, trigger_type = self._determine_level(
            snapshot, repetition_count)
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

    def _determine_level(self, snapshot: TemporalSnapshot,
                         repetition_count: int = 0) -> tuple:
        """
        Pure decision logic returning (level, trigger_description, trigger_type).
        Isolated for easy unit testing.

        Each pose axis is evaluated against its OWN thresholds rather than a
        single shared one, because the axes differ substantially in how noisy
        they are (see TemporalConfig). All HIGH conditions are checked before
        any MODERATE condition, so a quiet-but-decisive signal is never
        masked by a noisier one sitting at a lower level.
        """
        # --- HIGH: device present at all (no sustain requirement) ---
        # Checked first, and on ">0" rather than a ratio, because unlike a
        # head pose a visible device needs no corroboration to be meaningful.
        # device_ratio stays above zero for the remainder of the sliding
        # window after the device leaves frame, so a device glimpsed briefly
        # still holds HIGH long enough to be logged and screenshotted rather
        # than flickering away before the debounce in main.py commits it.
        if TemporalConfig.DEVICE_IMMEDIATE_HIGH and snapshot.device_ratio > 0:
            trigger = (f"Mobile device detected in frame "
                       f"({snapshot.device_ratio:.0%} of window)")
            return "HIGH", trigger, "device_immediate"

        # --- HIGH: dual-modal (device + head pose co-occurring) ---
        if snapshot.both_ratio >= self._high_ratio:
            trigger = (f"Dual-modal: device + suspicious head pose "
                       f"co-occurred {snapshot.both_ratio:.0%} of window")
            return "HIGH", trigger, "dual_modal"

        # --- HIGH: repeated suspicious-movement episodes ---
        # Single-axis sustained-alone no longer reaches HIGH (demoted
        # 2026-08-10 to match the paper — see module docstring); repetition
        # is the only non-dual-modal path left, checked here so several
        # separate glances (a deliberate pattern) still outranks the
        # single-signal MODERATE checks below.
        if RepetitionConfig.ENABLED and repetition_count >= RepetitionConfig.HIGH_COUNT:
            trigger = (f"Repeated suspicious movement: {repetition_count} separate "
                       f"episodes in {RepetitionConfig.WINDOW_SECONDS:.0f}s "
                       f"(threshold {RepetitionConfig.HIGH_COUNT})")
            return "HIGH", trigger, "repetition"

        # --- MODERATE: device alone ---
        if snapshot.device_ratio >= self._moderate_ratio:
            trigger = (f"Device detected {snapshot.device_ratio:.0%} of window")
            return "MODERATE", trigger, "device_only"

        # --- MODERATE: any single axis past its own moderate threshold ---
        for attr, moderate_name, label, stem in self._AXIS_RULES:
            ratio = getattr(snapshot, attr)
            moderate_threshold = getattr(TemporalConfig, moderate_name)
            if ratio >= moderate_threshold:
                trigger = (f"{label}: active {ratio:.0%} of window "
                           f"(threshold {moderate_threshold:.0%})")
                return "MODERATE", trigger, f"{stem}_moderate"

        # --- MODERATE: repeated movement, below the HIGH count ---
        if RepetitionConfig.ENABLED and repetition_count >= RepetitionConfig.MODERATE_COUNT:
            trigger = (f"Repeated suspicious movement: {repetition_count} separate "
                       f"episodes in {RepetitionConfig.WINDOW_SECONDS:.0f}s "
                       f"(threshold {RepetitionConfig.MODERATE_COUNT})")
            return "MODERATE", trigger, "repetition_moderate"

        return "LOW", "No sustained suspicious signals", "none"