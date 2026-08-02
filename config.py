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
    TARGET_CLASS_NAMES = {77: " Mobile Devices"}

    # --- Fine-tuned model replacement ---
    # Set CUSTOM_MODEL_PATH to your .pth file once training is done.
    # Leave as None to use COCO pre-trained weights.
    CUSTOM_MODEL_PATH = None
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
    SETTLE_SECONDS = 1.5     # ignore samples during this initial window — user

    # --- Distance / scale drift detection ---
    # Monocular head pose estimation (solvePnP with an approximated camera
    # matrix and a generic 3D face model) carries systematic error that
    # changes with distance-to-camera. If the examinee moves significantly
    # closer/farther after calibration, normalized angles become unreliable
    # and can produce false positives. We detect this via the change in
    # inter-eye pixel distance (a proxy for distance) relative to baseline.
    SCALE_DRIFT_TOLERANCE = 0.20   # ±20% change in face scale triggers a warning

    POST_CALIBRATION_GRACE_SECONDS = 2.0 # Grace period so the model can process recorded baselines


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
    YAW_THRESHOLD   = 32    # Horizontal left/right turn
    PITCH_THRESHOLD = 10    # Downward tilt (negative pitch)
    ROLL_THRESHOLD  = 22    # Lateral tilt

    # MediaPipe landmark indices used for solvePnP
    # Order: nose tip, chin, left eye corner, right eye corner,
    #        left mouth corner, right mouth corner
    LANDMARK_INDICES = [1, 152, 33, 263, 133, 362, 61, 291,
                        168, 234, 454, 10, 172, 397]

    # Corresponding 3D model points (standard face, in mm)
    FACE_3D_MODEL = np.array([
        [   0.0,    0.0,    0.0],   # 1   nose tip
        [   0.0, -330.0,  -65.0],   # 152 chin
        [-225.0,  170.0, -135.0],   # 33  left eye outer
        [ 225.0,  170.0, -135.0],   # 263 right eye outer
        [ -75.0,  170.0, -125.0],   # 133 left eye inner
        [  75.0,  170.0, -125.0],   # 362 right eye inner
        [-150.0, -150.0, -125.0],   # 61  left mouth corner
        [ 150.0, -150.0, -125.0],   # 291 right mouth corner
        [   0.0,  115.0,  -50.0],   # 168 nose bridge
        [-255.0,   35.0, -230.0],   # 234 left cheek
        [ 255.0,   35.0, -230.0],   # 454 right cheek
        [   0.0,  260.0, -100.0],   # 10  forehead center
        [-190.0, -230.0, -190.0],   # 172 left jaw
        [ 190.0, -230.0, -190.0],   # 397 right jaw
    ], dtype=np.float64)

    # One-Euro filter params (replaces the flat EMA). Smoothing adapts to
    # speed: heavy when still (kills jitter), light when actually moving.
    FILTER_MIN_CUTOFF = 1.0     # lower = more smoothing when still
    FILTER_BETA       = 0.007   # higher = more responsive to fast movement
    FILTER_D_CUTOFF   = 1.0

    # --- Direction-aware dropout ---
    # When MediaPipe loses the face we cannot see WHY it was lost. Treating
    # every dropout as suspicious caused false HIGH flags for simply looking
    # UP (tilting back hides the eyes/brow and breaks the face mesh just as
    # readily as looking down does).
    #
    # Instead, the last valid pose before tracking was lost decides whether
    # the dropout counts: if the examinee was already trending downward or
    # sideways, the loss is treated as a continuation of that movement. If
    # they were facing forward or tilting up, it is not counted.
    #
    # Expressed as a fraction of the normal thresholds, so a pose only part
    # of the way toward "suspicious" still establishes direction.
    DROPOUT_CONTEXT_FRACTION = 0.5   # 50% of YAW_/PITCH_THRESHOLD

class TemporalConfig:
    """
    Sliding window temporal analysis settings.

    Time-based rather than frame-count-based, so behavior is consistent
    regardless of actual FPS achieved on a given machine (CPU vs GPU,
    detection frame-skip settings, etc). Internally the window still
    stores discrete frame entries, but the analyzer prunes by elapsed
    time instead of a fixed frame count.
    """

    # Tightened from 5.0s after testing showed HIGH risk escalation was too
    # slow — by the time the flag fired, the examinee had already returned
    # to normal behavior, causing evidence screenshots to miss the moment.
    WINDOW_SECONDS = 3.5

    MODERATE_TRIGGER_RATIO = 0.35     # 30% of window = ~1.05 seconds of a single signal

    HIGH_TRIGGER_RATIO     = 0.50    # 40% of window = ~1.4 seconds of both signals
                                      # co-occurring. Lowered further for responsiveness.

    # --- Per-axis sustained-behavior thresholds ---
    # Each pose axis is tracked on its own sliding-window ratio rather than
    # being collapsed into one blended "head suspicious" signal, because the
    # axes have very different noise floors in practice. Measured on this
    # setup: a deliberate, sustained downward look reads only ~+20 degrees
    # of normalized pitch, while merely shifting in one's seat can swing
    # normalized yaw by 34-40 degrees. Forcing both through a single ratio
    # meant the threshold was necessarily wrong for at least one of them.
    #
    # Pitch is therefore the most sensitive (quiet, reliable signal) and yaw
    # /roll are stricter (noisy signals that need more sustained evidence
    # before they mean anything).
    PITCH_HIGH_RATIO       = 0.60    # ~2.1s of sustained downward tilt
    YAW_HIGH_RATIO         = 0.75    # ~2.6s — stricter, yaw is the noisy axis
    ROLL_HIGH_RATIO        = 0.75    # ~2.6s — same reasoning as yaw

    PITCH_MODERATE_RATIO   = 0.35
    YAW_MODERATE_RATIO     = 0.50
    ROLL_MODERATE_RATIO    = 0.50

    # --- Lost-face-tracking (dropout) thresholds ---
    # Dropout is tracked as its own signal rather than being folded into the
    # pose axes. It is deliberately the STRICTEST threshold: losing the face
    # is weak, ambiguous evidence on its own (the system cannot tell a
    # phone-in-lap glance from someone leaning back to stretch), so it needs
    # to persist far longer than a real pose deviation before it escalates.
    DROPOUT_HIGH_RATIO     = 0.85    # ~3.0s of near-continuous lost tracking
    DROPOUT_MODERATE_RATIO = 0.65

    # Buffer margin added on top of WINDOW_SECONDS when sizing the FrameBuffer
    # (monitoring/frame_buffer.py), so evidence capture can always look back
    # far enough to find the frame where sustained behavior actually began.
    EVIDENCE_LOOKBACK_MARGIN_SECONDS = 1.5

    # Safety cap on stored entries so memory doesn't grow unbounded if
    # FPS spikes very high — effectively irrelevant in practice.
    MAX_WINDOW_ENTRIES = 600

    # A new risk level must hold steady for this long before it's treated
    # as a genuine transition (evidence capture + report logging), rather
    # than reacting to every frame-to-frame change. Filters out boundary
    # flicker — e.g. brief MODERATE blips from resting jitter right at a
    # ratio threshold — so the session report reflects real incidents
    # instead of noise.
    LEVEL_LOG_HOLD_SECONDS = 0.75


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

class DatabaseConfig:
    """Firebase (Firestore) persistence settings."""

    # Service account key downloaded from Firebase Console -> Project
    # Settings -> Service Accounts -> Generate new private key. Never
    # commit this file — see .gitignore.
    FIREBASE_CREDENTIALS_PATH = "connection/firebase_credentials.json"
    FIRESTORE_COLLECTION      = "sessions"

    ENABLE_DB      = True    # False = JSON-only, unchanged legacy behavior
    KEEP_JSON      = True    # Keep writing session_report.json as a backup