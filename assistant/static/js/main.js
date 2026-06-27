// BRAP — main.js

// ── User Menu Dropdown ──
document.addEventListener('DOMContentLoaded', () => {
  const userMenu   = document.getElementById('userMenu');
  const avatarBtn  = document.getElementById('userAvatarBtn');
  const dropdown   = document.getElementById('userDropdown');

  if (avatarBtn && userMenu) {
    avatarBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = userMenu.classList.toggle('open');
      avatarBtn.setAttribute('aria-expanded', isOpen);
    });

    // Tutup saat klik di luar
    document.addEventListener('click', (e) => {
      if (!userMenu.contains(e.target)) {
        userMenu.classList.remove('open');
        avatarBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Tutup saat tekan Escape
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        userMenu.classList.remove('open');
        avatarBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }
});

// ── Smooth Page Transitions ──
document.addEventListener('DOMContentLoaded', () => {
  document.body.style.opacity = '0';
  requestAnimationFrame(() => {
    document.body.style.transition = 'opacity 0.3s ease';
    document.body.style.opacity = '1';
  });
});

// Intercept internal links for smooth out-transition
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href]');
  if (a && a.hostname === location.hostname && !a.target) {
    e.preventDefault();
    const href = a.href;
    document.body.style.opacity = '0';
    setTimeout(() => { window.location.href = href; }, 250);
  }
});

