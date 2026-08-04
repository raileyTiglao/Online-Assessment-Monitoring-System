<?php
// api/save_session.php — POST application/json, the full report dict
// produced by monitoring/session_report.py::_build_report_dict() plus
// session_uid/exam_code/professor_uid/exam_title/examinee_label (mirrors
// connection/firebase_db.py::FirestoreSessionRepository.save_report in
// the Firebase version). Upserts the session row and replaces its event
// rows — safe to call more than once for the same session_uid (e.g. a
// retried request after a network blip) without creating duplicates.
require_once __DIR__ . '/../includes/api_auth.php';
require_once __DIR__ . '/../includes/db.php';

header('Content-Type: application/json');
require_api_key();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'POST required']);
    exit;
}

$body = json_decode(file_get_contents('php://input'), true);
if (!is_array($body) || empty($body['session_uid'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid or missing session_uid']);
    exit;
}

$sessionId = $body['session_uid'];
$baseline = $body['calibration_baseline'] ?? null;
$events = $body['events'] ?? [];

$db = get_db();
$db->beginTransaction();
try {
    $stmt = $db->prepare(
        'INSERT INTO sessions
            (id, session_start, session_end, calibration_yaw, calibration_pitch,
             calibration_roll, calibration_samples, total_flagged_events,
             high_risk_count, moderate_risk_count, exam_code, professor_id,
             exam_title, examinee_label)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ON DUPLICATE KEY UPDATE
            session_start = VALUES(session_start),
            session_end = VALUES(session_end),
            calibration_yaw = VALUES(calibration_yaw),
            calibration_pitch = VALUES(calibration_pitch),
            calibration_roll = VALUES(calibration_roll),
            calibration_samples = VALUES(calibration_samples),
            total_flagged_events = VALUES(total_flagged_events),
            high_risk_count = VALUES(high_risk_count),
            moderate_risk_count = VALUES(moderate_risk_count),
            exam_code = VALUES(exam_code),
            professor_id = VALUES(professor_id),
            exam_title = VALUES(exam_title),
            examinee_label = VALUES(examinee_label)'
    );
    $stmt->execute([
        $sessionId,
        $body['session_start'],
        $body['session_end'],
        $baseline['yaw'] ?? null,
        $baseline['pitch'] ?? null,
        $baseline['roll'] ?? null,
        $baseline['sample_count'] ?? null,
        $body['total_flagged_events'] ?? 0,
        $body['high_risk_count'] ?? 0,
        $body['moderate_risk_count'] ?? 0,
        $body['exam_code'] ?? null,
        $body['professor_uid'] ?? null,
        $body['exam_title'] ?? null,
        $body['examinee_label'] ?? null,
    ]);

    // Replace this session's events wholesale rather than trying to diff —
    // simple and correct for the retry case, and a session's event count
    // is small enough (dozens, not thousands) that this is cheap.
    $db->prepare('DELETE FROM events WHERE session_id = ?')->execute([$sessionId]);

    $eventStmt = $db->prepare(
        'INSERT INTO events
            (session_id, event_timestamp, risk_level, yaw, pitch, roll,
             device_detected, behavioral_indicator, trigger_reason, screenshot_path,
             gaze_x, gaze_y, gaze_valid)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    );
    foreach ($events as $event) {
        $eventStmt->execute([
            $sessionId,
            $event['timestamp'],
            $event['risk_level'],
            $event['yaw'],
            $event['pitch'],
            $event['roll'],
            $event['device_detected'] ? 1 : 0,
            $event['behavioral_indicator'] ?? '',
            $event['trigger'] ?? '',
            $event['screenshot_path'] ?? null,
            $event['gaze_x'] ?? null,
            $event['gaze_y'] ?? null,
            !empty($event['gaze_valid']) ? 1 : 0,
        ]);
    }

    $db->commit();
} catch (Throwable $e) {
    $db->rollBack();
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'detail' => $e->getMessage()]);
    exit;
}

echo json_encode(['session_id' => $sessionId]);
