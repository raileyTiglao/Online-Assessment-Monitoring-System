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
import uuid
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
    trigger:              str = ""
    screenshot_path:      Optional[str] = None
    # Baseline-relative iris offset (eye-widths) at the moment this event
    # fired. gaze_valid is False when the eyes were too closed (blink/
    # squint) for gaze to be measured — gaze_x/gaze_y are then stale
    # zeros and should not be displayed as a real reading.
    gaze_x:               float = 0.0
    gaze_y:               float = 0.0
    gaze_valid:           bool  = False


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
        # Timestamp-derived with a short random suffix so two sessions
        # starting the same second on different machines can't collide.
        self._session_uid = (f"sess_{self._session_start.replace(':', '').replace('.', '')}"
                             f"_{uuid.uuid4().hex[:6]}")
        self._events: list[FlaggedEvent] = []
        self._baseline_info: Optional[dict] = None
        self._exam_code: Optional[str] = None
        self._professor_uid: Optional[str] = None
        self._exam_title: Optional[str] = None

    @property
    def session_uid(self) -> str:
        """
        The unique ID for this session, generated once at construction —
        needed early (before the session ends) so evidence screenshots can
        be uploaded under the same ID that save_to_db() will later use.
        """
        return self._session_uid

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

    def set_exam_info(self, exam_code: Optional[str], professor_uid: Optional[str],
                      exam_title: Optional[str]) -> None:
        """
        Record which exam/professor this session belongs to, so the
        dashboard can scope visibility to the owning professor. Should be
        called once at session start, right after the exam code (if any)
        is resolved — mirrors set_baseline(). All three arguments are None
        for a session that proceeded without a valid exam code.
        """
        self._exam_code = exam_code
        self._professor_uid = professor_uid
        self._exam_title = exam_title

    def log_event(self, risk_level: str, yaw: float, pitch: float, roll: float,
                  device_detected: bool, behavioral_indicator: str,
                  trigger: str = "",
                  screenshot_path: Optional[str] = None,
                  gaze_x: float = 0.0, gaze_y: float = 0.0,
                  gaze_valid: bool = False) -> None:
        """Append a new flagged event to the session log."""
        self._events.append(FlaggedEvent(
            timestamp=datetime.now().isoformat(),
            risk_level=risk_level,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            device_detected=device_detected,
            behavioral_indicator=behavioral_indicator,
            trigger=trigger,
            screenshot_path=screenshot_path,
            gaze_x=gaze_x,
            gaze_y=gaze_y,
            gaze_valid=gaze_valid,
        ))

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
    
    def save_to_db(self, repository, examinee_label: str = None) -> int | None:
        """
        Persist this session to the database. Safe to call alongside save() —
        a DB failure must never lose the session, so it degrades to a warning.
        """
        try:
            session_id = repository.save_report(
                self._build_report_dict(), self._session_uid, examinee_label)
            print(f"[SessionReport] Persisted to DB as session id={session_id}")
            return session_id
        except Exception as exc:
            print(f"[SessionReport][WARN] DB write failed ({exc}). "
                  f"JSON report is still intact.")
            return None

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
            "exam_code":            self._exam_code,
            "professor_uid":        self._professor_uid,
            "exam_title":           self._exam_title,
        }