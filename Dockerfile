# =============================================================================
# Monitoring client — Online Assessment Monitoring System
# Holy Angel University — School of Computing
#
# Packages main.py (Faster R-CNN + MediaPipe pipeline) with Python 3.11.
# See docs/DOCKER.md for how to build and run it.
# =============================================================================
FROM python:3.11-slim

# libgl1 and libglib2.0-0 are required by OpenCV and MediaPipe even without a
# display, and libportaudio2 by mediapipe's sounddevice dependency; the X11
# libraries are only used by the live window on Linux hosts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libportaudio2 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    TORCH_HOME=/opt/torch \
    OAMS_FIREBASE_CREDENTIALS=/secrets/firebase_credentials.json

WORKDIR /app

# Exact package versions from the development venv, installed as listed
# (--no-deps) because pip's resolver rejects the protobuf 3.20.3 pin that
# mediapipe needs; see the note at the top of requirements-lock.txt.
# PyTorch is the CPU build of the same version, so the image stays ~2 GB
# instead of ~8 GB; object_detector.py falls back to CPU automatically.
COPY requirements-lock.txt .
RUN pip install --no-cache-dir --no-deps torch==2.1.2 torchvision==0.16.2 \
        --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --no-deps -r requirements-lock.txt \
 && python -c "import cv2, mediapipe, torch, torchvision, firebase_admin; from google.cloud import firestore, storage; print('imports ok')"

# Download the deployed COCO weights at build time, so the container runs
# without internet access.
RUN python -c "from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2, FasterRCNN_ResNet50_FPN_V2_Weights as W; fasterrcnn_resnet50_fpn_v2(weights=W.DEFAULT)"

COPY . .

# Default: replay /data/session.mp4 headlessly into /output. docker-compose.yml
# overrides these arguments for the other modes.
ENTRYPOINT ["python", "main.py"]
CMD ["--source", "/data/session.mp4", "--headless", "--output-dir", "/output"]
