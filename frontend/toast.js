/**
 * toast.js — shared toast notification helper
 *
 * Requires a #toast element in the page:
 *   <div id="toast"></div>
 *
 * Usage:
 *   toast('Saved!');           // success (accent colour)
 *   toast('Error!', false);    // failure (danger colour)
 */
function toast(msg, success = true) {
  const t = document.getElementById('toast');
  if (!t) { console.warn('[toast]', msg); return; }
  t.textContent = msg;
  t.style.background = success ? 'var(--accent, #6366f1)' : 'var(--danger, #ef4444)';
  t.classList.add('show');
  clearTimeout(t._hideTimer);
  t._hideTimer = setTimeout(() => t.classList.remove('show'), 3000);
}
