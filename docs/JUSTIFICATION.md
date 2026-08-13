# Justification Log

**Purpose:** a record of what changed in the manuscript and codebase over
the last 24 hours, and — more importantly — the reasoning behind the
bigger decisions, so this can be referenced later (adviser questions,
panel defense, or just remembering "why did we do this" in a month).

---

## Summary of what was accomplished (last 24 hours)

**Manuscript (live Google Doc "08.12"):**
- Removed several instances of misleading "pending fine-tuning" /
  "prepared for fine-tuning" language across the Conceptual Framework,
  Scope and Delimitations, and System Output sections
- Rewrote the Scope and Delimitations paragraph: dropped tablets from the
  device-type claim, updated the fine-tuning claim to reflect what
  actually happened, dropped an unsupported "distances" claim from the
  dataset conditions list
- Rewrote the Modeling subsection (Research Procedure) to describe both
  fine-tuning attempts, their evaluation, rejection, and the deployment
  decision, instead of stating fine-tuning as an accomplished fact
- Rewrote the Data Preparation subsection to describe the dataset as
  compiled from existing public images, replacing an incorrect account
  of recruiting volunteers for recording sessions
- Added a new paragraph to Scope and Delimitations ("For the
  delimitations") justifying why tablet detection was scoped out
- Added Results, Discussions, Conclusions, and Recommendations chapter
  placeholders, and wrote real content into Recommendations (the
  COCO-vs-fine-tuned trade-off, plus a hard-negative-mining
  recommendation for future work)
- Fixed a wording overclaim in Data Analysis ("simulated examination
  sessions" implied a real exam took place; corrected to "controlled
  recording sessions simulating an online examination setting")
- Corrected the Behavioral Indicators dimension description (Research
  Instruments) to include roll, dropout, and repetition — signals the
  system already classifies on that the description had omitted (fix
  drafted, not yet pasted in)

**The actual expert-validation Google Form (Psychologist Panel):**
- Found and corrected stale numeric thresholds that no longer matched
  the deployed system's config (pitch threshold, observation window)
- Reframed five threshold-specific questions (B7–B11) to ask about the
  reasonableness of the design approach rather than asking a
  psychologist to validate exact degree/second calibration values
  outside their domain expertise

**Codebase:**
- Added `monitoring/pose_log.py` (`ContinuousPoseLog`) — opt-in
  per-frame CSV logging of pose/risk data, needed because the existing
  session report only logs already-flagged events, not the continuous
  data needed for descriptive statistics and threshold-accuracy analysis
- Wired the new logger into `main.py` and `config.py`
  (`ENABLE_CONTINUOUS_POSE_LOG`, off by default)

**Planning:**
- Reviewed the official SOC thesis templates (`Desktop\Thesis\Template`)
  and identified that two of the nine files are for the wrong program
  (BS IT – Web Development, not BS Computer Science) — ruled out
  "Statistical Treatment of Data" and "Trade-off" as required standalone
  sections for this thesis, confirmed "Ethical Consideration" is required
  and already adequately written
- Wrote `docs/ToDo(08-13).md` — a concrete plan for the still-outstanding
  data collection (10 scripted recording sessions) needed to produce the
  Results chapter's head-pose and risk-classification numbers

---

## Justification for the bigger changes

### 1. Tablet detection removed from scope

**What changed:** the paper now explicitly states tablet detection was
scoped out, with a dedicated justification paragraph in Scope and
Delimitations, plus a trade-off explanation in Recommendations.

**Why:** stock COCO-pretrained weights (the model actually deployed)
have no tablet class, only a phone/cell phone class. Reaching tablets
would have required a successful custom fine-tune. Two independent
fine-tuning attempts were made during this study and both were rejected
on evidence of unacceptable false-positive rates under real conditions
(see "Both fine-tuning attempts" below). Rather than silently drop
tablets or leave the gap unexplained, the paper now argues the choice
directly: in an academic-integrity context, a false positive falsely
implicates an innocent examinee, while a false negative on a device type
the fallback configuration cannot see simply defers to existing
safeguards like human proctor review. That asymmetry is what makes a
narrower, zero-false-positive detector the more defensible choice, not
an oversight.

### 2. Reverted from a custom-fine-tuned model to stock COCO-pretrained weights

**What changed:** the deployed detector uses stock COCO weights, not a
fine-tuned model, and the paper now describes this as a deliberate,
evidence-based decision rather than treating fine-tuning as an
accomplished fact.

**Why — both fine-tuning attempts, in full:**

*First attempt* (`training/train_fasterrcnn.py`): evaluated against 16
of this project's own real evidence frames (15 phone-free, 1
with-phone). All 15 phone-free frames triggered a false detection at
0.85–0.99 confidence, with boxes the size of a head or torso rather than
a phone. Root cause: domain mismatch — the negative training images were
generic stock photos, not webcam-style frames like this system actually
sees.

*Second attempt* (`training/merge_roboflow_negatives.py`): retrained on
a merged dataset (Open Images phone/tablet positives + Roboflow
exam-proctoring domain-matched negatives, 7,874 training images). Epoch
2 uniquely passed the same 16-frame test (0/15 false positives) and was
briefly deployed live — but live testing then surfaced further
false-positive modes the 16-frame test hadn't caught: other rectangular
objects (a door, a credit card), and the examinee's own head/body at
increased camera distance. This indicated the model had learned features
correlated with "mobile device" in general (foreground salience,
rectangular geometry, apparent scale) rather than the object itself.

Stock COCO measured **zero** false positives across all real-world
testing conducted, including live sessions — more reliable than either
fine-tuned attempt produced. That's the evidentiary basis for the
deployment decision, and for every downstream objective/methodology
revision built on top of it.

### 3. Dataset origin story corrected: public images, not volunteer recording sessions

**What changed:** Data Preparation no longer describes recruiting
volunteers and running scripted recording sessions; it describes
compiling and screening existing public images instead.

**Why:** no volunteers were ever recruited for this study. The original
text was aspirational/leftover from an earlier plan that didn't happen,
and it directly contradicted the "existing publicly available online
images" language already correct elsewhere (Objectives, Scope and
Delimitations). A thesis manuscript has to describe what was actually
done, not what was originally planned — this was a factual correction,
not a stylistic one.

### 4. Removed "pending fine-tuning" / "prepared for fine-tuning" language throughout

**What changed:** multiple instances of language implying fine-tuning
was still upcoming/not-yet-done were removed from the Conceptual
Framework, Scope and Delimitations, and System Output sections.

**Why:** this phrasing was misleading in the opposite direction from
issue #2 above — it implied fine-tuning simply hadn't happened yet
(future work), when in fact it had been attempted twice and deliberately
rejected. "Pending" and "not yet done" describe an open question; what
actually happened is a closed, evidence-based decision. Leaving this
language in would have undersold the actual methodological work done
during the study.

### 5. Reworded "simulated examination sessions" to avoid overclaiming

**What changed:** Data Analysis's description of the head-pose
evaluation data source no longer says "examination sessions."

**Why:** no actual examination (real test-taking) has occurred or will
occur as part of this evaluation — only scripted solo behavior
recordings under webcam, performed by the researcher. "Examination
sessions" implies more fidelity to a real exam context than what
actually happens. The corrected wording ("controlled recording sessions
simulating an online examination setting") keeps the honest framing
already established elsewhere in the paper (Scope and Delimitations:
"Behavioral scenarios are simulated and scripted rather than naturally
occurring") without claiming something that isn't true.

### 6. Added continuous per-frame pose logging to the codebase

**What changed:** a new opt-in logging path (`ContinuousPoseLog`) was
added, off by default, alongside the existing flagged-event session
report.

**Why:** Data Analysis already promises descriptive statistics on head
orientation distributions and threshold-accuracy data, but the existing
`SessionReport` only logs moments that already crossed into
MODERATE/HIGH risk. Computing a distribution or an accuracy rate
requires every frame's data, not just the frames that were already
flagged. Without this change, there was no way to actually produce the
data the paper already claims will exist.

### 7. Corrected the psychologist validation Google Form's thresholds, and reframed the threshold questions

**What changed:** numeric threshold claims in the form (pitch angle,
observation window duration) were corrected to match the deployed
system's actual config, and five questions (B7–B11) were reworded to ask
about the reasonableness of the design approach rather than asking the
reviewer to bless an exact number.

**Why:** the form's numbers had drifted out of sync with the system —
the pitch threshold in particular was off by 2x (form said 20°, system
uses 10°), and the observation window was stated as 3.5 seconds when the
system's own code comments confirm it was later "widened" to 6.0
seconds. Beyond the numeric drift, asking a psychologist to validate an
*exact* calibration value was arguably outside their domain regardless
of accuracy — construct validity ("is sustained downward head tilt a
meaningful signal of attention shift?") is squarely within psychological
expertise; "is 10° specifically correct, rather than 8° or 12°?" is
closer to an engineering tuning judgment. The reframe asks for the kind
of judgment a psychologist can actually make: whether requiring
*sustained* rather than *momentary* behavior, and tolerating brief
interruptions within that, is a psychologically reasonable way to define
suspicious behavior — without asking them to co-sign a specific number
they have no real basis to evaluate.

### 8. The 10-session evaluation plan is a coverage argument, not a statistical standard

**What changed:** a concrete plan for 10 scripted recording sessions was
drafted (`docs/ToDo(08-13).md`) to produce the still-missing Results
chapter data.

**Why this number, specifically:** it is **not** based on any
statistical-power calculation or methodological convention — there
isn't one that applies here, since this is a single-subject scripted
functional validation, not a population study aiming for statistical
generalization. The number 10 comes from counting the distinct
behavioral signal paths the system actually implements (yaw, pitch,
roll, dropout, gaze, repetition, device-only, dual-modal combination,
plus a baseline and an edge case) and assigning one scripted session to
each, so Results can demonstrate the threshold logic works across every
path the system implements, not just one. This is stated plainly so it
can be defended honestly if questioned: it's a coverage argument, and
it's adjustable (fewer sessions is a legitimate trade-off under time
pressure, not a violation of some required minimum).

### 9. Preliminary hard-negative mining attempted 2026-08-13 — informative, not sufficient, not deployed

**What happened:** `training/mine_hard_negatives.py` was built to
actually test the Recommendations section's own suggestion — run epoch 2
(the rejected checkpoint) against real webcam-domain imagery it hadn't
seen, and treat every false positive as a new hard negative. The pool
used was the raw Roboflow frames (`online_proctoring`,
`cheating_detection`) that `merge_roboflow_negatives.py` had capped per
source clip and never actually included in training — already on disk,
no new recording needed.

**Result:** 13,768 unused true-negative frames checked, 32 hard
negatives found (0.2% false-positive rate). `cheating_detection`
contributed nothing — all of it was already used in training.

**Why this doesn't change the deployment decision:** this mining pool is
still the same two Roboflow domains epoch 2 was partly trained on
already — more of the *same kind* of footage, not the specific
confounders that broke epoch 2 in live testing (a door, a credit card,
the examinee's own body at increased distance — see item #2 above).
Those aren't likely to appear incidentally in exam-proctoring footage.
32 additional negatives out of roughly 10,540 total training images is
also a small addition, unlikely to shift model behavior meaningfully on
its own.

**Decision:** treat this as informative but not sufficient, for now. The
32 hard negatives were NOT merged into `openimages_voc/train`, no
retrain was run, and `config.py` stays at `CUSTOM_MODEL_PATH = None`
(stock COCO deployed). Hard-negative mining remains accurately described
in the paper as a promising but not-yet-completed direction — this
preliminary pass didn't change that; it mainly narrowed down what kind
of data would actually be needed to make the direction worth pursuing
further (footage containing the actual known confounders, not just more
of the same domain-matched negatives already partly used).
