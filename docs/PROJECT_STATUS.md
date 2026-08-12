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

### 2.3 Firebase claim vs. active backend

**Paper (Conceptual Framework p.10, Objectives p.12, Figure 1):**
> "This session report is transmitted in real time to a **Firebase**
> database and made accessible to the supervising professor through a
> web-based dashboard"

**Code:** `DatabaseConfig.BACKEND = "local"`. The active system is a
locally-hosted **PHP/MySQL** stack (`php_backend/`, served via XAMPP) —
login, role-based access (admin/professor), exam management, and a
sessions dashboard. This was built by a teammate specifically because
Firebase **Storage** (for evidence screenshots) requires the paid Blaze
plan; Firestore-only code still exists (`connection/firebase_db.py`) but
isn't what runs.

This is now a substantial, deliberately-built system in its own right —
not a stub — so it's a real design decision that needs to be reflected
accurately, not a placeholder to note in passing.

**Resolution:** update every mention of "Firebase" in the paper to
describe the local PHP/MySQL architecture, or restore
`BACKEND = "firebase"` and get the project onto Blaze before the paper is
finalized.

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

**Resolution:** the model needs retraining with more negative
(person-only, no-device) examples before it can be used — this is a data
problem, not a wiring problem. `training/download_negatives.py` exists
for this but hasn't produced a checkpoint that passes the same
false-positive check yet.

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

1. **§2.1 and §2.2 — RESOLVED 2026-08-10 (code side).** Classifier now
   matches the paper's dual-modal HIGH definition, plus `repetition` kept
   as a deliberate third condition. Still open: p.9's text itself needs a
   line added describing `repetition`, since it's not in the original
   wording — a paper-only edit, no further code change needed.
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
