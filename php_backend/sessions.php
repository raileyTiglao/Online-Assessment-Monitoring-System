<?php
require_once __DIR__ . '/includes/auth.php';
// Admin included alongside professor for exam management — not a security
// boundary (admin already sees every professor's sessions unfiltered
// below), just convenience so testing/admin work doesn't require a
// separate professor account.
$pageUser = require_login();
$db = get_db();
$isAdmin = $pageUser['role'] === 'admin';

function generate_exam_code(): string {
    $chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // no 0/O/1/I ambiguity
    $suffix = '';
    for ($i = 0; $i < 5; $i++) {
        $suffix .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return "EXAM-$suffix";
}

$createError = null;
$justCreated = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'create_exam') {
    $title = trim($_POST['title'] ?? '');
    if ($title === '') {
        $createError = 'Title is required.';
    } else {
        $inserted = false;
        for ($attempt = 0; $attempt < 5 && !$inserted; $attempt++) {
            $code = generate_exam_code();
            try {
                $stmt = $db->prepare(
                    'INSERT INTO exams (code, title, professor_id, professor_email) VALUES (?, ?, ?, ?)'
                );
                $stmt->execute([$code, $title, $pageUser['id'], $pageUser['email']]);
                $inserted = true;

                // Reload straight into the (auto-refreshing) exam-filtered
                // view below, rather than leaving the professor/admin
                // looking at an unfiltered list — the code is still
                // visible in the "Watching <exam>" banner.
                header('Location: /oams/sessions.php?exam=' . urlencode($code));
                exit;
            } catch (PDOException $e) {
                if ($e->getCode() !== '23000') { // not a duplicate-key collision — a real error
                    throw $e;
                }
                // Duplicate code — loop and try another.
            }
        }
        if (!$inserted) {
            $createError = "Couldn't generate a unique exam code — please try again.";
        }
    }
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'toggle_exam') {
    $code = $_POST['code'] ?? '';
    $stmt = $db->prepare('UPDATE exams SET active = NOT active WHERE code = ? AND professor_id = ?');
    $stmt->execute([$code, $pageUser['id']]);
}

$examStmt = $db->prepare('SELECT * FROM exams WHERE professor_id = ? ORDER BY created_at DESC');
$examStmt->execute([$pageUser['id']]);
$exams = $examStmt->fetchAll();

$riskFilter = $_GET['risk'] ?? 'ALL';
$search = trim($_GET['q'] ?? '');
$examFilter = trim($_GET['exam'] ?? '');

$where = [];
$params = [];
if (!$isAdmin) {
    $where[] = 'professor_id = ?';
    $params[] = $pageUser['id'];
}
if ($examFilter !== '') {
    $where[] = 'exam_code = ?';
    $params[] = $examFilter;
}
if ($riskFilter === 'HIGH') {
    $where[] = 'high_risk_count > 0';
} elseif ($riskFilter === 'MODERATE') {
    $where[] = 'high_risk_count = 0 AND moderate_risk_count > 0';
} elseif ($riskFilter === 'LOW') {
    $where[] = 'high_risk_count = 0 AND moderate_risk_count = 0';
}
if ($search !== '') {
    $where[] = '(examinee_label LIKE ? OR exam_title LIKE ? OR exam_code LIKE ? OR id LIKE ?)';
    $needle = "%$search%";
    array_push($params, $needle, $needle, $needle, $needle);
}

$sql = 'SELECT * FROM sessions';
if ($where) {
    $sql .= ' WHERE ' . implode(' AND ', $where);
}
$sql .= ' ORDER BY session_start DESC';

$stmt = $db->prepare($sql);
$stmt->execute($params);
$sessions = $stmt->fetchAll();

function overall_risk(array $s): string {
    if ($s['high_risk_count'] > 0) return 'HIGH';
    if ($s['moderate_risk_count'] > 0) return 'MODERATE';
    return 'LOW';
}

$examTitle = null;
if ($examFilter !== '') {
    $stmt = $db->prepare('SELECT title FROM exams WHERE code = ?');
    $stmt->execute([$examFilter]);
    $row = $stmt->fetch();
    $examTitle = $row['title'] ?? $examFilter;

    // Auto-refresh while watching a specific exam for incoming sessions —
    // this page has no push/WebSocket, so a plain reload is the simplest
    // way to approximate "live" without adding a JS polling layer.
    $extraHead = '<meta http-equiv="refresh" content="5">';
}

require __DIR__ . '/includes/header.php';
?>
<h1>Exams &amp; Sessions</h1>

<div class="two-column-layout">
<section class="page-section ornate-frame">
  <h2>Exams</h2>

  <form class="exam-create-form" method="post">
    <input type="hidden" name="action" value="create_exam">
    <input type="text" name="title" placeholder="Exam title (e.g. Physics Midterm)" required>
    <button type="submit">Create exam</button>
  </form>
  <?php if ($createError): ?>
    <p class="page-error"><?= htmlspecialchars($createError) ?></p>
  <?php endif; ?>
  <?php if ($justCreated): ?>
    <p class="exam-created-note">
      Exam code: <strong><?= htmlspecialchars($justCreated) ?></strong> — give this to your students to enter
      when the monitoring app prompts them at startup.
    </p>
  <?php endif; ?>

  <?php if (empty($exams)): ?>
    <p class="empty-state">No exams yet — create one above.</p>
  <?php else: ?>
    <table>
      <thead><tr><th>Code</th><th>Title</th><th>Status</th><th></th></tr></thead>
      <tbody>
        <?php foreach ($exams as $exam): ?>
          <tr>
            <td><code><?= htmlspecialchars($exam['code']) ?></code></td>
            <td><?= htmlspecialchars($exam['title']) ?></td>
            <td><?= $exam['active'] ? 'Active' : 'Retired' ?></td>
            <td class="table-actions">
              <a href="/oams/sessions.php?exam=<?= urlencode($exam['code']) ?>" class="button-secondary">View sessions</a>
              <form method="post" style="display:inline">
                <input type="hidden" name="action" value="toggle_exam">
                <input type="hidden" name="code" value="<?= htmlspecialchars($exam['code']) ?>">
                <button type="submit" class="button-secondary"><?= $exam['active'] ? 'Retire' : 'Reactivate' ?></button>
              </form>
            </td>
          </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
  <?php endif; ?>
</section>

<section class="page-section ornate-frame">
  <h2>Sessions</h2>

  <?php if ($examFilter !== ''): ?>
    <p class="exam-created-note">
      Watching <strong><?= htmlspecialchars($examTitle) ?></strong> (<code><?= htmlspecialchars($examFilter) ?></code>)
      — this page refreshes automatically every 5s.
      <a href="/oams/sessions.php">Show all sessions instead</a>
    </p>
  <?php endif; ?>

  <form class="filter-row" method="get">
    <input type="hidden" name="exam" value="<?= htmlspecialchars($examFilter) ?>">
    <input type="search" name="q" placeholder="Search by examinee, exam, or session ID…" value="<?= htmlspecialchars($search) ?>">
    <select name="risk" onchange="this.form.submit()">
      <option value="ALL" <?= $riskFilter === 'ALL' ? 'selected' : '' ?>>All risk levels</option>
      <option value="HIGH" <?= $riskFilter === 'HIGH' ? 'selected' : '' ?>>HIGH</option>
      <option value="MODERATE" <?= $riskFilter === 'MODERATE' ? 'selected' : '' ?>>MODERATE</option>
      <option value="LOW" <?= $riskFilter === 'LOW' ? 'selected' : '' ?>>LOW</option>
    </select>
    <button type="submit">Filter</button>
  </form>

  <?php if (empty($sessions)): ?>
    <p class="empty-state">
      <?= $examFilter !== '' ? 'No sessions yet for this exam — waiting…' : 'No sessions match the current filters.' ?>
    </p>
  <?php endif; ?>

  <div class="session-list">
    <?php foreach ($sessions as $s): $risk = overall_risk($s); ?>
      <a class="session-card" href="/oams/session_detail.php?id=<?= urlencode($s['id']) ?>">
        <div class="session-card__main">
          <span class="risk-badge risk-badge--<?= strtolower($risk) ?>"><?= $risk ?></span>
          <span><?= htmlspecialchars($s['examinee_label'] ?? $s['id']) ?></span>
          <?php if ($s['exam_code']): ?>
            <span class="exam-badge"><?= htmlspecialchars($s['exam_title'] ?? $s['exam_code']) ?></span>
          <?php else: ?>
            <span class="exam-badge exam-badge--unassigned">Unassigned</span>
          <?php endif; ?>
        </div>
        <div class="session-card__meta">
          <span><?= htmlspecialchars($s['session_start']) ?></span>
          <span><?= (int) $s['total_flagged_events'] ?> flagged event(s)</span>
        </div>
      </a>
    <?php endforeach; ?>
  </div>
</section>
</div>

<?php require __DIR__ . '/includes/footer.php'; ?>
