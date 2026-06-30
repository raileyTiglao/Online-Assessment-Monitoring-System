"""
=============================================================================
config.py — Central Configuration
Online Assessment Monitoring System
Holy Angel University — School of Computing

All tunable parameters live here.
Change values here instead of hunting through multiple files.
=============================================================================
"""

import numpy as np


class DetectionConfig:
    """Settings for Faster R-CNN object detection."""

    # Minimum confidence score to accept a detection
    CONFIDENCE_THRESHOLD = 0.6

    # COCO class IDs: 77 = cell phone, 73 = laptop
    TARGET_CLASS_IDS = [77, 73]
    TARGET_CLASS_NAMES = {77: "Cell Phone", 73: "Laptop"}

    # --- Fine-tuned model replacement ---
    # Set CUSTOM_MODEL_PATH to your .pth file once training is done.
    # Leave as None to use COCO pre-trained weights.
    CUSTOM_MODEL_PATH = None       # e.g. "models/fasterrcnn_custom.pth"
    CUSTOM_NUM_CLASSES = 2         # background + 1 device class


class HeadPoseConfig:
    """Settings for MediaPipe Face Mesh + head pose estimation."""

    MAX_NUM_FACES            = 1
    MIN_DETECTION_CONFIDENCE = 0.5
    MIN_TRACKING_CONFIDENCE  = 0.5
    REFINE_LANDMARKS         = True

    # Angle thresholds (degrees) beyond which pose is flagged as suspicious
    YAW_THRESHOLD   = 30    # Horizontal left/right turn
    PITCH_THRESHOLD = 20    # Downward tilt (negative pitch)
    ROLL_THRESHOLD  = 20    # Lateral tilt

    # MediaPipe landmark indices used for solvePnP
    # Order: nose tip, chin, left eye corner, right eye corner,
    #        left mouth corner, right mouth corner
    LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]

    # Corresponding 3D model points (standard face, in mm)
    FACE_3D_MODEL = np.array([
        [  0.0,    0.0,    0.0],
        [  0.0, -330.0,  -65.0],
        [-225.0,  170.0, -135.0],
        [ 225.0,  170.0, -135.0],
        [-150.0, -150.0, -125.0],
        [ 150.0, -150.0, -125.0],
    ], dtype=np.float64)


class TemporalConfig:
    """Sliding window temporal analysis settings."""

    WINDOW_SIZE = 30              # Frames tracked (~2 sec at ~15 fps on CPU)
    MODERATE_TRIGGER_FRAMES = 10  # Frames of single signal to reach MODERATE
    HIGH_TRIGGER_FRAMES     = 20  # Frames of BOTH signals to reach HIGH


class CameraConfig:
    """Webcam settings."""

    CAMERA_INDEX = 0
    FRAME_WIDTH  = 1280
    FRAME_HEIGHT = 720


class OutputConfig:
    """Output paths and display settings."""

    SCREENSHOT_DIR      = "evidence_captures"
    SESSION_REPORT_FILE = "session_report.json"
    SCREENSHOT_COOLDOWN = 5    # Seconds between auto-captures

    # BGR colors for OpenCV
    RISK_COLORS = {
        "LOW":      (0, 200,   0),
        "MODERATE": (0, 165, 255),
        "HIGH":     (0,   0, 255),
    }


class SystemConfig:
    """General runtime settings."""

    USE_GPU = True    # False = force CPU
