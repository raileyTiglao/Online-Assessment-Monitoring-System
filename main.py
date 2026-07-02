"""
=============================================================================
main.py — Entry Point
Online Assessment Monitoring System
Holy Angel University — School of Computing

Orchestrates all components into a single real-time monitoring session:
    Calibrator            → Pre-session baseline head pose sampling
    ObjectDetector         → Faster R-CNN mobile device detection
    HeadPoseEstimator      → MediaPipe raw head pose estimation
    HeadPoseNormalizer     → Baseline-relative pose + suspicion analysis
    TemporalAnalyzer       → Time-based sliding window aggregation
    RiskClassifier         → Low / Moderate / High classification
    EvidenceCapture        → Auto screenshot on High Risk
    SessionReport          → Final JSON report
    OverlayRenderer        → Live visual feedback

SESSION FLOW:
    1. Open webcam
    2. CALIBRATION PHASE (~7 seconds) — examinee sits naturally, system
       samples raw yaw/pitch/roll and averages them into a baseline.
       Monitoring does NOT begin until this completes.
    3. MONITORING PHASE — all head pose behavioral decisions are made
       against the baseline (normalized angles), not absolute camera angles.

PERFORMANCE NOTE:
    Faster R-CNN is a heavy two-stage detector and is the main FPS
    bottleneck. Object detection runs every DetectionConfig.DETECTION_FRAME_SKIP
    frames, reusing the last known detection result on skipped frames.
    Head pose estimation (MediaPipe) is cheap and runs on every frame.

HOW TO RUN:
    py -3.11 main.py

Press 'Q' in the video window to end the session and save the report.
=============================================================================
"""

import cv2
import time

from config import CameraConfig, OutputConfig, DetectionConfig, CalibrationConfig
from detection import ObjectDetector, HeadPoseEstimator
from analysis import (
    Calibrator, HeadPoseNormalizer,
    TemporalAnalyzer, RiskClassifier,
)
from monitoring import EvidenceCapture, SessionReport
from display import OverlayRenderer


class MonitoringSession:
    """
    Coordinates all subsystems to run a full real-time monitoring session,
    including the pre-session calibration phase.

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
        self.detector        = ObjectDetector()
        self.pose_estimator  = HeadPoseEstimator()
        self.calibrator      = Calibrator()
        self.normalizer       = None   # Created after calibration completes
        self.temporal         = TemporalAnalyzer()
        self.classifier        = RiskClassifier()
        self.evidence            = EvidenceCapture()
        self.report               = SessionReport()
        self.renderer               = OverlayRenderer()

        # --- Webcam ---
        self.capture = None

        # --- Frame timing for FPS display (monitoring phase only) ---
        self._frame_count = 0
        self._timer_start = None

        # --- Track last logged level to avoid duplicate event spam ---
        self._last_logged_level = "LOW"

        # --- Detection frame-skip state ---
        self._detection_skip_counter = 0
        self._cached_device_detected = False
        self._cached_boxes  = []
        self._cached_scores = []
        self._cached_labels = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Run calibration, then the full monitoring session until quit."""
        if not self._open_camera():
            return

        try:
            calibration_ok = self._run_calibration_phase()
            if not calibration_ok:
                print("[MonitoringSession] Calibration did not complete "
                      "(webcam closed or interrupted). Ending session.")
                return

            print("[MonitoringSession] Calibration complete. "
                  "Starting monitoring...")
            print(f"[MonitoringSession] Detection runs every "
                  f"{DetectionConfig.DETECTION_FRAME_SKIP} frame(s) "
                  f"(head pose runs every frame).")
            print("[MonitoringSession] Press 'Q' to end the session.\n")

            self._timer_start = time.time()
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
    # Internal: calibration phase
    # ------------------------------------------------------------------

    def _run_calibration_phase(self) -> bool:
        """
        Show the calibration screen and collect raw head pose samples
        until the calibration duration elapses. Builds the baseline and
        creates the HeadPoseNormalizer that the monitoring phase will use.

        Returns:
            True if calibration completed normally, False if the user
            closed the window early (e.g. pressed Q or closed the webcam).
        """
        print(f"[MonitoringSession] Starting calibration "
              f"({CalibrationConfig.DURATION_SECONDS:.0f}s)...")
        print("[MonitoringSession] Please sit naturally and look at the screen.\n")

        self.calibrator.start()

        while not self.calibrator.is_complete():
            ret, frame = self.capture.read()
            if not ret:
                return False

            head_result = self.pose_estimator.estimate(frame)
            if head_result.success:
                self.calibrator.add_sample(
                    head_result.yaw, head_result.pitch, head_result.roll
                )

            display_frame = self.renderer.draw_calibration(frame, self.calibrator)
            cv2.imshow("Online Assessment Monitor — HAU", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[MonitoringSession] Calibration cancelled by user.")
                return False

        baseline = self.calibrator.compute_baseline()
        self.normalizer = HeadPoseNormalizer(baseline)

        self.report.set_baseline(
            yaw=baseline.yaw, pitch=baseline.pitch, roll=baseline.roll,
            sample_count=baseline.sample_count,
        )

        print(f"[MonitoringSession] Baseline captured: "
              f"yaw={baseline.yaw:.1f}° pitch={baseline.pitch:.1f}° "
              f"roll={baseline.roll:.1f}° "
              f"({baseline.sample_count} samples)")

        return True

    # ------------------------------------------------------------------
    # Internal: monitoring main loop
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

        # 1. Object detection (Faster R-CNN) — only every Nth frame
        device_detected, boxes, scores, labels = self._run_detection_with_skip(frame)

        # 2. Raw head pose estimation (MediaPipe) — every frame, it's cheap
        head_result = self.pose_estimator.estimate(frame)

        # 3. Normalize against calibration baseline + evaluate suspicion
        normalized_pose = self.normalizer.normalize(head_result)

        # 4. Temporal analysis (time-based sliding window aggregation)
        self.temporal.update(device_detected, normalized_pose.suspicious)
        snapshot = self.temporal.get_snapshot()

        # 5. Risk classification
        risk_result = self.classifier.classify(snapshot)

        # 6. Evidence capture + event logging on escalation
        self._handle_risk_result(risk_result, frame, device_detected, normalized_pose)

        # 7. Render overlays and display
        fps = self._calculate_fps()
        frame = self.renderer.draw(
            frame=frame,
            device_detected=device_detected,
            boxes=boxes,
            scores=scores,
            labels=labels,
            normalized_pose=normalized_pose,
            risk_level=risk_result.level,
            snapshot=snapshot,
            window_seconds=self.temporal.window_seconds,
            fps=fps,
        )

        cv2.imshow("Online Assessment Monitor — HAU", frame)

    def _run_detection_with_skip(self, frame) -> tuple:
        """
        Run Faster R-CNN only every DETECTION_FRAME_SKIP frames.
        On skipped frames, return the cached result from the last actual
        detection so display and temporal analysis stay consistent.
        """
        skip = max(1, DetectionConfig.DETECTION_FRAME_SKIP)

        if self._detection_skip_counter % skip == 0:
            device_detected, boxes, scores, labels = self.detector.detect(frame)
            self._cached_device_detected = device_detected
            self._cached_boxes  = boxes
            self._cached_scores = scores
            self._cached_labels = labels
        else:
            device_detected = self._cached_device_detected
            boxes  = self._cached_boxes
            scores = self._cached_scores
            labels = self._cached_labels

        self._detection_skip_counter += 1
        return device_detected, boxes, scores, labels

    def _handle_risk_result(self, risk_result, frame, device_detected,
                             normalized_pose) -> None:
        """Capture evidence and log an event when risk escalates to MODERATE/HIGH."""
        level = risk_result.level

        if level != self._last_logged_level and level in ("MODERATE", "HIGH"):
            screenshot_path = self.evidence.try_capture(frame, level)

            self.report.log_event(
                risk_level=level,
                yaw=normalized_pose.yaw,
                pitch=normalized_pose.pitch,
                roll=normalized_pose.roll,
                device_detected=device_detected,
                behavioral_indicator=normalized_pose.reason,
                trigger=risk_result.trigger,
                screenshot_path=screenshot_path,
            )

        self._last_logged_level = level

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _calculate_fps(self) -> float:
        """Compute running average FPS since monitoring phase started."""
        if self._timer_start is None:
            return 0.0
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