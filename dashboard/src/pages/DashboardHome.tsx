// src/pages/DashboardHome.tsx — landing page after login. Hero section
// (ported from php_backend/dashboard.php: astrolabe SVG + animated
// starfield + KPI row) summarizing what useSessions()/useExams() already
// loaded, plus quick links below.

import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useSessions } from "../hooks/useSessions";
import { useExams } from "../hooks/useExams";
import { HeroStarfield } from "../components/animations/HeroStarfield";

// Astrolabe's 12 radial tick lines, at 30deg increments between r=118 and
// r=145 around a (150,150) center — static geometry, computed once at
// module load, never per-render.
const ASTROLABE_TICKS = Array.from({ length: 12 }, (_, i) => {
  const angle = (i * 30 * Math.PI) / 180;
  return {
    x1: 150 + Math.cos(angle) * 118,
    y1: 150 + Math.sin(angle) * 118,
    x2: 150 + Math.cos(angle) * 145,
    y2: 150 + Math.sin(angle) * 145,
  };
});

function HeroKpiTile({ label, value }: { label: React.ReactNode; value: number }) {
  return (
    <div className="hero-kpi-tile">
      <span className="hero-kpi-label">{label}</span>
      <span className="main-num">{value}</span>
    </div>
  );
}

export function DashboardHome() {
  const { user, role } = useAuth();
  const { sessions, loading: sessionsLoading } = useSessions();
  const { exams, loading: examsLoading } = useExams();

  const highCount = sessions.filter((s) => s.high_risk_count > 0).length;
  const moderateOnlyCount = sessions.filter(
    (s) => s.high_risk_count === 0 && s.moderate_risk_count > 0,
  ).length;
  const activeExamCount = exams.filter((e) => e.active).length;
  const loading = sessionsLoading || examsLoading;

  const firstName = user?.email?.split("@")[0]?.split(" ")[0] ?? "";
  const isAdmin = role === "admin";

  return (
    <div className="page">
      <section className="hero">
        <HeroStarfield />

        <svg className="hero-astrolabe" viewBox="0 0 300 300" aria-hidden="true">
          <circle cx="150" cy="150" r="145" fill="none" stroke="currentColor" strokeWidth="0.75" />
          <circle cx="150" cy="150" r="110" fill="none" stroke="currentColor" strokeWidth="0.75" />
          <circle cx="150" cy="150" r="75" fill="none" stroke="currentColor" strokeWidth="1" />
          <g stroke="currentColor" strokeWidth="0.75">
            {ASTROLABE_TICKS.map((t, i) => (
              <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} />
            ))}
          </g>
          <path
            className="hero-astrolabe-star"
            d="M150 65 L162 138 L235 150 L162 162 L150 235 L138 162 L65 150 L138 138 Z"
            fill="currentColor"
            opacity="0.8"
          />
        </svg>

        <div className="hero-content">
          <div className="hero-greeting">
            <span className="hero-eyebrow">Welcome back</span>
            <h1>{isAdmin ? `System overview, ${firstName}` : `${firstName}'s dashboard`}</h1>
          </div>

          <div className="hero-kpi-row">
            <HeroKpiTile label={<><strong>Total</strong> sessions</>} value={sessions.length} />
            <HeroKpiTile label={<><strong>HIGH</strong> risk sessions</>} value={highCount} />
            <HeroKpiTile label={<><strong>MODERATE</strong>-only sessions</>} value={moderateOnlyCount} />
            <HeroKpiTile
              label={isAdmin ? <><strong>Active exams</strong> (all profs)</> : <><strong>Your exams</strong> active</>}
              value={activeExamCount}
            />
          </div>
        </div>
      </section>

      {loading && <p className="page-loading">Loading…</p>}

      <div className="quick-links">
        <Link to="/exams" className="button-secondary">Exams &amp; students</Link>
        {role === "admin" && <Link to="/admin/users" className="button-secondary">Manage users</Link>}
      </div>
    </div>
  );
}
