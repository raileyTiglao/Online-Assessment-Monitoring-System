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
from config import OutputConfig, CalibrationConfig
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

        ok = calibrator.status_ok
        guide_color = (0, 220, 0) if ok else (0, 165, 255)

        self._draw_silhouette(frame, w, h, guide_color)

        # Title
        cv2.putText(frame, "CALIBRATING", (w // 2 - 130, 52),
                    cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 200, 255), 2)
        cv2.putText(frame, "Align yourself with the outline and look at your screen",
                    (w // 2 - 300, 84),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (235, 235, 235), 1)

        # Live positioning feedback — the whole point of the guide, so it
        # gets the most prominent placement below the silhouette.
        status = calibrator.status
        (tw, _), _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)
        cv2.putText(frame, status, (w // 2 - tw // 2, h - 128),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, guide_color, 2)

        # Countdown + progress bar
        remaining = calibrator.remaining_seconds()
        cv2.putText(frame, f"{remaining:.1f}s", (w // 2 - 28, h - 96),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        bar_x1, bar_y1 = w // 2 - 200, h - 80
        bar_x2, bar_y2 = w // 2 + 200, h - 58
        progress = calibrator.progress_ratio()
        fill_x2  = int(bar_x1 + (bar_x2 - bar_x1) * progress)
        cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (100, 100, 100), 2)
        cv2.rectangle(frame, (bar_x1, bar_y1), (fill_x2, bar_y2), (0, 200, 255), -1)

        # Sample count — only samples taken while correctly positioned are
        # counted, so a stalled number tells the examinee their pose is
        # being rejected even if the countdown keeps running.
        cv2.putText(frame, f"Samples: {calibrator.sample_count}",
                    (w // 2 - 70, h - 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(frame, "Press Q or ESC to cancel", (w // 2 - 105, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (150, 150, 150), 1)

        return frame

    def _draw_silhouette(self, frame, w: int, h: int, color) -> None:
        """
        Draw a seated-person outline for the examinee to align to: head
        ellipse, neck, and shoulder curve.

        Sized from CalibrationConfig's own guide values rather than picked
        by eye, so what's drawn matches what the Calibrator actually
        accepts — an outline the examinee can fill but the validator still
        rejects would be worse than no outline at all.

        Only the head is machine-checked (MediaPipe tracks the face, not
        the body); the shoulders exist to make the intended posture
        obvious, which a bare rectangle can't convey.
        """
        cfg = CalibrationConfig
        cx = int(cfg.GUIDE_HEAD_CENTER[0] * w)
        cy = int(cfg.GUIDE_HEAD_CENTER[1] * h)

        # A head is roughly 2.2x as wide as the inter-eye distance the
        # scale check measures; aim the outline at the middle of the
        # accepted range so there's room on both sides.
        mid_scale = (cfg.GUIDE_SCALE_MIN + cfg.GUIDE_SCALE_MAX) / 2.0
        head_hw = int(1.1 * mid_scale * w)
        head_hh = int(head_hw * 1.3)

        cv2.ellipse(frame, (cx, cy), (head_hw, head_hh), 0, 0, 360, color, 2)

        # Neck — short verticals from the jaw down toward the shoulders
        neck_top = cy + head_hh
        neck_bottom = neck_top + int(head_hh * 0.22)
        for side in (-1, 1):
            x = cx + side * int(head_hw * 0.42)
            cv2.line(frame, (x, neck_top), (x, neck_bottom), color, 2)

        # Shoulders — upper arc of a wide ellipse, clipped at the frame
        # edge so it reads as a torso continuing out of view.
        shoulder_hw = int(head_hw * 2.7)
        shoulder_hh = int(head_hh * 0.95)
        cv2.ellipse(frame, (cx, neck_bottom + shoulder_hh), (shoulder_hw, shoulder_hh),
                    0, 185, 355, color, 2)

        # Centre crosshair — a small, unobtrusive target for the nose,
        # which is the landmark the position check actually uses.
        cv2.line(frame, (cx - 9, cy), (cx + 9, cy), color, 1)
        cv2.line(frame, (cx, cy - 9), (cx, cy + 9), color, 1)

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

        # Gaze readout (iris offset from calibrated neutral, in eye widths).
        # Shown even when gaze flagging is disabled, so the thresholds can be
        # tuned by watching real values during a session.
        if pose.gaze_valid:
            gaze_color = (0, 0, 255) if pose.gaze_suspicious else (150, 150, 150)
            gaze_text = f"Gaze: x={pose.gaze_x:+.3f} y={pose.gaze_y:+.3f}"
        else:
            gaze_color = (100, 100, 100)
            gaze_text = "Gaze: -- (eyes closed)"
        cv2.putText(frame, gaze_text, (10, 212),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, gaze_color, 1)

        if pose.drifted:
            cv2.putText(frame, f"! {pose.reason}", (10, 236),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2)
        elif pose.suspicious:
            cv2.putText(frame, f"! {pose.reason}", (10, 236),
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
                      f"Pitch: {snapshot.pitch_ratio:.0%}  "
                      f"Yaw: {snapshot.yaw_ratio:.0%}  "
                      f"Roll: {snapshot.roll_ratio:.0%}  "
                      f"Lost: {snapshot.dropout_ratio:.0%}  "
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