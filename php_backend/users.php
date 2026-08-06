<?php
require_once __DIR__ . '/includes/auth.php';
$pageUser = require_role(['admin']);
$db = get_db();

if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'toggle') {
    $id = (int) ($_POST['id'] ?? 0);
    // Guard against an admin locking themselves out by disabling their
    // own only account — not a security boundary, just avoids a
    // confusing self-inflicted lockout.
    if ($id !== (int) $pageUser['id']) {
        $stmt = $db->prepare('UPDATE users SET active = NOT active WHERE id = ?');
        $stmt->execute([$id]);
    }
}

$users = $db->query('SELECT id, email, display_name, role, active FROM users ORDER BY email')->fetchAll();

require __DIR__ . '/includes/header.php';
?>
<section class="page-section ornate-frame">
  <h2>Users</h2>

  <?php if (empty($users)): ?>
    <p class="empty-state">
      No accounts yet — run <code>provision_accounts.php</code> from the repo (not htdocs) to create one; see the comment at the top of that file for the exact command.
    </p>
  <?php endif; ?>

  <table>
    <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead>
    <tbody>
      <?php foreach ($users as $u): ?>
        <tr>
          <td><?= htmlspecialchars($u['email']) ?></td>
          <td><?= htmlspecialchars($u['display_name'] ?: '—') ?></td>
          <td><?= htmlspecialchars($u['role']) ?></td>
          <td><?= $u['active'] ? 'Active' : 'Disabled' ?></td>
          <td>
            <?php if ((int) $u['id'] !== (int) $pageUser['id']): ?>
              <form method="post" style="display:inline">
                <input type="hidden" name="action" value="toggle">
                <input type="hidden" name="id" value="<?= (int) $u['id'] ?>">
                <button type="submit" class="button-secondary"><?= $u['active'] ? 'Disable' : 'Enable' ?></button>
              </form>
            <?php endif; ?>
          </td>
        </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</section>

<?php require __DIR__ . '/includes/footer.php'; ?>
