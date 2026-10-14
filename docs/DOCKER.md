# Running with Docker

The system is packaged as two Docker images:

| Image | What it runs | Works on |
|---|---|---|
| `oams-dashboard` | The React web dashboard, served by nginx, connected to the live Firebase project | Any OS |
| `oams-monitor` | The monitoring client (`main.py`): Faster R-CNN device detection, MediaPipe head pose and gaze, temporal analysis, risk classification, evidence capture | Any OS for recorded videos; Linux for the live webcam |

Firebase itself stays in the cloud, so it does not need a container.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine with the Compose plugin (Linux)
- About 3 GB of free disk space. The first build downloads PyTorch, MediaPipe and the COCO weights and takes several minutes.

## 1. Dashboard

```bash
docker compose up --build dashboard
```

Open <http://localhost:8080> and sign in with a dashboard account. Stop it with `Ctrl+C`.

## 2. Monitoring client on a recorded video (any OS)

Docker Desktop on Windows and macOS cannot give a container access to the webcam or open a window on the screen. In this mode the monitor replays a recorded session through the full pipeline instead: calibration starts automatically, the session clock follows the video's own timestamps, so every duration rule behaves as it does live, and the results are written to files.

1. Put a recording of a session in a `data/` folder in the project root as `data/session.mp4`. The examinee should sit facing the camera, centered, for the first several seconds so calibration can take a baseline.
2. Build and run:

   ```bash
   docker compose run --rm --build monitor-video
   ```

   To use a different file in `data/`, set `VIDEO`, e.g. `VIDEO=session03.mp4 docker compose run --rm monitor-video` (on Windows PowerShell: `$env:VIDEO="session03.mp4"; docker compose run --rm monitor-video`).

3. Results appear in `output/`:

   | File | Contents |
   |---|---|
   | `session_annotated.mp4` | The video with the live overlay drawn on every frame: risk level, pose angles, sliding-window ratios |
   | `session_report.json` | Baseline, flagged events, risk levels and triggers |
   | `pose_log.csv` | Per-frame yaw, pitch, roll, gaze and risk level |
   | `evidence/` | High Risk screenshots |

## 3. Monitoring client with a live webcam (Linux only)

On a Linux host the container can use the webcam and open the monitoring window:

```bash
xhost +local:docker
docker compose run --rm --build monitor-live
```

The exam-code and student-name prompts appear in the terminal, and the controls are the same as running `main.py` directly: SPACE starts calibration, R recalibrates, Q or ESC ends the session. If the webcam is not `/dev/video0`, change the `devices` entry in `docker-compose.yml`.

## Saving sessions to the dashboard (optional)

Without a Firebase key the monitor still runs and writes everything to `output/`; it prints a warning and skips the cloud upload. To send sessions and evidence to the dashboard, place the service account key at:

```
secrets/firebase_credentials.json
```

The `secrets/` folder is mounted into the container at run time and is listed in both `.gitignore` and `.dockerignore`, so the key is never committed or built into an image. When a key is present, the video mode can also tag the session in advance, since it does not stop for prompts:

```bash
docker compose run --rm monitor-video --source /data/session.mp4 --headless --output-dir /output --exam-code ABC123 --name "Juan Dela Cruz"
```

## The same options without Docker

The video mode is part of `main.py` itself:

```bash
py -3.11 main.py --source session.mp4 --headless --output-dir output
```

| Option | Effect |
|---|---|
| `--source VIDEO` | Read a recorded video instead of the webcam |
| `--headless` | No window or keyboard; writes an annotated video and starts calibration automatically |
| `--output-dir DIR` | Folder for the report, pose log, evidence and annotated video |
| `--exam-code CODE`, `--name NAME` | Answer the startup prompts in advance |
| `--no-db` | Run without Firebase |

Running `py -3.11 main.py` with no options is unchanged: live webcam, window, prompts.

## Notes

- **CPU only.** The image uses CPU builds of PyTorch to stay small and run on any machine; the detector falls back to CPU automatically. Faster R-CNN is slow on CPU: replaying a recording takes roughly 13 times its length (a 32-second test video took about 7 minutes), so use a short clip for a quick check. Results do not depend on speed, because replays measure every duration in video time. Live monitoring on CPU runs at a lower frame rate than on the development GPU, but all timing rules are time-based, not frame-based, so the risk classification logic is unchanged.
- **Package versions.** `requirements-lock.txt` pins the exact packages from the development environment and the image installs them as listed; the note at the top of that file explains why pip cannot resolve them on its own.
- **Rebuilding.** After changing the code, add `--build` to the command (as above) so the image is rebuilt.
- **Cleaning up.** `docker compose down` stops the dashboard; `docker image rm oams-monitor oams-dashboard` removes the images.
