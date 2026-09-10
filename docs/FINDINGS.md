# Findings Log — Issues Discovered During Scripted Evaluation Sessions

**Purpose:** a running log of bugs or design flaws actually discovered
while recording the sessions in `docs/SCRIPTED_SESSIONS.md`, and the
fixes applied. Distinct from `docs/JUSTIFICATION.md` (which documents
reasoning behind decisions already made) — this file is specifically
for things the live testing itself caught that weren't known before
recording started. Worth keeping updated through the remaining sessions;
this kind of finding is also legitimate Discussion-chapter material —
it's direct evidence the evaluation methodology actually works, not
just a formality.

---

## Finding #1 — Yaw rotation falsely triggered distance-drift suppression, hiding the exact behavior it should catch

**Discovered:** during Session 3 (sustained lateral yaw) recording,
2026-08-15. Turning the head to either side was not escalating to
MODERATE as scripted — the system was reading it as the examinee having
moved farther from the camera instead.

### Root cause

`HeadPoseNormalizer` uses "scale" — the 2D pixel distance between the
two eye corners — as a proxy for distance-to-camera
(`analysis/head_pose_normalizer.py`, `_compute_scale_ratio`). If that
measurement changes by more than `CalibrationConfig.SCALE_DRIFT_TOLERANCE`
(20%) from the calibration baseline, the system treats it as the
examinee having moved and **suppresses all suspicion checks** for that
frame, on the reasoning that the baseline angles are no longer trustworthy
at a different distance.

The problem: inter-eye pixel distance doesn't only shrink when someone
moves farther away — it also shrinks when the head rotates in yaw, purely
from perspective foreshortening, at a completely constant physical
distance. A face turned 30-40° from the camera measures shorter eye-to-eye
in 2D than the same face photographed straight-on, even standing in
exactly the same spot.

`YAW_THRESHOLD` (the angle needed to flag yaw as suspicious in the first
place) is 32°. At that same rotation, the foreshortening effect on the
eye-corner measurement was large enough to also cross the 20%
distance-drift tolerance. The result: a yaw turn large enough to be
genuinely suspicious was, by the same motion, large enough to trip the
drift-suppression path — which then suppressed the yaw suspicion it
should have raised. The two thresholds were fighting each other, and
drift-suppression was winning every time, because in this pipeline
distance-drift is checked and applied *before* the pose thresholds are
evaluated (see the original `normalize()` ordering).

This is not a rare edge case — it's the expected outcome of turning to
look at something to the side, i.e. exactly the behavior this axis exists
to detect. Every yaw-suspicious frame was structurally at risk of also
reading as "moved away," making the loophole close to guaranteed rather
than occasional.

### Fix

`analysis/head_pose_normalizer.py`:
- `_compute_scale_ratio()` now takes the current baseline-relative yaw
  deviation and divides the raw scale by `cos(yaw_deviation)` before
  comparing it to the baseline — this estimates what the inter-eye
  distance would measure if the face were still pointed at the camera,
  removing the rotation artifact from the distance signal. A floor
  (`max(..., 0.3)`) guards against the correction blowing up or flipping
  sign at extreme angles.
- `normalize()` was reordered so `n_yaw` (needed for the correction) is
  computed *before* the scale/drift check that now depends on it,
  instead of after.

Genuine distance changes are unaffected by this fix — when someone
actually moves closer/farther without much yaw, `n_yaw` stays near
baseline, the correction factor is ~1.0, and the original drift-detection
behavior is preserved exactly as before.

### Verification

Session 3 was re-recorded after the fix. Before: yaw turns failed to
escalate at all — the drift-suppression path swallowed them. After: 9
clean MODERATE episodes (~4–4.6s each, consistent with the ~3.0s
`YAW_MODERATE_RATIO` trigger point), zero HIGH (correct — single-axis
should cap at MODERATE), no drift-suppression interference. Full data in
`pose_log_session03_yaw.csv`.

### Why this matters beyond just fixing the bug

This is a real example of the evaluation methodology doing its job — a
flaw that wasn't visible from reading the code or the config values in
isolation, only surfaced once an actual person performed the actual
scripted behavior and the result didn't match what the threshold math
predicted. Worth citing directly in Discussion as evidence the scripted
evaluation sessions found something design review alone didn't, rather
than treating the sessions as just a formality to produce numbers for
Results.

---

## Finding #2 — Brief MODERATE blips during Session 6 (dropout) traced to the repetition path, not a bug

**Discovered:** during Session 6 recording, 2026-08-16. A few MODERATE
episodes were much shorter (0.4–1.4s) than the ~3.9s
`DROPOUT_MODERATE_RATIO` threshold should require, and — more
suspiciously — `dropout_suspicious` stayed `True` continuously through
the entire blip with no flag change, which shouldn't produce a
mid-streak drop back to LOW if MODERATE were being driven by the
dropout axis ratio alone. Reproduced identically on a second, independent
recording, ruling out a one-off execution fluke.

### Investigation

Replayed the exact logged timestamp/flag sequences through the real
`TemporalAnalyzer` and `RepetitionAnalyzer` classes directly (not a
reimplementation — the actual production code, with `time.time()`
monkey-patched to inject the historical timestamps). Confirmed:
- `dropout_ratio` alone never exceeded ~0.40 in the relevant window —
  nowhere near the 0.65 needed to trigger MODERATE via the dropout axis
  rule.
- `RepetitionAnalyzer.episode_count` reached exactly 3
  (`RepetitionConfig.MODERATE_COUNT`) at the exact same timestamp
  MODERATE fired live, and dropped back to 2 at the exact timestamp risk
  fell back to LOW (the oldest of the 3 episodes aging out of the
  20-second repetition window).

### Conclusion — not a bug

Session 6 scripts repeated occlusions roughly 13–17 seconds apart, which
is close enough together that 3 separate dropout episodes stack up
within `RepetitionConfig.WINDOW_SECONDS` (20s) — triggering MODERATE via
the **repetition path** (`repetition_moderate`), independent of whether
any single occlusion held long enough to cross the dropout-specific
sustained-duration threshold. `RepetitionAnalyzer` tracks the *blended*
`suspicious` flag, which includes dropout among the signals it counts —
so repeated dropouts are exactly as valid a "repeated glance" pattern as
repeated head turns, by design (see the module's own docstring: "furtive
checking returns to the same place again and again").

This means Session 6, scripted purely to test sustained dropout, also
incidentally exercises the repetition mechanism (Session 7's intended
target) as a side effect of how closely the occlusions were spaced. Not
a flaw in either session's data — worth noting in Discussion if Session
6 and Session 7's results end up correlated, since they aren't fully
independent tests of separate mechanisms in this specific recording.

---

## Finding #3 — Distance-drift suppression creates a real detection blind spot, not just a false-positive guard

**Discovered:** during Session 10 (edge case: distance/lighting)
recording, 2026-08-16, second take. A scripted downward-pitch hold
attempted while at increased camera distance produced no MODERATE
escalation at all — not degraded, not delayed, simply never evaluated.

### Investigation

`pose_log.csv` doesn't log `scale_ratio`/`drifted` directly, so
suppression had to be confirmed indirectly: scanning for frames where
normalized pitch/yaw/roll clearly exceeded their thresholds yet the
corresponding `*_suspicious` flag stayed `False`. Found a suppressed
window from ~73.9s to ~89.1s, during which pitch climbed to a sustained
22–24° (more than double the 10° threshold, held over a second) with
`pitch_suspicious` remaining `False` throughout — confirming
`SCALE_DRIFT_TOLERANCE` (still at its original 0.20) had correctly
triggered, and the pitch-hold attempt happened to land inside that same
window. A second downward-pitch hold performed later (120.295–149.979s),
after distance had returned to normal, correctly triggered MODERATE as
expected.

### Conclusion — working as designed, but the design has a real cost

This isn't a bug — `HeadPoseNormalizer` explicitly suppresses all
suspicion checks while drifted, by design, specifically to avoid false
positives from unreliable angle estimates at an unverified distance (see
`docs/JUSTIFICATION.md` #2 and the yaw-foreshortening fix in Finding #1
for the same underlying mechanism). But this session demonstrates the
cost of that trade-off directly: genuine suspicious behavior performed
while drifted is not degraded or delayed, it is **not evaluated at
all**. A student who moves far enough from the camera to trigger
drift-suppression is, for as long as that condition holds, effectively
unmonitored on the pose axis — not a theoretical edge case, but something
this session's own data now demonstrates happening in practice.

### Why this matters beyond this one session

This sharpens what's already written in Limitations about degraded
performance under extreme conditions — the accurate framing isn't
"detection gets worse at distance," it's "detection stops entirely at
distance, by deliberate design choice, to avoid a worse failure mode
(false accusations from unreliable estimates)." That's a stronger,
more specific claim, and it's now backed by real recorded data rather
than a general acknowledgment. Worth citing directly alongside Finding
#1 as a second example of the drift-suppression mechanism's trade-offs —
one that causes false negatives (this finding) and one that used to
cause false negatives on a different axis via yaw-foreshortening before
the Finding #1 fix.
