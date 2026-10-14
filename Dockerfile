# =============================================================================
# Monitoring client — Online Assessment Monitoring System
# Holy Angel University — School of Computing
#
# Packages main.py (Faster R-CNN + MediaPipe pipeline) with Python 3.11.
# See docs/DOCKER.md for how to build and run it.
# =============================================================================
FROM python:3.11-slim

# libgl1 and libglib2.0-0 are required by OpenCV and MediaPipe even without a
# display; the X11 libraries are only used by the live window on Linux hosts.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    TORCH_HOME=/opt/torch \
    OAMS_FIREBASE_CREDENTIALS=/secrets/firebase_credentials.json

WORKDIR /app

# CPU-only PyTorch first, so the image stays ~2 GB instead of ~8 GB with
# CUDA. object_detector.py falls back to CPU when no GPU is available. The
# second install then finds torch/torchvision already satisfied and keeps
# the protobuf==3.20.3 pin that mediapipe 0.10.5 needs.
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.1.2 torchvision==0.16.2 \
        --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# Download the deployed COCO weights at build time, so the container runs
# without internet access.
RUN python -c "from torchvision.models.detection import fasterrcnn_resnet50_fpn_v2, FasterRCNN_ResNet50_FPN_V2_Weights as W; fasterrcnn_resnet50_fpn_v2(weights=W.DEFAULT)"

COPY . .

# Default: replay /data/session.mp4 headlessly into /output. docker-compose.yml
# overrides these arguments for the other modes.
ENTRYPOINT ["python", "main.py"]
CMD ["--source", "/data/session.mp4", "--headless", "--output-dir", "/output"]
