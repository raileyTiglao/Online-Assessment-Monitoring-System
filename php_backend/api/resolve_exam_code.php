<?php
// api/resolve_exam_code.php — GET ?code=EXAM-XXXXX
// Called by the Python monitoring app at session start (mirrors
// connection/firebase_db.py::ExamRepository.get_exam in the Firebase
// version). Returns the exam's professor_id/title as JSON, or 404 if the
// code doesn't exist or has been retired.
require_once __DIR__ . '/../includes/api_auth.php';
require_once __DIR__ . '/../includes/db.php';

header('Content-Type: application/json');
require_api_key();

$code = $_GET['code'] ?? '';
if ($code === '') {
    http_response_code(400);
    echo json_encode(['error' => 'Missing code parameter']);
    exit;
}

$stmt = get_db()->prepare(
    'SELECT code, title, professor_id, professor_email, active
     FROM exams WHERE code = ? LIMIT 1'
);
$stmt->execute([$code]);
$exam = $stmt->fetch();

if (!$exam || !$exam['active']) {
    http_response_code(404);
    echo json_encode(['error' => 'Exam code not found or inactive']);
    exit;
}

echo json_encode([
    'code' => $exam['code'],
    'title' => $exam['title'],
    'professorId' => (int) $exam['professor_id'],
    'professorEmail' => $exam['professor_email'],
]);
