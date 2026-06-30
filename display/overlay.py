"""
=============================================================================
display/overlay.py — Visual Overlay Renderer
Online Assessment Monitoring System
Holy Angel University — School of Computing

Encapsulates all OpenCV drawing/overlay logic for the live monitoring
window: risk banner, bounding boxes, head pose readout, temporal window
stats, and FPS counter.
=============================================================================
"""

import cv2
import numpy as np
from config import OutputConfig
from detection.head_pose import HeadPoseResult
from analysis.temporal import TemporalSnapshot


class OverlayRenderer:
    """
    Draws all visual overlays onto a frame for live display.

    Usage:
        renderer = OverlayRenderer()
        frame = renderer.draw(frame, device_detected=True, boxes=[...],
                               scores=[...], labels=[...],
                               head_result=head_result, risk_level="HIGH",
                               snapshot=snapshot, window_size=30, fps=24.5)
    """

    def __init__(self):
        self._risk_colors = OutputConfig.RISK_COLORS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw(self, frame: np.ndarray, device_detected: bool, boxes: list,
              scores: list, labels: list, head_result: HeadPoseResult,
              risk_level: str, snapshot: TemporalSnapshot,
              window_size: int, fps: float = None) -> np.ndarray:
        """
        Draw all overlays onto the frame and return the modified frame.

        Args:
            frame:           Current BGR frame to draw onto
            device_detected: Whether a device was detected this frame
            boxes:           List of bounding boxes from ObjectDetector
            scores:          Confidence scores matching boxes
            labels:          Class label names matching boxes
            head_result:     HeadPoseResult from HeadPoseEstimator
            risk_level:      Current risk classification string
            snapshot:        TemporalSnapshot with window counts
            window_size:     Configured sliding window size
            fps:             Optional current frames-per-second to display

        Returns:
            The frame with all overlays drawn on it
        """
        h, w = frame.shape[:2]
        risk_color = self._risk_colors.get(risk_level, (200, 200, 200))

        self._draw_risk_banner(frame, risk_level, risk_color, w)
        self._draw_device_boxes(frame, boxes, scores, labels)
        self._draw_device_status(frame, device_detected)
        self._draw_head_pose(frame, head_result)
        self._draw_temporal_panel(frame, snapshot, window_size, h, w)

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
            cv2.putText(frame, f"{label} {score:.0%}", (x1, max(y1 - 8, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)

    def _draw_device_status(self, frame, device_detected):
        """Text indicator: device detected or not."""
        text  = "DEVICE DETECTED" if device_detected else "No device"
        color = (0, 0, 255) if device_detected else (0, 200, 0)
        cv2.putText(frame, text, (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def _draw_head_pose(self, frame, head_result: HeadPoseResult):
        """Head pose angle readout and suspicious-behavior reason."""
        if not head_result.success:
            cv2.putText(frame, "No face detected", (10, 115),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 2)
            return

        color = (0, 0, 255) if head_result.suspicious else (0, 200, 0)
        cv2.putText(frame, f"Yaw:   {head_result.yaw:+.1f} deg", (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, f"Pitch: {head_result.pitch:+.1f} deg", (10, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, f"Roll:  {head_result.roll:+.1f} deg", (10, 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if head_result.suspicious:
            cv2.putText(frame, f"! {head_result.reason}", (10, 195),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    def _draw_temporal_panel(self, frame, snapshot: TemporalSnapshot,
                              window_size, h, w):
        """Bottom panel showing sliding window statistics."""
        panel_y = h - 80
        cv2.rectangle(frame, (0, panel_y), (w, h), (30, 30, 30), -1)

        stats_text = (f"Window ({window_size} frames):  "
                      f"Device={snapshot.device_count}  "
                      f"Head={snapshot.head_count}  "
                      f"Both={snapshot.both_count}")
        cv2.putText(frame, stats_text, (10, panel_y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(frame, "Press Q to end session", (10, panel_y + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

    def _draw_fps(self, frame, fps, w):
        """Frames-per-second counter, top right."""
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 150, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
