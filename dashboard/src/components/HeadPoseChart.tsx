// src/components/HeadPoseChart.tsx — yaw/pitch/roll across a session's
// flagged events.
//
// Data reality: the app only logs a pose reading at each flagged
// (MODERATE/HIGH) event (monitoring/session_report.py's FlaggedEvent) —
// there's no continuous per-frame trace. So each point here IS a flagged
// event; there's nothing to overlay separately. Linear (not smoothed)
// interpolation between them, since a curve-fit would imply a continuity
// the data doesn't have — these are real, sparse readings, not a dense
// signal. Dots stay visible (not decorative) for the same reason: every
// point is a real, individually meaningful sample.
//
// Form: one axis (yaw/pitch/roll share the same unit, degrees — never
// split across two y-axes), three named categorical series (identity) →
// multi-line chart. Colors: categorical slots 1/2/3 (blue/orange/aqua) —
// the only three-slot grouping validated all-pairs in both light and dark
// (dataviz skill, references/palette.md). Dot fill by risk level uses the
// fixed status colors (warning/critical), reserved and never reused as a
// series color, so risk state and pose identity read as two distinct
// channels rather than colliding.

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import type { FlaggedEvent } from "../hooks/useSessions";

interface HeadPoseChartProps {
  events: FlaggedEvent[];
}

function statusColor(risk: "MODERATE" | "HIGH"): string {
  return risk === "HIGH" ? "var(--status-critical)" : "var(--status-warning)";
}

function EventDot(props: {
  cx?: number; cy?: number; payload?: FlaggedEvent;
}) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  return (
    <circle cx={cx} cy={cy} r={4} fill={statusColor(payload.risk_level)}
            stroke="var(--surface-1)" strokeWidth={2} />
  );
}

export function HeadPoseChart({ events }: HeadPoseChartProps) {
  if (events.length === 0) {
    return <p className="empty-state">No flagged events — nothing to chart.</p>;
  }

  return (
    <div className="head-pose-chart">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={events} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="0" stroke="var(--gridline)" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={(t: string) => new Date(t).toLocaleTimeString()}
            stroke="var(--muted)"
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
          />
          <YAxis
            unit="°"
            stroke="var(--muted)"
            tick={{ fill: "var(--muted)", fontSize: 12 }}
            axisLine={{ stroke: "var(--baseline)" }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: "var(--surface-1)",
              border: "1px solid var(--border)",
              borderRadius: 6,
            }}
            labelFormatter={(t) => new Date(String(t)).toLocaleTimeString()}
            labelStyle={{ color: "var(--text-primary)" }}
          />
          <Legend wrapperStyle={{ color: "var(--text-secondary)", fontSize: 13 }} />

          <Line type="linear" dataKey="yaw" name="Yaw" stroke="var(--series-1)"
                strokeWidth={2} dot={<EventDot />} activeDot={{ r: 6 }} />
          <Line type="linear" dataKey="pitch" name="Pitch" stroke="var(--series-2)"
                strokeWidth={2} dot={<EventDot />} activeDot={{ r: 6 }} />
          <Line type="linear" dataKey="roll" name="Roll" stroke="var(--series-3)"
                strokeWidth={2} dot={<EventDot />} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
      <p className="head-pose-chart__note">
        Each point is a flagged event, colored by risk level —{" "}
        <span style={{ color: "var(--status-warning)" }}>●</span> MODERATE,{" "}
        <span style={{ color: "var(--status-critical)" }}>●</span> HIGH.
      </p>
    </div>
  );
}
