// src/pages/ExamsPage.tsx — professor's own exams: create (auto-generates
// a collision-retried code — see useExams.createExam) and toggle active.
// The generated code is what gets typed into the Python monitoring app's
// "Enter exam code" prompt (main.py::_resolve_exam_code).

import { useState, type FormEvent } from "react";
import { useExams } from "../hooks/useExams";

export function ExamsPage() {
  const { exams, loading, error, createExam, setExamActive } = useExams();
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<string | null>(null);

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

  return (
    <div className="page">
      <h1>Exams</h1>

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
      {!loading && !error && exams.length === 0 && (
        <p className="empty-state">No exams yet — create one above.</p>
      )}

      <table className="exam-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Title</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {exams.map((exam) => (
            <tr key={exam.code}>
              <td><code>{exam.code}</code></td>
              <td>{exam.title}</td>
              <td>{exam.active ? "Active" : "Retired"}</td>
              <td>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setExamActive(exam.code, !exam.active)}
                >
                  {exam.active ? "Retire" : "Reactivate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
