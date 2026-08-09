"""
=============================================================================
download_negatives.py — Hard-Negative Images for Mobile-Device Detection
Online Assessment Monitoring System
Holy Angel University — School of Computing

Every image in openimages_voc/ (from download_openimages.py) contains at
least one mobile_device box. With only one foreground class and zero
negative examples, the detector has no way to learn what a face/person
WITHOUT a device looks like — it was observed detecting faces as devices
during testing, a classic single-class-no-negatives failure mode.

This script downloads "Person" images from Open Images V7, keeps only the
ones that do NOT also contain a Mobile phone / Tablet computer box, and
exports them as VOC annotations with zero <object> elements — pure
background supervision for the mobile_device class.

Run with venv_download (same reason as download_openimages.py — fiftyone
needs numpy>=1.26, incompatible with the pinned numpy==1.24.3 in the main
venv):

    venv_download\\Scripts\\python.exe download_negatives.py

Output merges directly into the existing openimages_voc/train and
openimages_voc/val folders (distinct FiftyOne sample IDs avoid collisions
with the positive examples already there).
=============================================================================
"""

import argparse
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

import fiftyone as fo
import fiftyone.zoo as foz
from PIL import Image

PERSON_CLASS = "Person"
DEVICE_CLASSES = {"Mobile phone", "Tablet computer"}

OUTPUT_ROOT = Path(__file__).parent / "openimages_voc"


def is_true_negative(sample) -> bool:
    """Has a person in frame, and definitely no mobile device box."""
    labels = {det.label for det in sample.ground_truth.detections}
    return PERSON_CLASS in labels and labels.isdisjoint(DEVICE_CLASSES)


def download_negatives(split: str, target_count: int) -> list:
    """
    Download Person images for use as hard negatives.

    NOTE: we request ONLY the "Person" class here, not Person + device
    classes together. FiftyOne's Open Images loader biases its sample
    toward images containing *all* requested classes at once when you
    list several — asking for Person + Mobile phone + Tablet computer
    returned ~100% phone-containing images in testing, the opposite of
    what we want. Requesting Person alone gives a representative sample
    where phones are rare, at the cost of not being able to positively
    rule out an unboxed phone in a handful of images (acceptable noise
    for hard negatives).

    Also: FiftyOne reuses already-downloaded local images whenever a
    request can be satisfied from what's on disk. download_openimages.py
    already cached ~2000 train / ~114 val images selected specifically
    for Mobile phone/Tablet computer — and those almost all also contain
    a Person box, since people are usually visible holding the device.
    Requesting too few Person images just re-slices that same
    phone-heavy cache. Forcing max_samples well beyond what's already
    cached makes FiftyOne fetch genuinely new images instead.
    """
    already_cached = 2000 if split == "train" else 150
    fetch_count = max(int(target_count * 1.2), already_cached + target_count * 2)
    print(f"\n[download_negatives] Downloading '{split}' split "
          f"(fetching {fetch_count} Person images)")

    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split=split,
        label_types=["detections"],
        classes=[PERSON_CLASS],
        max_samples=fetch_count,
        seed=7,
        shuffle=True,
        dataset_name=f"mobile_device_negatives_{split}",
        drop_existing_dataset=True,
    )

    negatives = [s for s in dataset.iter_samples(progress=True) if is_true_negative(s)]
    negatives = negatives[:target_count]
    print(f"[download_negatives] {split}: {len(negatives)} negative "
          f"person images (of {len(dataset)} downloaded)")
    return negatives


def export_voc_negatives(samples: list, split_dir: Path):
    """Write JPEGImages/*.jpg + empty Annotations/*.xml (no <object>)."""
    images_dir = split_dir / "JPEGImages"
    annotations_dir = split_dir / "Annotations"
    images_dir.mkdir(parents=True, exist_ok=True)
    annotations_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for sample in samples:
        src_path = Path(sample.filepath)
        image_filename = f"neg_{sample.id}{src_path.suffix.lower()}"
        dst_image = images_dir / image_filename
        if not dst_image.exists():
            import shutil
            shutil.copyfile(src_path, dst_image)

        with Image.open(dst_image) as img:
            img_w, img_h = img.size

        annotation = Element("annotation")
        SubElement(annotation, "filename").text = image_filename
        size = SubElement(annotation, "size")
        SubElement(size, "width").text = str(img_w)
        SubElement(size, "height").text = str(img_h)
        SubElement(size, "depth").text = "3"
        # Deliberately no <object> elements: this image is pure background
        # for the mobile_device class.

        xml_path = annotations_dir / f"neg_{sample.id}.xml"
        ElementTree(annotation).write(xml_path, encoding="utf-8", xml_declaration=True)
        written += 1

    print(f"[download_negatives] Wrote {written} negative image/annotation pairs to {split_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-negatives", type=int, default=600,
                         help="True-negative person images for training (default: 600)")
    parser.add_argument("--val-negatives", type=int, default=100,
                         help="True-negative person images for validation (default: 100)")
    args = parser.parse_args()

    train_negatives = download_negatives("train", args.train_negatives)
    export_voc_negatives(train_negatives, OUTPUT_ROOT / "train")

    val_negatives = download_negatives("validation", args.val_negatives)
    export_voc_negatives(val_negatives, OUTPUT_ROOT / "val")

    print(f"\n[download_negatives] Done. Negatives merged into: {OUTPUT_ROOT}")
    print("Retrain with the main project venv:")
    print(r"    venv\Scripts\python.exe train_fasterrcnn.py")


if __name__ == "__main__":
    main()
