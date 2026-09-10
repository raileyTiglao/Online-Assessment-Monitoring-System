# Project Status: Implementation vs. Thesis Paper

**Last updated:** 2026-08-10
**Paper reviewed:** `Thesis-Revisions-Updated.pdf` (March 2026, with tracked
changes — not confirmed to be the latest revision)

This document compares what the codebase actually does against what
*Online Assessment Monitoring with Behavioral Analysis and Object
Detection using Computer Vision Enabled Cameras* claims, and lists what
needs to change — in either the code or the paper — for the two to agree.
See `docs/logs.md` for the full change history and supporting data behind
each item below.

---

## 1. Summary

The system runs end-to-end: webcam capture, calibration, per-frame head
pose (MediaPipe + solvePnP) and gaze (iris offset) estimation, object
detection (Faster R-CNN), time-windowed behavioral aggregation, three-tier
risk classification, evidence capture, and a live dashboard (local
PHP/MySQL). That much matches the paper's Conceptual Framework at a high
level.

Underneath that, four things the paper states as fact are not currently
true of the running system, one part of the paper contradicts another
part, and several mechanisms the system actually relies on are never
mentioned at all. None of these are subtle — a live demo would surface
all four critical items within minutes.

---

## 2. Critical — code contradicts the paper

These would fail immediately in front of anyone who has read the paper
and then watches the system run.

### 2.1 The HIGH risk definition — RESOLVED 2026-08-10

**Paper (p.9):**
> "High Risk is assigned when both the presence of an unauthorized device
> and a suspicious head orientation are detected concurrently and
> persistently within the same temporal window"

**Code (as of 2026-08-10):** `analysis/risk_classifier.py` now has 2 HIGH
paths — `dual_modal` (matches the paper exactly) and `repetition` (4+
separate suspicious episodes in 20s, kept deliberately as an extension:
persistence across discontinuous episodes, same principle as the paper's
"persistently" applied to a pattern the paper's continuous-window test
can't see). The single-axis paths (`pitch_only`, `yaw_only`, `roll_only`,
`dropout_only`, `gaze_only`) and `device_immediate` were demoted — those
signals now cap at MODERATE, matching the paper. See `docs/logs.md`
2026-08-10 for the reasoning and a note in the paper is still needed to
describe `repetition` as an added third condition (not in the original
p.9 text).

### 2.2 The MODERATE definition — RESOLVED 2026-08-10

**Paper (p.9):**
> "Moderate Risk is assigned when either an unauthorized device is
> briefly detected or the examinee's head pose deviates beyond an
> acceptable threshold, but both signals do not co-occur persistently"

**Code (as of 2026-08-10):** `TemporalConfig.DEVICE_IMMEDIATE_HIGH = False`
again — a device alone now reaches only MODERATE, matching the paper. HIGH
requires dual-modal co-occurrence (or repetition, see §2.1).

### 2.3 Firebase claim vs. active backend — RESOLVED 2026-08-12

**Paper (Conceptual Framework p.10, Objectives p.12, Figure 1):**
> "This session report is transmitted in real time to a **Firebase**
> database and made accessible to the supervising professor through a
> web-based dashboard"

**Code (as of 2026-08-12):** `DatabaseConfig.BACKEND = "firebase"`. The
project (`baandod-testing`) is now on the Blaze plan, and the system is
running the Firebase stack this claim describes — Firestore for
sessions/exams/events, Firebase Storage for evidence screenshots, and the
`dashboard/` React app deployed via Firebase Hosting at
**https://baandod-testing.web.app**. The local PHP/MySQL stack
(`php_backend/`) and its supporting code remain in the repo as a working
`"local"` fallback (the `DatabaseConfig.BACKEND` switch still supports it)
but is no longer the active path.

This was a reactivation, not a rebuild: `dashboard/`, `firestore.rules`,
`storage.rules`, `firebase.json` Hosting config, and the Python-side
`connection/firebase_db.py`/`firebase_storage.py` classes already existed
from before the team diverted to PHP over the Blaze cost concern — they
were unused, not unfinished. Verified end-to-end on the live deployment
(not the emulator): admin login sees all sessions, professor login sees
only their own and is server-side denied (Firestore rules, not just UI
filtering) from loading another professor's session by direct URL, and an
evidence screenshot uploaded via the Python Storage client renders
correctly through `storage.rules`-gated `getDownloadURL()`.

One local-environment note for whoever runs the Python monitoring app on
this machine going forward: this machine's antivirus (Avast) injects an
SSL-scanning root certificate that broke both the `requests`-based Firebase
Auth calls and the gRPC-based Firestore calls until fixed. Fix applied:
`pip-system-certs` installed in `venv` (patches `requests`/`urllib3` to
trust the Windows cert store) plus `connection/grpc_ca_bundle.pem`
(certifi + the exported Avast root) referenced via a permanent
`GRPC_DEFAULT_SSL_ROOTS_FILE_PATH` user environment variable (patches
grpc's separate trust store, which `pip-system-certs` doesn't cover). Both
fixes are machine-local; a different dev machine without this antivirus
product may not need them, and one with a different antivirus doing the
same kind of SSL inspection would need `grpc_ca_bundle.pem` regenerated
with its root instead.

### 2.4 Fine-tuned model not in use

**Paper (p.8, p.10, p.12, p.22, and the Objectives on p.11):**
> "the Faster R-CNN model, **fine-tuned on the custom dataset**, performs
> per-frame binary detection of mobile devices such as **cellphones and
> tablets**"

**Code:** `DetectionConfig.CUSTOM_MODEL_PATH = None`. The system runs
**stock COCO-pretrained** Faster R-CNN, filtering for class 77 (cell
phone) only. COCO has no "tablet" class, so the "cellphones and tablets"
claim isn't supported by what's running regardless of which weights are
active.

**Why it's not wired in:** both existing fine-tuned checkpoints
(`best_model.pth`, `final_model.pth`) were evaluated on 2026-08-02 against
real evidence frames containing **no phone**, and both returned 3–4
"device" detections per frame at 0.9+ confidence — firing on the
examinee's head, torso, and shirt. COCO on the identical frames returned
zero. Wiring in either checkpoint as-is, combined with the 2026-08-09
immediate-HIGH-on-device change (§2.2), would pin every session at HIGH
permanently. Full detail in `docs/logs.md`, 2026-08-02 entry.

**Resolution — UPDATED 2026-08-11, previous diagnosis was wrong.** The
"never saw a negative example" root cause below is empirically false, and
"retrain with more negatives" is not expected to fix this on its own. See
`docs/logs.md`, 2026-08-11 entry, for the full investigation. Summary:

- `openimages_voc/train/Annotations` already has 621/2620 (24%) zero-object
  files, `val` has 110/224 (49%) — negatives were present when
  `best_model.pth`/`final_model.pth` were trained (confirmed by file
  timestamps: negatives added 07-27, checkpoints trained 07-28) and
  `VOCMobileDeviceDataset` has always loaded every `.xml` in the folder
  with no filtering, per `training/train_fasterrcnn.py`. They just didn't
  help.
- Evaluated all 10 per-epoch checkpoints (`trained_model/epochs/epoch_0.pth`
  through `epoch_9.pth`) on mAP@0.5, not just the loss-selected
  `best_model.pth`: AP@0.5 sits flat at 0.35–0.38 for every epoch, with
  precision@0.5 never exceeding ~34% and predictions outnumbering ground
  truth 6–15× at every single epoch. There is no better epoch hiding in
  this run — the failure is present from epoch 0 and does not improve with
  more training.
- Ran `best_model.pth` against this project's own real evidence frames
  (`evidence_captures/`, 15 phone-free + 1 with-phone) rather than Open
  Images val data: **15/15 phone-free frames produced a false-positive
  detection at score≥0.5** (49 boxes total, mostly 0.85–0.99 confidence,
  each covering 10–46% of the frame — head/torso-sized, not phone-sized).
  100% false-positive rate on the actual deployment domain, not the
  "3–4 detections on 2 frames" originally documented (see
  `evaluation/check_evidence_frames.py`, added for this check).

**Actual likely cause:** a domain-gap / hard-negative problem, not an
absent-negative problem. The negative images are generic Open Images
"Person" photos — stylistically different (framing, lighting, pose,
composition) from this project's actual webcam self-capture domain. The
model appears to have learned "salient person-shaped foreground region"
as the positive-class cue rather than "phone," because the negatives it
saw during training were never *hard* negatives — i.e., a person in the
same pose/framing/domain as the positive examples, just without a phone.
Simply re-running `download_negatives.py` for a larger count of the same
kind of generic Open Images negatives is unlikely to fix this; the
negatives need to come from (or closely resemble) the actual deployment
domain — e.g., webcam-style frames of a person at a desk, phone-free, in
comparable framing to the positive examples — for the model to learn the
right discriminating feature.

---

## 3. The paper contradicts itself

### 3.1 Dataset origin

The tracked-changes revision to the first Objectives bullet (p.11) says:

> "To create a custom dataset from **existing publicly available online
> images**, depicting scenarios of mobile device usage, and non-usage"

This matches the code — `training/download_openimages.py` and
`download_negatives.py` pull from Open Images, not from live recording.

But five other sections were never updated to match, and still describe
recruiting volunteers to sit in front of a webcam:

- **Conceptual Framework (p.8):** "a custom webcam image dataset
  collected by the group"
- **Scope and Delimitations (p.12):** "custom-collected webcam dataset
  consisting of scenarios with and without mobile devices"
- **Participants (p.15–16):** purposive sampling, diversity in skin
  tone/gender/facial features, informed consent forms
- **Data Collection (p.18):** participants seated at a webcam performing
  scripted scenarios (holding a device below-frame, at desk level, etc.)
- **Ethical Considerations (p.23):** "collection and processing of
  webcam images and video recordings from volunteer participants"

**Resolution:** this needs a decision, not a code fix — did data
collection actually happen with volunteers, or was the dataset built from
public images? Whichever is true, the other four sections need to be
brought in line with the Objectives revision (or the revision reverted).

---

## 4. Under-claimed — built, working, and not in the paper

None of these contradict the paper; they're real, tested mechanisms the
paper simply doesn't mention. Several of them are direct, evidenced
answers to concerns the paper itself raises in the Related Literature
section — leaving them out weakens the argument rather than simplifying it.

### 4.1 Calibration and baseline normalization (entirely absent)

Nothing in the paper describes calibration, yet every angle/gaze
threshold in the system is measured **relative to a per-examinee
baseline**, not in absolute terms. This includes:

- A 7-second baseline-capture phase before monitoring begins
- A positioning silhouette (added 2026-08-06) the examinee aligns to,
  checked against actual face position/size — not decorative
- Orientation validation (rejects calibration samples with excessive yaw
  or roll) and stability warnings (rejects a baseline built while the
  examinee was moving)
- Distance-drift detection during the session, which suppresses
  suspicion rather than risk a false positive if the examinee's
  distance from the camera changes materially after calibration

This is the system's most direct, evidenced rebuttal to the exact
criticism the paper cites from **Coghlan et al. (2021)** — that existing
proctoring systems "penalize innocent behaviors such as looking away from
the screen briefly or adjusting one's seating position." Right now that
rebuttal exists in the code but not in the methodology write-up.

### 4.2 Gaze/iris tracking

Objectives (p.11) were revised to add "eye gaze direction" to the
MediaPipe bullet, but **Scope and Delimitations (p.12) and Figure 1**
still list only yaw/pitch/roll. Gaze is fully implemented — iris offset
from eye-center, normalized to eye width, baseline-relative, with
independently-tuned horizontal/vertical thresholds and its own place in
the temporal window and risk classifier.

### 4.3 Repeated-movement detection (`RepetitionAnalyzer`)

Added 2026-08-09; not mentioned anywhere in the paper. This is now one of
the 8 HIGH-risk paths (§2.1) and is specifically the one that catches
short, repeated glances or head movements — behavior the duration-based
sliding window structurally cannot see, since each individual movement
ends before it accumulates enough time to matter. If the Behavioral
Indicators section of the paper (or the expert questionnaire, §4.5) is
meant to be exhaustive, this is a real gap, not a minor omission.

### 4.4 Other undocumented mechanisms

- **One-Euro adaptive filtering** on pose angles (replaces a flat
  exponential moving average — heavier smoothing when still, lighter when
  actually moving)
- **Direction-aware dropout handling** — lost face tracking only counts
  as suspicious if the last known pose was already trending toward
  suspicious, so simply looking away or leaning back doesn't falsely
  escalate
- **Per-level debounce** — a new risk level must hold briefly before it's
  logged/acted on, filtering boundary flicker
- **Onset-based evidence retrieval** — because escalation is
  intentionally delayed (sustained behavior, not a single frame), the
  system retrieves the buffered frame from when the flagged behavior
  actually *began*, not the frame at the moment the flag fired (which may
  already show the examinee back to normal)

### 4.5 Expert validation questionnaire may be under-scoped

Research Instruments (p.17) describes the Behavioral Indicators dimension
as assessing "sustained downward pitch, repeated lateral yaw, and their
co-occurrence with mobile device detection." The system now also
classifies on roll, gaze, tracking dropout, immediate device detection,
and repetition-based escalation — none of which the experts would have
been asked to validate if the questionnaire wording is as quoted.

---

## 5. Minor

- **Landmark count:** paper says 468 (correct for MediaPipe's default);
  the system runs with `REFINE_LANDMARKS = True`, which returns 478 —
  the extra 10 are the iris points gaze tracking depends on.
- **Video clips:** p.9 says evidence capture includes "screenshots or
  video clips"; only screenshots exist. User has indicated this will be
  revised separately — not otherwise tracked here.

---

## 6. Recommended priority order

1. **§2.1 and §2.2 first** — these are what a live demo disproves in
   seconds. Decide per-item whether the paper or the code should move,
   independently for each (they don't have to resolve the same way).
2. **§3.1** — resolve before anything downstream (Methods, Data
   Collection, Ethics) gets cited or expanded further; five sections are
   currently inconsistent with the revised objective.
3. **§2.3 and §2.4** — larger decisions (Blaze billing; retraining with
   better negatives) that likely can't be resolved before a defense, so
   the paper should describe what's actually running rather than the
   aspirational version.
4. **§4** — lower urgency since nothing here is *wrong*, only missing.
   But §4.1 (calibration) in particular strengthens the paper's own
   argument in Related Literature and costs nothing to add.
