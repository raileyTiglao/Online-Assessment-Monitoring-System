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
    call load_custom_weights() to swap in your fine-tuned model.
 
    Usage:
        detector = ObjectDetector()
        detected, boxes, scores, labels = detector.detect(frame)
    """
 
    def __init__(self):
        self.device = self._setup_device()
        self.model  = self._load_model()
        self.config = DetectionConfig()
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
 
    def _load_custom_model(self, model_path: str):
        """
        Load your fine-tuned Faster R-CNN weights.
 
        Call this after training on your custom webcam dataset.
        The model expects DetectionConfig.CUSTOM_NUM_CLASSES output classes.
 
        Args:
            model_path: Path to the saved .pth checkpoint file.
        """
        print(f"[ObjectDetector] Loading custom model from: {model_path}")
        num_classes = DetectionConfig.CUSTOM_NUM_CLASSES
 
        # Build model with custom number of classes (no pretrained weights)
        model = fasterrcnn_resnet50_fpn(weights=None, num_classes=num_classes)
 
        # Load saved checkpoint
        checkpoint = torch.load(model_path, map_location=self.device)
 
        # Support both raw state_dict and wrapped checkpoint formats
        if "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
 
        model.to(self.device)
        model.eval()
        print(f"[ObjectDetector] Custom model loaded ({num_classes} classes).")
        return model
 
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
 
    def detect(self, frame: np.ndarray) -> tuple:
        """
        Run object detection on a single BGR frame.
 
        Args:
            frame: OpenCV BGR image (H x W x 3 numpy array)
 
        Returns:
            detected (bool):       True if at least one target device found
            boxes    (list[list]): Bounding boxes [[x1,y1,x2,y2], ...]
            scores   (list[float]):Confidence scores for each box
            labels   (list[str]):  Human-readable label for each box
        """
        tensor = self._preprocess(frame)
 
        with torch.no_grad():
            predictions = self.model(tensor)
 
        return self._postprocess(predictions[0])
 
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
 
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
        scores_tensor = prediction["scores"].cpu().numpy()
        boxes_tensor  = prediction["boxes"].cpu().numpy()
 
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