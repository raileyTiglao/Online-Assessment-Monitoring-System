<?php
// api/upload_evidence.php — POST multipart/form-data: file, session_id,
// professor_id (optional). Called by the Python monitoring app on every
// HIGH-risk screenshot capture (mirrors connection/firebase_storage.py::
// FirebaseStorageUploader.upload in the Firebase version). Saves under
// uploads/evidence/<professor_id or "_unassigned">/<session_id>/<filename>
// and returns that relative path — the same path convention the Firebase
// version used for its Storage object paths, so SessionDetailPage-style
// display logic carries over unchanged in spirit.
require_once __DIR__ . '/../includes/api_auth.php';
require_once __DIR__ . '/../includes/db.php';

header('Content-Type: application/json');
require_api_key();

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'POST required']);
    exit;
}

$sessionId = $_POST['session_id'] ?? '';
$professorId = $_POST['professor_id'] ?? '';
if ($sessionId === '' || !isset($_FILES['file'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing session_id or file']);
    exit;
}

// session_id/professor_id become path segments — reject anything that
// isn't a plain alphanumeric/underscore/hyphen token before it ever
// touches the filesystem, so a malicious value can't path-traverse
// (e.g. "../../../whatever") out of the uploads directory.
if (!preg_match('/^[A-Za-z0-9_\-]+$/', $sessionId)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid session_id']);
    exit;
}
$ownerSegment = $professorId !== '' ? $professorId : '_unassigned';
if (!preg_match('/^[A-Za-z0-9_\-]+$/', $ownerSegment)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid professor_id']);
    exit;
}

$file = $_FILES['file'];
if ($file['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo json_encode(['error' => 'Upload failed', 'code' => $file['error']]);
    exit;
}

// Only accept image content — this endpoint exists to receive evidence
// screenshots, not arbitrary files.
$imageInfo = @getimagesize($file['tmp_name']);
if ($imageInfo === false) {
    http_response_code(400);
    echo json_encode(['error' => 'File is not a valid image']);
    exit;
}

$destDir = UPLOADS_DIR . "/$ownerSegment/$sessionId";
if (!is_dir($destDir) && !mkdir($destDir, 0755, true) && !is_dir($destDir)) {
    http_response_code(500);
    echo json_encode(['error' => 'Could not create upload directory']);
    exit;
}

$filename = basename($file['name']);
$filename = preg_replace('/[^A-Za-z0-9_\-.]/', '_', $filename);
$destPath = "$destDir/$filename";

if (!move_uploaded_file($file['tmp_name'], $destPath)) {
    http_response_code(500);
    echo json_encode(['error' => 'Could not save uploaded file']);
    exit;
}

$relativePath = UPLOADS_URL_PREFIX . "/$ownerSegment/$sessionId/$filename";
echo json_encode(['path' => $relativePath]);
