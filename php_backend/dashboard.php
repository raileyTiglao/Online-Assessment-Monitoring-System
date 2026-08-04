<?php
require_once __DIR__ . '/includes/auth.php';
require_once __DIR__ . '/includes/assets.php';
$pageUser = require_login();
$db = get_db();
$isAdmin = $pageUser['role'] === 'admin';

if ($isAdmin) {
    $totalSessions = (int) $db->query('SELECT COUNT(*) c FROM sessions')->fetch()['c'];
    $highCount = (int) $db->query('SELECT COUNT(*) c FROM sessions WHERE high_risk_count > 0')->fetch()['c'];
    $moderateOnlyCount = (int) $db->query(
        'SELECT COUNT(*) c FROM sessions WHERE high_risk_count = 0 AND moderate_risk_count > 0'
    )->fetch()['c'];
    $activeExamCount = (int) $db->query('SELECT COUNT(*) c FROM exams WHERE active = 1')->fetch()['c'];
} else {
    $stmt = $db->prepare('SELECT COUNT(*) c FROM sessions WHERE professor_id = ?');
    $stmt->execute([$pageUser['id']]);
    $totalSessions = (int) $stmt->fetch()['c'];

    $stmt = $db->prepare('SELECT COUNT(*) c FROM sessions WHERE professor_id = ? AND high_risk_count > 0');
    $stmt->execute([$pageUser['id']]);
    $highCount = (int) $stmt->fetch()['c'];

    $stmt = $db->prepare(
        'SELECT COUNT(*) c FROM sessions WHERE professor_id = ? AND high_risk_count = 0 AND moderate_risk_count > 0'
    );
    $stmt->execute([$pageUser['id']]);
    $moderateOnlyCount = (int) $stmt->fetch()['c'];

    $stmt = $db->prepare('SELECT COUNT(*) c FROM exams WHERE professor_id = ? AND active = 1');
    $stmt->execute([$pageUser['id']]);
    $activeExamCount = (int) $stmt->fetch()['c'];
}

$firstName = explode(' ', explode('@', $pageUser['email'])[0])[0];
// three.js itself is already loaded globally in footer.php (the sidebar
// theme switch needs it on every page) — just add the hero's starfield.
$extraFoot = '<script src="' . asset_url('assets/hero-stars.js') . '"></script>';

require __DIR__ . '/includes/header.php';
?>
<section class="hero">
  <canvas id="heroCanvas"></canvas>

  <svg class="hero-astrolabe" viewBox="0 0 300 300" aria-hidden="true">
    <circle cx="150" cy="150" r="145" fill="none" stroke="currentColor" stroke-width="0.75"/>
    <circle cx="150" cy="150" r="110" fill="none" stroke="currentColor" stroke-width="0.75"/>
    <circle cx="150" cy="150" r="75" fill="none" stroke="currentColor" stroke-width="1"/>
    <g stroke="currentColor" stroke-width="0.75">
      <?php for ($i = 0; $i < 12; $i++):
          $angle = deg2rad($i * 30);
          $x1 = 150 + cos($angle) * 118; $y1 = 150 + sin($angle) * 118;
          $x2 = 150 + cos($angle) * 145; $y2 = 150 + sin($angle) * 145;
      ?>
        <line x1="<?= $x1 ?>" y1="<?= $y1 ?>" x2="<?= $x2 ?>" y2="<?= $y2 ?>"/>
      <?php endfor; ?>
    </g>
    <path class="hero-astrolabe-star" d="M150 65 L162 138 L235 150 L162 162 L150 235 L138 162 L65 150 L138 138 Z" fill="currentColor" opacity="0.8"/>
  </svg>

  <div class="hero-content">
    <div class="hero-greeting">
      <span class="hero-eyebrow">Welcome back</span>
      <h1><?= htmlspecialchars($isAdmin ? 'System overview, ' . $firstName : $firstName . "'s dashboard") ?></h1>
    </div>

    <div class="hero-kpi-row">
      <div class="hero-kpi-tile">
        <span class="hero-kpi-label"><strong>Total</strong> sessions</span>
        <span class="main-num"><?= $totalSessions ?></span>
      </div>
      <div class="hero-kpi-tile">
        <span class="hero-kpi-label"><strong>HIGH</strong> risk sessions</span>
        <span class="main-num"><?= $highCount ?></span>
      </div>
      <div class="hero-kpi-tile">
        <span class="hero-kpi-label"><strong>MODERATE</strong>-only sessions</span>
        <span class="main-num"><?= $moderateOnlyCount ?></span>
      </div>
      <div class="hero-kpi-tile">
        <span class="hero-kpi-label"><strong><?= $isAdmin ? 'Active exams' : 'Your exams' ?></strong> <?= $isAdmin ? '(all profs)' : 'active' ?></span>
        <span class="main-num"><?= $activeExamCount ?></span>
      </div>
    </div>
  </div>
</section>

<div class="quick-links">
  <a href="/oams/sessions.php" class="button-secondary">Exams &amp; sessions</a>
  <?php if ($isAdmin): ?>
    <a href="/oams/users.php" class="button-secondary">Manage users</a>
  <?php endif; ?>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
