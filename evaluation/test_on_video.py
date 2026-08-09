"""
=============================================================================
test_on_video.py — Headless video test for CustomMobileDeviceDetector
Online Assessment Monitoring System
Holy Angel University — School of Computing

Same detector as fasterrcnn_integration.py, but writes an annotated output
video instead of cv2.imshow — useful for running without a display attached
(e.g. over SSH, or from a script) and for keeping a reviewable result file.

Usage (main project venv):
    venv\\Scripts\\python.exe test_on_video.py <video_file> [--model PATH] [--out PATH]
=============================================================================
"""

import argparse
import time
from pathlib import Path

import cv2

from fasterrcnn_integration import CustomMobileDeviceDetector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("--model", type=Path, default=Path("trained_model/final_model.pth"))
    parser.add_argument("--out", type=Path, default=None,
                         help="Output annotated video path (default: <video>_annotated.mp4)")
    parser.add_argument("--confidence", type=float, default=0.5)
    args = parser.parse_args()

    out_path = args.out or args.video.with_name(args.video.stem + "_annotated.mp4")

    detector = CustomMobileDeviceDetector(str(args.model), confidence_threshold=args.confidence)

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise SystemExit(f"[ERROR] Cannot open video: {args.video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    print(f"\n[test_on_video] {args.video.name}: {width}x{height} @ {fps:.1f}fps, {total_frames} frames")
    print(f"[test_on_video] Writing annotated output to: {out_path}\n")

    frame_count = 0
    detection_count = 0
    all_scores = []
    start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        detected, boxes, scores = detector.detect(frame)
        if detected:
            detection_count += 1
            all_scores.extend(scores)

        display_frame = detector.visualize(frame, detected, boxes, scores)
        cv2.putText(display_frame, f"Frame: {frame_count} | Detections: {detection_count}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        writer.write(display_frame)

        if frame_count % 50 == 0:
            elapsed = time.time() - start
            print(f"  [{frame_count}/{total_frames}] {elapsed:.1f}s elapsed, "
                  f"{frame_count / elapsed:.1f} fps processing")

    cap.release()
    writer.release()

    elapsed = time.time() - start
    print(f"\n[Summary]")
    print(f"Total frames: {frame_count}")
    print(f"Frames with a detection: {detection_count}")
    if frame_count > 0:
        print(f"Detection rate: {detection_count / frame_count * 100:.1f}%")
    if all_scores:
        print(f"Confidence: min={min(all_scores):.2f} max={max(all_scores):.2f} "
              f"avg={sum(all_scores) / len(all_scores):.2f}")
    print(f"Processed in {elapsed:.1f}s ({frame_count / elapsed:.1f} fps)")
    print(f"Annotated video saved to: {out_path}")


if __name__ == "__main__":
    main()
