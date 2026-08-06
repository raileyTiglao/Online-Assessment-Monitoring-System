  </main>
</div>
<script>
(function () {
  var themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      var root = document.documentElement;
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('oams-theme', next); } catch (e) {}
      document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: next } }));
    });
  }
})();
</script>
<script src="<?= asset_url('assets/intro.js') ?>"></script>
<script src="https://unpkg.com/three@0.160.1/build/three.min.js"></script>
<script src="<?= asset_url('assets/theme-toggle-stars.js') ?>"></script>
<?= $extraFoot ?? '' ?>
</body>
</html>
