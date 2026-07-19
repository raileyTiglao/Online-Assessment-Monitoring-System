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
from config import HeadPoseConfig


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
    """
    success: bool
    yaw:     float = 0.0
    pitch:   float = 0.0
    roll:    float = 0.0
    scale:   float = 0.0


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

        return HeadPoseResult(
            success=True,
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            scale=round(scale, 2),
        )

    def close(self):
        """Release MediaPipe resources. Call this when the session ends."""
        self._face_mesh.close()
        print("[HeadPoseEstimator] Resources released.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
            flags=cv2.SOLVEPNP_ITERATIVE,
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