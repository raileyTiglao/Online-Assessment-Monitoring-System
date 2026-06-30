"""detection package — object detection and head pose estimation modules."""

from .object_detector import ObjectDetector
from .head_pose import HeadPoseEstimator, HeadPoseResult

__all__ = ["ObjectDetector", "HeadPoseEstimator", "HeadPoseResult"]
