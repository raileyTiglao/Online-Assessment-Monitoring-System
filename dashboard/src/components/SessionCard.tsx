// src/components/SessionCard.tsx — one row in SessionsListPage.

import { Link } from "react-router-dom";
import { RiskBadge } from "./RiskBadge";
import { ExamCodeBadge } from "./ExamCodeBadge";
import type { SessionDoc } from "../hooks/useSessions";

function overallRisk(session: SessionDoc): "LOW" | "MODERATE" | "HIGH" {
  if (session.high_risk_count > 0) return "HIGH";
  if (session.moderate_risk_count > 0) return "MODERATE";
  return "LOW";
}

export function SessionCard({ session }: { session: SessionDoc }) {
  return (
    <Link to={`/sessions/${session.id}`} className="session-card">
      <div className="session-card__main">
        <RiskBadge level={overallRisk(session)} />
        <span className="session-card__examinee">
          {session.examinee_label ?? session.id}
        </span>
        <ExamCodeBadge examCode={session.exam_code} examTitle={session.exam_title} />
      </div>
      <div className="session-card__meta">
        <span>{new Date(session.session_start).toLocaleString()}</span>
        <span>{session.total_flagged_events} flagged event(s)</span>
      </div>
    </Link>
  );
}
