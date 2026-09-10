# Scripted Recording Sessions — Detailed Protocol

**Purpose:** a precise, minute-by-minute script for each of the 10 sessions
outlined in `docs/ToDo(08-13).md`, built directly from the actual
threshold values in `config.py` — not rough behavior descriptions, but
concrete durations so each session reliably produces the risk level it's
meant to test, and so what you write down as "expected" ground truth is
grounded in the real numbers, not a guess.

---

## Reference: the actual thresholds this protocol is built on

| Signal | Per-frame flag threshold | Window | Ratio for MODERATE | Time to hold (MODERATE) | Reaches HIGH alone? |
|---|---|---|---|---|---|
| Pitch (downward) | 10° | 6.0s | 0.35 | ~2.1s | No (capped at MODERATE) |
| Yaw (sideways turn) | 32° | 6.0s | 0.50 | ~3.0s | No |
| Roll (head tilt) | 22° | 6.0s | 0.50 | ~3.0s | No |
| Dropout (lost tracking) | — | 6.0s | 0.65 | ~3.9s | No |
| Gaze (iris offset) | H:0.10 / V:0.035 (eye-widths) | 6.0s | 0.45 | ~2.7s | No |
| Device (phone visible) | — | 6.0s | 0.35 | ~2.1s | No (alone) |
| **Dual-modal** (device + any suspicious pose, together) | — | 6.0s | 0.50 | ~3.0s co-occurring | **Yes — HIGH** |
| **Repetition** (repeated brief episodes) | each episode ≥0.6s, gap ≥0.5s | 20.0s | 3 episodes = MODERATE | — | **Yes — HIGH at 4 episodes** |

Calibration takes 7 seconds once you press SPACE on the ready screen.
Every angle above is measured relative to your calibrated baseline, not
absolute camera position.

**Pre-flight checklist, every session:**
1. `config.py` → `OutputConfig.ENABLE_CONTINUOUS_POSE_LOG = True`
2. Have a stopwatch or visible clock running alongside the webcam window
   so you can jot rough timestamps as behaviors change
3. After the session ends, immediately rename `pose_log.csv` and
   `session_report.json` before starting the next one (see
   `ToDo(08-13).md` step 0 — they get overwritten otherwise)

---

## Session 1 — Baseline

**Tests:** false-positive rate. The system should read LOW the entire
time.

| Time | Action |
|---|---|
| 0:00–0:30 | Sit naturally, look at the screen as if reading |
| 0:30–1:30 | Type/read normally — small natural movements are fine, don't hold any pose deliberately |
| 1:30–2:30 | Continue normal behavior, occasionally glance at a keyboard briefly (<1s) — this should NOT trigger anything, since the whole point of the thresholds is to tolerate exactly this |
| 2:30–3:00 | Return to neutral, end session |

**Ground truth to log:** LOW, entire session, no exceptions.

---

## Session 2 — Sustained downward pitch

**Tests:** `PITCH_MODERATE_RATIO` (~2.1s to trigger).

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline, look at screen | LOW |
| 0:20–0:23 | Look down at desk, hold **3 seconds** | Should flip to MODERATE around the 2.1s mark |
| 0:23–0:35 | Return to neutral, hold 12s | Back to LOW |
| 0:35–0:38 | Look down again, hold **3 seconds** | MODERATE again |
| 0:38–0:50 | Neutral | LOW |
| 0:50–0:52 | Brief glance down, hold only **1 second** | Should NOT reach MODERATE — this is the negative control, confirming the threshold actually filters short glances |
| 0:52–2:30 | Repeat the 3s-down / 12s-neutral pattern 2–3 more times for a larger sample | Alternating LOW/MODERATE |

**Ground truth to log:** timestamp of each "look down" start/end, and
note the one deliberately-too-short glance at 0:50 as a negative control.

---

## Session 3 — Sustained lateral yaw

**Tests:** `YAW_MODERATE_RATIO` (~3.0s to trigger).

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline | LOW |
| 0:20–0:24 | Turn head to one side, hold **4 seconds** | MODERATE around the 3.0s mark |
| 0:24–0:36 | Return to center, hold 12s | LOW |
| 0:36–0:40 | Turn to the other side, hold **4 seconds** | MODERATE |
| 0:40–0:52 | Neutral | LOW |
| 0:52–0:54 | Brief head turn, only **2 seconds** | Should NOT reach MODERATE (negative control — under the ~3.0s bar) |
| 0:54–2:30 | Repeat alternating-side turns 2–3 more times | Alternating LOW/MODERATE |

**Ground truth to log:** direction and timestamp of each turn, and the
negative-control short turn at 0:52.

---

## Session 4 — Sustained head roll (tilt)

**Tests:** `ROLL_MODERATE_RATIO` (~3.0s to trigger).

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline | LOW |
| 0:20–0:24 | Tilt head sideways (ear toward shoulder), hold **4 seconds** | MODERATE |
| 0:24–0:36 | Return to level, hold 12s | LOW |
| 0:36–0:40 | Tilt to the other side, hold **4 seconds** | MODERATE |
| 0:40–0:52 | Neutral | LOW |
| 0:52–0:54 | Brief tilt, only **2 seconds** | Negative control — should stay LOW |
| 0:54–2:30 | Repeat alternating-side tilts 2–3 more times | Alternating LOW/MODERATE |

**Ground truth to log:** same pattern as Sessions 2–3.

---

## Session 5 — Gaze shift only (head stays still)

**Tests:** `GAZE_MODERATE_RATIO` (~2.7s), isolated from head movement —
the point of this session is proving gaze contributes independently of
pose.

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline, look at screen | LOW |
| 0:20–0:23 | Keep head completely still, move only your eyes off-screen (e.g., look down-left with eyes only), hold **3 seconds** | MODERATE around 2.7s |
| 0:23–0:35 | Eyes back to screen, head still unmoved | LOW |
| 0:35–0:38 | Eyes off-screen again, **3 seconds** | MODERATE |
| 0:38–2:30 | Repeat 2–3 more times, varying gaze direction | Alternating LOW/MODERATE |

**Important:** if your head visibly moves during the "gaze shift" steps,
this session doesn't isolate what it's supposed to test — the whole
point is proving the gaze signal fires independently of head pose. Keep
head motion to zero.

**Ground truth to log:** timestamp of each gaze-only shift.

---

## Session 6 — Tracking dropout

**Tests:** `DROPOUT_MODERATE_RATIO` (~3.9s).

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline | LOW |
| 0:20–0:25 | Move out of frame entirely, or fully occlude your face with a hand, hold **5 seconds** | MODERATE around 3.9s |
| 0:25–0:37 | Back in frame, normal | LOW |
| 0:37–0:42 | Occlude again, **5 seconds** | MODERATE |
| 0:42–0:54 | Normal | LOW |
| 0:54–0:56 | Brief occlusion, only **2 seconds** | Negative control — should stay LOW |
| 0:56–2:30 | Repeat 2–3 more occlusions | Alternating LOW/MODERATE |

**Note:** per `HeadPoseConfig.DROPOUT_CONTEXT_FRACTION`, whether a
dropout counts as suspicious depends on the pose direction *right
before* tracking was lost (looking down/sideways before disappearing
counts; looking up or straight ahead before disappearing doesn't). Make
sure you're facing generally forward/down right before occluding, not
tilting your head back, or the dropout may not register as suspicious at
all — that's a real, deliberate part of the system's design, not a bug,
so don't be surprised if a "look up then occlude" attempt doesn't
trigger anything.

**Ground truth to log:** timestamp of each occlusion, and your pose
direction immediately before covering your face.

---

## Session 7 — Repeated brief movements (repetition path)

**Tests:** `RepetitionConfig` — the *only* single-modality path that can
reach HIGH on its own. `MODERATE_COUNT=3`, `HIGH_COUNT=4` episodes
within a rolling 20-second window; each episode must be held ≥0.6s and
separated by ≥0.5s of normal posture.

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline | LOW |
| 0:20–0:21 | Quick glance down, ~1 second, then back to normal | Episode 1 — too short to trigger the duration-based path (Session 2), but counts toward repetition |
| 0:22–0:23 | Quick glance down again, ~1 second | Episode 2 |
| 0:24–0:25 | Quick glance down again, ~1 second | Episode 3 — MODERATE should fire here (3 episodes within 20s) |
| 0:26–0:27 | One more quick glance, ~1 second | Episode 4 — HIGH should fire here |
| 0:27–0:50 | Return to normal, stay still for the rest of the 20s window so the episode count decays | Should de-escalate back down as the window slides past the episodes |
| 0:50–2:30 | Repeat the whole 4-episode burst 1–2 more times, with a long neutral gap between bursts | Confirms repeatability |

**This is the most timing-sensitive session** — episodes need clear gaps
(≥0.5s of normal posture) or they may merge into one long episode
instead of counting separately. Exaggerate the "back to normal" moments
between glances.

**Ground truth to log:** timestamp of each individual episode, and which
one you expect to be the 3rd (MODERATE) and 4th (HIGH).

---

## Session 8 — Device visible only, pose normal

**Tests:** device detection in isolation — confirms device-alone caps at
MODERATE (`DEVICE_IMMEDIATE_HIGH = False`), never reaches HIGH without a
co-occurring pose signal.

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline, no phone visible | LOW |
| 0:20–0:23 | Hold phone clearly in frame, keep head/gaze at normal baseline, hold **3 seconds** | MODERATE around 2.1s |
| 0:23–0:35 | Put phone away, normal | LOW |
| 0:35–0:50 | Hold phone in frame continuously for 15 seconds, still keeping pose normal throughout | Should stay at MODERATE, must NOT escalate to HIGH on its own |
| 0:50–2:30 | Repeat phone-in/phone-out 2–3 more times | Alternating LOW/MODERATE, never HIGH |

**Ground truth to log:** timestamp of each phone-visible period, and
explicitly confirm it never reads HIGH no matter how long the phone
stays visible alone.

---

## Session 9 — Combined device + suspicious pose (dual-modal HIGH)

**Tests:** `HIGH_TRIGGER_RATIO` (~3.0s of co-occurrence) — the strongest,
fastest path to HIGH in the whole system.

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Baseline | LOW |
| 0:20–0:23 | Hold phone in frame AND look down at it simultaneously, hold **3 seconds** | Should escalate to MODERATE quickly (device alone crosses its own ~2.1s bar), then to **HIGH** around the 3.0s co-occurrence mark |
| 0:23–0:35 | Phone away, neutral pose | Back to LOW |
| 0:35–0:38 | Phone + downward pose together again, **3 seconds** | HIGH again |
| 0:38–0:50 | Neutral | LOW |
| 0:50–0:52 | Phone visible AND downward pose, but only **1.5 seconds** | Negative control — should reach MODERATE (device-alone bar) but NOT HIGH (under the 3.0s co-occurrence bar) |
| 0:52–2:30 | Repeat 2–3 more full dual-modal escalations | Alternating LOW/MODERATE/HIGH |

**This session directly exercises the evidence-capture onset lookup**
(`_select_evidence_frame`) — worth checking after the session that the
captured screenshot actually shows the moment the behavior *began*, not
the moment it was already over.

**Ground truth to log:** timestamp of each combined attempt, noting
which ones are full 3s+ (expect HIGH) vs. the deliberate 1.5s negative
control (expect MODERATE only).

---

## Session 10 — Edge case: distance / lighting

**Tests:** the degraded-performance conditions already acknowledged in
Limitations — increased camera distance and/or poor lighting.

| Time | Action | Expected |
|---|---|---|
| 0:00–0:20 | Normal distance/lighting, baseline | LOW |
| 0:20–0:40 | Move to increased distance from camera (far enough to trigger `SCALE_DRIFT_TOLERANCE`, ±20% face-scale change from baseline) | System should flag scale drift and suspend suspicion checks — confirm the overlay/log shows this, not a false MODERATE/HIGH |
| 0:40–1:00 | At increased distance, repeat a simple downward-pitch hold (as in Session 2), **4 seconds** | Uncertain/degraded — this is the point: document whatever actually happens, don't assume it'll behave like Session 2 |
| 1:00–1:20 | Return to normal distance, confirm normal behavior resumes | LOW, drift warning clears |
| 1:20–1:50 | Dim the room lighting substantially, repeat baseline behavior | Document whether detection quality visibly degrades (fewer/noisier landmarks, inconsistent flags) |
| 1:50–2:30 | Return to normal lighting, confirm recovery | LOW |

**Ground truth to log:** this session is exploratory by design — log
what you observe rather than a fixed expectation, since the point is
characterizing the failure mode, not confirming a known-good threshold.
This is the session most directly worth quoting in Discussion when
addressing the Limitations section's distance/lighting claims.

---

## After each session

1. Rename `pose_log.csv` → `pose_log_session##_<name>.csv` and
   `session_report.json` → `session_report##_<name>.json`
2. Write your timestamp notes into a plain text file alongside the CSV
   (e.g., `session02_groundtruth.txt`) while they're still fresh —
   don't rely on memory once you move to the next session
3. Quick sanity check: open the CSV and spot-check that `risk_level`
   actually changed where you expected — if a whole session shows flat
   LOW with no variation at all, something didn't trigger as scripted
   and it's worth re-recording that one before moving on, rather than
   discovering it during analysis later
