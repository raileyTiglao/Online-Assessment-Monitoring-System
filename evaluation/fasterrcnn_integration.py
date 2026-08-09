"""
=============================================================================
fasterrcnn_integration.py — Integrate Custom Faster R-CNN into Monitoring
Mobile Device Detection
Holy Angel University — School of Computing

Shows how to use your trained Faster R-CNN model in the monitoring system.
=============================================================================
"""

import torch
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import cv2
import numpy as np
from pathlib import Path


class CustomMobileDeviceDetector:
    """
    Load and use your fine-tuned Faster R-CNN model for mobile device detection.

    Usage:
        detector = CustomMobileDeviceDetector('trained_model/best_model.pth')
        detected, boxes, scores = detector.detect(frame)
    """

    def __init__(self, model_path: str, confidence_threshold: float = 0.5, gpu: int = 0):
        """
        Args:
            model_path: Path to trained model checkpoint (.pth file)
            confidence_threshold: Minimum confidence to accept detection
            gpu: GPU device index (0 for cuda:0, or -1 for CPU)
        """
        self.confidence_threshold = confidence_threshold

        # Setup device
        if gpu >= 0 and torch.cuda.is_available():
            self.device = torch.device(f'cuda:{gpu}')
            print(f"[Detector] Using GPU: {torch.cuda.get_device_name(gpu)}")
        else:
            self.device = torch.device('cpu')
            print("[Detector] Using CPU")

        # Load model
        self.model = self._load_model(model_path)
        self.model.to(self.device)
        self.model.eval()

        print(f"[Detector] Model loaded from: {model_path}")
        print(f"[Detector] Ready for inference")

    def _load_model(self, model_path: str):
        """Load trained Faster R-CNN model."""
        # Create model with custom number of classes
        model = fasterrcnn_resnet50_fpn(pretrained=False)  # Don't load COCO weights
        in_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)  # 2 classes

        # Load trained weights
        checkpoint = torch.load(model_path, map_location=self.device)
        model.load_state_dict(checkpoint)

        return model

    def detect(self, frame: np.ndarray) -> tuple:
        """
        Detect mobile devices in frame.

        Args:
            frame: BGR image (H x W x 3)

        Returns:
            (detected, boxes, scores)
            - detected: bool, True if any device detected
            - boxes: list of (x1, y1, x2, y2) tuples
            - scores: list of confidence scores
        """
        # Preprocess
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb_frame).float() / 255.0
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # Add batch dimension
        tensor = tensor.to(self.device)

        # Inference
        with torch.no_grad():
            predictions = self.model([tensor.squeeze(0)])[0]

        # Extract results
        boxes = predictions['boxes'].cpu().numpy()
        scores = predictions['scores'].cpu().numpy()
        labels = predictions['labels'].cpu().numpy()

        # Filter by confidence threshold
        valid_idx = scores > self.confidence_threshold
        boxes = boxes[valid_idx]
        scores = scores[valid_idx]

        # Convert to int for display
        boxes = [(int(b[0]), int(b[1]), int(b[2]), int(b[3])) for b in boxes]

        detected = len(boxes) > 0

        return detected, boxes, scores.tolist()

    def visualize(self, frame: np.ndarray, detected: bool, boxes: list,
                 scores: list) -> np.ndarray:
        """Draw detections on frame."""
        output = frame.copy()

        if detected:
            for (x1, y1, x2, y2), score in zip(boxes, scores):
                # Draw box
                cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Draw confidence score
                label = f"Device: {score:.2f}"
                cv2.putText(output, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return output


# =============================================================================
# INTEGRATION WITH EXISTING MONITORING SYSTEM
# =============================================================================

"""
Replace your existing object_detector in main.py with this:

BEFORE (COCO pre-trained, using existing ObjectDetector):
─────────────────────────────────────────────────────────

from detection import ObjectDetector

detector = ObjectDetector()  # Uses COCO weights

while monitoring_active:
    ret, frame = cap.read()
    detected, boxes, scores = detector.detect(frame)
    ...


AFTER (Custom fine-tuned model, using CustomMobileDeviceDetector):
──────────────────────────────────────────────────────────────────

from fasterrcnn_integration import CustomMobileDeviceDetector

detector = CustomMobileDeviceDetector('trained_model/best_model.pth',
                                      confidence_threshold=0.5,
                                      gpu=0)

while monitoring_active:
    ret, frame = cap.read()
    detected, boxes, scores = detector.detect(frame)

    # Rest of code unchanged
    head_pose = head_estimator.estimate(frame)
    risk = risk_classifier.classify(detected, head_pose)
    ...


That's it! Just replace the detector initialization and model path.
"""


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    import sys

    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python fasterrcnn_integration.py <model_path> [video_file]")
        print("Example: python fasterrcnn_integration.py trained_model/best_model.pth test.mp4")
        sys.exit(1)

    model_path = sys.argv[1]
    video_file = sys.argv[2] if len(sys.argv) > 2 else 0  # Use webcam if no video

    # Initialize detector
    print("\n[Initializing detector...]")
    detector = CustomMobileDeviceDetector(model_path, confidence_threshold=0.5)

    # Open video
    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_file}")
        sys.exit(1)

    print(f"\n[Testing on video: {video_file}]")
    print("Press 'q' to exit\n")

    frame_count = 0
    detection_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Detect
        detected, boxes, scores = detector.detect(frame)

        if detected:
            detection_count += 1
            print(f"Frame {frame_count}: {len(boxes)} device(s) detected, "
                  f"confidence: {scores[0]:.2f}")

        # Visualize
        display_frame = detector.visualize(frame, detected, boxes, scores)

        # Show frame count
        cv2.putText(display_frame, f"Frame: {frame_count} | Detections: {detection_count}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Display
        cv2.imshow("Mobile Device Detection", display_frame)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Print summary
    print(f"\n[Summary]")
    print(f"Total frames: {frame_count}")
    print(f"Detections: {detection_count}")
    if frame_count > 0:
        print(f"Detection rate: {detection_count/frame_count*100:.1f}%")
