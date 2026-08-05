<?php
require_once __DIR__ . '/includes/auth.php';
$pageUser = require_login();
$db = get_db();
$isAdmin = $pageUser['role'] === 'admin';

$sessionId = $_GET['id'] ?? '';

if ($isAdmin) {
    $stmt = $db->prepare('SELECT * FROM sessions WHERE id = ?');
    $stmt->execute([$sessionId]);
} else {
    // Access control enforced here, at the query itself — a professor
    // requesting another professor's session_id gets the same "not
    // found" as a nonexistent one, not a 403 that would confirm the ID
    // is real.
    $stmt = $db->prepare('SELECT * FROM sessions WHERE id = ? AND professor_id = ?');
    $stmt->execute([$sessionId, $pageUser['id']]);
}
$session = $stmt->fetch();

if ($session) {
    $eventStmt = $db->prepare('SELECT * FROM events WHERE session_id = ? ORDER BY event_timestamp ASC');
    $eventStmt->execute([$sessionId]);
    $events = $eventStmt->fetchAll();
}

function overall_risk_detail(array $s): string {
    if ($s['high_risk_count'] > 0) return 'HIGH';
    if ($s['moderate_risk_count'] > 0) return 'MODERATE';
    return 'LOW';
}

require __DIR__ . '/includes/header.php';
?>
<a href="/oams/sessions.php" style="text-decoration:none;color:var(--text-secondary);display:inline-block;margin-bottom:12px;">&larr; All sessions</a>

<?php if (!$session): ?>
  <p class="empty-state">Session not found.</p>
<?php else: $risk = overall_risk_detail($session); ?>
  <div class="session-detail__header">
    <span class="risk-badge risk-badge--<?= strtolower($risk) ?>"><?= $risk ?></span>
    <h1><?= htmlspecialchars($session['examinee_label'] ?? $session['id']) ?></h1>
    <?php if ($session['exam_code']): ?>
      <span class="exam-badge"><?= htmlspecialchars($session['exam_title'] ?? $session['exam_code']) ?></span>
    <?php else: ?>
      <span class="exam-badge exam-badge--unassigned">Unassigned</span>
    <?php endif; ?>
  </div>

  <dl class="session-detail__summary">
    <dt>Started</dt><dd><?= htmlspecialchars($session['session_start']) ?></dd>
    <dt>Ended</dt><dd><?= htmlspecialchars($session['session_end']) ?></dd>
    <dt>Flagged events</dt><dd><?= (int) $session['total_flagged_events'] ?></dd>
    <dt>HIGH risk</dt><dd><?= (int) $session['high_risk_count'] ?></dd>
    <dt>MODERATE risk</dt><dd><?= (int) $session['moderate_risk_count'] ?></dd>
  </dl>

  <?php if ($session['calibration_yaw'] !== null): ?>
    <section class="session-detail__section">
      <h2>Calibration baseline</h2>
      <dl class="session-detail__summary">
        <dt>Yaw</dt><dd><?= number_format($session['calibration_yaw'], 1) ?>°</dd>
        <dt>Pitch</dt><dd><?= number_format($session['calibration_pitch'], 1) ?>°</dd>
        <dt>Roll</dt><dd><?= number_format($session['calibration_roll'], 1) ?>°</dd>
        <dt>Samples</dt><dd><?= (int) $session['calibration_samples'] ?></dd>
      </dl>
    </section>
  <?php endif; ?>

  <section class="session-detail__section">
    <h2>Event timeline</h2>
    <?php if (empty($events)): ?>
      <p class="empty-state">No flagged events in this session.</p>
    <?php else: ?>
      <ol class="event-timeline">
        <?php foreach ($events as $event): ?>
          <li class="event-timeline__item">
            <div class="event-timeline__header">
              <span class="risk-badge risk-badge--<?= strtolower($event['risk_level']) ?>"><?= $event['risk_level'] ?></span>
              <time><?= htmlspecialchars($event['event_timestamp']) ?></time>
            </div>
            <p><?= htmlspecialchars($event['trigger_reason'] ?: $event['behavioral_indicator']) ?></p>
            <dl class="event-timeline__pose">
              <dt>Yaw</dt><dd><?= number_format($event['yaw'], 1) ?>°</dd>
              <dt>Pitch</dt><dd><?= number_format($event['pitch'], 1) ?>°</dd>
              <dt>Roll</dt><dd><?= number_format($event['roll'], 1) ?>°</dd>
              <dt>Device detected</dt><dd><?= $event['device_detected'] ? 'Yes' : 'No' ?></dd>
              <dt>Gaze H</dt><dd><?= $event['gaze_valid'] ? number_format($event['gaze_x'], 3) : '—' ?></dd>
              <dt>Gaze V</dt><dd><?= $event['gaze_valid'] ? number_format($event['gaze_y'], 3) : '—' ?></dd>
            </dl>
            <?php if ($event['screenshot_path']): ?>
              <img class="screenshot-image" src="/oams/<?= htmlspecialchars($event['screenshot_path']) ?>" alt="Evidence screenshot">
            <?php else: ?>
              <div class="screenshot-placeholder">No screenshot (MODERATE risk)</div>
            <?php endif; ?>
          </li>
        <?php endforeach; ?>
      </ol>
    <?php endif; ?>
  </section>
<?php endif; ?>

<?php require __DIR__ . '/includes/footer.php'; ?>
