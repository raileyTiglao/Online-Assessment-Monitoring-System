# Corrections to dataset-handoff-notes.md

**Read this alongside `dataset-handoff-notes.md` before acting on it —
not a replacement, a set of corrections to specific sections.** Written
2026-08-11 after independently investigating the same failure mode that
document's Section 2 diagnoses. Full evidence in `docs/PROJECT_STATUS.md`
§2.4 and `docs/logs.md`'s 2026-08-11 entry.

---

## §2 "Known failure mode" — the stated root cause is wrong

> "the training distribution almost certainly lacked sufficient negative
> examples... provenance/training-data unknown"

Provenance is known, and it isn't that. Checked directly:

- `openimages_voc/train/Annotations`: 621/2620 (24%) already zero-object.
  `val`: 110/224 (49%) already zero-object. File timestamps confirm the
  negatives existed a full day *before* `best_model.pth`/`final_model.pth`
  were trained (07-27 vs 07-28), and `VOCMobileDeviceDataset` has never
  filtered zero-object annotations out — they were in the training set.
- Evaluated all 10 individual epoch checkpoints from that run by mAP@0.5,
  not just the loss-selected one: every epoch lands in the same 0.35–0.38
  band. No epoch escapes the failure; it's present from epoch 0.

**So §4's ranking ("negative example ratio... single biggest lever") is
also wrong as stated.** A new Roboflow dataset with a better ratio,
sourced the same generic way (stock photos), is likely to reproduce the
identical failure — the existing dataset's ratio was already reasonable
and didn't help.

**What the evidence actually points to:** domain mismatch. The negatives
are generic Open Images "Person" photos — different framing, lighting,
composition from this project's actual webcam self-capture domain. The
model most likely learned "salient person-shaped foreground region" as
its cue rather than "phone," because nothing in training taught it that
a person-without-phone *in this specific domain* is background.

---

## §4 priority order — flip it

Current: ratio first, label cleanliness second, domain implicitly last
(mentioned only in the §5 checklist's final bullet).

**Recommended: domain match first.** A dataset with a clean single
`phone` class and a good ratio, but composed of generic/stock photos, is
not established to fix this — the failing checkpoints already had both a
plausible ratio and (per the classifier's confidently-wrong behavior) no
obvious label noise. What's untested is whether *domain-matched*
negatives fix it. §6's third bullet already names the right source —
see below.

---

## §6 "Sourcing negative examples" — promote the third bullet, don't bury it

> "our own evidence-capture frames from live sessions that are confirmed
> phone-free (ties directly back to the exact failure mode we're
> correcting for)"

This is the one most likely to actually work, per the domain-match
finding above — it's listed as one of three options under a ratio-first
framing. Recommend making webcam-domain negatives the *primary* source
for this retrain attempt, with the Roboflow/COCO-person sources as
supplementary bulk, not the other way around. If more phone-free webcam
frames are needed beyond what `evidence_captures/` already has, that's a
capture task, not a download task — and worth weighing against the
capture-vs-public-images tension already open in `PROJECT_STATUS.md` §3.1
before generating a lot of new footage.

---

## §10 "Open question" — answered, this is no longer a blocker

> "Do the original 2026-08-02 no-phone evidence frames still exist
> somewhere reusable... does a fresh no-phone validation set need to be
> collected before the regression test can run?"

Yes, they exist: `evidence_captures/` at the repo root, 16 frames total,
15 confirmed phone-free by direct visual inspection (the 16th has a real
phone, useful as a true-positive sanity check). No fresh collection
needed to *run* the regression test — only if more volume is wanted for
training data itself (see §6 above).

**The regression test in §9 has already been run** against
`best_model.pth`, at the actual production threshold
(`CONFIDENCE_THRESHOLD = 0.6`, not the 0.5 used in an earlier pass):

```
15/15 phone-free frames produced >=1 false-positive detection at score>=0.6
42 total false-positive boxes, mostly 0.85-0.99 confidence
```

`evaluation/check_evidence_frames.py` (new file, added 2026-08-11) is a
ready-to-run version of §9's script — same acceptance bar (zero false
positives at 0.6), reusable against whatever checkpoint this plan
produces:

```
venv\Scripts\python.exe evaluation\check_evidence_frames.py --model <new checkpoint> --score-thresh 0.6
```

---

## §1 "Current system state" — stale config snapshot

```python
DETECTION_INPUT_WIDTH = 480   # WRONG — actual current value is None
```

This knob was found to be a complete no-op and removed in the 2026-08-09
fix (`docs/logs.md`). The actual current resize controls, missing from
this section entirely:

```python
DETECTION_MIN_SIZE = 600
DETECTION_MAX_SIZE = 1000
```

Also `TARGET_CLASS_NAMES = {77: " Mobile Devices"}` currently (note the
stray leading space — separate minor bug, not urgent), not
`{77: "Cell Phone"}` as written. `CONFIDENCE_THRESHOLD = 0.6`,
`CUSTOM_MODEL_PATH = None`, `CUSTOM_NUM_CLASSES = 2` are all correct as
written.

---

## What's still fine as-is

The §5 Roboflow verification checklist, the §7 COCO merge script, and the
§8 training loop are technically sound and don't need rework — only the
*emphasis* (what negatives to prioritize sourcing) needs to change before
spending time on them.
