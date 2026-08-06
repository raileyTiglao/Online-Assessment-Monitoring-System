<?php
// config.php — local DB connection settings. XAMPP's default MySQL root
// account has no password, which is fine for a local-only dev setup but
// should not be treated as a real credential.
define('DB_HOST', '127.0.0.1');
define('DB_NAME', 'oams');
define('DB_USER', 'root');
define('DB_PASS', '');

define('UPLOADS_DIR', __DIR__ . '/uploads/evidence');
define('UPLOADS_URL_PREFIX', 'uploads/evidence'); // relative to this app's base URL

// Shared secret the Python monitoring app sends in an X-API-Key header on
// every api/*.php request. XAMPP's Apache listens on all interfaces by
// default, so without this, anything else on the same network could post
// fake session data or upload arbitrary files to this endpoint. CHANGE
// THIS before real use — it ships with a placeholder, not a real secret.
define('API_KEY', 'change-me-to-a-random-string');
