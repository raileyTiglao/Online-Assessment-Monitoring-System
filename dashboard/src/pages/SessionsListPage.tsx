// src/pages/SessionsListPage.tsx — filterable list of sessions, scoped by
// role via useSessions() (professor: own sessions only; admin: all).

import { useMemo, useState } from "react";
import { useSessions } from "../hooks/useSessions";
import { SessionCard } from "../components/SessionCard";

type RiskFilter = "ALL" | "LOW" | "MODERATE" | "HIGH";

function overallRisk(highCount: number, moderateCount: number): "LOW" | "MODERATE" | "HIGH" {
  if (highCount > 0) return "HIGH";
  if (moderateCount > 0) return "MODERATE";
  return "LOW";
}

export function SessionsListPage() {
  const { sessions, loading, error } = useSessions();
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      if (riskFilter !== "ALL" && overallRisk(s.high_risk_count, s.moderate_risk_count) !== riskFilter) {
        return false;
      }
      if (search.trim()) {
        const needle = search.trim().toLowerCase();
        const haystack = `${s.examinee_label ?? ""} ${s.exam_title ?? ""} ${s.exam_code ?? ""} ${s.id}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  }, [sessions, riskFilter, search]);

  return (
    <div className="page">
      <h1>Sessions</h1>

      <div className="filter-row">
        <input
          type="search"
          placeholder="Search by examinee, exam, or session ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value as RiskFilter)}>
          <option value="ALL">All risk levels</option>
          <option value="HIGH">HIGH</option>
          <option value="MODERATE">MODERATE</option>
          <option value="LOW">LOW</option>
        </select>
      </div>

      {loading && <p className="page-loading">Loading sessions…</p>}
      {error && <p className="page-error">Couldn't load sessions: {error}</p>}
      {!loading && !error && filtered.length === 0 && (
        <p className="empty-state">No sessions match the current filters.</p>
      )}

      <div className="session-list">
        {filtered.map((session) => (
          <SessionCard key={session.id} session={session} />
        ))}
      </div>
    </div>
  );
}
