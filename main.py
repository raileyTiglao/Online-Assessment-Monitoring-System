"""
=============================================================================
main.py — Entry Point
Online Assessment Monitoring System
Holy Angel University — School of Computing

Orchestrates all components into a single real-time monitoring session:
    ObjectDetector      → Faster R-CNN mobile device detection
    HeadPoseEstimator   → MediaPipe head pose estimation
    TemporalAnalyzer    → Sliding window aggregation
    RiskClassifier      → Low / Moderate / High classification
    EvidenceCapture     → Auto screenshot on High Risk
    SessionReport       → Final JSON report
    OverlayRenderer     → Live visual feedback

HOW TO RUN:
    py -3.11 main.py

Press 'Q' in the video window to end the session and save the report.
=============================================================================
"""

import cv2
import time

from config import CameraConfig, OutputConfig
from detection import ObjectDetector, HeadPoseEstimator
from analysis import TemporalAnalyzer, RiskClassifier
from monitoring import EvidenceCapture, SessionReport
from display import OverlayRenderer


class MonitoringSession:
    """
    Coordinates all subsystems to run a full real-time monitoring session.

    This class owns the webcam, runs the per-frame pipeline, and manages
    the lifecycle of every component (setup, loop, cleanup, report saving).

    Usage:
        session = MonitoringSession()
        session.run()
    """

    def __init__(self):
        print("\n" + "=" * 60)
        print("  Online Assessment Monitoring System")
        print("  Holy Angel University — School of Computing")
        print("=" * 60 + "\n")

        # --- Core components ---
        self.detector   = ObjectDetector()
        self.pose_estimator = HeadPoseEstimator()
        self.temporal   = TemporalAnalyzer()
        self.classifier = RiskClassifier()
        self.evidence   = EvidenceCapture()
        self.report     = SessionReport()
        self.renderer   = OverlayRenderer()

        # --- Webcam ---
        self.capture = None

        # --- Frame timing for FPS display ---
        self._frame_count = 0
        self._timer_start = None

        # --- Track last logged level to avoid duplicate event spam ---
        self._last_logged_level = "LOW"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run the full monitoring session until the user quits."""
        if not self._open_camera():
            return

        print("[MonitoringSession] Webcam opened. Starting session...")
        print("[MonitoringSession] Press 'Q' to end the session.\n")

        self._timer_start = time.time()

        try:
            self._main_loop()
        finally:
            self._cleanup()
            self.report.save(OutputConfig.SESSION_REPORT_FILE)
            print("\n[MonitoringSession] Session complete.")

    # ------------------------------------------------------------------
    # Internal: setup
    # ------------------------------------------------------------------

    def _open_camera(self) -> bool:
        """Open the webcam using settings from CameraConfig."""
        self.capture = cv2.VideoCapture(CameraConfig.CAMERA_INDEX)

        if not self.capture.isOpened():
            print("[ERROR] Could not open webcam. "
                  "Check that your camera is connected and not in use.")
            return False

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, CameraConfig.FRAME_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraConfig.FRAME_HEIGHT)
        return True

    # ------------------------------------------------------------------
    # Internal: main loop
    # ------------------------------------------------------------------

    def _main_loop(self) -> None:
        """Read frames and run the full detection → analysis → display pipeline."""
        while True:
            ret, frame = self.capture.read()
            if not ret:
                print("[WARNING] Failed to read frame from webcam.")
                break

            self._frame_count += 1
            self._process_frame(frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n[MonitoringSession] Session ended by user.")
                break

    def _process_frame(self, frame) -> None:
        """Run one full pipeline pass on a single frame and display it."""

        # 1. Object detection (Faster R-CNN)
        device_detected, boxes, scores, labels = self.detector.detect(frame)

        # 2. Head pose estimation (MediaPipe)
        head_result = self.pose_estimator.estimate(frame)

        # 3. Temporal analysis (sliding window aggregation)
        self.temporal.update(device_detected, head_result.suspicious)
        snapshot = self.temporal.get_snapshot()

        # 4. Risk classification
        risk_result = self.classifier.classify(snapshot)

        # 5. Evidence capture + event logging on escalation
        self._handle_risk_result(risk_result, frame, device_detected, head_result)

        # 6. Render overlays and display
        fps = self._calculate_fps()
        frame = self.renderer.draw(
            frame=frame,
            device_detected=device_detected,
            boxes=boxes,
            scores=scores,
            labels=labels,
            head_result=head_result,
            risk_level=risk_result.level,
            snapshot=snapshot,
            window_size=self.temporal.window_size,
            fps=fps,
        )

        cv2.imshow("Online Assessment Monitor — HAU", frame)

    def _handle_risk_result(self, risk_result, frame, device_detected,
                             head_result) -> None:
        """Capture evidence and log an event when risk escalates to MODERATE/HIGH."""
        level = risk_result.level

        # Only log a new event when the level actually changes upward,
        # to avoid flooding the report with duplicate entries every frame
        if level != self._last_logged_level and level in ("MODERATE", "HIGH"):
            screenshot_path = self.evidence.try_capture(frame, level)

            self.report.log_event(
                risk_level=level,
                yaw=head_result.yaw,
                pitch=head_result.pitch,
                roll=head_result.roll,
                device_detected=device_detected,
                behavioral_indicator=head_result.reason,
                screenshot_path=screenshot_path,
            )

        self._last_logged_level = level

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _calculate_fps(self) -> float:
        """Compute running average FPS since session start."""
        elapsed = time.time() - self._timer_start
        if elapsed <= 0:
            return 0.0
        return self._frame_count / elapsed

    def _cleanup(self) -> None:
        """Release all resources (camera, windows, MediaPipe)."""
        if self.capture is not None:
            self.capture.release()
        cv2.destroyAllWindows()
        self.pose_estimator.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    session = MonitoringSession()
    session.run()
