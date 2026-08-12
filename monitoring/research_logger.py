"""
=============================================================================
monitoring/research_logger.py — Continuous Per-Frame Research Logging
Online Assessment Monitoring System
Holy Angel University — School of Computing

session_report.json only records FLAGGED events (MODERATE/HIGH) — correct
for exam-time evidence, but useless for Chapter 3's data needs: pose
distributions and threshold accuracy both require every frame, not just
the ones that crossed a threshold.

Writes one CSV row per processed frame, plus a "scenario" column set by
whichever digit-key label (see ResearchLoggingConfig.SCENARIO_LABELS) was
last pressed — so a scripted data-collection session (operator performs
"normal", then presses '1' and performs "sustained_downward", etc.) can be
sliced back apart afterward by evaluation/analyze_research_log.py.

No-op when ResearchLoggingConfig.ENABLED is False, so main.py can call it
unconditionally without branching at every call site.
=============================================================================
"""

import csv
import time
from pathlib import Path
from config import ResearchLoggingConfig


class ResearchLogger:
    """
    Usage:
        logger = ResearchLogger(session_uid)
        ...
        logger.mark_scenario(key)   # on a 0-9 keypress
        logger.log_frame(normalized_pose, snapshot, risk_result, repetition_count)
        ...
        logger.close()
    """

    _FIELDS = [
        "timestamp", "elapsed_s", "scenario",
        "raw_yaw", "raw_pitch", "raw_roll",
        "norm_yaw", "norm_pitch", "norm_roll",
        "scale_ratio", "drifted",
        "gaze_x", "gaze_y", "gaze_valid",
        "device_detected",
        "pitch_suspicious", "yaw_suspicious", "roll_suspicious",
        "gaze_suspicious", "dropout_suspicious",
        "device_ratio", "both_ratio", "repetition_count",
        "risk_level", "trigger_type",
    ]

    def __init__(self, session_uid: str):
        self.enabled = ResearchLoggingConfig.ENABLED
        self._scenario = ResearchLoggingConfig.SCENARIO_LABELS[0]
        self._start_time = time.time()
        self._file = None
        self._writer = None

        if not self.enabled:
            return

        log_dir = Path(ResearchLoggingConfig.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"{session_uid}.csv"
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self._FIELDS)
        self._writer.writeheader()
        print(f"[ResearchLogger] ENABLED — logging every frame to {path}")
        print(f"[ResearchLogger] Press 0-9 to mark scenario "
              f"(0='{self._scenario}'): "
              f"{list(enumerate(ResearchLoggingConfig.SCENARIO_LABELS))}")

    def mark_scenario(self, key: int) -> bool:
        """
        Handle a raw key code from cv2.waitKey(). Returns True if it was a
        recognized scenario digit (so main.py knows to swallow the key
        rather than also checking it against other hotkeys).
        """
        if not self.enabled:
            return False
        if not (ord('0') <= key <= ord('9')):
            return False
        idx = key - ord('0')
        labels = ResearchLoggingConfig.SCENARIO_LABELS
        if idx >= len(labels):
            return False
        self._scenario = labels[idx]
        print(f"[ResearchLogger] Scenario -> '{self._scenario}'")
        return True

    def log_frame(self, normalized_pose, snapshot, risk_result,
                   repetition_count: int, device_detected: bool = False) -> None:
        """
        device_detected: the RAW per-frame detection boolean (before any
        windowing), logged separately from snapshot.device_ratio/both_ratio
        (which are already aggregated under whatever TemporalConfig was
        live at capture time). The raw value is what lets
        evaluation/threshold_sensitivity.py rebuild the sliding window from
        scratch under a different candidate config.
        """
        if not self.enabled:
            return
        self._writer.writerow({
            "timestamp":  time.time(),
            "elapsed_s":  round(time.time() - self._start_time, 3),
            "scenario":   self._scenario,
            "raw_yaw":    normalized_pose.raw_yaw,
            "raw_pitch":  normalized_pose.raw_pitch,
            "raw_roll":   normalized_pose.raw_roll,
            "norm_yaw":   normalized_pose.yaw,
            "norm_pitch": normalized_pose.pitch,
            "norm_roll":  normalized_pose.roll,
            "scale_ratio": normalized_pose.scale_ratio,
            "drifted":    normalized_pose.drifted,
            "gaze_x":     normalized_pose.gaze_x,
            "gaze_y":     normalized_pose.gaze_y,
            "gaze_valid": normalized_pose.gaze_valid,
            "device_detected": device_detected,
            "pitch_suspicious":   normalized_pose.pitch_suspicious,
            "yaw_suspicious":     normalized_pose.yaw_suspicious,
            "roll_suspicious":    normalized_pose.roll_suspicious,
            "gaze_suspicious":    normalized_pose.gaze_suspicious,
            "dropout_suspicious": normalized_pose.dropout_suspicious,
            "device_ratio":       snapshot.device_ratio,
            "both_ratio":         snapshot.both_ratio,
            "repetition_count":   repetition_count,
            "risk_level":         risk_result.level,
            "trigger_type":       risk_result.trigger_type,
        })

    def close(self) -> None:
        if self._file:
            self._file.close()
