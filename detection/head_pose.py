"""
=============================================================================
detection/head_pose.py — MediaPipe Head Pose Estimator
Online Assessment Monitoring System
Holy Angel University — School of Computing

Uses MediaPipe Face Mesh to extract 468 3D facial landmarks, then solves
the Perspective-n-Point (PnP) problem to compute Euler angles:
  - Yaw:   horizontal left/right rotation
  - Pitch: vertical up/down tilt
  - Roll:  lateral head tilt

These angles are then checked against thresholds to flag suspicious
head orientations (e.g. looking down at a phone, turning away).
=============================================================================
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional
from config import HeadPoseConfig


@dataclass
class HeadPoseResult:
    """
    Data container for a single frame's head pose output.

    Attributes:
        success:       False if no face was detected in the frame
        yaw:           Horizontal rotation in degrees (+ = right, - = left)
        pitch:         Vertical rotation in degrees (- = looking down)
        roll:          Lateral tilt in degrees
        suspicious:    True if any angle exceeds its threshold
        reason:        Human-readable description of what triggered suspicion
        landmarks_2d:  List of (x, y) pixel coords for all 468 landmarks
    """
    success:      bool
    yaw:          float = 0.0
    pitch:        float = 0.0
    roll:         float = 0.0
    suspicious:   bool  = False
    reason:       str   = "No face detected"
    landmarks_2d: list  = None

    def __post_init__(self):
        if self.landmarks_2d is None:
            self.landmarks_2d = []


class HeadPoseEstimator:
    """
    Estimates head orientation (yaw, pitch, roll) from a webcam frame
    using MediaPipe Face Mesh and OpenCV's solvePnP.

    Usage:
        estimator = HeadPoseEstimator()
        result = estimator.estimate(frame)
        print(result.yaw, result.pitch, result.suspicious)
        estimator.close()   # Call when done to release resources
    """

    def __init__(self):
        self._cfg       = HeadPoseConfig()
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
        Run head pose estimation on a single BGR frame.

        Args:
            frame: OpenCV BGR image (H x W x 3)

        Returns:
            HeadPoseResult dataclass with all pose values and flags
        """
        h, w = frame.shape[:2]

        # MediaPipe requires RGB input
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return HeadPoseResult(success=False)

        face_landmarks = results.multi_face_landmarks[0]

        # Extract the 6 key 2D landmark coordinates (pixels)
        image_points = self._extract_image_points(face_landmarks, w, h)

        # Build camera matrix from frame dimensions
        camera_matrix = self._build_camera_matrix(w, h)

        # Solve PnP to get head rotation
        yaw, pitch, roll = self._solve_pose(image_points, camera_matrix)

        # Extract all 468 landmark coords for optional drawing
        landmarks_2d = [
            (int(lm.x * w), int(lm.y * h))
            for lm in face_landmarks.landmark
        ]

        # Analyse angles against thresholds
        suspicious, reason = self._analyse_angles(yaw, pitch, roll)

        return HeadPoseResult(
            success=True,
            yaw=round(yaw, 2),
            pitch=round(pitch, 2),
            roll=round(roll, 2),
            suspicious=suspicious,
            reason=reason,
            landmarks_2d=landmarks_2d,
        )

    def close(self):
        """Release MediaPipe resources. Call this when the session ends."""
        self._face_mesh.close()
        print("[HeadPoseEstimator] Resources released.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_image_points(self, face_landmarks, w: int, h: int) -> np.ndarray:
        """
        Extract the 6 key landmark positions as 2D pixel coordinates.

        These 6 points correspond to the 6 points in FACE_3D_MODEL and
        are used together by solvePnP to compute the head rotation.
        """
        points = []
        for idx in self._indices:
            lm = face_landmarks.landmark[idx]
            points.append([lm.x * w, lm.y * h])
        return np.array(points, dtype=np.float64)

    def _build_camera_matrix(self, w: int, h: int) -> np.ndarray:
        """
        Approximate camera intrinsic matrix.
        Uses frame width as focal length — standard approximation for
        unknown camera parameters.
        """
        focal_length = float(w)
        cx, cy = w / 2.0, h / 2.0
        return np.array([
            [focal_length, 0,  cx],
            [0, focal_length,  cy],
            [0,            0,  1.0],
        ], dtype=np.float64)

    def _solve_pose(self, image_points: np.ndarray,
                    camera_matrix: np.ndarray) -> tuple:
        """
        Solve the PnP problem to obtain Euler angles.

        Returns:
            (yaw, pitch, roll) in degrees
        """
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)  # No lens distortion

        success, rotation_vec, translation_vec = cv2.solvePnP(
            self._3d_model,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return 0.0, 0.0, 0.0

        # Convert rotation vector → rotation matrix
        rotation_mat, _ = cv2.Rodrigues(rotation_vec)

        # Decompose projection matrix to extract Euler angles
        proj_matrix = np.hstack((rotation_mat, translation_vec))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)

        # euler_angles comes back as a (3,1) column vector — flatten before indexing
        euler_angles = euler_angles.flatten()

        pitch = float(euler_angles[0])
        yaw   = float(euler_angles[1])
        roll  = float(euler_angles[2])

        return yaw, pitch, roll

    def _analyse_angles(self, yaw: float, pitch: float,
                         roll: float) -> tuple:
        """
        Compare Euler angles against configured thresholds.

        Returns:
            suspicious (bool)
            reason (str): Description of what exceeded the threshold
        """
        reasons = []

        if abs(yaw) > HeadPoseConfig.YAW_THRESHOLD:
            direction = "left" if yaw < 0 else "right"
            reasons.append(f"Head turned {direction} ({yaw:+.1f}°)")

        if pitch < -HeadPoseConfig.PITCH_THRESHOLD:
            reasons.append(f"Looking down ({pitch:+.1f}°)")

        if abs(roll) > HeadPoseConfig.ROLL_THRESHOLD:
            reasons.append(f"Head tilted ({roll:+.1f}°)")

        if reasons:
            return True, " | ".join(reasons)
        return False, "Normal"