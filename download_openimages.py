"""
=============================================================================
download_openimages.py — Build a Mobile-Device Detection Dataset
Online Assessment Monitoring System
Holy Angel University — School of Computing

Downloads "Mobile phone" and "Tablet computer" images + boxes from Google's
Open Images V7 dataset via FiftyOne, collapses both into a single class,
and exports the result as a Pascal VOC dataset that train_fasterrcnn.py
can train on directly.

Run this with the venv_download interpreter (NOT the main project venv —
fiftyone needs numpy>=1.26, which conflicts with the pinned numpy==1.24.3
that torch/mediapipe rely on in the main venv):

    venv_download\\Scripts\\python.exe download_openimages.py

Output layout (Pascal VOC):
    openimages_voc/
        train/
            JPEGImages/*.jpg
            Annotations/*.xml
        val/
            JPEGImages/*.jpg
            Annotations/*.xml

All boxes are written with a single label: "mobile_device" (VOC class
name). train_fasterrcnn.py maps this to model label 1 (background is
implicitly 0), matching the 2-class head (background + mobile_device)
used in fasterrcnn_integration.py.
=============================================================================
"""

import argparse
import shutil
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

import fiftyone as fo
import fiftyone.zoo as foz
from PIL import Image

SOURCE_CLASSES = ["Mobile phone", "Tablet computer"]
TARGET_CLASS_NAME = "mobile_device"

OUTPUT_ROOT = Path(__file__).parent / "openimages_voc"


def download_split(split: str, max_samples: int) -> fo.Dataset:
    """Download an Open Images V7 split filtered to our target classes."""
    print(f"\n[download_openimages] Downloading '{split}' split "
          f"(max {max_samples} samples) for classes: {SOURCE_CLASSES}")

    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split=split,
        label_types=["detections"],
        classes=SOURCE_CLASSES,
        max_samples=max_samples,
        seed=42,
        shuffle=True,
        dataset_name=f"mobile_device_{split}",
        drop_existing_dataset=True,
    )

    # Keep only detections for our target classes (the zoo dataset can
    # include boxes for other classes present in the same images) and
    # collapse both source classes into one label.
    view = dataset.filter_labels(
        "ground_truth", fo.ViewField("label").is_in(SOURCE_CLASSES)
    )
    for sample in view.iter_samples(autosave=True, progress=True):
        for det in sample.ground_truth.detections:
            det.label = TARGET_CLASS_NAME

    # Drop samples that ended up with zero boxes after filtering.
    non_empty = dataset.match(fo.ViewField("ground_truth.detections").length() > 0)
    print(f"[download_openimages] {split}: {len(non_empty)} images with "
          f"{TARGET_CLASS_NAME} boxes (of {len(dataset)} downloaded)")
    return non_empty


def voc_xml_for_sample(sample, image_filename: str, img_w: int, img_h: int) -> Element:
    """Build a Pascal VOC <annotation> element for one FiftyOne sample."""

    annotation = Element("annotation")
    SubElement(annotation, "filename").text = image_filename

    size = SubElement(annotation, "size")
    SubElement(size, "width").text = str(img_w)
    SubElement(size, "height").text = str(img_h)
    SubElement(size, "depth").text = "3"

    for det in sample.ground_truth.detections:
        # FiftyOne stores boxes as relative [x, y, w, h] in [0, 1].
        x, y, w, h = det.bounding_box
        xmin = max(0, round(x * img_w))
        ymin = max(0, round(y * img_h))
        xmax = min(img_w, round((x + w) * img_w))
        ymax = min(img_h, round((y + h) * img_h))
        if xmax <= xmin or ymax <= ymin:
            continue

        obj = SubElement(annotation, "object")
        SubElement(obj, "name").text = TARGET_CLASS_NAME
        SubElement(obj, "difficult").text = "0"
        bbox = SubElement(obj, "bndbox")
        SubElement(bbox, "xmin").text = str(xmin)
        SubElement(bbox, "ymin").text = str(ymin)
        SubElement(bbox, "xmax").text = str(xmax)
        SubElement(bbox, "ymax").text = str(ymax)

    return annotation


def export_voc(view: fo.DatasetView, split_dir: Path):
    """Write JPEGImages/*.jpg + Annotations/*.xml for a FiftyOne view."""
    images_dir = split_dir / "JPEGImages"
    annotations_dir = split_dir / "Annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for sample in view.iter_samples(progress=True):
        src_path = Path(sample.filepath)
        image_filename = f"{sample.id}{src_path.suffix.lower()}"
        dst_image = images_dir / image_filename
        if not dst_image.exists():
            shutil.copyfile(src_path, dst_image)

        with Image.open(dst_image) as img:
            img_w, img_h = img.size

        annotation = voc_xml_for_sample(sample, image_filename, img_w, img_h)
        if annotation.find("object") is None:
            continue  # no valid boxes survived clamping, skip

        xml_path = annotations_dir / f"{sample.id}.xml"
        ElementTree(annotation).write(xml_path, encoding="utf-8", xml_declaration=True)
        written += 1

    print(f"[download_openimages] Wrote {written} image/annotation pairs to {split_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-samples", type=int, default=800,
                         help="Max training images to download (default: 800)")
    parser.add_argument("--val-samples", type=int, default=150,
                         help="Max validation images to download (default: 150)")
    args = parser.parse_args()

    if OUTPUT_ROOT.exists():
        print(f"[download_openimages] {OUTPUT_ROOT} already exists — "
              f"remove it first if you want a fresh download.")

    train_view = download_split("train", args.train_samples)
    export_voc(train_view, OUTPUT_ROOT / "train")

    val_view = download_split("validation", args.val_samples)
    export_voc(val_view, OUTPUT_ROOT / "val")

    print(f"\n[download_openimages] Done. Dataset ready at: {OUTPUT_ROOT}")
    print("Train with the main project venv:")
    print(r"    venv\Scripts\python.exe train_fasterrcnn.py")


if __name__ == "__main__":
    main()
