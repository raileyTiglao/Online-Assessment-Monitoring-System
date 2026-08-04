<?php
// includes/header.php — shared shell: fixed sidebar nav, no topbar.
// Expects $pageUser to already be set by the including page (via
// require_login()/require_role()). Optional $extraHead (raw HTML string,
// set before including this file) lets a page add things like an
// auto-refresh meta tag. Theme-toggle wiring lives in footer.php, where
// the closing </body> script tag already is.
require_once __DIR__ . '/assets.php';
$currentScript = basename($_SERVER['SCRIPT_NAME']);
function nav_active(string $script, string $current): string {
    return $script === $current ? ' active' : '';
}
?>
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OAMS Dashboard — Holy Angel University</title>
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
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Bebas+Neue&family=Playfair+Display:wght@600;700;800;900&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= asset_url('assets/style.css') ?>">
  <?= $extraHead ?? '' ?>
</head>
<body>

<div id="introOverlay" class="intro-overlay">
    <div id="introField" class="intro-field"></div>
</div>

<div class="app-shell">
  <aside id="sidebar" class="sidebar">
    <div class="sidebar-identity">
      <div class="avatar"><?= htmlspecialchars(strtoupper(substr($pageUser['email'], 0, 1))) ?></div>
      <div class="identity-text">
        <span class="identity-name"><?= htmlspecialchars($pageUser['email']) ?></span>
        <span class="identity-tag"><?= htmlspecialchars(ucfirst($pageUser['role'])) ?></span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <a href="/oams/dashboard.php" class="nav-item<?= nav_active('dashboard.php', $currentScript) ?>"><span class="nav-icon">⌂</span> Dashboard</a>
      <a href="/oams/sessions.php" class="nav-item<?= nav_active('sessions.php', $currentScript) ?>"><span class="nav-icon">▤</span> Exams &amp; Sessions</a>
      <?php if ($pageUser['role'] === 'admin'): ?>
        <a href="/oams/users.php" class="nav-item<?= nav_active('users.php', $currentScript) ?>"><span class="nav-icon">☺</span> Users</a>
      <?php endif; ?>
    </nav>

    <nav class="sidebar-nav sidebar-nav-bottom">
      <button id="themeToggle" class="theme-pill" type="button" title="Toggle theme" aria-label="Toggle light and dark mode">
        <canvas id="themeSwitchCanvas" class="theme-pill__canvas"></canvas>
        <span class="theme-pill__label">
          <span class="theme-toggle-pill__label-dark">Dark mode</span>
          <span class="theme-toggle-pill__label-light">Light mode</span>
        </span>
      </button>
      <a href="/oams/logout.php" class="nav-item"><span class="nav-icon">⏻</span> Sign out</a>
    </nav>

    <div class="sidebar-footer">
      <span>HOLY ANGEL UNIVERSITY</span>
      <strong>OAMS Dashboard</strong>
    </div>
  </aside>

  <main class="app-main">
