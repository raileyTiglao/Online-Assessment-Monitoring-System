"""
=============================================================================
threshold_sensitivity.py — Offline Threshold Sensitivity Analysis
Online Assessment Monitoring System
Holy Angel University — School of Computing

Answers one question for the defense: is the risk classifier fragile to
the EXACT threshold values chosen, or does it hold up under a reasonable
margin around them? Re-runs classification against recorded sessions with
each parameter group nudged +-15%/+-20%, one group at a time, and reports
where results move a lot versus where they barely move.

READ-ONLY BY DESIGN: never writes to config.py. Threshold values are
monkey-patched onto the live config classes for the duration of one
replay run (see `scaled_group()`), then restored immediately after — the
analysis operates on parameters swapped in at eval time; the shipped
system is untouched.

=============================================================================
BEFORE TRUSTING THE OUTPUT OF THIS SCRIPT, READ THIS:
=============================================================================
  - There was NO existing labeled ground-truth behavioral test set or
    scoring harness in this repo before this script. evaluation/eval_map.py
    scores the OBJECT DETECTOR (phone bounding boxes vs. Pascal VOC
    annotations) — a completely different evaluation, for a completely
    different component. This script is new, not a re-run of something
    that already existed.

  - "Ground truth" here means the scenario label YOU assigned live via
    the 0-9 hotkeys (monitoring/research_logger.py) while performing a
    scripted behavior yourself, mapped to an intended risk level via
    EXPECTED_RISK below. That is self-scripted pilot data from your own
    team, not an independent/blind researcher-labeled dataset — describe
    it that way in the writeup, not as "researcher-assigned ground-truth
    labels," which implies a level of independence this doesn't have.

  - This script reads research_logs/*.csv. If that directory is empty —
    which it is until someone actually runs main.py with
    ResearchLoggingConfig.ENABLED = True and performs scripted scenarios
    on camera — there is nothing to analyze. This script cannot
    manufacture that data; it can only be built ahead of time, which is
    what this is.

  - "mAP" does not apply here. mAP is an object-detection (bounding-box
    IoU) metric — meaningless for a 3-class (LOW/MODERATE/HIGH) decision.
    This reports precision/recall/F1 per class instead.

  - The DROPOUT axis is replayed using the dropout_suspicious flag AS
    RECORDED at capture time, NOT rescaled under the head_pose group.
    Rescaling it properly needs the raw pre-dropout pose history and a
    "was a face even detected this frame" flag — the current CSV schema
    doesn't capture the latter. Flagged here rather than silently
    approximated as if it were exact.

=============================================================================
PARAMETER GROUPS (varied one at a time — classic one-variable-at-a-time
sensitivity sweep; each group scaled together since that's how they're
used together in practice, not because they're assumed independent):
=============================================================================
  head_pose : HeadPoseConfig.YAW_THRESHOLD / PITCH_THRESHOLD / ROLL_THRESHOLD
  gaze      : GazeConfig.GAZE_H_THRESHOLD / GAZE_V_THRESHOLD
  temporal  : TemporalConfig.MODERATE_TRIGGER_RATIO, HIGH_TRIGGER_RATIO
              (dual-modal), and the five per-axis *_MODERATE_RATIO values.
              PITCH_HIGH_RATIO/YAW_HIGH_RATIO/ROLL_HIGH_RATIO/
              DROPOUT_HIGH_RATIO/GAZE_HIGH_RATIO are NOT included — those
              became dead config on 2026-08-10 when per-axis HIGH paths
              were demoted to MODERATE-only (see risk_classifier.py); the
              classifier never reads them, so scaling them would be a
              no-op dressed up as a result.

Usage:
    python evaluation/threshold_sensitivity.py
    python evaluation/threshold_sensitivity.py --file research_logs/sess_xxx.csv
=============================================================================
"""

import argparse
import csv
import glob
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from config import HeadPoseConfig, GazeConfig, TemporalConfig
from analysis.head_pose_normalizer import HeadPoseNormalizer
from analysis.temporal import TemporalAnalyzer
from analysis.repetition import RepetitionAnalyzer
from analysis.risk_classifier import RiskClassifier

from analyze_research_log import EXPECTED_RISK  # same mapping, one source of truth

LEVELS = ["LOW", "MODERATE", "HIGH"]

PARAM_GROUPS = {
    "head_pose": {
        "config_class": HeadPoseConfig,
        "attrs": ["YAW_THRESHOLD", "PITCH_THRESHOLD", "ROLL_THRESHOLD"],
    },
    "gaze": {
        "config_class": GazeConfig,
        "attrs": ["GAZE_H_THRESHOLD", "GAZE_V_THRESHOLD"],
    },
    "temporal": {
        "config_class": TemporalConfig,
        "attrs": [
            "MODERATE_TRIGGER_RATIO", "HIGH_TRIGGER_RATIO",
            "PITCH_MODERATE_RATIO", "YAW_MODERATE_RATIO",
            "ROLL_MODERATE_RATIO", "DROPOUT_MODERATE_RATIO",
            "GAZE_MODERATE_RATIO",
        ],
    },
}

PCT_STEPS = [-20, -15, 0, 15, 20]


@contextmanager
def scaled_group(group_name: str, pct: float):
    """
    Temporarily scale every attr in a parameter group by (1 + pct/100),
    yield, then restore the originals unconditionally — this is the
    read-only guarantee. Ratios are clamped to (0.01, 1.0] since a ratio
    outside that range is not a meaningful sliding-window threshold;
    angle/offset thresholds are clamped to a small positive floor.
    """
    group = PARAM_GROUPS[group_name]
    cls = group["config_class"]
    originals = {attr: getattr(cls, attr) for attr in group["attrs"]}
    try:
        mult = 1 + pct / 100.0
        for attr, orig in originals.items():
            new_val = orig * mult
            if "RATIO" in attr:
                new_val = min(max(new_val, 0.01), 1.0)
            else:
                new_val = max(new_val, 0.1)
            setattr(cls, attr, round(new_val, 5))
        yield
    finally:
        for attr, orig in originals.items():
            setattr(cls, attr, orig)


def _b(s: str) -> bool:
    return s == "True"


def load_sessions(paths):
    """Group rows by source file (one sliding window per session — windows
    must not bleed across separate recordings) and sort each by timestamp."""
    sessions = {}
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows.sort(key=lambda r: float(r["timestamp"]))
        sessions[Path(path).name] = rows
    return sessions


def replay_session(rows):
    """
    Re-run one session's recorded frames through fresh analyzer/classifier
    instances under whatever config is currently patched in. Returns
    parallel (y_true, y_pred) lists for frames whose scenario has a mapped
    expected level.
    """
    temporal = TemporalAnalyzer()
    repetition = RepetitionAnalyzer()
    classifier = RiskClassifier()

    y_true, y_pred = [], []

    for row in rows:
        ts = float(row["timestamp"])
        norm_yaw, norm_pitch, norm_roll = (
            float(row["norm_yaw"]), float(row["norm_pitch"]), float(row["norm_roll"]))
        gaze_x, gaze_y = float(row["gaze_x"]), float(row["gaze_y"])
        gaze_valid = _b(row["gaze_valid"])
        device_detected = _b(row["device_detected"])

        yaw_susp, pitch_susp, roll_susp, _ = HeadPoseNormalizer._analyse(
            norm_yaw, norm_pitch, norm_roll)
        gaze_susp = False
        if gaze_valid:
            gaze_susp, _ = HeadPoseNormalizer._analyse_gaze(gaze_x, gaze_y)
        # Dropout: frozen at capture time — see module docstring caveat.
        dropout_susp = _b(row["dropout_suspicious"])

        temporal.update(device_detected, yaw_suspicious=yaw_susp,
                         pitch_suspicious=pitch_susp, roll_suspicious=roll_susp,
                         dropout_suspicious=dropout_susp, gaze_suspicious=gaze_susp,
                         timestamp=ts)
        snapshot = temporal.get_snapshot()

        blended = yaw_susp or pitch_susp or roll_susp or gaze_susp or dropout_susp
        repetition.update(blended, timestamp=ts)
        rep_count = repetition.episode_count_at(ts)

        result = classifier.classify(snapshot, rep_count)

        scenario = row["scenario"]
        if scenario in EXPECTED_RISK:
            y_true.append(EXPECTED_RISK[scenario])
            y_pred.append(result.level)

    return y_true, y_pred


def prf1(y_true, y_pred):
    """Per-class precision/recall/F1 (macro-averaged) from parallel label lists."""
    per_class = {}
    for lvl in LEVELS:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lvl and p == lvl)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lvl and p == lvl)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lvl and p != lvl)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) else 0.0)
        per_class[lvl] = (precision, recall, f1)

    macro_p = sum(v[0] for v in per_class.values()) / len(LEVELS)
    macro_r = sum(v[1] for v in per_class.values()) / len(LEVELS)
    macro_f1 = sum(v[2] for v in per_class.values()) / len(LEVELS)
    accuracy = (sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
                if y_true else 0.0)
    return per_class, (macro_p, macro_r, macro_f1), accuracy


def run_variant(sessions, group_name=None, pct=0):
    """Replay every session under one scaled (or baseline) config, pool results."""
    def _run():
        y_true, y_pred = [], []
        for rows in sessions.values():
            t, p = replay_session(rows)
            y_true.extend(t)
            y_pred.extend(p)
        return y_true, y_pred

    if group_name is None:
        y_true, y_pred = _run()
    else:
        with scaled_group(group_name, pct):
            y_true, y_pred = _run()

    return prf1(y_true, y_pred), len(y_true)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", action="append",
                         help="Specific CSV(s) to analyze. Defaults to all of research_logs/*.csv")
    args = parser.parse_args()

    paths = args.file or sorted(glob.glob("research_logs/*.csv"))
    if not paths:
        print("No research log CSVs found in research_logs/. This script needs "
              "at least one recorded session (ResearchLoggingConfig.ENABLED = "
              "True, scripted scenarios tagged via 0-9 hotkeys) before it can "
              "report anything. See docs/OBJECT_DETECTION_NEXT_STEPS.md's "
              "sibling doc for the research-logging workflow, or main.py.")
        return

    sessions = load_sessions(paths)
    n_frames = sum(len(r) for r in sessions.values())
    print(f"Loaded {len(sessions)} session(s), {n_frames} total frames: "
          f"{list(sessions.keys())}")

    unscored = {s for rows in sessions.values() for s in
                {r["scenario"] for r in rows} if s not in EXPECTED_RISK}
    if unscored:
        print(f"(Scenario labels with no EXPECTED_RISK mapping are excluded "
              f"from scoring: {sorted(unscored)})")

    (baseline_pc, baseline_macro, baseline_acc), n = run_variant(sessions)
    if n == 0:
        print("\nNo frames matched a scenario in EXPECTED_RISK — nothing to score. "
              "Check that scenario labels used during recording match EXPECTED_RISK "
              "keys in analyze_research_log.py.")
        return

    print("\n" + "=" * 92)
    print("BASELINE (current config.py, unmodified)")
    print("=" * 92)
    print(f"n={n} scored frames | accuracy={baseline_acc:.1%} | "
          f"macro P/R/F1 = {baseline_macro[0]:.2f} / {baseline_macro[1]:.2f} / {baseline_macro[2]:.2f}")
    for lvl in LEVELS:
        p, r, f1 = baseline_pc[lvl]
        print(f"  {lvl:<10} precision={p:.2f}  recall={r:.2f}  F1={f1:.2f}")

    print("\n" + "=" * 92)
    print("SENSITIVITY SWEEP — one parameter group at a time")
    print("=" * 92)
    header = f"{'group':<12}{'%change':>9}  {'accuracy':>9}  {'macroF1':>9}  " \
             f"{'d_acc':>8}  {'d_F1':>8}  flag"
    print(header)
    print("-" * len(header))

    # Flag any swing more than this many percentage points from baseline as
    # disproportionate — i.e. a +-15/20% threshold nudge shouldn't be able to
    # swing accuracy or F1 by more than this for the system to be considered
    # robust. Adjust if your committee wants a stricter/looser bar.
    FLAG_THRESHOLD = 0.10

    results = []
    for group_name in PARAM_GROUPS:
        for pct in PCT_STEPS:
            if pct == 0:
                # Baseline already computed above — reuse rather than rerun.
                pc, macro, acc = baseline_pc, baseline_macro, baseline_acc
            else:
                (pc, macro, acc), _ = run_variant(sessions, group_name, pct)

            d_acc = acc - baseline_acc
            d_f1 = macro[2] - baseline_macro[2]
            flag = "<<<" if (abs(d_acc) > FLAG_THRESHOLD or abs(d_f1) > FLAG_THRESHOLD) else ""
            print(f"{group_name:<12}{pct:>+8}%  {acc:>9.1%}  {macro[2]:>9.2f}  "
                  f"{d_acc:>+8.1%}  {d_f1:>+8.2f}  {flag}")
            results.append((group_name, pct, acc, macro[2], d_acc, d_f1))

    flagged = [r for r in results if abs(r[4]) > FLAG_THRESHOLD or abs(r[5]) > FLAG_THRESHOLD]
    print("\n" + "=" * 92)
    if flagged:
        print(f"FLAGGED — disproportionate swing (>±{FLAG_THRESHOLD:.0%}) from a "
              f"threshold nudge within +-20%:")
        for group_name, pct, acc, f1, d_acc, d_f1 in flagged:
            print(f"  {group_name} at {pct:+d}%: accuracy {d_acc:+.1%}, F1 {d_f1:+.2f}")
    else:
        print("No parameter group produced a swing beyond the flagged threshold "
              "within +-20% — supports a claim that the system is not highly "
              "sensitive to the exact threshold values chosen, within that range.")


if __name__ == "__main__":
    main()
