# Online Assessment Monitoring System

**Online Assessment Monitoring with Behavioral Analysis and Object Detection using Computer Vision Enabled Cameras**
Holy Angel University, School of Computing (BS Computer Science thesis)

A decision-support tool for online examinations. It combines mobile device detection with head pose and gaze tracking to flag potentially suspicious examinee behavior for a human proctor's review:

- **Object detection:** Faster R-CNN (COCO-pretrained) detects smartphones in the webcam feed.
- **Behavioral analysis:** MediaPipe Face Mesh with solvePnP estimates yaw, pitch and roll, and iris landmarks give gaze direction, all measured against a 7-second per-examinee calibration baseline.
- **Temporal analysis:** a 6-second sliding window and a 20-second repetition window separate sustained or repeated behavior from brief glances.
- **Risk classification:** Low, Moderate, or High. High requires a device together with suspicious head pose, or repeated suspicious episodes.
- **Evidence and reporting:** High Risk events capture the frame where the behavior began; sessions and evidence go to a Firebase-backed web dashboard for the supervising professor.

The system's outputs are advisory. They indicate behavior that warrants review and do not determine misconduct on their own.

## Running it

**With Docker (recommended):** see [docs/DOCKER.md](docs/DOCKER.md).

```bash
docker compose up --build dashboard
```

```bash
docker compose run --rm --build monitor-video
```

**Without Docker:** Python 3.11; see [docs/PROJECT_SETUP.md](docs/PROJECT_SETUP.md).

```bash
py -3.11 -m venv venv
venv\Scripts\pip install -r requirements.txt
py -3.11 main.py
```

## Project layout

| Folder | Contents |
|---|---|
| `main.py`, `config.py`, `clock.py` | Entry point, all thresholds and settings, session time source |
| `detection/` | Faster R-CNN detector and MediaPipe head pose / gaze estimator |
| `analysis/` | Calibration, pose normalization, temporal and repetition analysis, risk classification |
| `monitoring/` | Evidence capture, frame buffer, session report, pose log |
| `display/` | On-screen overlay |
| `connection/` | Firebase client, Firestore and Storage access |
| `dashboard/` | React + Vite web dashboard |
| `evaluation/`, `training/` | Model evaluation and fine-tuning scripts |
| `docs/` | Setup, Docker, and design notes |

## Authors

Arthur Christian M. David, Yvanne D. Gubguban, Marvin Jay C. Nilayan, Railey G. Tiglao
Adviser: Mr. Wilson D. Concepcion
