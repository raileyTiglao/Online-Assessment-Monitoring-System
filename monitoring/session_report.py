"""
=============================================================================
monitoring/session_report.py — Session Reporting
Online Assessment Monitoring System
Holy Angel University — School of Computing

Logs flagged behavioral events throughout a monitoring session and
exports a structured JSON report at the end, matching the study's
output specification: timestamps, risk levels, behavioral indicators,
and evidence references.
=============================================================================
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class FlaggedEvent:
    """A single logged behavioral event."""

    timestamp:            str
    risk_level:           str
    yaw:                  float
    pitch:                float
    roll:                 float
    device_detected:      bool
    behavioral_indicator: str
    screenshot_path:      Optional[str] = None


class SessionReport:
    """
    Accumulates flagged events during a monitoring session and saves
    a final JSON report when the session ends.

    Usage:
        report = SessionReport()
        report.log_event(risk_level="HIGH", yaw=35.2, pitch=-25.0, roll=4.1,
                          device_detected=True, behavioral_indicator="...",
                          screenshot_path="evidence_captures/high_risk_....jpg")
        report.save("session_report.json")
    """

    def __init__(self):
        self._session_start = datetime.now().isoformat()
        self._events: list[FlaggedEvent] = []
        self._baseline_info: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_baseline(self, yaw: float, pitch: float, roll: float,
                      sample_count: int) -> None:
        """
        Record the calibration baseline used for this session, so the
        report shows exactly what "normal" was defined as for this
        examinee. Should be called once, right after calibration completes.
        """
        self._baseline_info = {
            "yaw": round(yaw, 2),
            "pitch": round(pitch, 2),
            "roll": round(roll, 2),
            "sample_count": sample_count,
        }

    def log_event(self, risk_level: str, yaw: float, pitch: float, roll: float,
                  device_detected: bool, behavioral_indicator: str,
                  trigger: str = "",
                  screenshot_path: Optional[str] = None) -> None:
        """Append a new flagged event to the session log."""
        event = FlaggedEvent(
            timestamp=datetime.now().isoformat(),
            risk_level=risk_level,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            device_detected=device_detected,
            behavioral_indicator=behavioral_indicator,
            screenshot_path=screenshot_path,
        )
        # Attach trigger description as an extra field if provided
        if trigger:
            event.__dict__["trigger"] = trigger
        self._events.append(event)

    def save(self, filepath: str) -> dict:
        """
        Write the full session report to a JSON file.

        Returns:
            The report dict that was written (useful for printing a summary)
        """
        report = self._build_report_dict()

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n[SessionReport] Saved to: {filepath}")
        print(f"[SessionReport] Total flagged events: {report['total_flagged_events']}")
        print(f"[SessionReport]   HIGH risk:     {report['high_risk_count']}")
        print(f"[SessionReport]   MODERATE risk: {report['moderate_risk_count']}")

        return report

    @property
    def event_count(self) -> int:
        return len(self._events)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_report_dict(self) -> dict:
        """Assemble the full report structure, including summary counts."""
        high_count     = sum(1 for e in self._events if e.risk_level == "HIGH")
        moderate_count = sum(1 for e in self._events if e.risk_level == "MODERATE")

        return {
            "session_start":        self._session_start,
            "session_end":          datetime.now().isoformat(),
            "calibration_baseline": self._baseline_info,
            "total_flagged_events": len(self._events),
            "high_risk_count":      high_count,
            "moderate_risk_count":  moderate_count,
            "events":               [asdict(e) for e in self._events],
        }