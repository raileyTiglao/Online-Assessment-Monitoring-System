// src/pages/SessionDetailPage.tsx — one session's full detail: exam/professor
// context, calibration baseline, head-pose chart, and the event timeline
// with evidence screenshots. Access control is enforced by firestore.rules
// (a professor who isn't the session's owner gets permission-denied on the
// doc read, surfaced here as an error state) — this page doesn't duplicate
// that check client-side.

import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { doc, onSnapshot } from "firebase/firestore";
import { db } from "../firebase";
import type { SessionDoc } from "../hooks/useSessions";
import { RiskBadge } from "../components/RiskBadge";
import { ExamCodeBadge } from "../components/ExamCodeBadge";
import { EventTimeline } from "../components/EventTimeline";
import { HeadPoseChart } from "../components/HeadPoseChart";

function overallRisk(session: SessionDoc): "LOW" | "MODERATE" | "HIGH" {
  if (session.high_risk_count > 0) return "HIGH";
  if (session.moderate_risk_count > 0) return "MODERATE";
  return "LOW";
}

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<SessionDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    return onSnapshot(
      doc(db, "sessions", sessionId),
      (snap) => {
        setSession(snap.exists() ? ({ id: snap.id, ...snap.data() } as SessionDoc) : null);
        setLoading(false);
      },
      (err) => {
        setError(err.message);
        setLoading(false);
      },
    );
  }, [sessionId]);

  if (loading) return <div className="page"><p className="page-loading">Loading…</p></div>;
  if (error) return <div className="page"><p className="page-error">Couldn't load this session: {error}</p></div>;
  if (!session) return <div className="page"><p className="empty-state">Session not found.</p></div>;

  const baseline = session.calibration_baseline;

  return (
    <div className="page">
      <Link to="/exams" className="back-link">&larr; Exams &amp; students</Link>

      <div className="session-detail__header">
        <RiskBadge level={overallRisk(session)} />
        <h1>{session.examinee_label ?? session.id}</h1>
        <ExamCodeBadge examCode={session.exam_code} examTitle={session.exam_title} />
      </div>

      <dl className="session-detail__summary">
        <dt>Started</dt><dd>{new Date(session.session_start).toLocaleString()}</dd>
        <dt>Ended</dt><dd>{new Date(session.session_end).toLocaleString()}</dd>
        <dt>Flagged events</dt><dd>{session.total_flagged_events}</dd>
        <dt>HIGH risk</dt><dd>{session.high_risk_count}</dd>
        <dt>MODERATE risk</dt><dd>{session.moderate_risk_count}</dd>
      </dl>

      {baseline && (
        <section className="session-detail__section">
          <h2>Calibration baseline</h2>
          <dl className="session-detail__summary">
            <dt>Yaw</dt><dd>{baseline.yaw.toFixed(1)}°</dd>
            <dt>Pitch</dt><dd>{baseline.pitch.toFixed(1)}°</dd>
            <dt>Roll</dt><dd>{baseline.roll.toFixed(1)}°</dd>
            <dt>Samples</dt><dd>{baseline.sample_count}</dd>
          </dl>
        </section>
      )}

      <section className="session-detail__section">
        <h2>Head pose over session</h2>
        <HeadPoseChart events={session.events} />
      </section>

      <section className="session-detail__section">
        <h2>Event timeline</h2>
        <EventTimeline events={session.events} />
      </section>
    </div>
  );
}
