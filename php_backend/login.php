<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/assets.php';

if (current_user()) {
    header('Location: /oams/dashboard.php');
    exit;
}

$error = null;
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    $user = attempt_login($email, $password);
    if ($user) {
        header('Location: /oams/dashboard.php');
        exit;
    }
    // Deliberately vague — see attempt_login()'s docblock.
    $error = 'Invalid email or password.';
}
?>
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sign in — OAMS Dashboard</title>
  <script>
    (function () {
      try {
        var saved = localStorage.getItem('oams-theme');
        if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
      } catch (e) {}
    })();
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Playfair+Display:wght@600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= asset_url('assets/style.css') ?>">
</head>
<body>

<div id="introOverlay" class="intro-overlay">
    <div id="introField" class="intro-field"></div>
</div>

<div class="login-page">
  <form class="login-form" method="post">
    <h1>Online Assessment Monitoring System</h1>
    <p class="login-subtitle">Professor / Admin Dashboard</p>

    <label for="email">Email</label>
    <input id="email" name="email" type="email" required autocomplete="email">

    <label for="password">Password</label>
    <input id="password" name="password" type="password" required autocomplete="current-password">

    <?php if ($error): ?>
      <p class="login-error"><?= htmlspecialchars($error) ?></p>
    <?php endif; ?>

    <button type="submit">Sign in</button>
  </form>
</div>

<script src="<?= asset_url('assets/intro.js') ?>"></script>
</body>
</html>
