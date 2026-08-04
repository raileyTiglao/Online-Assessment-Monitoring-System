<?php
// includes/api_auth.php — shared-secret check for api/*.php endpoints,
// called by the Python monitoring app rather than a logged-in browser
// session. Responds 401 and exits if the X-API-Key header doesn't match.
require_once __DIR__ . '/../config.php';

function require_api_key(): void {
    $headers = getallheaders();
    $provided = $headers['X-Api-Key'] ?? $headers['X-API-Key'] ?? '';
    if (!hash_equals(API_KEY, $provided)) {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Invalid or missing API key']);
        exit;
    }
}
