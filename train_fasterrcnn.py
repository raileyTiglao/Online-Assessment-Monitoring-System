"""
=============================================================================
train_fasterrcnn.py — Fine-tune Faster R-CNN for Mobile Device Detection
Online Assessment Monitoring System
Holy Angel University — School of Computing

Fine-tunes a COCO-pretrained Faster R-CNN (ResNet50-FPN) on the Pascal VOC
dataset produced by download_openimages.py, using a single class
("mobile_device" -> label 1) on top of the implicit background (label 0).

Run with the main project venv (NOT venv_download — that one has a
numpy>=1.26 fiftyone stack incompatible with torch/mediapipe here):

    venv\\Scripts\\python.exe train_fasterrcnn.py

Output:
    trained_model/best_model.pth      <- raw state_dict of the epoch with the
                                          lowest validation LOSS. Loss is only
                                          a proxy for detection quality — use
                                          eval_map.py against trained_model/epochs/
                                          to pick the epoch with the best AP@0.5
                                          instead of trusting this file blindly.
    trained_model/epochs/epoch_N.pth  <- raw state_dict after every epoch
    trained_model/last_checkpoint.pth <- full checkpoint (epoch, optimizer,
                                          scaler) for resuming with --resume
=============================================================================
"""

import argparse
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import torch
import torchvision
from torch.utils.data import Dataset, DataLoader
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
    FasterRCNN_ResNet50_FPN_Weights,
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms import functional as TF
from PIL import Image

NUM_CLASSES = 2  # background (0) + mobile_device (1)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class VOCMobileDeviceDataset(Dataset):
    """Reads JPEGImages/*.jpg + Annotations/*.xml written by download_openimages.py."""

    def __init__(self, root: Path, train: bool):
        self.images_dir = root / "JPEGImages"
        self.annotations_dir = root / "Annotations"
        self.ids = sorted(p.stem for p in self.annotations_dir.glob("*.xml"))
        self.train = train
        if not self.ids:
            raise RuntimeError(f"No annotations found under {self.annotations_dir}")

    def __len__(self):
        return len(self.ids)

    def __getitem__(self, idx):
        image_id = self.ids[idx]
        tree = ET.parse(self.annotations_dir / f"{image_id}.xml")
        root_el = tree.getroot()

        filename = root_el.find("filename").text
        image = Image.open(self.images_dir / filename).convert("RGB")

        boxes, labels = [], []
        for obj in root_el.findall("object"):
            bbox = obj.find("bndbox")
            boxes.append([
                float(bbox.find("xmin").text),
                float(bbox.find("ymin").text),
                float(bbox.find("xmax").text),
                float(bbox.find("ymax").text),
            ])
            labels.append(1)  # single foreground class: mobile_device

        if boxes:
            boxes = torch.as_tensor(boxes, dtype=torch.float32)
            labels = torch.as_tensor(labels, dtype=torch.int64)
            area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        else:
            # Negative example (e.g. a face/person image with no device in
            # frame): an image-shaped empty target, not an absent one.
            boxes = torch.zeros((0, 4), dtype=torch.float32)
            labels = torch.zeros((0,), dtype=torch.int64)
            area = torch.zeros((0,), dtype=torch.float32)

        image = TF.to_tensor(image)

        if self.train and random.random() < 0.5:
            image = TF.hflip(image)
            w = image.shape[-1]
            flipped = boxes.clone()
            flipped[:, 0] = w - boxes[:, 2]
            flipped[:, 2] = w - boxes[:, 0]
            boxes = flipped

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id": torch.tensor([idx]),
            "area": area,
            "iscrowd": torch.zeros((len(labels),), dtype=torch.int64),
        }
        return image, target


def collate_fn(batch):
    return tuple(zip(*batch))


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def build_model(min_size: int, max_size: int):
    """COCO-pretrained Faster R-CNN with a fresh 2-class detection head."""
    weights = FasterRCNN_ResNet50_FPN_Weights.DEFAULT
    model = fasterrcnn_resnet50_fpn(weights=weights, min_size=min_size, max_size=max_size)

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, NUM_CLASSES)
    return model


# ---------------------------------------------------------------------------
# Train / eval loops
# ---------------------------------------------------------------------------

def run_epoch_train(model, loader, optimizer, scaler, device, use_amp, epoch, log_every=20):
    model.train()
    total_loss = 0.0
    start = time.time()

    for i, (images, targets) in enumerate(loader):
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        optimizer.zero_grad()
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
            loss_dict = model(images, targets)
            loss = sum(loss_dict.values())

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        total_loss += loss.item()
        if (i + 1) % log_every == 0:
            print(f"  epoch {epoch} [{i + 1}/{len(loader)}] "
                  f"loss={loss.item():.4f} avg={total_loss / (i + 1):.4f}")

    elapsed = time.time() - start
    print(f"[train] epoch {epoch} done in {elapsed:.1f}s, avg loss {total_loss / len(loader):.4f}")
    return total_loss / len(loader)


@torch.no_grad()
def run_epoch_val(model, loader, device, use_amp):
    # torchvision detection models only return the loss dict in train()
    # mode; wrapping in no_grad() keeps this a pure evaluation pass.
    model.train()
    total_loss = 0.0
    for images, targets in loader:
        images = [img.to(device) for img in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
            loss_dict = model(images, targets)
            loss = sum(loss_dict.values())
        total_loss += loss.item()
    avg = total_loss / len(loader)
    print(f"[val]   avg loss {avg:.4f}")
    return avg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("openimages_voc"))
    parser.add_argument("--output-dir", type=Path, default=Path("trained_model"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=0.005)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--min-size", type=int, default=600, help="Shorter-side resize; lower = less VRAM")
    parser.add_argument("--max-size", type=int, default=1000)
    parser.add_argument("--no-amp", action="store_true", help="Disable mixed-precision training")
    parser.add_argument("--resume", action="store_true", help="Resume from trained_model/last_checkpoint.pth")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train_fasterrcnn] Using device: {device}")
    if device.type == "cuda":
        print(f"[train_fasterrcnn] GPU: {torch.cuda.get_device_name(0)}")
    use_amp = device.type == "cuda" and not args.no_amp

    train_set = VOCMobileDeviceDataset(args.data_dir / "train", train=True)
    val_set = VOCMobileDeviceDataset(args.data_dir / "val", train=False)
    print(f"[train_fasterrcnn] train images: {len(train_set)}, val images: {len(val_set)}")

    train_loader = DataLoader(train_set, batch_size=args.batch_size, shuffle=True,
                               num_workers=args.workers, collate_fn=collate_fn)
    val_loader = DataLoader(val_set, batch_size=args.batch_size, shuffle=False,
                             num_workers=args.workers, collate_fn=collate_fn)

    model = build_model(args.min_size, args.max_size).to(device)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.SGD(params, lr=args.lr, momentum=0.9, weight_decay=0.0005)
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    best_path = args.output_dir / "best_model.pth"
    checkpoint_path = args.output_dir / "last_checkpoint.pth"
    epochs_dir = args.output_dir / "epochs"
    epochs_dir.mkdir(exist_ok=True)

    start_epoch = 0
    best_val_loss = float("inf")

    if args.resume and checkpoint_path.exists():
        ckpt = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scaler.load_state_dict(ckpt["scaler_state_dict"])
        lr_scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        best_val_loss = ckpt["best_val_loss"]
        print(f"[train_fasterrcnn] Resumed from epoch {start_epoch}, best_val_loss={best_val_loss:.4f}")

    for epoch in range(start_epoch, args.epochs):
        run_epoch_train(model, train_loader, optimizer, scaler, device, use_amp, epoch)
        val_loss = run_epoch_val(model, val_loader, device, use_amp)
        lr_scheduler.step()

        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scaler_state_dict": scaler.state_dict(),
            "scheduler_state_dict": lr_scheduler.state_dict(),
            "best_val_loss": best_val_loss,
        }, checkpoint_path)

        epoch_path = epochs_dir / f"epoch_{epoch}.pth"
        torch.save(model.state_dict(), epoch_path)
        print(f"[train_fasterrcnn] Saved {epoch_path}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), best_path)
            print(f"[train_fasterrcnn] New best model by val_loss: {best_path} (val_loss={val_loss:.4f})")

    print(f"\n[train_fasterrcnn] Training complete. Best val loss: {best_val_loss:.4f}")
    print(f"[train_fasterrcnn] Best model weights: {best_path}")


if __name__ == "__main__":
    main()
