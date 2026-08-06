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

    # --- Positioning guide (silhouette) ---
    # A body-shaped outline the examinee aligns themselves to during
    # calibration. Its purpose is measurement consistency, not decoration:
    # the baseline is only meaningful relative to a known seating position,
    # and SCALE_DRIFT_TOLERANCE compares later face size against whatever
    # size was captured here — so if someone calibrates leaning in and then
    # sits back, they read as "drifted" for the whole session.
    #
    # Only the HEAD portion is machine-checkable (MediaPipe tracks the face,
    # not the body). The shoulders are guidance for the human eye.
    GUIDE_HEAD_CENTER    = (0.50, 0.42)   # normalized frame coords (x, y)
    GUIDE_HEAD_TOLERANCE = 0.13           # max normalized distance from centre

    # Acceptable face size, as inter-eye distance / frame width. Expressed
    # as a fraction rather than pixels so it holds at any camera resolution.
    GUIDE_SCALE_MIN = 0.075
    GUIDE_SCALE_MAX = 0.160

    # When True, samples taken while out of position are discarded rather
    # than merely warned about. Safe to leave on: calibration is time-based,
    # so it always finishes — an out-of-position examinee simply collects
    # too few samples and gets the MIN_SAMPLES warning instead of silently
    # producing a baseline built from a bad position.
    ENFORCE_POSITION_GUIDE = True

    # --- Orientation validation ---
    # Guards against baking a bad pose into the baseline: someone can sit
    # perfectly inside the guide with their head turned or tilted, and that
    # would silently become their definition of "normal", throwing off every
    # later measurement.
    #
    # Only yaw and roll are gated. Both sit near zero when facing the camera
    # squarely (confirmed on this setup: baseline yaw -7.2, roll +3.7).
    # Pitch is deliberately NOT gated — its resting value is dominated by
    # camera height and the 3D model's convention (around -160 here, not 0),
    # so an absolute pitch limit would wrongly reject people whose webcam
    # sits low or high. Pitch is still checked for stability below.
    ORIENTATION_YAW_TOLERANCE  = 16.0   # degrees from camera-facing
    ORIENTATION_ROLL_TOLERANCE = 13.0

    # --- Stability validation ---
    # A baseline is the median of the calibration samples; if the examinee
    # was moving throughout, that median represents no actual pose. Spread
    # above this (std dev, degrees) triggers a warning to recalibrate.
    # This same spread is what a future per-person threshold scheme would
    # use as the examinee's own jitter measurement.
    STABILITY_WARN_DEGREES = 7.0


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

class GazeConfig:
    """
    Iris-based gaze estimation settings.

    MediaPipe Face Mesh already returns iris landmarks whenever
    HeadPoseConfig.REFINE_LANDMARKS is True (478 landmarks instead of 468),
    so the eye data costs no extra inference — it was simply being discarded
    before. Gaze closes the biggest blind spot in head-pose-only monitoring:
    an examinee glancing down at a device while keeping their head level
    produces almost no pose change, but a large iris shift.

    Gaze is measured as the iris centre's offset from the eye centre,
    expressed as a FRACTION OF EYE WIDTH so it stays comparable regardless
    of how close the examinee sits or how large their eyes are. Like head
    pose, it is then normalized against the calibration baseline, so what
    matters is deviation from where they naturally looked while calibrating
    — no separate "look at each screen corner" step is required.
    """

    # MediaPipe iris landmark indices (only present when REFINE_LANDMARKS).
    IRIS_CENTER_INDICES = (468, 473)

    # Eye corner + eyelid landmarks, per eye: (outer, inner, upper, lower)
    LEFT_EYE_LANDMARKS  = (33, 133, 159, 145)
    RIGHT_EYE_LANDMARKS = (263, 362, 386, 374)

    # Eye openness below this fraction of eye width counts as a blink or
    # squint, where the iris is partly occluded and its position is
    # unreliable. Such frames are excluded rather than guessed at.
    MIN_EYE_OPENNESS = 0.12

    # --- Suspicion threshold ---
    # Deviation (in eye-widths) from the calibrated neutral gaze before a
    # frame counts as looking away. Horizontal and vertical are separate
    # because the eye's usable vertical range is much smaller than its
    # horizontal one — the eyelids cut it off.
    #
    # Tuned from real footage on this camera (7 frames: 4 looking normally
    # at the screen, 3 looking away). The two axes turned out to be very
    # unequal, so they are set on quite different logic:
    #
    #   VERTICAL is the strong signal. Normal screen use spanned only
    #   +/-0.015, while every look-away frame read +0.030 to +0.091 — all
    #   downward. Nothing about reading a screen requires looking down the
    #   way a phone in the lap does, so the separation is clean. 0.035
    #   leaves better than 2x margin over observed normal movement.
    #
    #   HORIZONTAL is weak and deliberately conservative. Normal scanning
    #   across a wide monitor reached 0.086 — overlapping one of the
    #   look-away frames (0.082) — so a sensitive threshold here would fire
    #   during ordinary reading. 0.15 clears the normal range entirely and
    #   acts only as a backstop for pronounced sideways gaze.
    #
    # Based on a small sample (4 neutral / 3 away); revisit with more data.
    GAZE_H_THRESHOLD = 0.15    # horizontal, fraction of eye width
    GAZE_V_THRESHOLD = 0.035   # vertical, the discriminating axis

    # Master switch for whether gaze contributes to RISK CLASSIFICATION.
    # When False, gaze is still computed, displayed on the overlay, and
    # recorded — it simply cannot escalate a risk level. Set False to
    # disable gaze flagging without touching any other code.
    ENABLE_GAZE_FLAGGING = True


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

    # --- Gaze (iris) thresholds ---
    # Deliberately strict to start with: gaze is the newest and least-tuned
    # signal, and eyes flick around constantly during normal reading, so it
    # needs to be sustained well before it means anything. Only applies when
    # GazeConfig.ENABLE_GAZE_FLAGGING is True.
    GAZE_HIGH_RATIO        = 0.70
    GAZE_MODERATE_RATIO    = 0.50

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

    # Which backend main.py talks to for exam lookup, screenshot upload,
    # and session persistence:
    #   "local"    = PHP/MySQL via XAMPP (php_backend/) — no cloud
    #                account, no billing. See LocalBackendConfig below.
    #   "firebase" = Firestore + Firebase Storage — needs a Firebase
    #                project on the Blaze plan for Storage specifically.
    BACKEND = "local"

    # Service account key downloaded from Firebase Console -> Project
    # Settings -> Service Accounts -> Generate new private key. Never
    # commit this file — see .gitignore. Unused when BACKEND = "local".
    FIREBASE_CREDENTIALS_PATH = "connection/firebase_credentials.json"
    FIRESTORE_COLLECTION      = "sessions"
    FIRESTORE_EXAMS_COLLECTION = "exams"
    FIRESTORE_USERS_COLLECTION = "users"

    ENABLE_DB      = True    # False = JSON-only, unchanged legacy behavior
    KEEP_JSON      = True    # Keep writing session_report.json as a backup

    # --- Evidence screenshot upload (Firebase Storage) ---
    # Explicit, not inferred: firebase_admin.initialize_app() is called
    # with no "storageBucket" option (see connection/firebase_db.py), and
    # newer Firebase projects default to a "<project>.firebasestorage.app"
    # bucket rather than the older "<project>.appspot.com" convention the
    # Admin SDK guesses — inference isn't reliable, so name it directly.
    STORAGE_BUCKET = "baandod-testing.firebasestorage.app"
    EVIDENCE_STORAGE_PREFIX = "evidence"

    # --- Exam code (links a session to the professor who owns it) ---
    # False = a missing/invalid exam code doesn't block monitoring; the
    # session proceeds "unassigned" (visible only to Admin in the dashboard)
    # rather than stopping an examinee from taking the exam over a forgotten
    # or mistyped code.
    REQUIRE_EXAM_CODE = False


class LocalBackendConfig:
    """
    Settings for the local PHP/MySQL backend (php_backend/, served by
    XAMPP). Only used when DatabaseConfig.BACKEND = "local".
    """

    # Base URL of the deployed php_backend/ app — see php_backend's own
    # README comments for how to get it running under XAMPP's Apache.
    BASE_URL = "http://localhost/oams"

    # Must match php_backend/config.php's API_KEY exactly — change both
    # together. Ships as a placeholder in both places; not a real secret
    # until you change it.
    API_KEY = "change-me-to-a-random-string"
