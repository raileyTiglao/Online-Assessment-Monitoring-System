"""
=============================================================================
detection/object_detector.py — Faster R-CNN Object Detector
Online Assessment Monitoring System
Holy Angel University — School of Computing

Wraps the Faster R-CNN model into a clean class with a single
detect() method that accepts a frame and returns detection results.

Includes performance optimizations to address low-FPS inference:
  - Optional input resizing before inference (smaller tensor = faster)
  - Optional mixed-precision (FP16) inference on GPU via autocast
Boxes are scaled back to the original frame's coordinate space so
callers (overlay rendering, evidence capture) don't need to know
resizing happened at all.
=============================================================================
"""

import torch
import torchvision
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
    FasterRCNN_ResNet50_FPN_Weights
)
import cv2
import numpy as np
from config import DetectionConfig, SystemConfig


class ObjectDetector:
    """
    Faster R-CNN based mobile device detector.

    By default loads COCO pre-trained weights, which already includes
    a 'cell phone' class (ID 77). Once your custom dataset is trained,
    set DetectionConfig.CUSTOM_MODEL_PATH to swap in your fine-tuned model.

    Usage:
        detector = ObjectDetector()
        detected, boxes, scores, labels = detector.detect(frame)
    """

    def __init__(self):
        self.device = self._setup_device()
        self.model  = self._load_model()
        self.config = DetectionConfig()
        self._use_amp = DetectionConfig.USE_AMP and self.device.type == "cuda"
        if self._use_amp:
            print("[ObjectDetector] Mixed-precision (FP16) inference enabled.")
        print("[ObjectDetector] Ready.")

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_device(self):
        """Select GPU if available and enabled, otherwise CPU."""
        if SystemConfig.USE_GPU and torch.cuda.is_available():
            device = torch.device("cuda")
            print(f"[ObjectDetector] Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device("cpu")
            print("[ObjectDetector] Using CPU.")
        return device

    def _load_model(self):
        """
        Load Faster R-CNN.

        Checks DetectionConfig.CUSTOM_MODEL_PATH first.
        Falls back to COCO pre-trained weights if no custom path is set.
        """
        if DetectionConfig.CUSTOM_MODEL_PATH:
            return self._load_custom_model(DetectionConfig.CUSTOM_MODEL_PATH)
        else:
            return self._load_coco_model()

    def _load_coco_model(self):
        """Load Faster R-CNN with default COCO pre-trained weights."""
        print("[ObjectDetector] Loading COCO pre-trained Faster R-CNN...")
        weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
        model   = fasterrcnn_resnet50_fpn(weights=weights)
        model.to(self.device)
        model.eval()
        print("[ObjectDetector] COCO model loaded.")
        return model

    
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame: np.ndarray) -> tuple:
        """
        Run object detection on a single BGR frame.

        If DetectionConfig.DETECTION_INPUT_WIDTH is set, the frame is
        downscaled before inference for speed, and resulting boxes are
        scaled back up to match the original frame's dimensions.

        Args:
            frame: OpenCV BGR image (H x W x 3 numpy array)

        Returns:
            detected (bool):       True if at least one target device found
            boxes    (list[list]): Bounding boxes [[x1,y1,x2,y2], ...] in
                                    the ORIGINAL frame's coordinate space
            scores   (list[float]):Confidence scores for each box
            labels   (list[str]):  Human-readable label for each box
        """
        original_h, original_w = frame.shape[:2]
        inference_frame, scale = self._resize_for_inference(frame)

        tensor = self._preprocess(inference_frame)

        with torch.no_grad():
            if self._use_amp:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    predictions = self.model(tensor)
            else:
                predictions = self.model(tensor)

        detected, boxes, scores, labels = self._postprocess(predictions[0])

        if scale != 1.0:
            boxes = [self._scale_box(box, scale) for box in boxes]

        return detected, boxes, scores, labels

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resize_for_inference(self, frame: np.ndarray) -> tuple:
        """
        Downscale the frame to DetectionConfig.DETECTION_INPUT_WIDTH if set.
        Smaller input significantly speeds up Faster R-CNN, which is a
        heavy two-stage detector.

        Returns:
            resized_frame, scale_factor (to map boxes back to original size)
        """
        target_width = DetectionConfig.DETECTION_INPUT_WIDTH
        if target_width is None:
            return frame, 1.0

        h, w = frame.shape[:2]
        if w <= target_width:
            return frame, 1.0

        scale = target_width / float(w)
        new_h = int(h * scale)
        resized = cv2.resize(frame, (target_width, new_h), interpolation=cv2.INTER_LINEAR)

        # Scale factor to map detection boxes back to original coordinates
        inverse_scale = w / float(target_width)
        return resized, inverse_scale

    def _scale_box(self, box: list, scale: float) -> list:
        """Scale a [x1, y1, x2, y2] box by the given factor."""
        return [int(coord * scale) for coord in box]

    def _preprocess(self, frame: np.ndarray) -> list:
        """Convert OpenCV BGR frame to a normalised RGB tensor."""
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
        return [tensor.to(self.device)]

    def _postprocess(self, prediction: dict) -> tuple:
        """
        Filter predictions to only include target classes above threshold.

        Args:
            prediction: Raw model output dict with keys:
                        'boxes', 'labels', 'scores'

        Returns:
            detected, boxes, scores, label_names
        """
        labels_tensor = prediction["labels"].cpu().numpy()
        scores_tensor = prediction["scores"].cpu().float().numpy()
        boxes_tensor  = prediction["boxes"].cpu().float().numpy()

        target_ids = DetectionConfig.TARGET_CLASS_IDS
        threshold  = DetectionConfig.CONFIDENCE_THRESHOLD
        name_map   = DetectionConfig.TARGET_CLASS_NAMES

        boxes       = []
        scores      = []
        label_names = []

        for label, score, box in zip(labels_tensor, scores_tensor, boxes_tensor):
            if int(label) in target_ids and score >= threshold:
                boxes.append(box.astype(int).tolist())
                scores.append(float(score))
                label_names.append(name_map.get(int(label), "Device"))

        detected = len(boxes) > 0
        return detected, boxes, scores, label_names