# Project Setup — Continuing on Another PC

**Purpose:** everything needed to pick this project back up on a
different machine, since `git clone` alone does NOT bring everything —
several things are deliberately excluded from the repo (`.gitignore`)
and need separate, manual handling. Model setup is the biggest of these
— see the warning right below before anything else.

---

## Model state (resolved 2026-08-13)

`config.py`'s `CUSTOM_MODEL_PATH` is now `None` — the deployed system
runs stock COCO-pretrained weights, matching what the paper describes
(both fine-tuning attempts were evaluated and rejected for unacceptable
false-positive rates; see `JUSTIFICATION.md` #2). This was previously
out of sync (code still pointed at the rejected fine-tuned checkpoint)
but has since been fixed.

**In progress:** hard-negative mining against the rejected checkpoint
(`trained_model/selected_model_epoch2.pth`) is the next planned attempt
at improving detection accuracy — see the Recommendations section of the
paper and `JUSTIFICATION.md` #8. This is a separate training experiment
and doesn't affect what's currently deployed (`CUSTOM_MODEL_PATH` stays
`None` unless/until a new checkpoint actually passes evaluation).

---

## What transfers automatically via `git clone`

- All source code (`main.py`, `config.py`, `detection/`, `analysis/`,
  `monitoring/`, `display/`, `connection/`, `evaluation/`, `training/`
  scripts)
- `dashboard/` React source (including `dashboard/src/firebase.ts` —
  its Firebase web config is safe to commit, it's a public client
  identifier, not a secret; access control lives in `firestore.rules`/
  `storage.rules`, not in hiding this file)
- `docs/` — this file, `PAPER_EDITS_NEEDED.md`, `JUSTIFICATION.md`,
  `THESIS_FORMATTING.md`, `ToDo(08-13).md`, and anything else added here
- `firebase.json`, `.firebaserc`, `firestore.rules`, `firestore.indexes.json`,
  `storage.rules` (Firebase project config — project ID `baandod-testing`)
- `requirements.txt`

## What does NOT transfer — needs manual setup on the new PC

**1. Python environment**
- Requires **Python 3.11** specifically (confirmed via
  `venv/pyvenv.cfg`: `3.11.9`) — not a newer 3.12/3.13, matching
  `main.py`'s own run instruction (`py -3.11 main.py`)
- Requires **CUDA 12** for GPU inference (per the repo's own `read_me`
  note: "update gpu cuda to version 12") — `SystemConfig.USE_GPU = True`
  by default in `config.py`; set to `False` to force CPU if the new
  machine doesn't have a compatible GPU/driver
- Recreate the venv fresh (`venv/` itself is gitignored):
  ```
  py -3.11 -m venv venv
  venv\Scripts\pip install -r requirements.txt
  ```
- Note the pinned `protobuf==3.20.3` in `requirements.txt` — deliberately
  pinned because newer versions break `mediapipe==0.10.5`'s FaceMesh
  construction. Don't let pip resolve it to something newer.

**2. Model weight files**
- `trained_model/` (the actual `.pth` checkpoints from both fine-tuning
  attempts, including `selected_model_epoch2.pth`) is gitignored
  entirely — has to be copied over manually (USB/cloud transfer) if
  needed at all
- Given the revert-to-COCO decision, the fine-tuned checkpoint may not
  even be needed going forward except for reference/reproducibility —
  worth deciding whether to bring it to the new PC or just note its
  results are already fully captured in `JUSTIFICATION.md`
- Stock COCO weights download automatically via `torchvision` on first
  run once `CUSTOM_MODEL_PATH = None` — no manual file needed for that
  path

**3. Firebase credentials (secret — never in git)**
- `connection/firebase_credentials.json` — the Firebase Admin SDK
  service account key. Must be re-downloaded from the Firebase Console
  (Project Settings → Service Accounts) for project `baandod-testing`,
  or securely copied from this PC. Never commit this file.
- `connection/grpc_ca_bundle.pem` — explicitly a **local, machine-specific**
  TLS fix (per the `.gitignore` comment: this PC's antivirus/SSL
  scanning injects a root cert grpc's bundled trust store doesn't
  include). Don't copy this file to the new PC — regenerate it there if
  the same issue occurs, since it's specific to this machine's local
  cert situation.

**4. Training dataset**
- `openimages_voc/` is gitignored (regenerable, hundreds of MBs) —
  regenerate via the `download_openimages.py`/`download_negatives.py`/
  `merge_roboflow_negatives.py` scripts in `training/`, not by copying
  the folder, if fine-tuning work continues at all

**5. Dashboard dependencies**
- Standard `npm install` inside `dashboard/` — `node_modules/` isn't in
  git (normal, not project-specific)
- `npm run dev` uses the Firebase Local Emulator Suite (see
  `dashboard/src/firebase.ts`), started separately — check if Firebase
  CLI (`firebase emulators:start --project demo-oams`) is installed
  globally on the new PC

**6. Session-generated files**
- `session_report.json`, `evidence_captures/`, and (once used)
  `pose_log.csv` are all runtime output, not source — don't need to be
  brought over, and will only appear locally as sessions are run

---

## Cloud resources that need login, not file transfer

These aren't local files at all — they need the right Google/Firebase
account signed in on the new PC, not any copying:

- **Live thesis manuscript** — Google Doc "08.12" (the doc this entire
  editing thread has been working against)
- **Expert validation questionnaires** — the Psychologist Panel Google
  Form (reviewed/corrected in this session) and the computer vision/AI
  specialist forms (exist, not yet reviewed — see
  `PAPER_EDITS_NEEDED.md` item 9c)
- **Firebase project** `baandod-testing` — Firebase Console access for
  credentials, Firestore data, deployed hosting
  (`https://baandod-testing.web.app`)

---

## Suggested first steps on a new PC

1. `git clone` the repo
2. Read `docs/PAPER_EDITS_NEEDED.md` for outstanding manuscript edits,
   `docs/ToDo(08-13).md` for the pending evaluation-session recording
   plan, and `docs/JUSTIFICATION.md` for the reasoning behind decisions
   already made — this file plus those three should be enough to
   resume without re-deriving context
3. Decide on the `CUSTOM_MODEL_PATH` revert (see warning at the top)
   before running any session
4. Set up the Python venv (3.11) and install `requirements.txt`
5. Obtain `connection/firebase_credentials.json` separately if Firebase
   persistence (`DatabaseConfig.ENABLE_DB`) is needed
6. `npm install` in `dashboard/` if working on the dashboard
