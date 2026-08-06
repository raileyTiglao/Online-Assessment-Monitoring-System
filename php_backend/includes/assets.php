<?php
// includes/assets.php — cache-busting for local CSS/JS. Appends the
// file's mtime as a version query string so browsers fetch a fresh copy
// whenever we edit style.css or a script, instead of serving whatever
// they cached on a previous visit.
function asset_url(string $path): string {
    $full = __DIR__ . '/../' . $path;
    $v = file_exists($full) ? filemtime($full) : time();
    return '/oams/' . $path . '?v=' . $v;
}
