"""
=============================================================================
analyze_research_log.py — Chapter 3 Data Analysis for research_logs/*.csv
Online Assessment Monitoring System
Holy Angel University — School of Computing

Consumes the continuous per-frame CSVs written by
monitoring/research_logger.py (one row per processed frame, tagged with
whichever scenario label was active — see ResearchLoggingConfig in
config.py) and produces the two things Chapter 3 needs:

  1. Descriptive pose statistics per scenario — mean/stdev of normalized
     yaw/pitch/roll/gaze, justifying the calibration approach and the
     threshold values chosen (Head Pose Estimation Module, "how to
     interpret").
  2. A confusion matrix of intended scenario vs. system-assigned risk
     level, plus a trigger_type breakdown per scenario — showing per-frame
     classifier accuracy AND which HIGH/MODERATE path (dual_modal,
     repetition, per-axis, ...) is doing the work for each scenario
     (Temporal Analysis / Risk Classification Module, "how to interpret").

EXPECTED_RISK below maps each scripted scenario to the risk level a
researcher intends it to represent — edit it to match whatever scenarios
were actually scripted in a given data-collection session; unmapped
scenario labels are reported but skipped in the confusion matrix rather
than guessed at.

Usage:
    python evaluation/analyze_research_log.py
        (defaults to every CSV in research_logs/)
    python evaluation/analyze_research_log.py --file research_logs/sess_xxx.csv
=============================================================================
"""

import argparse
import csv
import glob
import statistics
from collections import defaultdict
from pathlib import Path

# Edit this to match the scenarios actually scripted for a session — must
# agree with ResearchLoggingConfig.SCENARIO_LABELS in config.py, but only
# needs entries for labels you want scored in the confusion matrix.
#
# Matches risk_classifier.py as of 2026-08-10: single-axis signals (pitch/
# yaw/roll/dropout/gaze alone) and device-alone all cap at MODERATE now —
# only dual_modal (device + pose together) and repetition (4+ episodes in
# 20s) reach HIGH. Corrected 2026-08-12 — this previously still mapped the
# single-axis scenarios to HIGH from before that demotion, which would
# have scored 6 of 9 scenarios as "wrong" for no real reason.
EXPECTED_RISK = {
    "normal":              "LOW",
    "sustained_downward":  "MODERATE",
    "sustained_sideways":  "MODERATE",
    "sustained_tilt":      "MODERATE",
    "device_visible":      "MODERATE",
    "device_and_pose":     "HIGH",
    "repeated_glances":    "HIGH",
    "tracking_dropout":    "MODERATE",
    "gaze_offscreen":      "MODERATE",
}

LEVELS = ["LOW", "MODERATE", "HIGH"]


def load_rows(paths):
    rows = []
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            rows.extend(csv.DictReader(f))
    return rows


def print_pose_stats(rows):
    print("\n" + "=" * 78)
    print("1. POSE DISTRIBUTION PER SCENARIO (normalized, baseline-relative)")
    print("=" * 78)

    by_scenario = defaultdict(list)
    for r in rows:
        by_scenario[r["scenario"]].append(r)

    header = f"{'scenario':<22}{'n':>6}  " \
             f"{'yaw mean/sd':>16}  {'pitch mean/sd':>16}  {'roll mean/sd':>16}"
    print(header)
    print("-" * len(header))
    for scenario, srows in sorted(by_scenario.items()):
        yaw   = [float(r["norm_yaw"])   for r in srows]
        pitch = [float(r["norm_pitch"]) for r in srows]
        roll  = [float(r["norm_roll"])  for r in srows]
        def fmt(vals):
            if len(vals) < 2:
                return f"{statistics.mean(vals):6.1f} / n/a"
            return f"{statistics.mean(vals):6.1f} / {statistics.stdev(vals):5.1f}"
        print(f"{scenario:<22}{len(srows):>6}  "
              f"{fmt(yaw):>16}  {fmt(pitch):>16}  {fmt(roll):>16}")


def print_confusion_matrix(rows):
    print("\n" + "=" * 78)
    print("2. CONFUSION MATRIX — intended scenario vs. system-assigned risk level")
    print("=" * 78)

    scored = [r for r in rows if r["scenario"] in EXPECTED_RISK]
    skipped = {r["scenario"] for r in rows if r["scenario"] not in EXPECTED_RISK}
    if skipped:
        print(f"(Skipping unmapped scenario labels — add them to EXPECTED_RISK "
              f"in this script if they should be scored: {sorted(skipped)})")

    by_scenario = defaultdict(list)
    for r in scored:
        by_scenario[r["scenario"]].append(r["risk_level"])

    header = f"{'scenario':<22}{'expected':>10}  " + \
             "  ".join(f"{lvl:>9}" for lvl in LEVELS) + f"  {'accuracy':>9}"
    print(header)
    print("-" * len(header))

    total_correct, total_n = 0, 0
    for scenario, levels in sorted(by_scenario.items()):
        expected = EXPECTED_RISK[scenario]
        counts = {lvl: levels.count(lvl) for lvl in LEVELS}
        n = len(levels)
        correct = counts[expected]
        total_correct += correct
        total_n += n
        pct = "  ".join(f"{counts[lvl]:>9}" for lvl in LEVELS)
        print(f"{scenario:<22}{expected:>10}  {pct}  {correct/n:>8.0%}")

    if total_n:
        print("-" * len(header))
        print(f"{'OVERALL':<22}{'':<10}  {'':<9}  {'':<9}  {'':<9}  "
              f"{total_correct/total_n:>8.0%}  ({total_correct}/{total_n} frames)")
    print("\nNote: this scores PER-FRAME accuracy against the sliding window's\n"
          "intended level. A scenario is expected to spend its first few\n"
          "seconds at LOW while the window fills/sustains — that's expected\n"
          "startup lag, not misclassification. Consider also reporting\n"
          "steady-state accuracy (last N seconds of each scenario) alongside\n"
          "this raw number.")


def print_trigger_breakdown(rows):
    print("\n" + "=" * 78)
    print("3. TRIGGER-TYPE BREAKDOWN PER SCENARIO (which path fired, HIGH/MODERATE only)")
    print("=" * 78)

    by_scenario = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["risk_level"] in ("MODERATE", "HIGH"):
            by_scenario[r["scenario"]][r["trigger_type"]] += 1

    for scenario, triggers in sorted(by_scenario.items()):
        total = sum(triggers.values())
        parts = ", ".join(f"{t}={c} ({c/total:.0%})"
                           for t, c in sorted(triggers.items(), key=lambda kv: -kv[1]))
        print(f"{scenario:<22}{parts}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append",
                         help="Specific CSV(s) to analyze. Defaults to all "
                              "of research_logs/*.csv")
    args = parser.parse_args()

    paths = args.file or sorted(glob.glob("research_logs/*.csv"))
    if not paths:
        print("No research log CSVs found. Run a session with "
              "ResearchLoggingConfig.ENABLED = True first, or pass --file.")
        return

    print(f"Analyzing {len(paths)} file(s): {[Path(p).name for p in paths]}")
    rows = load_rows(paths)
    if not rows:
        print("Files found but contained no rows.")
        return

    print_pose_stats(rows)
    print_confusion_matrix(rows)
    print_trigger_breakdown(rows)


if __name__ == "__main__":
    main()
