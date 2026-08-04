<?php
require_once __DIR__ . '/includes/auth.php';
header('Location: ' . (current_user() ? '/oams/dashboard.php' : '/oams/login.php'));
exit;
