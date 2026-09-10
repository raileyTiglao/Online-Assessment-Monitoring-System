"""Ad-hoc check: run a checkpoint against this project's own real evidence
frames (not Open Images) to see how it behaves in the actual deployment
domain. 15 of the 16 frames in evidence_captures/ contain no phone; one
(high_risk_20260802_172856.jpg) does.
"""
import argparse
import sys
from pathlib import Path

import torch
import torchvision.transforms.functional as TF
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "training"))
from train_fasterrcnn import NUM_CLASSES  # noqa: E402

KNOWN_PHONE_FRAME = "high_risk_20260802_172856.jpg"


def load_model(model_path: Path, device):
    model = fasterrcnn_resnet50_fpn(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)
    checkpoint = torch.load(model_path, map_location=device)
    is_wrapped = isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
    state_dict = checkpoint["model_state_dict"] if is_wrapped else checkpoint
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dir", type=Path, default=Path("evidence_captures"))
    parser.add_argument("--score-thresh", type=float, default=0.5)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(args.model, device)

    frames = sorted(args.dir.glob("*.jpg"))
    print(f"[check] {len(frames)} frames from {args.dir}\n")

    total_fp_boxes = 0
    fp_frame_count = 0
    for f in frames:
        image = Image.open(f).convert("RGB")
        w, h = image.size
        tensor = TF.to_tensor(image).to(device)
        with torch.no_grad():
            pred = model([tensor])[0]

        boxes = pred["boxes"].cpu().numpy()
        scores = pred["scores"].cpu().numpy()
        keep = scores >= args.score_thresh
        boxes, scores = boxes[keep], scores[keep]

        has_phone = f.name == KNOWN_PHONE_FRAME
        label = "HAS PHONE" if has_phone else "no phone"
        print(f"{f.name}  [{label}]  frame={w}x{h}  detections={len(boxes)}")
        for b, s in zip(boxes, scores):
            bw, bh = b[2] - b[0], b[3] - b[1]
            frac_area = (bw * bh) / (w * h)
            print(f"    score={s:.3f}  box=({b[0]:.0f},{b[1]:.0f})-({b[2]:.0f},{b[3]:.0f})"
                  f"  size={bw:.0f}x{bh:.0f}  frame_area_frac={frac_area:.2f}")
            if not has_phone:
                total_fp_boxes += 1
        if not has_phone and len(boxes) > 0:
            fp_frame_count += 1

    no_phone_count = sum(1 for f in frames if f.name != KNOWN_PHONE_FRAME)
    print(f"\n[check] False positives: {fp_frame_count}/{no_phone_count} phone-free frames "
          f"had >=1 detection ({total_fp_boxes} total boxes) at score>={args.score_thresh}")


if __name__ == "__main__":
    main()
