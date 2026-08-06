// src/components/ExamCodeBadge.tsx — small pill showing an exam code, or
// an "Unassigned" state for sessions started without a valid code
// (DatabaseConfig.REQUIRE_EXAM_CODE = False allows this).

export function ExamCodeBadge({ examCode, examTitle }: { examCode: string | null; examTitle: string | null }) {
  if (!examCode) {
    return <span className="exam-badge exam-badge--unassigned">Unassigned</span>;
  }
  return (
    <span className="exam-badge" title={examTitle ?? undefined}>
      {examTitle ?? examCode}
    </span>
  );
}
