"""
=============================================================================
detection/head_pose.py — MediaPipe Head Pose Estimator
Online Assessment Monitoring System
Holy Angel University — School of Computing

Uses MediaPipe Face Mesh to extract 468 3D facial landmarks, then solves
the Perspective-n-Point (PnP) problem to compute raw Euler angles:
  - Yaw:   horizontal left/right rotation
  - Pitch: vertical up/down tilt
  - Roll:  lateral head tilt

Also computes a "scale" value — the pixel distance between the two eye
corners — as a proxy for the examinee's distance from the camera. This
is used downstream (HeadPoseNormalizer) to detect when the examinee has
moved significantly closer/farther since calibration, which invalidates
the calibrated baseline (monocular pose estimation error is distance
dependent).

This class is intentionally limited to RAW signal extraction only — it
has no knowledge of calibration baselines or suspicion thresholds. That
logic lives in analysis/head_pose_normalizer.py.
=============================================================================
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from config import HeadPoseConfig, GazeConfig


@dataclass
class HeadPoseResult:
    """
    Raw (camera-relative) head pose output for a single frame.

    Attributes:
        success:       False if no face was detected in the frame
        yaw:           Horizontal rotation in degrees (+ = right, - = left)
        pitch:         Vertical rotation in degrees (- = looking down)
        roll:          Lateral tilt in degrees
        scale:         Pixel distance between the two eye corners — a proxy
                       for distance-to-camera, used for drift detection
        gaze_x:        Iris offset from eye centre, horizontal, as a
                       fraction of eye width (+ = toward the examinee's
                       right in image space, - = left). 0.0 = centred.
        gaze_y:        Same, vertical (+ = downward, - = upward)
        gaze_valid:    False when the eyes were too closed (blink/squint)
                       for the iris position to be trusted — callers should
                       ignore gaze_x/gaze_y on those frames rather than
                       treating them as a centred gaze
    """
    success:    bool
    yaw:        float = 0.0
    pitch:      float = 0.0
    roll:       float = 0.0
    scale:      float = 0.0
    gaze_x:     float = 0.0
    gaze_y:     float = 0.0
    gaze_valid: bool  = False


class HeadPoseEstimator:
    """
    Estimates raw head orientation (yaw, pitch, roll) and a face-scale
    reference from a webcam frame using MediaPipe Face Mesh and OpenCV's
    solvePnP.

    Note: This returns CAMERA-RELATIVE angles only. To get baseline-relative
    (normalized) angles suitable for suspicion checks, pass the result
    through analysis.head_pose_normalizer.HeadPoseNormalizer.

    Usage:
        estimator = HeadPoseEstimator()
        result = estimator.estimate(frame)
        print(result.yaw, result.pitch, result.roll, result.scale)
        estimator.close()   # Call when done to release resources
    """

    def __init__(self):
        self._face_mesh = self._init_face_mesh()
        self._3d_model  = HeadPoseConfig.FACE_3D_MODEL
        self._indices   = HeadPoseConfig.LANDMARK_INDICES
        print("[HeadPoseEstimator] Ready.")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _init_face_mesh(self):
        """Initialise MediaPipe Face Mesh solution."""
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=HeadPoseConfig.MAX_NUM_FACES,
            refine_landmarks=HeadPoseConfig.REFINE_LANDMARKS,
            min_detection_confidence=HeadPoseConfig.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=HeadPoseConfig.MIN_TRACKING_CONFIDENCE,
        )
        return face_mesh

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def estimate(self, frame: np.ndarray) -> HeadPoseResult:
        """
        Run raw head pose estimation on a single BGR frame.

        Args:
            frame: OpenCV BGR image (H x W x 3)

        Returns:
            HeadPoseResult with raw camera-relative yaw/pitch/roll and scale
        """
        h, w = frame.shape[:2]

        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return HeadPoseResult(success=False)

        face_landmarks = results.multi_face_landmarks[0]

        image_points  = self._extract_image_points(face_landmarks, w, h)
        camera_matrix = self._build_camera_matrix(w, h)
        yaw, pitch, roll = self._solve_pose(image_points, camera_matrix)
        scale = self._compute_scale(image_points)
        gaze_x, gaze_y, gaze_valid = self._compute_gaze(face_landmarks, w, h)

        return HeadPoseResult(
            success=True,
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            scale=round(scale, 2),
            gaze_x=round(gaze_x, 4),
            gaze_y=round(gaze_y, 4),
            gaze_valid=gaze_valid,
        )

    def close(self):
        """Release MediaPipe resources. Call this when the session ends."""
        self._face_mesh.close()
        print("[HeadPoseEstimator] Resources released.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_gaze(self, face_landmarks, w: int, h: int) -> tuple:
        """
        Estimate where the eyes are pointing, independently of head pose.

        For each eye the iris centre is measured against the midpoint of the
        eye's two corners, then divided by the eye's width. Using eye width
        as the unit makes the result scale-free: the same glance yields the
        same number whether the examinee sits near or far, and regardless of
        their eye size. Both eyes are averaged when available.

        Eyes that are too closed (blink, squint, or a heavy downward glance
        that drops the lid) have their iris partly occluded, so its centre
        drifts unpredictably. Those eyes are skipped, and if neither eye is
        usable the frame is reported as gaze_valid=False rather than
        silently returning a centred reading.

        Returns:
            (gaze_x, gaze_y, gaze_valid) — offsets in eye-width units,
            positive x toward image-right, positive y downward
        """
        landmarks = face_landmarks.landmark

        # Guard against a mesh without iris points (REFINE_LANDMARKS off).
        if len(landmarks) <= max(GazeConfig.IRIS_CENTER_INDICES):
            return 0.0, 0.0, False

        def point(idx):
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h], dtype=np.float64)

        iris_points = [point(i) for i in GazeConfig.IRIS_CENTER_INDICES]

        offsets = []
        for outer_i, inner_i, upper_i, lower_i in (GazeConfig.LEFT_EYE_LANDMARKS,
                                                   GazeConfig.RIGHT_EYE_LANDMARKS):
            outer, inner = point(outer_i), point(inner_i)
            upper, lower = point(upper_i), point(lower_i)

            eye_width = float(np.linalg.norm(outer - inner))
            if eye_width <= 1e-6:
                continue

            # Skip this eye if the lid is too closed to trust the iris.
            openness = float(np.linalg.norm(upper - lower)) / eye_width
            if openness < GazeConfig.MIN_EYE_OPENNESS:
                continue

            eye_center = (outer + inner) / 2.0

            # Pair each eye with its nearest iris landmark, rather than
            # assuming a fixed index order — avoids silently mixing up the
            # two eyes if MediaPipe's ordering ever differs.
            iris = min(iris_points,
                       key=lambda p: float(np.linalg.norm(p - eye_center)))

            offsets.append((iris - eye_center) / eye_width)

        if not offsets:
            return 0.0, 0.0, False

        mean_offset = np.mean(offsets, axis=0)
        return float(mean_offset[0]), float(mean_offset[1]), True

    def _extract_image_points(self, face_landmarks, w: int, h: int) -> np.ndarray:
        """Extract the 6 key landmark positions as 2D pixel coordinates."""
        points = []
        for idx in self._indices:
            lm = face_landmarks.landmark[idx]
            points.append([lm.x * w, lm.y * h])
        return np.array(points, dtype=np.float64)

    def _compute_scale(self, image_points: np.ndarray) -> float:
        """
        Compute the pixel distance between the two eye corners (indices
        2 and 3 in image_points, corresponding to LANDMARK_INDICES[2]=33
        and LANDMARK_INDICES[3]=263). Used as a proxy for distance-to-camera:
        a larger value means the face appears bigger (closer to camera).
        """
        left_eye  = image_points[2]
        right_eye = image_points[3]
        return float(np.linalg.norm(left_eye - right_eye))

    def _build_camera_matrix(self, w: int, h: int) -> np.ndarray:
        """Approximate camera intrinsic matrix from frame dimensions."""
        focal_length = float(w)
        cx, cy = w / 2.0, h / 2.0
        return np.array([
            [focal_length, 0,  cx],
            [0, focal_length,  cy],
            [0,            0,  1.0],
        ], dtype=np.float64)

    def _solve_pose(self, image_points: np.ndarray,
                    camera_matrix: np.ndarray) -> tuple:
        """Solve the PnP problem to obtain raw Euler angles."""
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rotation_vec, translation_vec = cv2.solvePnP(
            self._3d_model,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_SQPNP,   # more stable than ITERATIVE with many points
        )

        if not success:
            return 0.0, 0.0, 0.0

        rotation_mat, _ = cv2.Rodrigues(rotation_vec)
        proj_matrix = np.hstack((rotation_mat, translation_vec))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)

        # euler_angles comes back as a (3,1) column vector — flatten before indexing
        euler_angles = euler_angles.flatten()

        pitch = float(euler_angles[0])
        yaw   = float(euler_angles[1])
        roll  = float(euler_angles[2])

        return yaw, pitch, roll