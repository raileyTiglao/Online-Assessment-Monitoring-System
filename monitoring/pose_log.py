"""
=============================================================================
monitoring/pose_log.py — Continuous Pose Logging
Online Assessment Monitoring System
Holy Angel University — School of Computing

SessionReport (session_report.py) only records FLAGGED events — moments
that already crossed into MODERATE/HIGH risk. That's correct for the
deployed system's evidence trail, but it can't support descriptive
statistics or threshold-accuracy analysis, which need every frame's pose
data, not just the frames that were already flagged.

ContinuousPoseLog fills that gap for evaluation sessions: one row per
frame, written to CSV for easy import into pandas/Excel/Sheets. Disabled
by default (OutputConfig.ENABLE_CONTINUOUS_POSE_LOG) so normal monitoring
sessions aren't slowed down or bloated by a file no one needs.
=============================================================================
"""

import csv
import time
from typing import Optional


class ContinuousPoseLog:
    """
    Accumulates one row per processed frame during a session and writes
    it to CSV on save(). Optional per-row scenario_label lets a scripted
    evaluation session mark which behavior was being performed at each
    moment, so recorded rows can later be compared against ground truth.

    Usage:
        pose_log = ContinuousPoseLog()
        pose_log.set_label("downward_gaze")   # optional, before a scripted segment
        pose_log.log_sample(normalized_pose, risk_level="LOW", device_detected=False)
        pose_log.save("pose_log.csv")
    """

    FIELDNAMES = [
        "elapsed_seconds", "scenario_label",
        "raw_yaw", "raw_pitch", "raw_roll",
        "yaw", "pitch", "roll",
        "yaw_suspicious", "pitch_suspicious", "roll_suspicious",
        "dropout_suspicious", "gaze_suspicious", "suspicious",
        "gaze_x", "gaze_y", "gaze_valid",
        "device_detected", "risk_level",
    ]

    def __init__(self):
        self._session_start = time.time()
        self._current_label = ""
        self._rows: list[dict] = []

    def set_label(self, label: str) -> None:
        """
        Mark the scenario label to attach to subsequent rows, e.g.
        "baseline", "downward_gaze", "phone_visible". Call again with a
        new label when the scripted behavior changes, or with "" to clear.
        """
        self._current_label = label

    def log_sample(self, normalized_pose, risk_level: str,
                   device_detected: bool) -> None:
        """Append one row for the current frame."""
        self._rows.append({
            "elapsed_seconds":    round(time.time() - self._session_start, 3),
            "scenario_label":     self._current_label,
            "raw_yaw":            round(normalized_pose.raw_yaw, 2),
            "raw_pitch":          round(normalized_pose.raw_pitch, 2),
            "raw_roll":           round(normalized_pose.raw_roll, 2),
            "yaw":                round(normalized_pose.yaw, 2),
            "pitch":              round(normalized_pose.pitch, 2),
            "roll":               round(normalized_pose.roll, 2),
            "yaw_suspicious":     normalized_pose.yaw_suspicious,
            "pitch_suspicious":   normalized_pose.pitch_suspicious,
            "roll_suspicious":    normalized_pose.roll_suspicious,
            "dropout_suspicious": normalized_pose.dropout_suspicious,
            "gaze_suspicious":    normalized_pose.gaze_suspicious,
            "suspicious":         normalized_pose.suspicious,
            "gaze_x":             round(normalized_pose.gaze_x, 3),
            "gaze_y":             round(normalized_pose.gaze_y, 3),
            "gaze_valid":         normalized_pose.gaze_valid,
            "device_detected":    device_detected,
            "risk_level":         risk_level,
        })

    def save(self, filepath: str) -> int:
        """
        Write all buffered rows to CSV. Returns the row count written.
        """
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(self._rows)

        print(f"[ContinuousPoseLog] Saved {len(self._rows)} rows to: {filepath}")
        return len(self._rows)
