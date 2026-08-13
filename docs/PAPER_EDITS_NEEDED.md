# Paper edits needed: object detection objective, methodology, and findings

**For:** whoever is editing the thesis manuscript (live Google Doc "08.12")
**Status as of 2026-08-26 (checked directly against the live doc):** several
edits are already applied — see "Already done" below. What's left is listed
in "Still outstanding," with exact current wording quoted so it's a direct
find-and-fix, not a re-derivation.

**RESOLVED 2026-08-13:** `config.py`'s `DetectionConfig.CUSTOM_MODEL_PATH`
has been reverted to `None` — the deployed system now actually runs stock
COCO-pretrained weights, matching what the paper describes. (Previously
this note warned it was still pointing at the rejected fine-tuned
checkpoint; that's fixed now.)

---

## Writing style preferences (apply to ALL future drafted paper text)

- **No em dashes.** Use commas, periods, or semicolons instead.
- **Match the paper's existing diction/phrasing**, not just its meaning.
  When rewriting or drafting a passage, reuse the vocabulary and phrasing
  already established elsewhere in the manuscript rather than
  substituting different wording for the same content — even when the
  underlying facts are identical, drifting stylistically from the rest
  of the paper is undesirable.

---

## Already done (verified directly in the live doc, no action needed)

- **Objective 1** (dataset creation) — the "under varying lighting
  conditions, angles, and distances" clause has been removed. Now reads
  cleanly: "To create a custom dataset from existing publicly available
  online images, depicting scenarios of mobile device usage and
  non-usage."
- **Objective 3** (fine-tuning) — already reads: "To fine-tune and
  evaluate a Faster R-CNN model against a COCO-pretrained baseline,
  deploying whichever proves more reliable for real-time mobile device
  detection." Exactly the revised wording agreed on.
- **Conceptual Framework, device-detection sentence** — already says
  "mobile devices, specifically cellphones" (tablets dropped).
- **Firebase claim** — genuinely deployed and live at
  https://baandod-testing.web.app, no edit needed.
- **Dataset origin (Objectives/Scope)** — settled on public/compiled
  images in the sections that were already updated (Objectives). See
  "Still outstanding" below though — this isn't consistent everywhere yet.
- Manual strikethrough/highlight tracked-changes formatting has been
  cleaned up throughout the sections checked (Conceptual Framework,
  Objectives) — no leftover markup, but see below, some of that cleanup
  removed the *formatting* without fixing the underlying *wording* in a
  few spots.

---

## Still outstanding — exact current text, quoted directly from the live doc

### 1. Conceptual Framework, COCO-dataset intro paragraph

**Current:**
> "...is currently used directly for testing purposes while the custom
> dataset is prepared for fine-tuning. During system operation, a live
> webcam feed captured in real time during simulated online examination
> sessions also serves as input to the integrated monitoring pipeline."

**Fix:** remove "while the custom dataset is prepared for fine-tuning" —
> "...is currently used directly for testing purposes. During system
> operation, ..."

### 2. Conceptual Framework, Faster R-CNN description (same section, a few sentences later)

**Current:**
> "...the Faster R-CNN model, currently using stock COCO-pretrained
> weights for testing purposes, pending fine-tuning on the custom
> dataset, performs per-frame binary detection of mobile devices,
> specifically cellphones, within the webcam feed..."

**Fix:** remove ", pending fine-tuning on the custom dataset" —
> "...the Faster R-CNN model, currently using stock COCO-pretrained
> weights for testing purposes, performs per-frame binary detection of
> mobile devices, specifically cellphones, within the webcam feed..."

### 2b. NEW — found by user, another instance of the same "pending fine-tuning" claim (System Output / Outputs section)

**Current:**
> "The trained models produced include the Faster R-CNN mobile device
> detection model (currently the stock COCO-pretrained weights, pending
> fine-tuning on the custom dataset)"

Same issue as #2 above — implies fine-tuning is still upcoming when it's
actually a rejected, already-decided-against path. **Fix:** remove ",
pending fine-tuning on the custom dataset" —
> "The trained models produced include the Faster R-CNN mobile device
> detection model (currently the stock COCO-pretrained weights)"

Worth a final pass searching the whole doc for "pending fine-tuning" and
"prepared for fine-tuning" to catch any remaining instances not listed
here.

### 3. Scope and Delimitations — DONE (verified directly in the live doc 2026-08-12)

All three sub-fixes confirmed applied. Current live text: "The system
integrates a mobile device (cellphones) object detection module based on
the Faster R-CNN architecture and a behavioral analysis module utilizing
MediaPipe Face Mesh for facial landmark extraction and orientation
computation. The object detection component was fine-tuned and evaluated
against a COCO-pretrained baseline, using a custom dataset compiled from
existing publicly available online images, consisting of scenarios with
and without mobile devices under varying lighting and viewing angles."

### 4. Research Procedure → Modeling subsection — DONE (verified directly in the live doc 2026-08-12)

Replaced with the full two-attempt account (both attempts, evaluation,
rejection, deployment decision), condensed from the "Why" section below.
Live text now reads: "The Faster R-CNN model underwent two independent
fine-tuning attempts using transfer learning from COCO pre-trained
weights, each evaluated against real evidence frames captured under
actual deployment conditions. The first attempt, trained primarily on
generic stock imagery, produced false-positive detections across nearly
all phone-free evaluation frames, a result attributed to a domain
mismatch between the training images and real webcam footage. The second
attempt was retrained on a merged dataset combining object-detection
positives with domain-matched negative examples drawn from
exam-proctoring imagery; one resulting checkpoint initially eliminated
false positives on the evaluation set and was briefly deployed, but
subsequent real-world testing revealed additional false-positive cases
involving other rectangular objects and the examinee's own body at
increased camera distance. As neither fine-tuning attempt achieved a
reliable false-positive rate under real conditions, the stock
COCO-pretrained Faster R-CNN model was retained for deployment, having
measured zero false positives across all real-world evidence-frame
testing conducted."

### 5. Research Procedure → Data Preparation subsection — DONE (verified directly in the live doc 2026-08-12)

**Current:**
> "Volunteer participants were recruited and oriented on the scripted
> behavioral scenarios. Recording sessions were conducted in a controlled
> environment simulating an online examination setting, capturing webcam
> footage under varied conditions."

**Resolved 2026-08-12 — confirmed by user: no volunteers were recruited;
dataset was compiled from existing public images.** Also checked the live
doc directly and found the paragraph is longer than originally quoted
above — it continues with "Individual frames were extracted at regular
intervals, reviewed for quality, and annotated using bounding box labels
indicating the presence or absence of a mobile device. The finalized
annotated dataset was partitioned into training, validation, and testing
subsets following an 80-10-10 split ratio." The "frames extracted at
regular intervals" phrase is also a video-recording artifact and doesn't
fit the public-images story either — confirmed via repo search
(`main.py`, `evaluation/fasterrcnn_integration.py`,
`evaluation/test_on_video.py`, `training/merge_roboflow_negatives.py`)
that no stage of this project's own pipeline extracted frames from a
video to build the training/annotation dataset.

**Full replacement text for the whole paragraph** (paste over all four
existing sentences, keeping the split-ratio fact verbatim at the end):
> "Images depicting mobile device usage and non-usage scenarios were
> compiled from existing publicly available online sources. Collected
> images were screened for quality and relevance, retaining only those
> depicting clear, unobstructed views suitable for object detection
> annotation. Each retained image was annotated using bounding box
> labels indicating the presence or absence of a mobile device. The
> finalized annotated dataset was partitioned into training, validation,
> and testing subsets following an 80-10-10 split ratio."

**Keep in mind for later (deliberately not mentioned in the paper for
now, per user):** the Roboflow-sourced negatives folded in during the
second fine-tuning attempt (`online_proctoring`, `cheating_detection` —
see `training/merge_roboflow_negatives.py`) were themselves pre-extracted
from video by their original Roboflow creators before this project
downloaded them. That's a layer of provenance below "compiled from public
images" that isn't reflected in the simplified paper text above — revisit
if a reviewer asks for more sourcing detail, or if the fine-tuning
narrative (item #4/#7) ever needs to go deeper on dataset composition.

### 6. Add the tablet-gap argument to Scope and Delimitations — DONE (verified directly in the live doc 2026-08-12)

Added inside "For the delimitations," (not "For the limitations,") right
after the existing "...does not include other electronic devices such as
smartwatches, hidden earpieces, or secondary monitors." sentence — moved
there after an initial placement mistake (first pasted as a floating
paragraph between the section's overview paragraph and "For the
delimitations,", before either subsection was noticed). Confirmed correct
final position, live doc, 2026-08-12. Text used:

> Tablet detection was scoped out of the deployed system. Extending
> detection coverage to tablets required a custom-fine-tuned model, and
> two independent fine-tuning attempts during this study were evaluated
> and rejected on evidence of unacceptable false-positive rates under
> real conditions (see Methodology/Findings). In an academic-integrity
> context, this asymmetry is significant: a false positive falsely
> implicates an innocent examinee, while a false negative, involving a
> device type this system's fallback configuration cannot see, simply
> defers to existing safeguards such as human proctor review. Given this
> asymmetry, a narrower detector with zero measured false positives was
> judged the more defensible choice. This directly reflects the critique
> this study cites from Coghlan et al. (2021) regarding proctoring
> systems that penalize innocent behavior. The scope decision here is a
> deliberate application of that principle, not an oversight.

(No em dashes, per user preference — apply this to all future paper-text
suggestions too.)

### 7. Add a Recommendations / Trade-offs section — DONE (verified directly in the live doc 2026-08-13)

**Superseded placement note:** the original plan (single ad-hoc
"Recommendations" heading dropped into the blank gap before "Reference")
is moot — user has since added real placeholder headings for Results,
Discussions, Conclusions, and Recommendations after Ethical
Consideration, each currently filled with the generic guide/instruction
text copied verbatim from the wrong-program template
(`02_SOC Official Template Body.docx`, confirmed NOT the BSCS-correct
template — see chat). No sign the earlier ad-hoc paragraph was ever
pasted, so no duplication risk.

**Current placement:** replace the placeholder guide text under the real
"Recommendations," heading (the paragraph starting "In this section, you
finally have the opportunity to present and discuss the actions that
future researchers should take...") with the text below. Note for later:
once Results/Discussion have real written content, the first paragraph
below (the trade-off justification) may read better moved into
Discussion — it's explaining/justifying a decision already made, not a
forward-looking action item, which is what "Recommendations" is
specifically defined as in the template guide text it's replacing. Left
as one block in Recommendations for now since Discussion isn't written
yet either.

Text (em dashes already removed, per user preference):

> "The decision to deploy COCO-pretrained weights rather than a
> custom-fine-tuned model reflects a deliberate trade-off between
> detection scope and reliability. A fine-tuned model, if successful,
> would additionally detect tablets, a category outside COCO's
> vocabulary, but two independent fine-tuning attempts during this study
> were evaluated and rejected due to unacceptable false-positive rates
> under real deployment conditions (see Methodology/Findings). The
> COCO-pretrained configuration was selected because it demonstrated zero
> false positives across all real-world evidence-frame testing conducted,
> at the cost of tablet-class detection.
>
> Future work on this system should prioritize hard-negative mining over
> further manual curation of training data: rather than anticipating
> specific confounding objects, the recommended approach is to run the
> current best-performing checkpoint against a large, diverse pool of
> real webcam-domain imagery, treat every false-positive prediction as a
> new training negative, and retrain on the resulting set. This was
> identified as the most promising direction during this study but was
> not pursued further within its time constraints."

**Addendum 2026-08-13:** this recommendation was actually given a
preliminary test (`training/mine_hard_negatives.py`, 32 hard negatives
found out of 13,768 checked, 0.2% FP rate) — result judged informative
but not sufficient to act on yet, so no paper-text change needed; the
manuscript's framing above is still accurate. Full writeup in
`JUSTIFICATION.md` #9.

### 8. Lean into "simulated/controlled study" framing + pre-commit to a fixed N for outstanding Results work — PENDING (2026-08-13)

Full data-collection plan (session scripts, per-session steps, analysis
steps) moved to a dedicated file: `docs/ToDo(08-13).md`. This section
tracks only the paper-text side.

**Text fix — DONE, verified directly in the live doc 2026-08-13.** Now
reads: "...to characterize the distribution of head orientations
recorded during controlled recording sessions simulating an online
examination setting." No other sentence in Data Analysis needed
touching — the risk-classification sentence right after already said
"behavioral scenarios," not "examination sessions," so it didn't
overclaim.

**N commitment — not yet decided/written.** Recommended: 10 scripted
sessions, one per distinct signal path the system implements (baseline,
yaw, pitch, roll, dropout, gaze, repetition, device-only, dual-modal
combo, edge case). Explicitly NOT a statistical-power number — it's a
coverage argument (one scripted scenario per threshold path), confirmed
with user this isn't a methodological standard, just this analysis's own
reasoning. Adjustable down if time is tight (see `ToDo(08-13).md` for
which sessions are safest to cut first). Once the actual number of
sessions recorded is known, that count needs to be written into Data
Analysis or Research Procedure as a concrete fact (e.g., "N sessions were
recorded, each containing a scripted behavioral scenario") — currently
nowhere in the live doc.

**Code prerequisite — DONE.** `ENABLE_CONTINUOUS_POSE_LOG` per-frame CSV
logging added (`monitoring/pose_log.py`, wired into `main.py` and
`config.py`) so sessions can actually produce analyzable data. See
`ToDo(08-13).md` for how to use it.

### 9. Expert-validation questionnaire — manuscript text + actual Google Form both need fixes (2026-08-13)

**9a. Manuscript text (Research Instruments, Behavioral Indicators
dimension) — fix drafted, not yet pasted into the live doc.** Live
wording (checked 2026-08-13) already includes gaze but still misses
roll, dropout, and repetition:
> "...specifically sustained downward pitch, repeated lateral yaw, gaze
> deviation from the examinee's calibrated baseline, and their
> co-occurrence, are valid and justifiable indicators..."

**Fix:** select `specifically sustained downward pitch, repeated lateral
yaw, gaze deviation from the examinee's calibrated baseline, and their
co-occurrence` and replace with `specifically sustained downward pitch,
repeated lateral yaw, sustained head roll, gaze deviation from the
examinee's calibrated baseline, tracking dropout, repeated brief
suspicious movements, and their co-occurrence`.

**9b. The actual Psychologist Panel Google Form — fixes drafted, not
yet pasted in (form not yet sent, so no response-validity risk).**
Checked the live form directly (separate Google Forms tab from the
manuscript doc) against `config.py`/`risk_classifier.py` and found real
threshold drift, not just outdated scope:
- Pitch threshold: form said 20°, actual `PITCH_THRESHOLD = 10°` (not
  rounding — a real 2x mismatch)
- Yaw/roll thresholds: form said 30°/20°, actual 32°/22° (minor rounding)
- Observation window: form said 3.5 seconds throughout (glossary, B10,
  B11), actual `TemporalConfig.WINDOW_SECONDS = 6.0` — code comment
  confirms this was "widened from 3.5s," so the form reflects a stale,
  pre-retune config
- Confirmed correct and unchanged: calibration "~7 seconds" (matches
  `CalibrationConfig.DURATION_SECONDS = 7.0`), E3 "screenshot only on
  HIGH" (confirmed in `evidence_capture.py:88`), E4 "5-second cooldown"
  (matches), E6 (matches paper), B12/B13 dual-modal and repetition logic
  (both confirmed accurate against `risk_classifier.py`)

Rather than just correcting the numbers, B7–B11 were reframed (with
user's approval) to ask the psychologist to judge the *design approach*
(requiring sustained rather than momentary behavior, tolerating brief
interruptions) instead of asking them to bless exact degree/second
values — a judgment more within psychological expertise than validating
specific calibration numbers. Full reframed text for B7–B11 is in the
chat transcript 2026-08-13; user still needs to paste it into the actual
Google Form. The glossary's "3.5-second" references (term definition +
the 30%-example, recalculated to 1.8s at the corrected 6-second window)
still need the numeric fix even after the B10/B11 reframe, since the
glossary is standalone reference context.

**9c. Computer vision specialist and AI specialist questionnaires exist
but were NOT reviewed** — user confirmed they exist but doesn't currently
have access to them. Given what turned up in the psychologist form
(stale thresholds from an earlier config iteration), the other two are
worth the same check once accessible: do their claimed numbers/scope
match current `config.py`/`risk_classifier.py`, and do their claimed
dimensions-per-specialist match what Research Instruments' text actually
promises (System Design and Architecture + Risk Classification Logic +
Dataset Design and Representativeness, per the manuscript's five-dimension
breakdown — the psychologist form only ever covered Behavioral Indicators
+ Ethical Soundness, so these three remaining dimensions should be
covered somewhere in the other two forms).

---

## Why (full version, both fine-tuning attempts — for use in #4 and #7 above)

**First attempt** (`training/train_fasterrcnn.py`, checkpoints in
`trained_model/`, trained 2026-07-28): evaluated against 16 of this
project's own real evidence frames (15 phone-free, 1 with-phone). All 15
phone-free frames triggered a false detection at 0.85–0.99 confidence,
with boxes the size of a head or torso rather than a phone. Root cause
diagnosed as domain mismatch — the negative training images were generic
stock photos, not webcam-style frames like this system actually sees.

**Second attempt** (2026-08-12, `training/merge_roboflow_negatives.py`):
retrained on a merged dataset (Open Images phone+tablet positives +
Roboflow exam-proctoring domain-matched negatives, 7,874 training images).
All 10 epochs were evaluated by mAP@0.5 and against the same 16 real
evidence frames. Epoch 2 uniquely passed — 0/15 false positives, correct
true-phone detection — while every other epoch still produced 9–15/15
false positives. Epoch 2 was deployed live and initially appeared to
work, but live real-world testing then surfaced three further
false-positive modes the 16-frame test didn't catch: other rectangular
objects (a door, a credit card), and the examinee's own head/body at
increased camera distance — indicating the model had learned features
correlated with "mobile device" (foreground salience, rectangular
geometry, apparent object scale) rather than the object itself.

Stock COCO has measured **zero** false positives across all real-world
testing conducted, including live sessions, and is more reliable than
either fine-tuned attempt produced — the basis for the deployment
decision and every objective/methodology revision above. (Again: this is
the *decision*, not yet the *deployed state* — see the IMPORTANT note at
the top.)

---

## What's NOT being done (on purpose, for now)

Hard-negative mining (§7 above) was scoped but not executed — real,
bounded additional work with no guarantee of convergence before defense,
given the pattern of new failure modes surfacing under each round of
real-world testing so far. Stays a recommended next step, not a blocker.

## Still outstanding, not a text edit — blocks writing the Results chapter

- Head pose descriptive statistics + threshold-accuracy data (needs real
  recorded sessions; current pipeline only logs *flagged* events, not
  continuous pose data)
- Risk classification accuracy data (needs scripted scenarios + ground
  truth labels + confusion matrix)

These are the real remaining bottleneck — everything above is
writing/editing work on material that already exists.
