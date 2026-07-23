"""
=============================================================================
display/overlay.py — Visual Overlay Renderer
Online Assessment Monitoring System
Holy Angel University — School of Computing

Encapsulates all OpenCV drawing/overlay logic for the live monitoring
window: calibration screen, risk banner, bounding boxes, normalized head
pose readout, temporal window stats, and FPS counter.
=============================================================================
"""

import cv2
import numpy as np
from config import OutputConfig
from analysis.head_pose_normalizer import NormalizedPose
from analysis.temporal import TemporalSnapshot
from analysis.calibration import Calibrator


class OverlayRenderer:
    """
    Draws all visual overlays onto a frame for live display.

    Usage:
        renderer = OverlayRenderer()
        frame = renderer.draw_calibration(frame, calibrator)   # during calibration
        frame = renderer.draw(frame, ..., normalized_pose, ...)  # during monitoring
    """

    def __init__(self):
        self._risk_colors = OutputConfig.RISK_COLORS

    # ------------------------------------------------------------------
    # Public API — Calibration Screen
    # ------------------------------------------------------------------

    def draw_calibration(self, frame: np.ndarray, calibrator: Calibrator) -> np.ndarray:
        """
        Draw the pre-session calibration screen: instructions, countdown,
        and a progress bar. Shown while the examinee sits naturally so
        their baseline head pose can be sampled.

        Args:
            frame:      Current BGR frame to draw onto
            calibrator: Active Calibrator instance tracking progress

        Returns:
            The frame with the calibration overlay drawn on it
        """
        h, w = frame.shape[:2]

        # Dim the frame slightly so text is readable over any background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.35, frame, 0.65, 0)

        # Title
        cv2.putText(frame, "CALIBRATING...", (w // 2 - 160, h // 2 - 100),
                    cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 200, 255), 3)

        # Instructions
        cv2.putText(frame, "Please sit naturally and look at your screen",
                    (w // 2 - 280, h // 2 - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Countdown
        remaining = calibrator.remaining_seconds()
        cv2.putText(frame, f"{remaining:.1f}s remaining",
                    (w // 2 - 100, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Progress bar
        bar_x1, bar_y1 = w // 2 - 200, h // 2 + 40
        bar_x2, bar_y2 = w // 2 + 200, h // 2 + 70
        progress = calibrator.progress_ratio()
        fill_x2  = int(bar_x1 + (bar_x2 - bar_x1) * progress)

        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (100, 100, 100), 2)
        cv2.rectangle(frame, (bar_x1, bar_y1), (fill_x2, bar_y2), (0, 200, 255), -1)

        # Sample count
        cv2.putText(frame, f"Samples collected: {calibrator.sample_count}",
                    (w // 2 - 130, h // 2 + 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        cv2.putText(frame, "Press Q or ESC to cancel",
                    (w // 2 - 110, h // 2 + 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        return frame

    # ------------------------------------------------------------------
    # Public API — Monitoring Overlays
    # ------------------------------------------------------------------

    def draw(self, frame: np.ndarray, device_detected: bool, boxes: list,
             scores: list, labels: list, normalized_pose: NormalizedPose,
             risk_level: str, snapshot: TemporalSnapshot,
             window_seconds: float, fps: float = None) -> np.ndarray:
        """
        Draw all overlays onto the frame and return the modified frame.

        Args:
            frame:            Current BGR frame to draw onto
            device_detected:  Whether a device was detected this frame
            boxes:            List of bounding boxes from ObjectDetector
            scores:           Confidence scores matching boxes
            labels:           Class label names matching boxes
            normalized_pose:  NormalizedPose (baseline-relative) from HeadPoseNormalizer
            risk_level:       Current risk classification string
            snapshot:         TemporalSnapshot with time-based ratios
            window_seconds:   Configured sliding window duration in seconds
            fps:              Optional current frames-per-second to display

        Returns:
            The frame with all overlays drawn on it
        """
        risk_color = self._risk_colors.get(risk_level, (200, 200, 200))
        h, w = frame.shape[:2]

        self._draw_risk_banner(frame, risk_level, risk_color, w)
        self._draw_device_boxes(frame, boxes, scores, labels)
        self._draw_device_status(frame, device_detected)
        self._draw_normalized_pose(frame, normalized_pose)
        self._draw_temporal_panel(frame, snapshot, window_seconds, h, w)

        if fps is not None:
            self._draw_fps(frame, fps, w)

        return frame

    # ------------------------------------------------------------------
    # Internal drawing helpers
    # ------------------------------------------------------------------

    def _draw_risk_banner(self, frame, risk_level, risk_color, w):
        """Top banner showing the current risk level."""
        cv2.rectangle(frame, (0, 0), (w, 50), risk_color, -1)
        text = f"RISK: {risk_level}"
        cv2.putText(frame, text, (w // 2 - 120, 36),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)

    def _draw_device_boxes(self, frame, boxes, scores, labels):
        """Bounding boxes around detected devices."""
        for box, score, label in zip(boxes, scores, labels):
            x1, y1, x2, y2 = box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
            cv2.putText(frame, f"{label} {score:.0%}",
                        (x1, max(y1 - 8, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)

    def _draw_device_status(self, frame, device_detected):
        """Text indicator: device detected or not."""
        text  = "DEVICE DETECTED" if device_detected else "No device"
        color = (0, 0, 255) if device_detected else (0, 200, 0)
        cv2.putText(frame, text, (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def _draw_normalized_pose(self, frame, pose: NormalizedPose):
        """
        Baseline-relative head pose angle readout and status message.
        Shows a distinct ORANGE drift warning when the examinee has moved
        significantly closer/farther from the camera since calibration
        (normalized angles are unreliable in this state), versus a RED
        suspicious-behavior reason when the baseline is still valid.
        """
        if not pose.success:
            cv2.putText(frame, "No face detected", (10, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)
            return

        color = (0, 0, 255) if pose.suspicious else (0, 200, 0)
        cv2.putText(frame, f"Yaw Delta:   {pose.yaw:+.1f} deg", (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, f"Pitch Delta: {pose.pitch:+.1f} deg", (10, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, f"Roll Delta:  {pose.roll:+.1f} deg", (10, 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Scale readout — helps the examinee/proctor see distance drift forming
        scale_color = (0, 165, 255) if pose.drifted else (150, 150, 150)
        cv2.putText(frame, f"Distance: {pose.scale_ratio:.0%} of calibrated",
                    (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.5, scale_color, 1)

        if pose.drifted:
            cv2.putText(frame, f"! {pose.reason}", (10, 215),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2)
        elif pose.suspicious:
            cv2.putText(frame, f"! {pose.reason}", (10, 215),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    def _draw_temporal_panel(self, frame, snapshot: TemporalSnapshot,
                              window_seconds: float, h: int, w: int):
        """Bottom panel showing time-based sliding window statistics."""
        panel_y = h - 90
        cv2.rectangle(frame, (0, panel_y), (w, h), (30, 30, 30), -1)

        window_info = (f"Window: {snapshot.window_seconds:.1f}s "
                       f"/ {window_seconds:.0f}s  "
                       f"({snapshot.sample_count} samples)")
        cv2.putText(frame, window_info, (10, panel_y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1)

        ratio_text = (f"Device: {snapshot.device_ratio:.0%}  "
                      f"Head: {snapshot.head_ratio:.0%}  "
                      f"Both: {snapshot.both_ratio:.0%}")
        cv2.putText(frame, ratio_text, (10, panel_y + 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1)

        cv2.putText(frame, "Press Q/ESC to end · R to recalibrate",
                    (10, panel_y + 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (150, 150, 150), 1)

    def _draw_fps(self, frame, fps, w):
        """Frames-per-second counter, top right."""
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 150, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)