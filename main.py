"""
=============================================================================
main.py — Entry Point
Online Assessment Monitoring System
Holy Angel University — School of Computing

Orchestrates all components into a single real-time monitoring session:
    Calibrator            → Pre-session baseline head pose + scale sampling
    ObjectDetector          → Faster R-CNN mobile device detection
    HeadPoseEstimator        → MediaPipe raw head pose + scale estimation
    HeadPoseNormalizer         → Baseline-relative pose + drift + suspicion
    TemporalAnalyzer              → Time-based sliding window aggregation
    RiskClassifier                  → Low / Moderate / High classification
    FrameBuffer                       → Rolling frame history for evidence lookup
    EvidenceCapture                     → Onset-based screenshot on High Risk
    SessionReport                         → Final JSON report
    OverlayRenderer                         → Live visual feedback

SESSION FLOW:
    1. Open webcam
    2. CALIBRATION PHASE (~7 seconds) — examinee sits naturally, system
       samples raw yaw/pitch/roll/scale and averages them into a baseline.
    3. MONITORING PHASE — behavioral decisions are made against the
       baseline. Distance drift is detected and suppresses false
       positives. Press 'R' to recalibrate, 'Q'/ESC to end the session.

EVIDENCE CAPTURE NOTE:
    Because HIGH risk escalation is intentionally delayed (it requires
    sustained behavior over the temporal window, not a single frame), the
    frame at the MOMENT of escalation may already show the examinee back
    to normal. To fix this, a rolling FrameBuffer keeps recent frames, and
    when HIGH risk fires, TemporalAnalyzer.get_onset_timestamp() finds
    when the sustained behavior actually BEGAN — the buffer then supplies
    the frame from that moment for the evidence screenshot instead of the
    live current frame.

HOW TO RUN:
    py -3.11 main.py
=============================================================================
"""

 #Test
import cv2
import time

from config import (
    CameraConfig, OutputConfig, DetectionConfig,
    CalibrationConfig, HotkeyConfig, TemporalConfig,
)
from detection import ObjectDetector, HeadPoseEstimator
from analysis import (
    Calibrator, HeadPoseNormalizer,
    TemporalAnalyzer, RiskClassifier,
)
from monitoring import EvidenceCapture, SessionReport, FrameBuffer
from display import OverlayRenderer


class MonitoringSession:
    """
    Coordinates all subsystems to run a full real-time monitoring session,
    including calibration, on-demand recalibration, and onset-based
    evidence capture.

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
        self.normalizer      = None   # Created/replaced after each calibration
        self.temporal        = TemporalAnalyzer()
        self.classifier      = RiskClassifier()
        self.evidence        = EvidenceCapture()
        self.report          = SessionReport()
        self.renderer        = OverlayRenderer()

        # Frame buffer sized to the temporal window + a safety margin, so
        # the onset frame (up to WINDOW_SECONDS in the past) is always
        # still available when a HIGH risk event needs it.
        buffer_duration = (TemporalConfig.WINDOW_SECONDS
                          + TemporalConfig.EVIDENCE_LOOKBACK_MARGIN_SECONDS)
        self.frame_buffer = FrameBuffer(max_age_seconds=buffer_duration)

        # --- Webcam ---
        self.capture = None

        # --- Frame timing for FPS display (resets on each recalibration) ---
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
        """
        Run calibration, then monitoring, looping back to calibration
        whenever the user requests recalibration, until the user quits.
        """
        if not self._open_camera():
            return

        try:
            while True:
                calibration_ok = self._run_calibration_phase()
                if not calibration_ok:
                    print("[MonitoringSession] Calibration did not complete "
                          "(cancelled or webcam issue). Ending session.")
                    return

                print(f"[MonitoringSession] Detection runs every "
                      f"{DetectionConfig.DETECTION_FRAME_SKIP} frame(s) "
                      f"(head pose runs every frame).")
                print("[MonitoringSession] Press 'R' to recalibrate, "
                      "'Q' or ESC to end the session.\n")

                self._reset_for_new_monitoring_phase()
                action = self._main_loop()

                if action == "quit":
                    break
                print("\n[MonitoringSession] Recalibrating...\n")
        finally:
            self._cleanup()
            self.report.save(OutputConfig.SESSION_REPORT_FILE)
            print(f"[MonitoringSession] Evidence screenshots captured: "
                  f"{self.evidence.capture_count}")
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
        
        print(f"[MonitoringSession] Please get comfortable, then press SPACE "
              f"to begin calibration ({CalibrationConfig.DURATION_SECONDS:.0f}s)...")

        self.calibrator.arm()

        # Wait for the user to signal they're ready
        while self.calibrator.is_waiting_to_start:
            ret, frame = self.capture.read()
            if not ret:
                return False

            display_frame = self.renderer.draw_ready_screen(frame)
            cv2.imshow("Online Assessment Monitor — HAU", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in HotkeyConfig.QUIT_KEYS:
                print("[MonitoringSession] Calibration cancelled by user.")
                return False
            if key == HotkeyConfig.START_CALIBRATION_KEY:
                self.calibrator.start()

        while not self.calibrator.is_complete():
            ret, frame = self.capture.read()
            if not ret:
                return False

            head_result = self.pose_estimator.estimate(frame)
            if head_result.success:
                self.calibrator.add_sample(
                    head_result.yaw, head_result.pitch, head_result.roll,
                    head_result.scale,
                )

            display_frame = self.renderer.draw_calibration(frame, self.calibrator)
            cv2.imshow("Online Assessment Monitor — HAU", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key in HotkeyConfig.QUIT_KEYS:
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
              f"roll={baseline.roll:.1f}° scale={baseline.scale:.1f}px "
              f"({baseline.sample_count} samples)")

        return True

    def _reset_for_new_monitoring_phase(self) -> None:
        """Clear state that shouldn't carry over between calibrations."""
        self.temporal.reset()
        self.classifier.reset()
        self.frame_buffer.reset()
        self._last_logged_level = "LOW"
        self._frame_count = 0
        self._timer_start = time.time()

    # ------------------------------------------------------------------
    # Internal: monitoring main loop
    # ------------------------------------------------------------------

    def _main_loop(self) -> str:
        """
        Read frames and run the full pipeline until the user quits or
        requests recalibration.

        Returns:
            "quit" or "recalibrate"
        """
        while True:
            ret, frame = self.capture.read()
            if not ret:
                print("[WARNING] Failed to read frame from webcam.")
                return "quit"

            self._frame_count += 1
            self._process_frame(frame)

            key = cv2.waitKey(1) & 0xFF
            if key in HotkeyConfig.QUIT_KEYS:
                print("\n[MonitoringSession] Session ended by user.")
                return "quit"
            if key == HotkeyConfig.RECALIBRATE_KEY:
                print("\n[MonitoringSession] Recalibration requested by user.")
                return "recalibrate"

    def _process_frame(self, frame) -> None:
        """Run one full pipeline pass on a single frame and display it."""

        # Buffer the raw current frame BEFORE any processing, so it's
        # available later for onset-based evidence lookup.
        self.frame_buffer.add(frame)

        # 1. Object detection (Faster R-CNN) — only every Nth frame
        device_detected, boxes, scores, labels = self._run_detection_with_skip(frame)

        # 2. Raw head pose + scale estimation (MediaPipe) — every frame
        head_result = self.pose_estimator.estimate(frame)

        # 3. Normalize against calibration baseline; detects distance drift
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
        """Run Faster R-CNN only every DETECTION_FRAME_SKIP frames."""
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
        """
        Capture evidence and log an event when risk escalates to
        MODERATE/HIGH. For HIGH risk, retrieves the ONSET frame (when the
        sustained behavior began) from the frame buffer instead of using
        the current (possibly already-normal) frame.
        """
        level = risk_result.level

        if level != self._last_logged_level and level in ("MODERATE", "HIGH"):
            evidence_frame = self._select_evidence_frame(frame, level, risk_result)
            screenshot_path = self.evidence.try_capture(evidence_frame, level)

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

    def _select_evidence_frame(self, current_frame, level, risk_result):
        """
        For HIGH risk, look up the frame from when the sustained behavior
        actually began (onset), rather than the current frame at the
        moment of escalation. Falls back to the current frame if no
        onset timestamp or buffered frame is available.
        """
        if level != "HIGH":
            return current_frame

        require_device = (risk_result.trigger_type == "dual_modal")
        onset_timestamp = self.temporal.get_onset_timestamp(require_device=require_device)

        if onset_timestamp is None:
            return current_frame

        onset_frame = self.frame_buffer.get_frame_near(onset_timestamp)
        return onset_frame if onset_frame is not None else current_frame

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _calculate_fps(self) -> float:
        """Compute running average FPS since the current monitoring phase started."""
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