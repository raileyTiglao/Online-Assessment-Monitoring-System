<?php
// includes/auth.php — PHP-native session auth + RBAC helpers.
// Passwords are hashed with password_hash() (bcrypt by default) and
// checked with password_verify() — PHP's own secure, battle-tested
// implementation, not a custom hashing scheme.
require_once __DIR__ . '/db.php';

function start_session(): void {
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }
}

/**
 * Attempt to log in. On success, stores the user's id/email/role/
 * display_name in $_SESSION and returns the user row (password_hash
 * stripped out — never keep the hash in session state). Returns null on
 * any failure (unknown email, wrong password, or a disabled account) —
 * deliberately the same null for all three, so a caller can't use timing
 * or response shape to distinguish "no such user" from "wrong password".
 */
function attempt_login(string $email, string $password): ?array {
    $stmt = get_db()->prepare('SELECT * FROM users WHERE email = ? LIMIT 1');
    $stmt->execute([$email]);
    $user = $stmt->fetch();

    if (!$user || !$user['active'] || !password_verify($password, $user['password_hash'])) {
        return null;
    }

    unset($user['password_hash']);
    start_session();
    session_regenerate_id(true); // prevent session fixation across the privilege change
    $_SESSION['user'] = $user;
    return $user;
}

function logout(): void {
    start_session();
    $_SESSION = [];
    session_destroy();
}

function current_user(): ?array {
    start_session();
    return $_SESSION['user'] ?? null;
}

/** Redirects to login.php and exits if no user is signed in. */
function require_login(): array {
    $user = current_user();
    if (!$user) {
        header('Location: /oams/login.php');
        exit;
    }
    return $user;
}

/**
 * Redirects to login.php (not signed in) or dashboard.php (signed in,
 * wrong role) and exits unless the signed-in user's role is in $roles.
 */
function require_role(array $roles): array {
    $user = require_login();
    if (!in_array($user['role'], $roles, true)) {
        header('Location: /oams/dashboard.php?error=unauthorized');
        exit;
    }
    return $user;
}
