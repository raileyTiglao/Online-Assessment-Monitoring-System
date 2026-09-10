"""
evaluation/eval_finetuned_checkpoint.py — full Table-6-style metrics for a
FINE-TUNED checkpoint (best_model.pth / selected_model_epoch2.pth / any
other trained_model/*.pth), computed the same way eval_deployed_model.py
computes them for the deployed stock model, so the two are comparable.

Unlike evaluation/eval_map.py (AP@0.5 only, single score threshold),
this reports mAP@[.5:.95], AP@0.5, AP@0.75, precision/recall/F1 at the
production score threshold (both raw and duplicate-collapsed ground
truth), and per-frame inference time.

IMPORTANT — resize mismatch fix: eval_map.py builds the model with
fasterrcnn_resnet50_fpn(weights=None) and never passes min_size/max_size,
so it silently resizes at torchvision's default (800/1333). But
training/train_fasterrcnn.py's build_model() trains at --min-size 600
/ --max-size 1000 by default (matching config.py's DETECTION_MIN_SIZE/
MAX_SIZE for the deployed detector). Evaluating at 800/1333 when the
model was trained at 600/1000 is an eval/train mismatch — this script
uses 600/1000 to match what these checkpoints were actually trained at.
That means numbers here may legitimately differ from the historical
AP@0.5 0.35-0.38 band recorded in docs/logs.md, which was produced by
eval_map.py's mismatched resize.

Usage (main project venv):
    venv\\Scripts\\python.exe evaluation\\eval_finetuned_checkpoint.py --model trained_model\\best_model.pth
    venv\\Scripts\\python.exe evaluation\\eval_finetuned_checkpoint.py --model trained_model\\selected_model_epoch2.pth
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import torch
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "training"))

from train_fasterrcnn import VOCMobileDeviceDataset, NUM_CLASSES  # noqa: E402

FOREGROUND_LABEL = 1  # VOCMobileDeviceDataset's single foreground class == this model's predicted label for it
GT_LABEL = 1
IOU_THRESHOLDS_MAP = [round(0.5 + 0.05 * i, 2) for i in range(10)]  # 0.50..0.95, COCO-style
REPORT_IOU = 0.5
REPORT_SCORE_THRESH = 0.6  # matches DetectionConfig.CONFIDENCE_THRESHOLD, for comparability with Table 6

# Must match training/train_fasterrcnn.py's build_model() defaults, so
# evaluation happens at the same resize the checkpoint was trained at.
TRAIN_MIN_SIZE = 600
TRAIN_MAX_SIZE = 1000


def load_finetuned_model(model_path: Path, device):
    model = fasterrcnn_resnet50_fpn(
        weights=None,
        min_size=TRAIN_MIN_SIZE,
        max_size=TRAIN_MAX_SIZE,
    )
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)

    checkpoint = torch.load(model_path, map_location=device)
    # last_checkpoint.pth wraps weights under "model_state_dict"; best_model.pth
    # and selected_model_epoch2.pth are raw state_dicts. Detect which this is.
    is_wrapped = isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
    state_dict = checkpoint["model_state_dict"] if is_wrapped else checkpoint

    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def box_iou(box, boxes):
    x1 = torch.max(box[0], boxes[:, 0])
    y1 = torch.max(box[1], boxes[:, 1])
    x2 = torch.min(box[2], boxes[:, 2])
    y2 = torch.min(box[3], boxes[:, 3])
    inter = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)
    area_box = (box[2] - box[0]) * (box[3] - box[1])
    area_boxes = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    union = area_box + area_boxes - inter
    return inter / union.clamp(min=1e-9)


def compute_ap(all_scores, all_matches, num_gt):
    if num_gt == 0:
        return 0.0
    order = sorted(range(len(all_scores)), key=lambda i: -all_scores[i])
    matches = [all_matches[i] for i in order]
    tp = fp = 0
    precisions, recalls = [], []
    for m in matches:
        if m:
            tp += 1
        else:
            fp += 1
        precisions.append(tp / (tp + fp))
        recalls.append(tp / num_gt)
    for i in range(len(precisions) - 2, -1, -1):
        precisions[i] = max(precisions[i], precisions[i + 1])
    ap = 0.0
    prev_recall = 0.0
    for p, r in zip(precisions, recalls):
        ap += p * (r - prev_recall)
        prev_recall = r
    return ap


def dedupe_gt_boxes(gt_boxes, iou_thresh=0.7):
    if len(gt_boxes) <= 1:
        return gt_boxes
    keep = []
    used = torch.zeros(len(gt_boxes), dtype=torch.bool)
    for i in range(len(gt_boxes)):
        if used[i]:
            continue
        keep.append(gt_boxes[i])
        used[i] = True
        for j in range(i + 1, len(gt_boxes)):
            if used[j]:
                continue
            if box_iou(gt_boxes[i], gt_boxes[j:j + 1])[0].item() >= iou_thresh:
                used[j] = True
    return torch.stack(keep) if keep else gt_boxes[:0]


def run_inference(model, dataset, device):
    results = []
    times_ms = []
    with torch.no_grad():
        for idx in range(len(dataset)):
            image, target = dataset[idx]
            tensor = image.to(device)

            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()

            pred = model([tensor])[0]

            if device.type == "cuda":
                torch.cuda.synchronize()
            t1 = time.perf_counter()

            if idx > 0:  # skip first-frame CUDA warm-up
                times_ms.append((t1 - t0) * 1000.0)

            labels = pred["labels"].cpu()
            scores = pred["scores"].cpu()
            boxes = pred["boxes"].cpu()
            keep = labels == FOREGROUND_LABEL
            results.append({
                "det_boxes": boxes[keep],
                "det_scores": scores[keep],
                "gt_boxes": target["boxes"],
            })
    return results, times_ms


def compute_map(results, iou_thresholds):
    aps = {}
    for iou_t in iou_thresholds:
        all_scores, all_matches = [], []
        num_gt_total = 0
        for r in results:
            gt_boxes = r["gt_boxes"]
            num_gt_total += len(gt_boxes)
            matched = torch.zeros(len(gt_boxes), dtype=torch.bool)
            order = torch.argsort(r["det_scores"], descending=True)
            for i in order:
                score = r["det_scores"][i].item()
                box = r["det_boxes"][i]
                is_match = False
                if len(gt_boxes) > 0:
                    ious = box_iou(box, gt_boxes)
                    best_iou, best_j = ious.max(0)
                    if best_iou.item() >= iou_t and not matched[best_j]:
                        matched[best_j] = True
                        is_match = True
                all_scores.append(score)
                all_matches.append(is_match)
        aps[iou_t] = compute_ap(all_scores, all_matches, num_gt_total)
    return aps


def compute_precision_recall_f1(results, score_thresh, iou_thresh=REPORT_IOU, dedupe=False):
    tp = fp = fn = 0
    for r in results:
        gt_boxes = dedupe_gt_boxes(r["gt_boxes"]) if dedupe else r["gt_boxes"]
        matched = torch.zeros(len(gt_boxes), dtype=torch.bool)

        keep = r["det_scores"] >= score_thresh
        det_boxes = r["det_boxes"][keep]
        det_scores = r["det_scores"][keep]
        order = torch.argsort(det_scores, descending=True)

        for i in order:
            box = det_boxes[i]
            is_match = False
            if len(gt_boxes) > 0:
                ious = box_iou(box, gt_boxes)
                best_iou, best_j = ious.max(0)
                if best_iou.item() >= iou_thresh and not matched[best_j]:
                    matched[best_j] = True
                    is_match = True
            if is_match:
                tp += 1
            else:
                fp += 1
        fn += int((~matched).sum().item())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("openimages_voc") / "val")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[eval_finetuned_checkpoint] model={args.model}  device={device}  "
          f"min_size={TRAIN_MIN_SIZE} max_size={TRAIN_MAX_SIZE} score_thresh={REPORT_SCORE_THRESH}")

    dataset = VOCMobileDeviceDataset(PROJECT_ROOT / args.data_dir, train=False)
    print(f"[eval_finetuned_checkpoint] validation set: {len(dataset)} images")

    model = load_finetuned_model(PROJECT_ROOT / args.model, device)
    results, times_ms = run_inference(model, dataset, device)

    aps = compute_map(results, IOU_THRESHOLDS_MAP)
    map_5095 = sum(aps.values()) / len(aps)
    ap50 = aps[0.5]
    ap75 = aps[0.75]

    pr = compute_precision_recall_f1(results, REPORT_SCORE_THRESH, REPORT_IOU, dedupe=False)
    pr_dedup = compute_precision_recall_f1(results, REPORT_SCORE_THRESH, REPORT_IOU, dedupe=True)

    total_gt_raw = sum(len(r["gt_boxes"]) for r in results)
    total_gt_dedup = sum(len(dedupe_gt_boxes(r["gt_boxes"])) for r in results)

    mean_ms = sum(times_ms) / len(times_ms)
    std_ms = statistics.pstdev(times_ms)

    print("\n=== Results ===")
    print(f"mAP@[.5:.95] = {map_5095:.4f}")
    print(f"AP@0.5       = {ap50:.4f}")
    print(f"AP@0.75      = {ap75:.4f}")
    print(f"\nGround-truth boxes: {total_gt_raw} raw -> {total_gt_dedup} after "
          f"collapsing same-image IoU>=0.7 duplicates")
    print(f"\n[RAW ground truth]")
    print(f"Precision@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU} = {pr['precision']:.4f}  "
          f"(TP={pr['tp']} FP={pr['fp']} FN={pr['fn']})")
    print(f"Recall@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU}    = {pr['recall']:.4f}")
    print(f"F1@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU}        = {pr['f1']:.4f}")
    print(f"\n[DEDUPLICATED ground truth]")
    print(f"Precision@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU} = {pr_dedup['precision']:.4f}  "
          f"(TP={pr_dedup['tp']} FP={pr_dedup['fp']} FN={pr_dedup['fn']})")
    print(f"Recall@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU}    = {pr_dedup['recall']:.4f}")
    print(f"F1@score>={REPORT_SCORE_THRESH}, IoU>={REPORT_IOU}        = {pr_dedup['f1']:.4f}")
    print(f"\nInference time: {mean_ms:.2f}ms +/- {std_ms:.2f}ms per frame "
          f"(n={len(times_ms)}, first-frame warm-up excluded)")

    out = {
        "model": str(args.model),
        "device": str(device),
        "min_size": TRAIN_MIN_SIZE,
        "max_size": TRAIN_MAX_SIZE,
        "num_images": len(dataset),
        "score_thresh": REPORT_SCORE_THRESH,
        "report_iou": REPORT_IOU,
        "map_50_95": map_5095,
        "ap_per_iou": aps,
        "ap50": ap50,
        "ap75": ap75,
        "total_gt_boxes_raw": total_gt_raw,
        "total_gt_boxes_dedup": total_gt_dedup,
        "raw": {"precision": pr["precision"], "recall": pr["recall"], "f1": pr["f1"],
                "tp": pr["tp"], "fp": pr["fp"], "fn": pr["fn"]},
        "dedup": {"precision": pr_dedup["precision"], "recall": pr_dedup["recall"], "f1": pr_dedup["f1"],
                  "tp": pr_dedup["tp"], "fp": pr_dedup["fp"], "fn": pr_dedup["fn"]},
        "mean_inference_ms": mean_ms,
        "std_inference_ms": std_ms,
        "n_timed_frames": len(times_ms),
    }
    out_path = Path(__file__).parent / f"{args.model.stem}_eval_results.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
