"""
=============================================================================
eval_map.py — mAP@0.5 evaluation for the mobile-device Faster R-CNN
Online Assessment Monitoring System
Holy Angel University — School of Computing

Loss (what train_fasterrcnn.py logs per epoch) is a proxy, not the metric
that actually matters for a detector. This computes single-class Average
Precision at IoU 0.5 (PASCAL VOC-style, all-point interpolation) against
the held-out validation set, so checkpoints can be compared on the metric
that belongs in a report, not on loss curves.

Usage (main project venv):
    venv\\Scripts\\python.exe eval_map.py --model trained_model/best_model.pth
    venv\\Scripts\\python.exe eval_map.py --model trained_model/last_checkpoint.pth
=============================================================================
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from train_fasterrcnn import VOCMobileDeviceDataset, collate_fn, NUM_CLASSES


def load_model(model_path: Path, device):
    model = fasterrcnn_resnet50_fpn(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)

    checkpoint = torch.load(model_path, map_location=device)
    # last_checkpoint.pth wraps the weights under "model_state_dict";
    # best_model.pth is a raw state_dict. Detect which one this is.
    is_wrapped = isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
    state_dict = checkpoint["model_state_dict"] if is_wrapped else checkpoint

    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def box_iou(box, boxes):
    """IoU of one box [4] against an array of boxes [N,4]."""
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box = (box[2] - box[0]) * (box[3] - box[1])
    area_boxes = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    union = area_box + area_boxes - inter
    return inter / np.clip(union, 1e-9, None)


def compute_ap(all_scores, all_matches, num_gt):
    """PASCAL VOC-style all-point-interpolated AP from matched detections."""
    order = np.argsort(-all_scores)
    matches = all_matches[order]

    tp = np.cumsum(matches == 1)
    fp = np.cumsum(matches == 0)
    recall = tp / max(num_gt, 1)
    precision = tp / np.maximum(tp + fp, 1)

    # all-point interpolation: precision envelope, then integrate over recall
    mrec = np.concatenate(([0.0], recall, [1.0]))
    mpre = np.concatenate(([0.0], precision, [0.0]))
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    ap = np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1])
    return ap, precision, recall


@torch.no_grad()
def evaluate(model, loader, device, iou_thresh: float, score_thresh_report: float):
    all_scores = []
    all_matches = []  # 1 = true positive, 0 = false positive
    num_gt = 0

    for images, targets in loader:
        images = [img.to(device) for img in images]
        outputs = model(images)

        for output, target in zip(outputs, targets):
            gt_boxes = target["boxes"].numpy()
            num_gt += len(gt_boxes)
            matched = np.zeros(len(gt_boxes), dtype=bool)

            scores = output["scores"].cpu().numpy()
            boxes = output["boxes"].cpu().numpy()
            order = np.argsort(-scores)

            for i in order:
                score = scores[i]
                box = boxes[i]
                all_scores.append(score)

                if len(gt_boxes) == 0:
                    all_matches.append(0)
                    continue

                ious = box_iou(box, gt_boxes)
                ious[matched] = -1  # already-claimed GT boxes can't match again
                best = np.argmax(ious)
                if ious[best] >= iou_thresh:
                    matched[best] = True
                    all_matches.append(1)
                else:
                    all_matches.append(0)

    all_scores = np.array(all_scores)
    all_matches = np.array(all_matches)

    ap, precision, recall = compute_ap(all_scores, all_matches, num_gt)

    # precision/recall at a single practical confidence threshold, for a
    # human-readable "how does this behave at inference time" number
    keep = all_scores >= score_thresh_report
    if keep.sum() > 0:
        tp_at_thresh = all_matches[keep].sum()
        p_at_thresh = tp_at_thresh / keep.sum()
        r_at_thresh = tp_at_thresh / max(num_gt, 1)
    else:
        p_at_thresh = r_at_thresh = 0.0

    return {
        "AP@0.5": ap,
        "num_gt_boxes": num_gt,
        "num_predictions": len(all_scores),
        f"precision@score>={score_thresh_report}": p_at_thresh,
        f"recall@score>={score_thresh_report}": r_at_thresh,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("openimages_voc") / "val")
    parser.add_argument("--iou-thresh", type=float, default=0.5)
    parser.add_argument("--score-thresh", type=float, default=0.5,
                         help="Confidence threshold for the reported precision/recall")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--workers", type=int, default=0)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[eval_map] Evaluating {args.model} on {device}")

    model = load_model(args.model, device)
    dataset = VOCMobileDeviceDataset(args.data_dir, train=False)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                         num_workers=args.workers, collate_fn=collate_fn)
    print(f"[eval_map] {len(dataset)} validation images")

    results = evaluate(model, loader, device, args.iou_thresh, args.score_thresh)

    print(f"\n[eval_map] Results for {args.model.name}:")
    for k, v in results.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
