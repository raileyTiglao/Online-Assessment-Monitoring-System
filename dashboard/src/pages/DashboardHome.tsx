// src/pages/DashboardHome.tsx — landing page after login. Stat tiles
// (dataviz skill: label + semibold value, no delta/trend — we don't have a
// prior-period baseline to compare against yet) summarizing what
// useSessions()/useExams() already loaded, plus quick links.

import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useSessions } from "../hooks/useSessions";
import { useExams } from "../hooks/useExams";

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat-tile">
      <span className="stat-tile__value">{value}</span>
      <span className="stat-tile__label">{label}</span>
    </div>
  );
}

export function DashboardHome() {
  const { role } = useAuth();
  const { sessions, loading: sessionsLoading } = useSessions();
  const { exams, loading: examsLoading } = useExams();

  const highCount = sessions.filter((s) => s.high_risk_count > 0).length;
  const moderateOnlyCount = sessions.filter(
    (s) => s.high_risk_count === 0 && s.moderate_risk_count > 0,
  ).length;
  const activeExamCount = exams.filter((e) => e.active).length;

  return (
    <div className="page">
      <h1>{role === "admin" ? "System overview" : "Your dashboard"}</h1>

      {(sessionsLoading || examsLoading) && <p className="page-loading">Loading…</p>}

      <div className="stat-tile-row">
        <StatTile label="Total sessions" value={sessions.length} />
        <StatTile label="Sessions with a HIGH event" value={highCount} />
        <StatTile label="Sessions with only MODERATE events" value={moderateOnlyCount} />
        <StatTile label={role === "admin" ? "Active exams (all professors)" : "Your active exams"}
                  value={activeExamCount} />
      </div>

      <div className="quick-links">
        <Link to="/sessions" className="button-secondary">View all sessions</Link>
        {role === "professor" && <Link to="/exams" className="button-secondary">Manage exams</Link>}
        {role === "admin" && <Link to="/admin/users" className="button-secondary">Manage users</Link>}
      </div>
    </div>
  );
}
