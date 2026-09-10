"""
=============================================================================
merge_roboflow_negatives.py — Fold Roboflow exam-proctoring exports into
the training set as domain-matched positives/negatives
Online Assessment Monitoring System
Holy Angel University — School of Computing

Takes the raw Pascal VOC exports downloaded from Roboflow Universe
("Online Proctoring System" and "Cheating Object Detection") and merges
them into openimages_voc/train ONLY (val is left untouched on purpose —
see below).

What it does per source image:
  - Keeps only boxes whose <name> is a phone class (cell phone / phone /
    mobile phone / smartphone), case-insensitive, and relabels them
    "mobile_device" to match train_fasterrcnn.py's single-class scheme.
    All other classes (person, laptop, book, tv, headphone, student
    cheating, paper, calculator, ...) are dropped, not relabeled.
  - An image left with zero kept boxes becomes a negative (empty
    <object> list) — same convention download_negatives.py already uses.

Why train only, not val:
  Both datasets' own train/valid/test split labels turned out unreliable
  for our purposes — checked directly, and `cheating_detection` has the
  same source video's frames scattered across train/valid/test in 192 of
  233 clips. Rather than try to rebuild a clean split from that, this
  script ignores Roboflow's split labels entirely, pools everything, and
  writes it all into openimages_voc/train. The existing 224-image
  openimages_voc/val stays untouched so mAP@0.5 comparisons across
  epochs (eval_map.py) remain apples-to-apples with prior runs, and the
  real acceptance bar stays evaluation/check_evidence_frames.py against
  evidence_captures/.

Why per-source capping:
  online_proctoring's images come from consecutive video frames. One
  clip ("final-2_mp4") supplies 19,134 of its 22,440 train-labeled
  images -- almost all of it -- while the other ~580 clips average ~6
  frames each. Left uncapped, "domain-matched negatives" would mostly
  mean one recording session repeated thousands of times. Each source
  clip is capped at --max-per-source images, sampled at an even stride
  across that clip's frame-number range (not just the first N) so the
  kept frames still span the clip instead of clustering at the start.

Usage (main project venv, no GPU/torch needed -- pure stdlib):
    venv\\Scripts\\python.exe merge_roboflow_negatives.py

    (add --dry-run to see counts without writing anything)
=============================================================================
"""

import argparse
import re
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

PHONE_NAMES = {"cell phone", "phone", "mobile phone", "smartphone"}

SOURCE_RE = re.compile(r"^(.+?)-(\d+)_jpg\.rf\.")

SOURCES = [
    ("rfop", Path(__file__).parent / "roboflow_raw" / "online_proctoring"),
    ("rfcheat", Path(__file__).parent / "roboflow_raw" / "cheating_detection"),
]

DEST_ROOT = Path(__file__).parent.parent / "openimages_voc" / "train"


def group_key_and_frame(xml_path: Path):
    """Return (source_clip_id, frame_number) for even-stride sampling.

    Files without a '-<digits>_jpg.rf.' suffix (standalone photos, not
    video frames) become their own singleton group.
    """
    m = SOURCE_RE.match(xml_path.name)
    if m:
        return m.group(1), int(m.group(2))
    return xml_path.stem, 0


def select_with_cap(files_with_frames, max_per_source):
    """files_with_frames: list of (xml_path, frame_number). Returns the
    subset to keep, evenly spaced across frame number if over the cap."""
    if len(files_with_frames) <= max_per_source:
        return [f for f, _ in files_with_frames]
    ordered = sorted(files_with_frames, key=lambda t: t[1])
    n = len(ordered)
    stride = n / max_per_source
    picked = []
    seen = set()
    for i in range(max_per_source):
        idx = int(i * stride)
        if idx in seen:
            continue
        seen.add(idx)
        picked.append(ordered[idx][0])
    return picked


def filter_boxes(xml_path: Path):
    """Parse a Roboflow VOC xml, return list of (xmin,ymin,xmax,ymax) for
    phone-class boxes only (case-insensitive name match)."""
    root = ET.parse(xml_path).getroot()
    boxes = []
    for obj in root.findall("object"):
        name_el = obj.find("name")
        if name_el is None or (name_el.text or "").strip().lower() not in PHONE_NAMES:
            continue
        bb = obj.find("bndbox")
        boxes.append((
            float(bb.find("xmin").text),
            float(bb.find("ymin").text),
            float(bb.find("xmax").text),
            float(bb.find("ymax").text),
        ))
    return boxes


def write_voc_xml(dest_xml: Path, filename: str, width: int, height: int, boxes):
    ann = ET.Element("annotation")
    ET.SubElement(ann, "filename").text = filename
    size = ET.SubElement(ann, "size")
    ET.SubElement(size, "width").text = str(width)
    ET.SubElement(size, "height").text = str(height)
    ET.SubElement(size, "depth").text = "3"
    for (xmin, ymin, xmax, ymax) in boxes:
        obj = ET.SubElement(ann, "object")
        ET.SubElement(obj, "name").text = "mobile_device"
        bb = ET.SubElement(obj, "bndbox")
        ET.SubElement(bb, "xmin").text = str(int(xmin))
        ET.SubElement(bb, "ymin").text = str(int(ymin))
        ET.SubElement(bb, "xmax").text = str(int(xmax))
        ET.SubElement(bb, "ymax").text = str(int(ymax))
    ET.ElementTree(ann).write(dest_xml, encoding="utf-8", xml_declaration=True)


def get_size(xml_path: Path):
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    return int(size.find("width").text), int(size.find("height").text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-source", type=int, default=150,
                         help="Cap on images kept from any single source clip")
    parser.add_argument("--dry-run", action="store_true",
                         help="Report counts without writing files")
    args = parser.parse_args()

    dest_images = DEST_ROOT / "JPEGImages"
    dest_annots = DEST_ROOT / "Annotations"
    if not args.dry_run:
        dest_images.mkdir(parents=True, exist_ok=True)
        dest_annots.mkdir(parents=True, exist_ok=True)

    grand_pos = grand_neg = grand_skipped_missing_jpg = 0

    for tag, src_root in SOURCES:
        if not src_root.exists():
            print(f"[skip] {src_root} not found")
            continue

        all_xml = list(src_root.glob("*/*.xml"))  # train/valid/test, pooled
        groups = defaultdict(list)
        for xml_path in all_xml:
            key, frame = group_key_and_frame(xml_path)
            groups[key].append((xml_path, frame))

        kept_xml = []
        for key, files_with_frames in groups.items():
            kept_xml.extend(select_with_cap(files_with_frames, args.max_per_source))

        print(f"\n=== {tag} ({src_root.name}) ===")
        print(f"  source clips: {len(groups)}, raw images: {len(all_xml)}, "
              f"kept after cap: {len(kept_xml)}")

        pos = neg = skipped = 0
        for xml_path in kept_xml:
            jpg_path = xml_path.with_suffix(".jpg")
            if not jpg_path.exists():
                skipped += 1
                continue

            boxes = filter_boxes(xml_path)
            width, height = get_size(xml_path)

            stem = f"{tag}_{xml_path.stem}"
            dest_jpg = dest_images / f"{stem}.jpg"
            dest_xml = dest_annots / f"{stem}.xml"

            if boxes:
                pos += 1
            else:
                neg += 1

            if not args.dry_run:
                shutil.copyfile(jpg_path, dest_jpg)
                write_voc_xml(dest_xml, dest_jpg.name, width, height, boxes)

        print(f"  -> {pos} positive (phone box kept), {neg} negative "
              f"(zero phone boxes), {skipped} skipped (missing jpg)")
        grand_pos += pos
        grand_neg += neg
        grand_skipped_missing_jpg += skipped

    print(f"\n=== TOTAL {'(dry run, nothing written)' if args.dry_run else 'written to ' + str(DEST_ROOT)} ===")
    print(f"  positives: {grand_pos}")
    print(f"  negatives: {grand_neg}")
    print(f"  ratio: {grand_neg / max(1, grand_pos + grand_neg):.1%} negative")
    if grand_skipped_missing_jpg:
        print(f"  skipped (missing jpg): {grand_skipped_missing_jpg}")


if __name__ == "__main__":
    main()
