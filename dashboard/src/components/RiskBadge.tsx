// src/components/RiskBadge.tsx — colored pill for a risk level, matching
// the LOW/MODERATE/HIGH semantics from analysis/risk_classifier.py.

type RiskLevel = "LOW" | "MODERATE" | "HIGH";

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk-badge risk-badge--${level.toLowerCase()}`}>{level}</span>;
}
