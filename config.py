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

    # COCO class IDs: 77 = cell phone only
    # Laptop removed — focus is on mobile device (phone/tablet) cheating
    # Tablets are partially detected under the phone class in COCO.
    # Your fine-tuned model will handle phone/tablet distinction more precisely.
    TARGET_CLASS_IDS = [77]
    TARGET_CLASS_NAMES = {77: "Cell Phone"}

    # --- Fine-tuned model replacement ---
    # Set CUSTOM_MODEL_PATH to your .pth file once training is done.
    # Leave as None to use COCO pre-trained weights.
    CUSTOM_MODEL_PATH = None       # e.g. "models/fasterrcnn_custom.pth"
    CUSTOM_NUM_CLASSES = 2         # background + 1 device class

    # --- Performance optimizations ---
    # Run Faster R-CNN every Nth frame instead of every frame.
    # Head pose still runs every frame (it's cheap). Detection boxes are
    # reused on skipped frames so the display doesn't flicker.
    # 1 = run every frame (slowest, most responsive)
    # 2 = run every 2nd frame (better balance at low FPS)
    DETECTION_FRAME_SKIP = 2

    # Resize the frame before feeding it to Faster R-CNN.
    # Smaller input = much faster inference. Detection boxes are scaled
    # back up to original frame size for display, so accuracy on phone-sized
    # objects is barely affected at these resolutions.
    # Set to None to disable resizing (use full camera resolution).
    DETECTION_INPUT_WIDTH = 480

    # Use mixed-precision (FP16) inference on GPU for a speed boost.
    # Has no effect on CPU.
    USE_AMP = True


class CalibrationConfig:
    """
    Settings for the pre-session head pose calibration phase.

    Before monitoring begins, the examinee is asked to sit naturally and
    look at the screen for a short period. Their average yaw/pitch/roll
    (and face scale) during this window becomes the baseline that all
    later readings are compared against, rather than absolute
    camera-relative angles.
    """

    DURATION_SECONDS = 7.0   # How long calibration runs before monitoring starts
    MIN_SAMPLES = 10          # Minimum face samples needed to trust the baseline

    # --- Distance / scale drift detection ---
    # Monocular head pose estimation (solvePnP with an approximated camera
    # matrix and a generic 3D face model) carries systematic error that
    # changes with distance-to-camera. If the examinee moves significantly
    # closer/farther after calibration, normalized angles become unreliable
    # and can produce false positives. We detect this via the change in
    # inter-eye pixel distance (a proxy for distance) relative to baseline.
    SCALE_DRIFT_TOLERANCE = 0.20   # ±20% change in face scale triggers a warning


class HotkeyConfig:
    """Keyboard controls available during a monitoring session."""

    QUIT_KEYS = [ord('q'), 27]     # 'q' or ESC ends the session
    RECALIBRATE_KEY = ord('r')     # 'r' redoes the calibration phase mid-session


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
    """
    Sliding window temporal analysis settings.

    Time-based rather than frame-count-based, so behavior is consistent
    regardless of actual FPS achieved on a given machine (CPU vs GPU,
    detection frame-skip settings, etc). Internally the window still
    stores discrete frame entries, but the analyzer prunes by elapsed
    time instead of a fixed frame count.
    """

    WINDOW_SECONDS = 5.0             # Slightly wider window gives more time to accumulate signal

    MODERATE_TRIGGER_RATIO = 0.25    # 25% of window = ~1.25 seconds of a single signal

    HIGH_TRIGGER_RATIO     = 0.45    # 45% of window = ~2.25 seconds of both signals co-occurring
                                      # Lowered from 0.65 — more achievable with frame-skip detection

    # Head-pose-only HIGH risk threshold.
    # If the student sustains a suspicious head orientation for this fraction
    # of the window WITHOUT any device being detected, that alone escalates
    # to HIGH. Captures behaviors like prolonged downward gaze without a visible device.
    HEAD_ONLY_HIGH_RATIO   = 0.65    # 65% of window = ~3.25 seconds sustained head pose alone
                                      # Stricter than dual-modal since it's a single signal

    # Safety cap on stored entries so memory doesn't grow unbounded if
    # FPS spikes very high — effectively irrelevant in practice.
    MAX_WINDOW_ENTRIES = 600


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

    USE_GPU = True    # False = force CPU (DetectionConfig.USE_AMP is ignored on CPU)