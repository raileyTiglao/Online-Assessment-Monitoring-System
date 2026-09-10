// src/pages/ExamsAndSessionsPage.tsx — merges the old ExamsPage (exam
// creation + code list) and SessionsListPage (filterable session reports)
// into one two-panel view: exams on the left, session reports on the
// right. Available to both roles — useExams/useSessions already scope
// each query correctly (professor: own only; admin: all).
//
// Clicking an exam row selects it, which filters the right panel down to
// that exam's sessions only (via session.exam_code === exam.code); "All
// exams" clears the filter back to the full list. Selection lives here,
// not in either panel, since both panels need it.

import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useExams, type ExamDoc } from "../hooks/useExams";
import { useSessions } from "../hooks/useSessions";
import { RiskBadge } from "../components/RiskBadge";
import { ExamCodeBadge } from "../components/ExamCodeBadge";
import { ConfirmModal } from "../components/ConfirmModal";

type RiskFilter = "ALL" | "LOW" | "MODERATE" | "HIGH";

function overallRisk(highCount: number, moderateCount: number): "LOW" | "MODERATE" | "HIGH" {
  if (highCount > 0) return "HIGH";
  if (moderateCount > 0) return "MODERATE";
  return "LOW";
}

function ExamsPanel({
  selectedExamCode,
  onSelectExam,
}: {
  selectedExamCode: string | null;
  onSelectExam: (exam: ExamDoc | null) => void;
}) {
  const { exams, loading, error, createExam, deleteExam } = useExams();
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<string | null>(null);
  const [examPendingDelete, setExamPendingDelete] = useState<ExamDoc | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletedNotice, setDeletedNotice] = useState<string | null>(null);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    setCreateError(null);
    setJustCreated(null);
    try {
      const code = await createExam(title.trim());
      setJustCreated(code);
      setTitle("");
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Couldn't create the exam.");
    } finally {
      setCreating(false);
    }
  }

  async function handleConfirmDelete() {
    if (!examPendingDelete) return;
    const exam = examPendingDelete;

    setDeleting(true);
    setDeleteError(null);
    setDeletedNotice(null);
    try {
      const deletedSessionCount = await deleteExam(exam.code);
      if (selectedExamCode === exam.code) onSelectExam(null);
      setDeletedNotice(`Deleted "${exam.title}" and ${deletedSessionCount} session(s).`);
      setExamPendingDelete(null);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Couldn't delete the exam.");
      setExamPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="panel exams-panel">
      <h2>Exams</h2>

      <form className="exam-create-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Exam title (e.g. Physics Midterm)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <button type="submit" disabled={creating}>
          {creating ? "Creating…" : "Create exam"}
        </button>
      </form>
      {createError && <p className="page-error">{createError}</p>}
      {justCreated && (
        <p className="exam-created-note">
          Exam code: <strong>{justCreated}</strong> — give this to your students to enter
          when the monitoring app prompts them at startup.
        </p>
      )}

      {loading && <p className="page-loading">Loading exams…</p>}
      {error && <p className="page-error">Couldn't load exams: {error}</p>}
      {deleteError && <p className="page-error">Couldn't delete: {deleteError}</p>}
      {deletedNotice && <p className="exam-created-note">{deletedNotice}</p>}
      {!loading && !error && exams.length === 0 && (
        <p className="empty-state">No exams yet — create one above.</p>
      )}

      {exams.length > 0 && (
        <table className="exam-table">
          <thead>
            <tr>
              <th>Code</th>
              <th>Title</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              className={selectedExamCode === null ? "exam-row exam-row--selected" : "exam-row"}
              onClick={() => onSelectExam(null)}
            >
              <td colSpan={2}><em>All exams</em></td>
              <td></td>
            </tr>
            {exams.map((exam) => (
              <tr
                key={exam.code}
                className={selectedExamCode === exam.code ? "exam-row exam-row--selected" : "exam-row"}
                onClick={() => onSelectExam(exam)}
              >
                <td><code>{exam.code}</code></td>
                <td>{exam.title}</td>
                <td>
                  <button
                    type="button"
                    className="button-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeletedNotice(null);
                      setExamPendingDelete(exam);
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ConfirmModal
        open={examPendingDelete !== null}
        title="Delete exam?"
        message={
          examPendingDelete && (
            <>
              Delete <strong>"{examPendingDelete.title}"</strong> ({examPendingDelete.code})?
              This permanently deletes the exam AND every session recorded under it,
              including evidence screenshots. This cannot be undone.
            </>
          )
        }
        confirmLabel="Delete"
        danger
        busy={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setExamPendingDelete(null)}
      />
    </section>
  );
}

function SessionsPanel({ selectedExam }: { selectedExam: ExamDoc | null }) {
  const navigate = useNavigate();
  const { sessions, loading, error } = useSessions();
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("ALL");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return sessions.filter((s) => {
      if (selectedExam && s.exam_code !== selectedExam.code) return false;
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
  }, [sessions, riskFilter, search, selectedExam]);

  return (
    <section className="panel sessions-panel">
      <h2>
        Session Reports
        {selectedExam && <span className="sessions-panel__scope"> — {selectedExam.title}</span>}
      </h2>

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
        <p className="empty-state">
          {selectedExam
            ? `No sessions match the current filters for "${selectedExam.title}".`
            : "No sessions match the current filters."}
        </p>
      )}

      {filtered.length > 0 && (
        <div className="table-scroll">
        <table className="session-table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Exam</th>
              <th>Risk</th>
              <th>Date</th>
              <th>Flagged events</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((session) => (
              <tr
                key={session.id}
                className="session-row"
                onClick={() => navigate(`/sessions/${session.id}`)}
              >
                <td>{session.examinee_label ?? <em className="muted">Unassigned</em>}</td>
                <td><ExamCodeBadge examCode={session.exam_code} examTitle={session.exam_title} /></td>
                <td><RiskBadge level={overallRisk(session.high_risk_count, session.moderate_risk_count)} /></td>
                <td>{new Date(session.session_start).toLocaleString()}</td>
                <td>{session.total_flagged_events}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </section>
  );
}

export function ExamsAndSessionsPage() {
  const [selectedExam, setSelectedExam] = useState<ExamDoc | null>(null);

  return (
    <div className="page">
      <h1>Exams &amp; Students</h1>
      <div className="exams-students-layout">
        <ExamsPanel selectedExamCode={selectedExam?.code ?? null} onSelectExam={setSelectedExam} />
        <SessionsPanel selectedExam={selectedExam} />
      </div>
    </div>
  );
}
