"""
=============================================================================
mine_hard_negatives.py — Hard-negative mining against unused Roboflow frames
Online Assessment Monitoring System
Holy Angel University — School of Computing

Runs a trained checkpoint (default: trained_model/selected_model_epoch2.pth
— the model rejected for live false positives, see docs/JUSTIFICATION.md #2)
against the raw Roboflow frames that were NEVER included in training.
merge_roboflow_negatives.py capped how many frames it kept per source clip
(--max-per-source, default 150), so most of the ~27,000 downloaded frames
were left unused — that leftover pool is legitimate out-of-sample data,
already on disk, with no new recording needed.

For each unused frame with no real phone (per its own Roboflow ground-truth
label), a model prediction above --score-thresh is a genuine false
positive — exactly the kind of hard negative this checkpoint needs more of,
found from its own real mistakes rather than anticipated in advance. Hits
are written out as new VOC negatives (empty <object> list, same convention
merge_roboflow_negatives.py uses) directly into openimages_voc/train,
prefixed "hardneg_" so their origin stays traceable. Frames with a real
phone are skipped entirely — this script mines negatives, it doesn't
evaluate recall.

Usage (main project venv, GPU strongly recommended — this checks
thousands of images):
    venv\\Scripts\\python.exe mine_hard_negatives.py --dry-run
    venv\\Scripts\\python.exe mine_hard_negatives.py
=============================================================================
"""

import argparse
import shutil
import sys
from pathlib import Path

import torch
import torchvision.transforms.functional as TF
from PIL import Image
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from merge_roboflow_negatives import SOURCES, filter_boxes, write_voc_xml
from train_fasterrcnn import NUM_CLASSES

DEST_ROOT = Path(__file__).parent.parent / "openimages_voc" / "train"
DEFAULT_MODEL = Path(__file__).parent.parent / "trained_model" / "selected_model_epoch2.pth"


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


def already_used_stems(tag: str) -> set:
    """
    Stems (tag prefix stripped) already copied into openimages_voc/train by
    merge_roboflow_negatives.py — checked directly against what's actually
    on disk, not recomputed from the merge script's capping logic, so this
    stays correct regardless of what --max-per-source it was originally run
    with.
    """
    images_dir = DEST_ROOT / "JPEGImages"
    prefix = f"{tag}_"
    return {p.stem[len(prefix):] for p in images_dir.glob(f"{prefix}*.jpg")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--score-thresh", type=float, default=0.5,
                         help="Confidence above which a prediction counts as a false positive")
    parser.add_argument("--dry-run", action="store_true",
                         help="Report counts without writing any files")
    parser.add_argument("--limit", type=int, default=None,
                         help="Stop after checking this many candidate images per source "
                              "(for a quick smoke test — omit for a full run)")
    args = parser.parse_args()

    if not args.model.exists():
        raise SystemExit(f"[ERROR] Model not found: {args.model}\n"
                          f"(trained_model/ is gitignored — see docs/PROJECT_SETUP.md "
                          f"if this is a fresh checkout)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[mine] Loading {args.model} on {device}...")
    model = load_model(args.model, device)

    dest_images = DEST_ROOT / "JPEGImages"
    dest_annots = DEST_ROOT / "Annotations"
    if not args.dry_run:
        dest_images.mkdir(parents=True, exist_ok=True)
        dest_annots.mkdir(parents=True, exist_ok=True)

    grand_checked = grand_hard_negatives = 0

    for tag, src_root in SOURCES:
        if not src_root.exists():
            print(f"[skip] {src_root} not found")
            continue

        used = already_used_stems(tag)
        all_xml = list(src_root.glob("*/*.xml"))
        print(f"\n=== {tag} ({src_root.name}) ===")
        print(f"  raw images: {len(all_xml)}, already used in training: {len(used)}")

        checked = skipped_used = skipped_positive = skipped_missing_jpg = hard_negatives = 0
        for xml_path in all_xml:
            if xml_path.stem in used:
                skipped_used += 1
                continue

            jpg_path = xml_path.with_suffix(".jpg")
            if not jpg_path.exists():
                skipped_missing_jpg += 1
                continue

            boxes = filter_boxes(xml_path)
            if boxes:
                # A real phone is present per Roboflow's own label — not a
                # candidate negative. Whether the model correctly detects
                # it is a recall question, not what this script mines for.
                skipped_positive += 1
                continue

            checked += 1
            image = Image.open(jpg_path).convert("RGB")
            w, h = image.size
            tensor = TF.to_tensor(image).to(device)
            with torch.no_grad():
                pred = model([tensor])[0]
            scores = pred["scores"].cpu().numpy()

            if (scores >= args.score_thresh).any():
                hard_negatives += 1
                stem = f"hardneg_{tag}_{xml_path.stem}"
                if not args.dry_run:
                    shutil.copyfile(jpg_path, dest_images / f"{stem}.jpg")
                    write_voc_xml(dest_annots / f"{stem}.xml", f"{stem}.jpg", w, h, [])

            if checked % 500 == 0:
                print(f"  ...checked {checked}, {hard_negatives} hard negatives so far")

            if args.limit is not None and checked >= args.limit:
                print(f"  ...--limit {args.limit} reached, stopping this source early")
                break

        print(f"  -> checked {checked} unused true-negative frames "
              f"(skipped {skipped_used} already-used, {skipped_positive} real-phone, "
              f"{skipped_missing_jpg} missing jpg)")
        print(f"  -> found {hard_negatives} hard negatives")
        grand_checked += checked
        grand_hard_negatives += hard_negatives

    print(f"\n=== TOTAL {'(dry run, nothing written)' if args.dry_run else 'written to ' + str(DEST_ROOT)} ===")
    print(f"  checked: {grand_checked}")
    print(f"  hard negatives found: {grand_hard_negatives}")
    if grand_checked:
        print(f"  false-positive rate on unused frames: {grand_hard_negatives / grand_checked:.1%}")


if __name__ == "__main__":
    main()
