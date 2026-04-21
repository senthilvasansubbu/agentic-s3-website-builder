const API = '/api/v1';
let token = localStorage.getItem('wb_token');
let currentUser = null;
let planFeatures = {};  // populated on init from /payments/plan-features
let websites = [];

const THEMES = [
  { id: 'modern',     label: 'Modern',      primary: '#667eea', secondary: '#764ba2', accent: '#f093fb', bg: '#f5f7fa', text: '#2d3748', gradient: 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)', fontHeading: 'Poppins', fontBody: 'Inter',      desc: 'Clean & contemporary' },
  { id: 'classic',    label: 'Classic',     primary: '#1a365d', secondary: '#2b6cb0', accent: '#e53e3e', bg: '#ffffff', text: '#2d3748', gradient: 'linear-gradient(135deg,#1a365d 0%,#2b6cb0 100%)', fontHeading: 'Playfair Display', fontBody: 'Georgia', desc: 'Timeless & trustworthy' },
  { id: 'minimal',    label: 'Minimal',     primary: '#1a1a1a', secondary: '#555',    accent: '#f6c90e', bg: '#fafafa', text: '#222',    gradient: 'linear-gradient(135deg,#1a1a1a 0%,#444 100%)',    fontHeading: 'Space Grotesk',    fontBody: 'DM Sans',    desc: 'Less is more' },
  { id: 'dark',       label: 'Dark',        primary: '#7c3aed', secondary: '#4f46e5', accent: '#06b6d4', bg: '#0f172a', text: '#e2e8f0', gradient: 'linear-gradient(135deg,#7c3aed 0%,#4f46e5 100%)', fontHeading: 'Montserrat',       fontBody: 'Roboto',     desc: 'Bold & immersive' },
  { id: 'nature',     label: 'Nature',      primary: '#276749', secondary: '#38a169', accent: '#f6ad55', bg: '#f0fff4', text: '#1a202c', gradient: 'linear-gradient(135deg,#276749 0%,#38a169 100%)', fontHeading: 'Merriweather',     fontBody: 'Lato',       desc: 'Organic & calming' },
  { id: 'ecommerce',  label: 'E-Commerce',  primary: '#dd6b20', secondary: '#c05621', accent: '#3182ce', bg: '#ffffff', text: '#2d3748', gradient: 'linear-gradient(135deg,#dd6b20 0%,#c05621 100%)', fontHeading: 'Nunito',           fontBody: 'Open Sans',  desc: 'Conversion-focused' },
];
let selectedTheme = 'modern';

const CLASSIFICATIONS = [
  { id: 'b2b',         icon: '🤝', label: 'B2B',          desc: 'Business to business',   cta: 'Request a Demo',     nav: ['Solutions','Case Studies','Pricing','About','Contact'], hero: 'Enterprise solutions that drive measurable ROI', sections: ['solutions','case-studies','stats','testimonials','integrations','contact'] },
  { id: 'b2c',         icon: '🛍️', label: 'B2C',          desc: 'Business to consumer',   cta: 'Shop Now',           nav: ['Products','Offers','About','Reviews','Contact'], hero: 'Products your customers will love', sections: ['products','offers','reviews','gallery','contact'] },
  { id: 'doctor',      icon: '🩺', label: 'Doctor',        desc: 'Medical / clinic',       cta: 'Book Appointment',   nav: ['Services','About','Credentials','Patients','Contact'], hero: 'Compassionate care you can trust', sections: ['services','credentials','team','patient-info','testimonials','appointment'] },
  { id: 'lawyer',      icon: '⚖️', label: 'Lawyer',        desc: 'Legal / law firm',       cta: 'Free Consultation',  nav: ['Practice Areas','Results','About','Team','Contact'], hero: 'Experienced legal counsel. Results that matter.', sections: ['practice-areas','results','team','testimonials','consultation'] },
  { id: 'teacher',     icon: '📚', label: 'Teacher',       desc: 'Educator / tutor',       cta: 'Enroll Now',         nav: ['Courses','About','Curriculum','Testimonials','Contact'], hero: 'Empowering learners to reach their full potential', sections: ['courses','curriculum','testimonials','certifications','enroll'] },
  { id: 'restaurant',  icon: '🍽️', label: 'Restaurant',    desc: 'Food & dining',          cta: 'Reserve a Table',    nav: ['Menu','About','Gallery','Reservations','Contact'], hero: 'An unforgettable dining experience', sections: ['menu','gallery','specials','testimonials','reservation','contact'] },
  { id: 'engineer',    icon: '⚙️', label: 'Engineer',      desc: 'Freelancer / technical', cta: 'Hire Me',            nav: ['Portfolio','Skills','Experience','About','Contact'], hero: 'Building robust solutions with modern technology', sections: ['portfolio','skills','experience','open-source','contact'] },
  { id: 'startup',     icon: '🚀', label: 'Startup / SaaS', desc: 'Tech product',          cta: 'Start Free Trial',   nav: ['Features','Pricing','Testimonials','Blog','Contact'], hero: 'The smarter way to grow your business', sections: ['features','how-it-works','pricing','testimonials','faq','cta'] },
  { id: 'artist',      icon: '🎨', label: 'Artist',        desc: 'Creative / portfolio',   cta: 'Commission Work',    nav: ['Gallery','Process','Exhibitions','About','Contact'], hero: 'Art that speaks without words', sections: ['gallery','process','exhibitions','press','commissions','contact'] },
  { id: 'ngo',         icon: '🌍', label: 'NGO / Non-Profit', desc: 'Non-profit / cause',  cta: 'Donate Now',         nav: ['Mission','Impact','Programs','Volunteer','Donate'], hero: 'Together we can make a difference', sections: ['mission','impact-stats','programs','team','stories','donate'] },
  { id: 'scientist',   icon: '🔬', label: 'Scientist',     desc: 'Research / academic',    cta: 'View Research',      nav: ['Research','Publications','Lab','About','Contact'], hero: 'Advancing knowledge through rigorous research', sections: ['research','publications','lab','collaborations','contact'] },
  { id: 'student',     icon: '🎓', label: 'Student',       desc: 'Portfolio / CV site',    cta: 'View My Work',       nav: ['Projects','Skills','About','Resume','Contact'], hero: 'Ready to build something great together', sections: ['projects','skills','education','certifications','contact'] },
  { id: 'salon',       icon: '💇', label: 'Salon / Spa',   desc: 'Beauty & wellness',      cta: 'Book Treatment',     nav: ['Services','Gallery','Team','Pricing','Contact'], hero: 'Your haven of beauty and relaxation', sections: ['services','gallery','team','pricing','testimonials','booking'] },
  { id: 'realestate',  icon: '🏠', label: 'Real Estate',   desc: 'Property / agency',      cta: 'View Properties',    nav: ['Properties','Services','About','Testimonials','Contact'], hero: 'Finding you the perfect place to call home', sections: ['listings','services','team','testimonials','valuation','contact'] },
  { id: 'fitness',     icon: '💪', label: 'Fitness',       desc: 'Gym / trainer',          cta: 'Join Now',           nav: ['Programs','Trainers','Pricing','Success Stories','Contact'], hero: 'Transform your body and mind', sections: ['programs','trainers','pricing','success-stories','schedule','contact'] },
  { id: 'generic',     icon: '🌐', label: 'General',       desc: 'Any other business',     cta: 'Get in Touch',       nav: ['About','Services','Gallery','Testimonials','Contact'], hero: 'Welcome to our website', sections: ['services','about','gallery','testimonials','contact'] },
];
let selectedClassification = 'generic';

// ── Auth guard ─────────────────────────────────────────────────────────────
if (!token) { window.location.href = '/login'; }

// Superuser → admin console; customer → no dashboard
(function checkStoredRole() {
  const r = localStorage.getItem('wb_role');
  if (r === 'superuser') { window.location.href = '/console'; }
  if (r === 'customer')  { window.location.href = '/'; }
})();

// ── Helpers ────────────────────────────────────────────────────────────────
function headers() { return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }; }

async function apiFetch(path, opts = {}) {
  const r = await fetch(API + path, { headers: headers(), cache: 'no-store', ...opts });
  if (r.status === 401) { logout(); return null; }
  if (!r.ok) {
    try {
      const err = await r.json();
      apiFetch._lastError = err?.detail || `HTTP ${r.status}`;
    } catch { apiFetch._lastError = `HTTP ${r.status}`; }
    return null;
  }
  apiFetch._lastError = null;
  return r.json();
}

// toast() is provided by /static/frontend/toast.js (loaded before this script)
// Kept as a no-op fallback in case the external script fails to load.
if (typeof toast === 'undefined') {
  window.toast = function toast(msg, success = true) {
    const t = document.getElementById('toast');
    if (!t) { console.warn('[toast]', msg); return; }
    t.textContent = msg;
    t.style.background = success ? 'var(--accent, #6366f1)' : 'var(--danger, #ef4444)';
    t.classList.add('show');
    clearTimeout(t._hideTimer);
    t._hideTimer = setTimeout(() => t.classList.remove('show'), 3000);
  };
}

/**
 * Returns a debounced version of fn that delays invocation by `wait` ms.
 * Useful for oninput handlers that trigger expensive DOM updates.
 */
function _debounce(fn, wait = 120) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}

// Debounced wrappers for hot oninput paths
const _previewFieldStyleDebounced = _debounce((fid) => previewFieldStyle(fid), 120);
const _previewBgDebounced         = _debounce(() => previewBg(), 120);

function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  const item = [...document.querySelectorAll('.nav-item')].find(n => n.getAttribute('onclick')?.includes(`'${id}'`));
  if (item) item.classList.add('active');
  location.hash = id;
  if (id === 'websites') loadAllSites();
  if (id === 'cart-items') { populateImportSiteDropdown(); loadCartItems(); switchProdTab('services'); }
  if (id === 'billing') loadBilling();
  if (id === 'build') applyBuildPlanRestrictions();
  if (id === 'feedback') loadFeedback();
  if (id === 'monitoring') loadMonitoring();
  if (id === 'team') loadTeam();
  if (id === 'clients') loadClients();
  if (id === 'coupons') initCouponPage();
  if (id === 'notifications') initCampaignPage();
  if (id === 'staging') loadStagingWebsites();
  if (id === 'edit-website') loadEditWebsiteOptions();
}

function logout() {
  localStorage.removeItem('wb_token');
  localStorage.removeItem('wb_user_id');
  localStorage.removeItem('wb_plan');
  localStorage.removeItem('wb_role');
  window.location.href = '/login';
}

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  currentUser = await apiFetch('/auth/me');
  if (!currentUser) return;
  planFeatures = await apiFetch('/payments/plan-features') || {};
  document.getElementById('userEmail').textContent = currentUser.email;
  document.getElementById('statPlan').textContent = (currentUser.plan || '—').toUpperCase();
  buildThemeGrid();
  buildClassGrids();

  const role = currentUser.role || 'app_user';
  localStorage.setItem('wb_role', role);

  // Role → badge style
  const badge = document.getElementById('planBadge');
  const roleColors = { superuser: '#dc2626', app_user: 'var(--accent)', client: '#0d9488', customer: '#6b7280' };
  badge.textContent = role;
  badge.style.background = roleColors[role] || 'var(--accent)';

  // Redirect if wrong page for role
  if (role === 'superuser') { window.location.href = '/console'; return; }
  if (role === 'customer')  { window.location.href = '/'; return; }

  // Hide nav items not permitted for this role
  document.querySelectorAll('.nav-item[data-roles]').forEach(n => {
    const allowed = n.dataset.roles.split(',');
    if (!allowed.includes(role)) n.style.display = 'none';
  });

  // Clients cannot see the Client Services tab (they can't manage their own permissions)
  if (role === 'client') {
    const svcTab = document.getElementById('prodTab-services');
    if (svcTab) svcTab.style.display = 'none';
  }

  // Legacy permission-based hiding for sub-users (app_user team)
  const perms = currentUser.permissions;
  if (Array.isArray(perms) && perms.length > 0 && role === 'app_user') {
    document.querySelectorAll('.nav-item[data-page]').forEach(n => {
      const page = n.dataset.page;
      if (!perms.includes(page)) n.style.display = 'none';
    });
  }

  loadOverview();
  const hash = location.hash.replace('#', '');
  const validPages = ['overview','websites','build','staging','edit-website','cart-items','billing','feedback','monitoring','team','coupons','notifications','clients'];
  if (hash && validPages.includes(hash)) showPage(hash);
  else showPage('overview');
}

// ── Helpers ────────────────────────────────────────────────────────────────
/** Fetch all websites for the current user (unwraps paginated envelope). */
async function _fetchMyWebsites() {
  const data = await apiFetch('/websites/my?limit=200') || {};
  return Array.isArray(data) ? data : (data.items || []);
}

// ── Overview ───────────────────────────────────────────────────────────────
async function loadOverview() {
  websites = await _fetchMyWebsites();
  document.getElementById('statSites').textContent = websites.length;
  document.getElementById('statPublished').textContent = websites.filter(w => w.status === 'published').length;
  const tbody = document.getElementById('recentSitesBody');
  if (!websites.length) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:var(--muted);text-align:center;padding:24px">No websites yet — <a href="javascript:showPage('build')" style="color:var(--accent)">build one now</a>!</td></tr>`;
    return;
  }
  tbody.innerHTML = websites.slice(0, 5).map(siteRowReadOnly).join('');
  loadCartItemCount();
}

async function loadCartItemCount() {
  let total = 0;
  for (const w of websites) {
    const prods = await apiFetch(`/shop/cart-items/${w.website_id}`) || [];
    total += prods.length;
  }
  document.getElementById('statCartItems').textContent = total;
}

function featureBadges(w) {
  const badges = [];
  try {
    const cf = typeof w.cart_features === 'string' ? JSON.parse(w.cart_features) : (w.cart_features || []);
    if (cf.length) badges.push(`<span class="tag published" style="font-size:.72rem;padding:2px 8px">🛒 Cart</span>`);
  } catch(e) {}
  if (w.enable_livestream) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#fff0f0;color:#dc2626">🟥 Live</span>`);
  if (w.enable_blog) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#f0fdf4;color:#15803d">📝 Blog</span>`);
  if (w.enable_chatbot) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#e8f4fd;color:#1a73e8">💬 Bot</span>`);
  return badges.join(' ') || '<span style="color:var(--muted);font-size:.82rem">—</span>';
}

function statusBadge(status) {
  if (status === 'inactive') {
    return `<span class="tag" style="background:#fff3cd;color:#856404">⏸ Offline</span>`;
  }
  if (status === 'published' || status === 'built' || status === 'live') {
    return `<span class="tag published">🟢 Live</span>`;
  }
  if (status === 'error') {
    return `<span class="tag danger">❌ Error</span>`;
  }
  return `<span class="tag draft">📝 Draft</span>`;
}

function siteRowReadOnly(w) {
  const domainDisplay = w.domain
    ? `<a href="https://${w.domain.replace(/^https?:\/\//,'')}" target="_blank" style="color:var(--accent);font-size:.85rem">${w.domain}</a>`
    : `<span style="color:var(--muted);font-size:.82rem">Not set</span>`;
  const dateStr = w.created_at ? w.created_at.replace('T', ' ').slice(0, 16) : '—';
  const changedStr = w.updated_at ? w.updated_at.replace('T', ' ').slice(0, 16) : dateStr;
  const isInactive = w.status === 'inactive';
  return `<tr style="${isInactive ? 'opacity:.6' : ''}">
    <td style="font-weight:600">${w.name || '—'}</td>
    <td>${domainDisplay}</td>
    <td style="text-transform:capitalize">${w.theme || '—'}</td>
    <td>${featureBadges(w)}</td>
    <td>${statusBadge(w.status)}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${dateStr}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${changedStr}</td>
  </tr>`;
}

function refreshRow(id) {
  const w = websites.find(x => x.website_id === id);
  const row = document.getElementById('row-' + id);
  if (!w || !row) return;
  // Flash the row to signal an update
  row.style.transition = 'background .15s';
  row.style.background = 'rgba(99,102,241,.12)';
  setTimeout(() => { row.style.background = ''; }, 600);
  // Re-render the full row in-place
  const newRow = document.createElement('tbody');
  newRow.innerHTML = siteRow(w);
  row.replaceWith(newRow.firstChild);
}

function siteRow(w) {
  const domainDisplay = w.domain
    ? `<a href="https://${w.domain.replace(/^https?:\/\//,'')}" target="_blank" style="color:var(--accent);font-size:.85rem">${w.domain}</a>`
    : `<span style="color:var(--muted);font-size:.82rem">Not set</span>`;
  const dateStr = w.created_at ? w.created_at.replace('T', ' ').slice(0, 16) : '—';
  const changedStr = w.updated_at ? w.updated_at.replace('T', ' ').slice(0, 16) : (w.created_at ? w.created_at.replace('T', ' ').slice(0, 16) : '—');
  const isInactive = w.status === 'inactive';
  return `<tr id="row-${w.website_id}" style="${isInactive?'opacity:.6':''}">
    <td style="font-weight:600">${w.name || '—'}</td>
    <td>${domainDisplay}</td>
    <td style="text-transform:capitalize">${w.theme || '—'}</td>
    <td>${featureBadges(w)}</td>
    <td id="status-${w.website_id}">${statusBadge(w.status)}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${dateStr}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${changedStr}</td>
    <td id="actions-${w.website_id}" style="white-space:nowrap">
      <button class="btn btn-secondary btn-sm" ${isInactive?'disabled title="Activate the website to view"':"onclick=\"viewSite('" + w.website_id + "')\" title=\"Open website\""}>👁 View</button>
      <button class="btn btn-secondary btn-sm" style="margin-left:4px" ${isInactive?'disabled title="Activate the website to edit"':"onclick=\"editSite('" + w.website_id + "')\" title=\"Edit details\""}>✏️ Edit</button>
      <button class="btn ${isInactive?'btn-primary':'btn-secondary'} btn-sm" style="${!isInactive?'margin-left:4px':''}" onclick="deactivateSite('${w.website_id}','${w.status}')">${isInactive?'▶ Activate':'⏸ Deactivate'}</button>
      <button class="btn btn-danger btn-sm" style="margin-left:4px" ${!isInactive?'disabled title="Deactivate the website first to delete"':'title="Delete permanently"'} onclick="${isInactive?`deleteSite('${w.website_id}')`:'void(0)'}">🗑 Delete</button>
    </td>
  </tr>`;
}

function viewSite(id) {
  const w = websites.find(x => x.website_id === id);
  if (!w) return;
  if (w.domain) {
    const url = w.domain.startsWith('http') ? w.domain : `https://${w.domain}`;
    window.open(url, '_blank');
  } else if (w.s3_url) {
    window.open(w.s3_url, '_blank');
  } else if (w.live_url) {
    // Published site URL
    window.open(w.live_url, '_blank');
  } else if (w.local_path) {
    // Staging build — strip 'output/' prefix for URL
    const slug = w.local_path.replace(/^output\//, '').replace(/\/$/, '');
    window.open(`/output/${slug}/index.html`, '_blank');
  } else if (w.name) {
    // Fallback: derive slug from site name
    const slug = w.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
    window.open(`/output/staging/${slug}/index.html`, '_blank');
  } else {
    toast('No URL available for this site yet', false);
  }
}

function editSite(id) {
  const w = websites.find(x => x.website_id === id);
  if (!w) return;
  document.getElementById('editSiteId').value = w.website_id;
  document.getElementById('editSiteName').value = w.name || '';
  document.getElementById('editSiteDomain').value = w.domain || '';
  document.getElementById('editSiteTheme').value = w.theme || 'modern';
  openModal('editSiteModal');
}

async function saveEditSite() {
  const id = document.getElementById('editSiteId').value;
  const payload = {
    name:   document.getElementById('editSiteName').value.trim() || undefined,
    domain: document.getElementById('editSiteDomain').value.trim() || undefined,
    theme:  document.getElementById('editSiteTheme').value || undefined,
  };
  const r = await fetch(`${API}/websites/${id}`, {
    method: 'PATCH', headers: { ...headers(), 'Content-Type':'application/json' },
    body: JSON.stringify(payload)
  });
  if (r.ok) {
    toast('Website updated ✅');
    closeModal('editSiteModal');
    // Update in-memory and refresh just this row
    const idx = websites.findIndex(x => x.website_id === id);
    if (idx !== -1) {
      if (payload.name) websites[idx].name = payload.name;
      if (payload.domain) websites[idx].domain = payload.domain;
      if (payload.theme) websites[idx].theme = payload.theme;
      websites[idx].updated_at = new Date().toISOString().replace('T', ' ').slice(0, 16);
    }
    refreshRow(id);
  } else {
    toast('Update failed', false);
  }
}

function showConfirm({ icon, title, msg, btnLabel, btnClass, onConfirm }) {
  document.getElementById('confirmIcon').textContent = icon || '';
  document.getElementById('confirmTitle').textContent = title;
  document.getElementById('confirmMsg').textContent = msg;
  const btn = document.getElementById('confirmOkBtn');
  btn.textContent = btnLabel || 'Confirm';
  btn.className = `btn ${btnClass || 'btn-primary'}`;
  btn.onclick = () => { closeModal('confirmModal'); onConfirm(); };
  openModal('confirmModal');
}

async function deactivateSite(id, currentStatus) {
  const goingOffline = currentStatus !== 'inactive';
  const newStatus = goingOffline ? 'inactive' : 'built';
  showConfirm({
    icon: goingOffline ? '⏸' : '▶',
    title: goingOffline ? 'Deactivate Website?' : 'Activate Website?',
    msg: goingOffline ? 'The website will show as Offline and visitors will not see it.' : 'The website will go Live and be visible to visitors.',
    btnLabel: goingOffline ? 'Deactivate' : 'Activate',
    btnClass: goingOffline ? 'btn-danger' : 'btn-primary',
    onConfirm: async () => {
      const r = await fetch(`${API}/websites/${id}`, {
        method: 'PATCH', cache: 'no-store', headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (r.ok) {
        toast(goingOffline ? '⏸ Website is now Offline' : '🟢 Website is now Live');
        const idx = websites.findIndex(x => x.website_id === id);
        if (idx !== -1) {
          websites[idx].status = newStatus;
          websites[idx].updated_at = new Date().toISOString().replace('T', ' ').slice(0, 16);
        }
        refreshRow(id);
      } else {
        toast('Action failed', false);
      }
    }
  });
}

async function deleteSite(id) {
  showConfirm({
    icon: '🗑',
    title: 'Delete Website?',
    msg: 'This will permanently delete the website and all its data. This cannot be undone.',
    btnLabel: 'Delete',
    btnClass: 'btn-danger',
    onConfirm: async () => {
      const r = await fetch(`${API}/websites/${id}`, { method: 'DELETE', headers: headers() });
      if (r.ok) { toast('Website deleted 🗑'); await loadAllSites(); loadOverview(); }
      else toast('Could not delete', false);
    }
  });
}

// ── All Sites ──────────────────────────────────────────────────────────────
async function loadAllSites() {
  websites = await _fetchMyWebsites();
  const tbody = document.getElementById('allSitesBody');
  if (!tbody) return;
  if (!websites.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">No websites yet — <a href="javascript:showPage('build')" style="color:var(--accent)">build one now</a>!</td></tr>`;
    return;
  }
  tbody.innerHTML = websites.map(siteRow).join('');
}

// ── Build Website ──────────────────────────────────────────────────────────
function buildThemeGrid() {
  document.getElementById('themeGrid').innerHTML = THEMES.map(t => `
    <div class="theme-card ${t.id === selectedTheme ? 'selected' : ''}" id="tc-${t.id}" onclick="selectTheme('${t.id}')">
      <div class="swatch" style="background:${t.gradient}">
        <div class="swatch-fonts">
          <div class="sh">${t.fontHeading}</div>
          <div class="sb">${t.fontBody}</div>
        </div>
        <span class="selected-badge">✓ Selected</span>
      </div>
      <div class="card-body">
        <div class="card-label">${t.label}</div>
        <div class="card-desc">${t.desc}</div>
        <button class="preview-btn" onclick="event.stopPropagation();openThemePreview('${t.id}')">👁 Preview</button>
      </div>
    </div>`).join('');
}

function selectTheme(id) {
  selectedTheme = id;
  document.querySelectorAll('.theme-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById('tc-' + id);
  if (card) card.classList.add('selected');
}

let currentPreviewTheme = 'modern';
let currentPreviewClass = 'generic';

// ── Classification grid builders ───────────────────────────────────────────
function classCardHTML(c, gridId) {
  return `<div class="class-card ${c.id === selectedClassification ? 'selected' : ''}" id="${gridId}-cc-${c.id}" onclick="selectClassification('${c.id}')">
    <div class="class-icon">${c.icon}</div>
    <div class="class-label">${c.label}</div>
    <div class="class-desc">${c.desc}</div>
    <span class="selected-badge">✓</span>
  </div>`;
}

function buildClassGrids() {
  ['importClassGrid','agentClassGrid'].forEach(gid => {
    const el = document.getElementById(gid);
    if (el) el.innerHTML = CLASSIFICATIONS.map(c => classCardHTML(c, gid)).join('');
  });
}

function selectClassification(id) {
  selectedClassification = id;
  document.querySelectorAll('.class-card').forEach(c => c.classList.remove('selected'));
  ['importClassGrid','agentClassGrid'].forEach(gid => {
    const card = document.getElementById(`${gid}-cc-${id}`);
    if (card) card.classList.add('selected');
  });
  // Refresh preview if modal is open
  if (document.getElementById('themePreviewModal').classList.contains('open')) {
    currentPreviewClass = id;
    refreshPreview();
  }
}

// ── Theme grid builders ─────────────────────────────────────────────────────
function themeCardHTML(t, gridId) {
  return `
    <div class="theme-card ${t.id === selectedTheme ? 'selected' : ''}" id="${gridId}-tc-${t.id}" onclick="selectTheme('${t.id}')">
      <div class="swatch" style="background:${t.gradient}">
        <div class="swatch-fonts">
          <div class="sh">${t.fontHeading}</div>
          <div class="sb">${t.fontBody}</div>
        </div>
        <span class="selected-badge">✓ Selected</span>
      </div>
      <div class="card-body">
        <div class="card-label">${t.label}</div>
        <div class="card-desc">${t.desc}</div>
        <button class="preview-btn" onclick="event.stopPropagation();openThemePreview('${t.id}')">👁 Preview</button>
      </div>
    </div>`;
}

function buildThemeGrid() {
  const grids = [
    { id: 'themeGrid',       prefix: 'main' },
    { id: 'importThemeGrid', prefix: 'import' },
  ];
  grids.forEach(({ id, prefix }) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = THEMES.map(t => themeCardHTML(t, prefix)).join('');
  });
}

function selectTheme(id) {
  selectedTheme = id;
  document.querySelectorAll('.theme-card').forEach(c => c.classList.remove('selected'));
  ['main','import'].forEach(prefix => {
    const card = document.getElementById(`${prefix}-tc-${id}`);
    if (card) card.classList.add('selected');
  });
  if (document.getElementById('themePreviewModal').classList.contains('open')) {
    currentPreviewTheme = id;
    refreshPreview();
  }
}

// ── Preview modal ───────────────────────────────────────────────────────────
function openThemePreview(themeId) {
  currentPreviewTheme = themeId || selectedTheme;
  currentPreviewClass = selectedClassification;
  buildPreviewPills();
  refreshPreview();
  document.getElementById('themePreviewModal').classList.add('open');
}

function closeThemePreview() {
  document.getElementById('themePreviewModal').classList.remove('open');
}

function selectFromPreview() {
  selectTheme(currentPreviewTheme);
  selectClassification(currentPreviewClass);
  closeThemePreview();
}

function buildPreviewPills() {
  // Theme pills
  document.getElementById('previewThemePills').innerHTML =
    '<span style="font-size:.7rem;color:#8892a4;margin-right:4px">THEME:</span>' +
    THEMES.map(t => `<button class="preview-pill ${t.id === currentPreviewTheme ? 'active' : ''}" id="tpill-${t.id}" onclick="previewSwitchTheme('${t.id}')">${t.label}</button>`).join('');
  // Class pills
  document.getElementById('previewClassPills').innerHTML =
    CLASSIFICATIONS.map(c => `<button class="preview-pill ${c.id === currentPreviewClass ? 'active' : ''}" id="cpill-${c.id}" onclick="previewSwitchClass('${c.id}')">${c.icon} ${c.label}</button>`).join('');
}

function previewSwitchTheme(id) {
  currentPreviewTheme = id;
  document.querySelectorAll('[id^="tpill-"]').forEach(b => b.classList.remove('active'));
  const pill = document.getElementById('tpill-' + id);
  if (pill) pill.classList.add('active');
  refreshPreview();
}

function previewSwitchClass(id) {
  currentPreviewClass = id;
  document.querySelectorAll('[id^="cpill-"]').forEach(b => b.classList.remove('active'));
  const pill = document.getElementById('cpill-' + id);
  if (pill) pill.classList.add('active');
  refreshPreview();
}

function refreshPreview() {
  const t = THEMES.find(x => x.id === currentPreviewTheme) || THEMES[0];
  const c = CLASSIFICATIONS.find(x => x.id === currentPreviewClass) || CLASSIFICATIONS[CLASSIFICATIONS.length - 1];
  document.getElementById('themePreviewTitle').textContent = `${c.icon} ${c.label} · ${t.label} Theme — Preview`;
  document.getElementById('themePreviewFrame').innerHTML = buildThemePreviewHTML(t, c);
}

function buildThemePreviewHTML(t, c) {
  const isDark = t.bg === '#0f172a';
  const cardBg = isDark ? '#1e293b' : '#fff';
  const cardBorder = isDark ? '#334155' : '#e2e8f0';
  const mutedText = isDark ? '#94a3b8' : '#718096';
  const navItems = c.nav.slice(0, 5).map(n => `<span>${n}</span>`).join('');
  // Build section items based on classification sections
  const sectionItems = (c.sections.slice(0, 3)).map((s, i) => {
    const label = s.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    const kw = s.replace(/-/g, '+');
    return `<div style="background:${cardBg};border:1px solid ${cardBorder};border-radius:${t.radius};padding:18px;box-shadow:${t.shadow}">
      <img src="https://source.unsplash.com/featured/400x220/?${kw}" style="width:100%;height:110px;object-fit:cover;border-radius:6px;margin-bottom:10px" loading="lazy" alt="${label}">
      <h3 style="font-family:${t.fontHeading},serif;font-size:.9rem;font-weight:700;margin-bottom:5px;color:${isDark ? t.text : t.primary}">${label}</h3>
      <p style="font-size:.75rem;color:${mutedText};line-height:1.5">Tailored ${label.toLowerCase()} content for your ${c.label.toLowerCase()} website.</p>
    </div>`;
  }).join('');

  return `<div style="font-family:${t.fontBody},sans-serif;background:${t.bg};color:${t.text};font-size:14px">
    <nav style="background:${t.primary};padding:12px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:10">
      <span style="font-family:${t.fontHeading},serif;color:#fff;font-weight:700;font-size:1.1rem">${c.icon} YourBrand</span>
      <span style="display:flex;gap:16px;font-size:.78rem;color:rgba(255,255,255,.8)">${navItems}</span>
      <button style="background:${t.accent};color:#fff;border:none;padding:7px 16px;border-radius:${t.radius};font-weight:700;font-size:.75rem;cursor:pointer">${c.cta}</button>
    </nav>
    <div style="background:${t.gradient};padding:48px 28px;text-align:center">
      <div style="display:inline-block;background:rgba(255,255,255,.15);border-radius:20px;padding:4px 14px;font-size:.72rem;color:rgba(255,255,255,.9);margin-bottom:14px;font-weight:600">${c.icon} ${c.label} Website</div>
      <h1 style="font-family:${t.fontHeading},serif;color:#fff;font-size:1.9rem;font-weight:700;margin-bottom:12px;line-height:1.2">${c.hero}</h1>
      <p style="color:rgba(255,255,255,.8);max-width:440px;margin:0 auto 22px;font-size:.88rem;line-height:1.6">Built with the <strong>${t.label}</strong> theme. Every section is structured for your ${c.label} audience.</p>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
        <button style="background:${t.accent};color:#fff;border:none;padding:10px 24px;border-radius:${t.radius};font-weight:700;font-size:.85rem;cursor:pointer">${c.cta}</button>
        <button style="background:transparent;color:#fff;border:2px solid rgba(255,255,255,.6);padding:10px 24px;border-radius:${t.radius};font-weight:700;font-size:.85rem;cursor:pointer">Learn More</button>
      </div>
    </div>
    <div style="padding:28px 24px;">
      <h2 style="font-family:${t.fontHeading},serif;font-size:1.1rem;font-weight:700;margin-bottom:16px;color:${t.primary}">Key Sections</h2>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px">${sectionItems}</div>
    </div>
    <div style="background:${t.primary};padding:24px;text-align:center">
      <h3 style="font-family:${t.fontHeading},serif;color:#fff;font-size:1rem;margin-bottom:8px">Ready to build your ${c.label} website?</h3>
      <button style="background:${t.accent};color:#fff;border:none;padding:9px 24px;border-radius:${t.radius};font-weight:700;font-size:.82rem;cursor:pointer">${c.cta}</button>
    </div>
    <footer style="background:${isDark ? '#020617' : '#111827'};color:rgba(255,255,255,.45);text-align:center;padding:14px;font-size:.72rem">
      © ${new Date().getFullYear()} YourBrand · ${c.label} · ${t.label} Theme
    </footer>
  </div>`;
}

function toggleCartFeatures() {
  const enabled = document.getElementById('buildCart').checked;
  document.getElementById('cartFeaturesPanel').style.display = enabled ? 'block' : 'none';
}

async function applyBuildPlanRestrictions() {
  const plan = currentUser?.plan || 'free';
  // Always fetch fresh from API; fall back to cached planFeatures; then deny-by-default
  const defaultFeatures = { web_search: true, social_search: false, shopping_cart: false, livestream: false, blog: false, chatbot: false };
  let allFeatures = planFeatures;
  if (!allFeatures || !allFeatures[plan]) {
    allFeatures = await apiFetch('/payments/plan-features') || {};
    if (allFeatures && Object.keys(allFeatures).length) planFeatures = allFeatures; // update cache
  }
  const features = (allFeatures && allFeatures[plan]) ? allFeatures[plan] : defaultFeatures;

  const mapping = [
    { row: 'toggleRowCart',       input: 'buildCart',         feature: 'shopping_cart', label: 'Enable Shopping Cart' },
    { row: 'toggleRowSocial',     input: 'buildSocialSearch', feature: 'social_search', label: 'Auto-search Social Profiles' },
    { row: 'toggleRowLivestream', input: 'buildLivestream',   feature: 'livestream',    label: 'Enable Live Stream' },
    { row: 'toggleRowBlog',       input: 'buildBlog',         feature: 'blog',          label: 'Enable Blog' },
    { row: 'toggleRowChatbot',    input: 'buildChatbot',      feature: 'chatbot',       label: 'Enable Chatbot' },
  ];

  mapping.forEach(({ row, input, feature }) => {
    const allowed = !!features[feature];
    const rowEl = document.getElementById(row);
    const inputEl = document.getElementById(input);
    if (rowEl) {
      rowEl.classList.toggle('locked', !allowed);
      rowEl.title = allowed ? '' : 'Upgrade your plan to unlock this feature';
    }
    if (inputEl) {
      inputEl.disabled = !allowed;
      if (!allowed) {
        inputEl.checked = false;
        // hide any dependent panel (e.g. cart features panel)
        if (input === 'buildCart') document.getElementById('cartFeaturesPanel').style.display = 'none';
      }
    }
  });
}

function toggleSocialSearch() {
  const on = document.getElementById('buildSocialSearch').checked;
  // When agent will auto-search, dim the manual URL inputs and show info hint
  ['buildInstagram', 'buildFacebook', 'buildLinkedin'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.disabled = on; el.style.opacity = on ? '.4' : '1'; }
  });
  document.getElementById('socialSearchRow').style.display = on ? 'block' : 'none';
}

function getSelectedCartFeatures() {
  return [...document.querySelectorAll('input[name="cartFeature"]:checked')].map(el => el.value);
}

function resetBuildForm() {
  ['buildName', 'buildNiche', 'buildReq'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('buildPages').value = '3';
  document.getElementById('buildColor').value = '#6366f1';
  document.getElementById('buildCart').checked = false;
  document.getElementById('cartFeaturesPanel').style.display = 'none';
  document.getElementById('buildWebSearch').checked = true;
  document.getElementById('buildLivestream').checked = false;
  document.getElementById('buildBlog').checked = false;
  document.getElementById('buildChatbot').checked = false;
  selectedTheme = 'modern';
  selectedClassification = 'generic';
  buildThemeGrid();
  buildClassGrids();
}

async function fetchWebsiteInfo() {
  const url = document.getElementById('existingUrl').value.trim();
  if (!url) { toast('Please enter a URL', false); return; }

  const btn = document.getElementById('fetchUrlBtn');
  const statusEl = document.getElementById('fetchUrlStatus');
  btn.disabled = true;
  btn.textContent = '⏳ Fetching…';
  statusEl.style.display = 'block';
  statusEl.style.color = 'var(--muted)';
  statusEl.textContent = 'Scraping website…';

  try {
    const data = await apiFetch('/websites/scrape-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });

    if (!data) throw new Error('Empty response');

    // Pre-fill form fields with scraped data
    if (data.title && !document.getElementById('buildName').value)
      document.getElementById('buildName').value = data.title;

    if (data.description && !document.getElementById('buildReq').value)
      document.getElementById('buildReq').value = data.description;

    if (data.emails?.length && !document.getElementById('buildEmail').value)
      document.getElementById('buildEmail').value = data.emails[0];

    if (data.phones?.length && !document.getElementById('buildPhone').value)
      document.getElementById('buildPhone').value = data.phones[0];

    if (data.headings?.length && !document.getElementById('buildCategories').value) {
      // Use headings as category hints (max 5, short ones)
      const hints = data.headings.filter(h => h.length < 40).slice(0, 5);
      if (hints.length) document.getElementById('buildCategories').value = hints.join(', ');
    }

    const summary = [
      data.title ? `✅ Title: ${data.title}` : null,
      data.emails?.length ? `📧 Email: ${data.emails[0]}` : null,
      data.phones?.length ? `📞 Phone: ${data.phones[0]}` : null,
      data.colors?.length ? `🎨 ${data.colors.length} brand colour(s) detected` : null,
    ].filter(Boolean).join(' · ');

    statusEl.style.color = '#22c55e';
    statusEl.textContent = summary || '✅ Info extracted. Form pre-filled.';
    toast('Website info imported! Switching to Agentic Build tab…');
    setTimeout(() => switchBuildTab('agent'), 800);
  } catch (err) {
    statusEl.style.color = '#ef4444';
    statusEl.textContent = `❌ ${err.message || 'Failed to fetch website info.'}`;
    toast('Failed to fetch website info', false);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Fetch Info';
  }
}

async function buildWebsite() {
  const name = document.getElementById('buildName').value.trim();
  const requirements = document.getElementById('buildReq').value.trim();
  if (!name || !requirements) { toast('Name and requirements are required', false); return; }

  const rawCategories = document.getElementById('buildCategories')?.value.trim();
  const categories = rawCategories ? rawCategories.split(',').map(c => c.trim()).filter(Boolean) : undefined;
  const location = document.getElementById('buildLocation')?.value.trim() || undefined;
  const email = document.getElementById('buildEmail')?.value.trim() || undefined;
  const phone = document.getElementById('buildPhone')?.value.trim() || undefined;

  const parseSocial = id => {
    const raw = document.getElementById(id)?.value.trim();
    if (!raw) return undefined;
    const parts = raw.split(',').map(s => s.trim()).filter(Boolean);
    return parts.length === 1 ? parts[0] : parts;
  };
  const instagram = parseSocial('buildInstagram');
  const facebook = parseSocial('buildFacebook');
  const linkedin = parseSocial('buildLinkedin');
  const social_links = (instagram || facebook || linkedin)
    ? { ...(instagram && { instagram }), ...(facebook && { facebook }), ...(linkedin && { linkedin }) }
    : undefined;
  const use_social_search = document.getElementById('buildSocialSearch')?.checked ?? false;
  const existing_website_url = document.getElementById('existingUrl')?.value.trim() || undefined;

  document.getElementById('buildProgress').style.display = 'block';
  document.getElementById('buildProgressMsg').textContent = '🔄 Generating your website — this may take 30–90 seconds…';

  const msgs = [
    '🧠 Analysing requirements…',
    '✍️ Writing content…',
    '🎨 Applying theme…',
    '🔗 Building pages…',
    '🚀 Finalising…',
  ];
  let mi = 0;
  const ticker = setInterval(() => {
    document.getElementById('buildProgressMsg').textContent = msgs[mi++ % msgs.length];
  }, 8000);

  // Step 1: create website record
  const cartEnabled = document.getElementById('buildCart').checked;
  const createPayload = {
    name,
    title: name,
    description: requirements.slice(0, 300),
    theme: selectedTheme,
    classification: selectedClassification,
    hosting_env: 's3',
    include_shopping_cart: cartEnabled,
    cart_features: cartEnabled ? getSelectedCartFeatures() : [],
    enable_chatbot: document.getElementById('buildChatbot').checked,
    enable_blog: document.getElementById('buildBlog').checked,
    enable_livestream: document.getElementById('buildLivestream').checked,
    num_pages: parseInt(document.getElementById('buildPages').value),
  };

  const created = await apiFetch('/websites', { method: 'POST', body: JSON.stringify(createPayload) });
  if (!created || !created.website_id) {
    clearInterval(ticker);
    const errMsg = apiFetch._lastError || 'Failed to create website record.';
    document.getElementById('buildProgressMsg').textContent = `❌ ${errMsg}`;
    toast(errMsg, false);
    return;
  }

  // Step 2: trigger AI build
  const buildPayload = {
    requirements,
    use_web_search: document.getElementById('buildWebSearch').checked,
    use_social_search,
    ...(categories?.length && { categories }),
    ...(location && { location }),
    ...(email && { email }),
    ...(phone && { phone }),
    ...(social_links && { social_links }),
    ...(existing_website_url && { existing_website_url }),
  };

  // Step 2: trigger build (returns immediately with job_id)
  const result = await apiFetch(`/websites/${created.website_id}/build`, {
    method: 'POST',
    body: JSON.stringify(buildPayload),
  });
  clearInterval(ticker);

  if (!result || !result.job_id) {
    const errMsg = apiFetch._lastError || 'Failed to queue build.';
    document.getElementById('buildProgressMsg').textContent = `❌ ${errMsg}`;
    document.getElementById('buildSpinner').style.display = 'none';
    toast(errMsg, false);
    return;
  }

  // Step 3: stream build-status via SSE until complete
  const stageLabels = {
    queued:  { msg: '⏳ Build queued — waiting for worker…',     pct: 10 },
    running: { msg: '🤖 AI agents are building your website…',   pct: 55 },
    built:   { msg: '✅ Website generated successfully!',         pct: 100 },
    error:   { msg: '❌ Build failed.',                           pct: 100 },
    timeout: { msg: '⚠️ Build is taking longer than expected. Check My Websites for status.', pct: 100 },
  };

  const setStage = (status, errorMsg) => {
    const s = stageLabels[status] || stageLabels.queued;
    document.getElementById('buildProgressMsg').textContent = errorMsg ? `❌ ${errorMsg}` : s.msg;
    document.getElementById('buildProgressBar').style.width = s.pct + '%';
    document.getElementById('buildStageLabel').textContent  = 'Stage: ' + status;
    if (['built', 'error', 'timeout'].includes(status)) {
      document.getElementById('buildSpinner').style.display = 'none';
    }
  };

  setStage('queued');

  await new Promise(resolve => {
    const es = new EventSource(
      `${API}/../api/v1/websites/${created.website_id}/build-stream?token=${encodeURIComponent(token)}`
    );
    es.onmessage = async (e) => {
      try {
        const data = JSON.parse(e.data);
        const status = data.build_status || 'queued';
        setStage(status, data.error);
        if (['built', 'error', 'timeout', 'not_found'].includes(status)) {
          es.close();
          if (status === 'built') {
            toast('Website built! Opening Staging Area…');
            setTimeout(async () => {
              resetBuildForm();
              await loadAllSites();
              await loadStagingWebsites();
              showPage('staging');
              loadStagedSite(created.website_id);
            }, 1500);
          } else if (status === 'error') {
            toast(data.error || 'Build failed. Please try again.', false);
          }
          resolve();
        }
      } catch (_) {}
    };
    es.onerror = () => { es.close(); resolve(); };
  });
}

// ── Products ───────────────────────────────────────────────────────────────
let allCartItems = [];

function _cartSites() {
  return (websites || []).filter(w => {
    try { return JSON.parse(w.cart_features || '[]').length > 0; }
    catch { return false; }
  });
}

function populateImportSiteDropdown() {
  const cartSites = _cartSites();
  const impSel = document.getElementById('importCatalogSite');
  if (!impSel) return;
  impSel.innerHTML = cartSites.length
    ? cartSites.map(w => `<option value="${w.website_id}">${w.name || w.website_name}</option>`).join('')
    : '<option value="">— No cart-enabled websites —</option>';
}

async function loadCartItems() {
  const tbody = document.getElementById('cartItemsBody');
  tbody.innerHTML = '<tr><td colspan="12" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';
  websites = await _fetchMyWebsites();

  const cartSites = _cartSites();
  populateImportSiteDropdown();

  if (!cartSites.length) {
    tbody.innerHTML = `<tr><td colspan="12" style="color:var(--muted);text-align:center;padding:24px">
      No websites with shopping cart enabled.<br>
      <small style="font-size:.8rem">When building a website, enable the <strong>Shopping Cart</strong> feature to manage cart items here.</small>
    </td></tr>`;
    return;
  }

  allCartItems = [];
  for (const w of cartSites) {
    const prods = await apiFetch(`/shop/cart-items/${w.website_id}?include_inactive=true`) || [];
    prods.forEach(p => allCartItems.push({ ...p, siteName: w.name || w.website_name }));
  }
  renderCartItems(allCartItems);
}

function filterCartItems() {
  const cat = (document.getElementById('cartFilterCategory').value || '').toLowerCase();
  const min = parseFloat(document.getElementById('cartFilterMin').value) || 0;
  const max = parseFloat(document.getElementById('cartFilterMax').value) || Infinity;
  const flashOnly = document.getElementById('cartFilterFlash').checked;
  const filtered = allCartItems.filter(p => {
    if (cat && !(p.category || '').toLowerCase().includes(cat)) return false;
    const price = parseFloat(p.price || 0);
    if (price < min || price > max) return false;
    if (flashOnly && !p.is_flash_offer) return false;
    return true;
  });
  renderCartItems(filtered);
}

function renderCartItems(rows) {
  const tbody = document.getElementById('cartItemsBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="12" style="color:var(--muted);text-align:center;padding:24px">No cart items found.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(p => {
    const img = p.image_url
      ? `<img src="${p.image_url}" style="width:44px;height:44px;object-fit:cover;border-radius:6px;cursor:pointer" onclick="viewCartItem('${p.product_id}')" loading="lazy">`
      : `<div style="width:44px;height:44px;background:var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:1.2rem">\ud83d\udce6</div>`;
    const price = `<strong>${p.currency || 'USD'} ${parseFloat(p.price || 0).toFixed(2)}</strong>`;
    const compare = p.compare_price && p.compare_price > 0
      ? `<span style="color:var(--muted);text-decoration:line-through;font-size:.82rem">${parseFloat(p.compare_price).toFixed(2)}</span>` : '\u2014';
    const disc = p.discount_pct && p.discount_pct > 0
      ? `<span class="tag" style="background:rgba(239,68,68,.12);color:var(--danger)">-${p.discount_pct}%</span>` : '\u2014';
    const flash = p.is_flash_offer ? '<span class="tag" style="background:rgba(251,146,60,.15);color:#f97316">\u26a1 Flash</span>' : '\u2014';
    const isActive = p.is_active === undefined ? true : !!p.is_active;
    const statusBadge = isActive
      ? '<span class="tag published">\u2714 Active</span>'
      : '<span class="tag draft">\u23f8 Disabled</span>';
    const toggleBtn = isActive
      ? `<button class="btn btn-sm" style="background:rgba(234,179,8,.15);color:#d97706;border:1px solid #d97706" onclick="toggleCartItem('${p.product_id}', false)" title="Disable">\u23f8</button>`
      : `<button class="btn btn-sm" style="background:rgba(34,197,94,.12);color:#16a34a;border:1px solid #16a34a" onclick="toggleCartItem('${p.product_id}', true)" title="Enable">\u25b6</button>`;
    const cat = p.category || p.category_name || '\u2014';
    return `<tr style="${isActive ? '' : 'opacity:.55'}">
      <td>${img}</td>
      <td style="max-width:160px">
        <div style="font-weight:600;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${(p.name||'').replace(/"/g,'&quot;')}">${p.name || '\u2014'}</div>
        ${p.description ? `<div style="font-size:.75rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:155px" title="${(p.description||'').replace(/"/g,'&quot;')}">${p.description}</div>` : ''}
      </td>
      <td style="font-size:.82rem;color:var(--muted)">${cat}</td>
      <td>${price}</td>
      <td>${compare}</td>
      <td>${disc}</td>
      <td style="font-size:.82rem">${p.currency || 'USD'}</td>
      <td style="font-size:.88rem">${p.stock_quantity ?? p.stock ?? 0}</td>
      <td>${flash}</td>
      <td>${statusBadge}</td>
      <td style="color:var(--muted);font-size:.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px">${p.siteName || ''}</td>
      <td style="white-space:nowrap">
        <div style="display:flex;gap:4px;flex-wrap:nowrap">
          <button class="btn btn-sm btn-secondary" onclick="viewCartItem('${p.product_id}')" title="View">\ud83d\udc41</button>
          <button class="btn btn-sm btn-secondary" onclick="editCartItem('${p.product_id}')" title="Edit">\u270f\ufe0f</button>
          ${toggleBtn}
          <button class="btn btn-danger btn-sm" onclick="deleteCartItem('${p.product_id}')" title="Remove">\ud83d\uddd1</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

function openAddCartItem() {
  const cartSites = _cartSites();
  const opts = cartSites.length
    ? cartSites.map(w => `<option value="${w.website_id}">${w.name || w.website_name}</option>`).join('')
    : '<option value="">— No cart-enabled websites —</option>';
  document.getElementById('prodSite').innerHTML = opts;
  openModal('cartItemModal');
}

async function addCartItem() {
  // Resolve image URL: prefer uploaded file, fall back to manual URL
  const imgFinal = document.getElementById('prodImageFinal').value.trim();
  const imgUrl   = document.getElementById('prodImageUrl')?.value.trim();
  const image_url = imgFinal || imgUrl || null;

  const payload = {
    website_id: document.getElementById('prodSite').value,
    name: document.getElementById('prodName').value.trim(),
    price: parseFloat(document.getElementById('prodPrice').value) || 0,
    compare_price: parseFloat(document.getElementById('prodCompare').value) || null,
    discount_pct: parseFloat(document.getElementById('prodDiscount').value) || 0,
    stock_quantity: parseInt(document.getElementById('prodStock').value) || 0,
    category: document.getElementById('prodCategory').value.trim(),
    description: document.getElementById('prodDesc').value.trim(),
    image_url,
    is_flash_offer: document.getElementById('prodFlash').checked ? 1 : 0,
    flash_offer_ends: document.getElementById('prodFlashEnds').value || null,
  };
  if (!payload.name) { toast('Cart item name required', false); return; }
  const r = await apiFetch('/shop/cart-items', { method: 'POST', body: JSON.stringify(payload) });
  if (r) {
    toast('Cart item added');
    closeModal('cartItemModal');
    // Reset image uploader
    document.getElementById('prodImageFinal').value = '';
    document.getElementById('imgPreviewWrap').style.display = 'none';
    document.getElementById('imgDropLabel').style.display = '';
    document.getElementById('imgUploadProgress').style.display = 'none';
    if (document.getElementById('prodImageUrl')) document.getElementById('prodImageUrl').value = '';
    switchImgTab('upload');
    loadCartItems();
  } else toast('Failed to add cart item', false);
}

async function deleteCartItem(id) {
  if (!confirm('Permanently remove this cart item? This cannot be undone.')) return;
  const r = await apiFetch(`/shop/cart-items/${id}`, { method: 'DELETE' });
  if (r) { toast('Cart item removed'); loadCartItems(); }
  else toast(`Failed to remove: ${apiFetch._lastError || 'unknown error'}`, false);
}

async function toggleCartItem(id, enable) {
  const r = await apiFetch(`/shop/cart-items/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: enable }),
  });
  if (r) { toast(enable ? 'Product enabled' : 'Product disabled'); loadCartItems(); }
  else toast(`Failed: ${apiFetch._lastError || 'unknown error'}`, false);
}

async function viewCartItem(id) {
  const p = await apiFetch(`/shop/cart-items/item/${id}`);
  if (!p) { toast('Could not load cart item', false); return; }
  const isActive = p.is_active === undefined ? true : !!p.is_active;
  document.getElementById('viewProdBody').innerHTML = `
    <div style="display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap">
      ${p.image_url ? `<img src="${p.image_url}" style="width:120px;height:120px;object-fit:cover;border-radius:10px;flex-shrink:0">` : ''}
      <div style="flex:1;min-width:200px">
        <div style="font-size:1.2rem;font-weight:700;margin-bottom:4px">${p.name || '—'}</div>
        <div style="font-size:.82rem;color:var(--muted);margin-bottom:10px">${p.description || '<em>No description</em>'}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;font-size:.85rem">
          <div><span style="color:var(--muted)">Category:</span> ${p.category || '—'}</div>
          <div><span style="color:var(--muted)">Currency:</span> ${p.currency || 'USD'}</div>
          <div><span style="color:var(--muted)">Price:</span> <strong>${p.currency || 'USD'} ${parseFloat(p.price||0).toFixed(2)}</strong></div>
          <div><span style="color:var(--muted)">Compare Price:</span> ${p.compare_price ? parseFloat(p.compare_price).toFixed(2) : '—'}</div>
          <div><span style="color:var(--muted)">Discount:</span> ${p.discount_pct ? p.discount_pct + '%' : '—'}</div>
          <div><span style="color:var(--muted)">Stock:</span> ${p.stock_quantity ?? p.stock ?? 0}</div>
          <div><span style="color:var(--muted)">Flash Offer:</span> ${p.is_flash_offer ? '⚡ Yes' : 'No'}</div>
          <div><span style="color:var(--muted)">Status:</span> ${isActive ? '<span class="tag published">Active</span>' : '<span class="tag draft">Disabled</span>'}</div>
          ${p.flash_offer_ends ? `<div colspan="2"><span style="color:var(--muted)">Flash Ends:</span> ${p.flash_offer_ends}</div>` : ''}
        </div>
      </div>
    </div>`;
  openModal('viewCartItemModal');
}

let _editCartItemId = null;
async function editCartItem(id) {
  const p = await apiFetch(`/shop/cart-items/item/${id}`);
  if (!p) { toast('Could not load cart item', false); return; }
  _editCartItemId = id;
  document.getElementById('editProdName').value = p.name || '';
  document.getElementById('editProdDesc').value = p.description || '';
  document.getElementById('editProdPrice').value = p.price ?? '';
  document.getElementById('editProdCompare').value = p.compare_price || '';
  document.getElementById('editProdDiscount').value = p.discount_pct || '';
  document.getElementById('editProdCurrency').value = p.currency || 'USD';
  document.getElementById('editProdStock').value = p.stock_quantity ?? p.stock ?? 0;
  document.getElementById('editProdCategory').value = p.category || '';
  document.getElementById('editProdImageUrl').value = p.image_url || '';
  document.getElementById('editProdFlash').checked = !!p.is_flash_offer;
  document.getElementById('editProdFlashEnds').value = p.flash_offer_ends || '';
  document.getElementById('editProdActive').checked = p.is_active === undefined ? true : !!p.is_active;
  // Show image preview
  const prev = document.getElementById('editProdImgPreview');
  if (p.image_url) { prev.src = p.image_url; prev.style.display = ''; }
  else prev.style.display = 'none';
  openModal('editCartItemModal');
}

async function saveEditCartItem() {
  if (!_editCartItemId) return;
  const imgUrl = document.getElementById('editProdImageUrl').value.trim();
  const payload = {
    name: document.getElementById('editProdName').value.trim(),
    description: document.getElementById('editProdDesc').value.trim(),
    price: parseFloat(document.getElementById('editProdPrice').value) || 0,
    compare_price: parseFloat(document.getElementById('editProdCompare').value) || 0,
    discount_pct: parseFloat(document.getElementById('editProdDiscount').value) || 0,
    currency: document.getElementById('editProdCurrency').value,
    stock_quantity: parseInt(document.getElementById('editProdStock').value) || 0,
    category_id: null,
    image_url: imgUrl || null,
    is_flash_offer: document.getElementById('editProdFlash').checked,
    flash_offer_ends: document.getElementById('editProdFlashEnds').value || null,
    is_active: document.getElementById('editProdActive').checked,
  };
  if (!payload.name) { toast('Name is required', false); return; }
  const r = await apiFetch(`/shop/cart-items/${_editCartItemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  if (r) {
    toast('Cart item updated');
    closeModal('editCartItemModal');
    loadCartItems();
  } else toast(`Save failed: ${apiFetch._lastError || 'unknown error'}`, false);
}

// ── Image upload helpers ───────────────────────────────────────────────

function switchImgTab(tab) {
  const isUpload = tab === 'upload';
  document.getElementById('imgPanelUpload').style.display = isUpload ? '' : 'none';
  document.getElementById('imgPanelUrl').style.display    = isUpload ? 'none' : '';
  document.getElementById('imgTabUpload').style.background = isUpload ? 'var(--accent)' : 'var(--card)';
  document.getElementById('imgTabUpload').style.color     = isUpload ? '#fff' : 'var(--muted)';
  document.getElementById('imgTabUrl').style.background   = isUpload ? 'var(--card)' : 'var(--accent)';
  document.getElementById('imgTabUrl').style.color        = isUpload ? 'var(--muted)' : '#fff';
}

function handleImgDrop(event) {
  event.preventDefault();
  document.getElementById('imgDropZone').style.borderColor = 'var(--border)';
  const file = event.dataTransfer.files?.[0];
  if (file) uploadCartItemImage(file);
}

async function uploadCartItemImage(file) {
  if (!file) return;
  if (!file.type.startsWith('image/')) { toast('Please select an image file', false); return; }

  const progress  = document.getElementById('imgUploadProgress');
  const bar       = document.getElementById('imgProgressBar');
  const msg       = document.getElementById('imgUploadMsg');
  const label     = document.getElementById('imgDropLabel');
  const previewWrap = document.getElementById('imgPreviewWrap');

  label.style.display = 'none';
  progress.style.display = 'block';
  bar.style.width = '30%';
  msg.textContent = 'Uploading & compressing…';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch(`${API}/shop/upload-image`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('wb_token')}` },
      body: formData,
    });
    bar.style.width = '80%';
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    bar.style.width = '100%';

    // Store thumb URL in hidden field (used by addProduct)
    document.getElementById('prodImageFinal').value = data.thumb_url;

    // Show previews
    const base = window.location.origin;
    document.getElementById('imgThumbPreview').src = base + data.thumb_url;
    document.getElementById('imgFullPreview').src  = base + data.full_url;
    document.getElementById('imgStats').innerHTML =
      `<strong>Thumb:</strong> ${data.thumb_size_kb} KB<br>` +
      `<strong>Full:</strong>  ${data.full_size_kb} KB<br>` +
      `<strong>Original:</strong> ${data.original_size_kb} KB<br>` +
      `<span style="color:#22c55e">↓ ${data.compression_pct}% smaller</span>`;
    previewWrap.style.display = 'flex';
    progress.style.display = 'none';
    label.style.display = 'none';
    toast(`Image uploaded — ${data.compression_pct}% size reduction`);
  } catch (err) {
    bar.style.width = '0';
    progress.style.display = 'none';
    label.style.display = '';
    toast(`Upload failed: ${err.message}`, false);
  }
}

async function importCatalog() {
  const siteId = document.getElementById('importCatalogSite').value;
  const url = document.getElementById('importCatalogUrl').value.trim();
  const currency = document.getElementById('importCatalogCurrency').value;
  const overwrite = document.getElementById('importCatalogOverwrite').checked;

  if (!siteId) { toast('Please select a website', false); return; }
  if (!url) { toast('Please enter a catalogue URL', false); return; }

  const btn = document.getElementById('importCatalogBtn');
  const statusEl = document.getElementById('importCatalogStatus');
  btn.disabled = true;
  btn.textContent = '⏳ Importing…';
  statusEl.style.display = 'block';
  statusEl.style.color = 'var(--muted)';
  statusEl.textContent = 'Fetching catalogue — this may take a few seconds…';

  try {
    const data = await apiFetch('/shop/import-catalog', {
      method: 'POST',
      body: JSON.stringify({ website_id: siteId, catalog_url: url, default_currency: currency, overwrite }),
    });
    if (!data) throw new Error('Empty response from server');
    _showImportResult(data, statusEl);
  } catch (err) {
    statusEl.style.color = '#ef4444';
    statusEl.textContent = `❌ ${err.message || 'Import failed.'}`;
    toast('Catalogue import failed', false);
  } finally {
    btn.disabled = false;
    btn.textContent = '📥 Import Items';
  }
}

async function importCatalogFile() {
  const siteId = document.getElementById('importCatalogSite').value;
  const fileInput = document.getElementById('importCatalogFile');
  const currency = document.getElementById('importCatalogCurrency').value;
  const overwrite = document.getElementById('importCatalogOverwrite').checked;

  if (!siteId) { toast('Please select a website', false); return; }
  if (!fileInput.files.length) { toast('Please select a file to upload', false); return; }

  const btn = document.getElementById('importCatalogFileBtn');
  const statusEl = document.getElementById('importCatalogStatus');
  btn.disabled = true;
  btn.textContent = '⏳ Uploading…';
  statusEl.style.display = 'block';
  statusEl.style.color = 'var(--muted)';
  statusEl.textContent = 'Uploading and parsing file…';

  try {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const token = localStorage.getItem('wb_token');
    const params = new URLSearchParams({ website_id: siteId, overwrite, default_currency: currency });
    const resp = await fetch(`/api/v1/shop/import-catalog/upload?${params}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
    _showImportResult(data, statusEl);
  } catch (err) {
    statusEl.style.color = '#ef4444';
    statusEl.textContent = `❌ ${err.message || 'Upload failed.'}`;
    toast('File import failed', false);
  } finally {
    btn.disabled = false;
    btn.textContent = '📂 Upload & Import';
  }
}

function _showImportResult(data, statusEl) {
  const parts = [
    data.imported > 0 ? `✅ ${data.imported} cart item(s) imported` : '⚠️ No cart items imported',
    data.skipped > 0 ? `${data.skipped} skipped` : null,
    data.source_type ? `(source: ${data.source_type})` : null,
  ].filter(Boolean).join(' · ');
  statusEl.style.color = data.imported > 0 ? '#22c55e' : '#f59e0b';
  statusEl.innerHTML = parts;
  if (data.warnings?.length) {
    statusEl.innerHTML += `<br><span style="color:#f59e0b">${data.warnings.join(' ')}</span>`;
  }
  if (data.imported > 0) {
    toast(`${data.imported} cart item(s) imported!`);
    loadCartItems();
  } else {
    toast('No cart items were imported', false);
  }
}

function switchImportTab(tab) {
  const urlPanel = document.getElementById('importPanelUrl');
  const filePanel = document.getElementById('importPanelFile');
  const urlTab = document.getElementById('importTabUrl');
  const fileTab = document.getElementById('importTabFile');
  const statusEl = document.getElementById('importCatalogStatus');
  if (statusEl) { statusEl.style.display = 'none'; statusEl.textContent = ''; }
  if (tab === 'url') {
    urlPanel.style.display = '';
    filePanel.style.display = 'none';
    urlTab.style.borderBottomColor = 'var(--accent)';
    urlTab.style.color = 'var(--text)';
    fileTab.style.borderBottomColor = 'transparent';
    fileTab.style.color = 'var(--muted)';
  } else {
    urlPanel.style.display = 'none';
    filePanel.style.display = '';
    fileTab.style.borderBottomColor = 'var(--accent)';
    fileTab.style.color = 'var(--text)';
    urlTab.style.borderBottomColor = 'transparent';
    urlTab.style.color = 'var(--muted)';
  }
}

// ── Billing ────────────────────────────────────────────────────────────────
async function loadBilling() {
  const plans = await apiFetch('/payments/plans') || [];
  const current = currentUser?.plan || 'free';
  const isSuperuser = currentUser?.plan === 'superuser';
  document.getElementById('plansGrid').innerHTML = plans.filter(p => p.plan !== 'superuser' || isSuperuser).map(p => `
    <div style="background:var(--card);border:2px solid ${p.plan === current ? 'var(--accent)' : 'var(--border)'};border-radius:10px;padding:20px">
      <div style="font-size:.75rem;text-transform:uppercase;color:var(--muted);letter-spacing:.5px">${p.plan}</div>
      <div style="font-size:1.6rem;font-weight:700;margin:8px 0">$${p.price_usd}<span style="font-size:.9rem;font-weight:400;color:var(--muted)">/mo</span></div>
      <div style="font-size:.8rem;color:var(--muted);margin-bottom:12px">${p.max_pages} pages · ${p.max_websites >= 9999 ? 'Unlimited websites' : p.max_websites + ' website' + (p.max_websites > 1 ? 's' : '')} · ${p.shopping_cart ? '🛒 Cart' : 'No cart'} · ${p.analytics ? '📊 Analytics' : ''}</div>
      ${p.plan === current
        ? `<button class="btn btn-secondary btn-sm" disabled style="opacity:.5;cursor:default">Current plan</button>`
        : `<button class="btn btn-primary btn-sm" onclick="switchPlan('${p.plan}')">Switch</button>`}
    </div>`).join('');

  const sub = await apiFetch('/payments/subscription') || null;
  document.getElementById('subDetails').innerHTML = sub
    ? `Plan: <strong>${sub.plan}</strong> · Status: <strong>${sub.status}</strong> · Next billing: <strong>${sub.next_billing_date || '—'}</strong>`
    : `Plan: <strong>${current}</strong> · No active subscription record.`;
}

async function switchPlan(plan) {
  const r = await apiFetch(`/payments/subscribe/${plan}`, { method: 'POST' });
  if (r && r.checkout_url) { window.location.href = r.checkout_url; }
  else if (r && r.message) { toast(r.message); currentUser.plan = plan; document.getElementById('planBadge').textContent = plan; loadBilling(); applyBuildPlanRestrictions(); }
  else toast('Could not switch plan', false);
}

// ── Feedback ───────────────────────────────────────────────────────────────
async function loadFeedback() {
  const list = document.getElementById('feedbackList');
  websites = await _fetchMyWebsites();
  if (!websites.length) { list.innerHTML = '<p style="color:var(--muted)">No websites yet.</p>'; return; }
  let all = [];
  for (const w of websites) {
    const fb = await apiFetch(`/feedback/${w.website_id}`) || [];
    fb.forEach(f => all.push({ ...f, siteName: w.name || w.website_name }));
  }
  if (!all.length) { list.innerHTML = '<p style="color:var(--muted)">No feedback yet.</p>'; return; }
  list.innerHTML = all.map(f => `
    <div class="feedback-item">
      <div class="stars">${'★'.repeat(f.rating || 5)}${'☆'.repeat(5 - (f.rating || 5))}</div>
      <div class="meta">${f.siteName} · ${f.created_at ? new Date(f.created_at).toLocaleDateString() : ''}</div>
      <div class="msg">${f.message || ''}</div>
    </div>`).join('');
}

// ── Monitoring ─────────────────────────────────────────────────────────────
async function loadMonitoring() {
  const data = await apiFetch('/monitoring/platform') || {};
  const stats = document.getElementById('monitoringStats');
  stats.innerHTML = `
    <div class="stat-card"><div class="label">Status</div><div class="value" style="font-size:1.2rem;color:${data.status === 'healthy' ? 'var(--success)' : 'var(--danger)'}">${data.status || '—'}</div></div>
    <div class="stat-card"><div class="label">Total Users</div><div class="value">${data.total_users ?? '—'}</div></div>
    <div class="stat-card"><div class="label">Total Websites</div><div class="value">${data.total_websites ?? '—'}</div></div>
    <div class="stat-card"><div class="label">DB Connection</div><div class="value" style="font-size:1rem;margin-top:10px;color:${data.db_connected ? 'var(--success)' : 'var(--danger)'}">${data.db_connected ? '✓ Connected' : '✗ Error'}</div></div>
  `;
  const sitesData = await apiFetch('/monitoring/websites') || [];
  const tbody = document.getElementById('monitoringBody');
  if (!sitesData.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:24px">No website monitoring data.</td></tr>';
    return;
  }
  tbody.innerHTML = sitesData.map(s => `<tr>
    <td>${s.name || s.website_id}</td>
    <td><span class="tag ${s.status === 'up' ? 'published' : 'draft'}">${s.status || '—'}</span></td>
    <td style="color:var(--muted)">${s.last_checked ? new Date(s.last_checked).toLocaleString() : '—'}</td>
    <td>${s.response_ms != null ? s.response_ms + ' ms' : '—'}</td>
  </tr>`).join('');
}

// ── Coupons ────────────────────────────────────────────────────────────────
async function initCouponPage() {
  websites = await _fetchMyWebsites();
  const sel = document.getElementById('couponSiteFilter');
  sel.innerHTML = '<option value="">Select website…</option>' + websites.map(w => `<option value="${w.website_id}">${w.name || w.website_name}</option>`).join('');
}

function openCouponModal() {
  const siteId = document.getElementById('couponSiteFilter').value;
  if (!siteId) { toast('Select a website first', false); return; }
  openModal('couponModal');
}

async function loadCoupons() {
  const siteId = document.getElementById('couponSiteFilter').value;
  if (!siteId) return;
  const tbody = document.getElementById('couponsBody');
  tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';
  const coupons = await apiFetch(`/commerce/coupons/${siteId}`) || [];
  if (!coupons.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="color:var(--muted);text-align:center;padding:24px">No coupons yet.</td></tr>';
    return;
  }
  tbody.innerHTML = coupons.map(c => `<tr>
    <td><strong>${c.code}</strong></td>
    <td>${c.discount_type}</td>
    <td>${c.discount_type === 'percent' ? c.discount_value + '%' : '$' + parseFloat(c.discount_value).toFixed(2)}</td>
    <td>${c.used_count ?? 0} / ${c.max_uses || '∞'}</td>
    <td style="color:var(--muted)">${c.expires_at ? new Date(c.expires_at).toLocaleDateString() : '—'}</td>
    <td><span class="tag ${c.is_active ? 'published' : 'draft'}">${c.is_active ? 'Active' : 'Inactive'}</span></td>
    <td><button class="btn btn-danger btn-sm" onclick="deleteCoupon('${c.coupon_id}')">Delete</button></td>
  </tr>`).join('');
}

async function createCoupon() {
  const siteId = document.getElementById('couponSiteFilter').value;
  const payload = {
    website_id: siteId,
    code: (document.getElementById('couponCode').value || '').toUpperCase().trim(),
    discount_type: document.getElementById('couponType').value,
    discount_value: parseFloat(document.getElementById('couponValue').value) || 0,
    max_uses: parseInt(document.getElementById('couponMaxUses').value) || 0,
    expires_at: document.getElementById('couponExpiry').value || null,
  };
  if (!payload.code) { toast('Coupon code required', false); return; }
  const r = await apiFetch('/commerce/coupons', { method: 'POST', body: JSON.stringify(payload) });
  if (r) { toast('Coupon created'); closeModal('couponModal'); loadCoupons(); }
  else toast('Failed to create coupon', false);
}

async function deleteCoupon(id) {
  if (!confirm('Delete this coupon?')) return;
  const r = await fetch(`${API}/commerce/coupons/${id}`, { method: 'DELETE', headers: headers() });
  if (r.ok) { toast('Coupon deleted'); loadCoupons(); }
  else toast('Failed', false);
}

// ── Campaigns ──────────────────────────────────────────────────────────────
async function initCampaignPage() {
  websites = await _fetchMyWebsites();
  const sel = document.getElementById('campaignSiteFilter');
  sel.innerHTML = '<option value="">Select website…</option>' + websites.map(w => `<option value="${w.website_id}">${w.name || w.website_name}</option>`).join('');
}

function openCampaignModal() {
  const siteId = document.getElementById('campaignSiteFilter').value;
  if (!siteId) { toast('Select a website first', false); return; }
  openModal('campaignModal');
}

async function loadCampaigns() {
  const siteId = document.getElementById('campaignSiteFilter').value;
  if (!siteId) return;
  const tbody = document.getElementById('campaignsBody');
  tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';
  const campaigns = await apiFetch(`/commerce/campaigns/${siteId}`) || [];
  if (!campaigns.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:24px">No campaigns yet.</td></tr>';
    return;
  }
  tbody.innerHTML = campaigns.map(c => `<tr>
    <td>${c.title}</td>
    <td><span class="tag" style="background:rgba(99,102,241,.15);color:var(--accent)">${c.channel}</span></td>
    <td><span class="tag ${c.status === 'sent' ? 'published' : 'draft'}">${c.status || 'draft'}</span></td>
    <td style="color:var(--muted)">${c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</td>
    <td style="display:flex;gap:6px">
      ${c.status !== 'sent' ? `<button class="btn btn-primary btn-sm" onclick="sendCampaign('${c.campaign_id}')">Send</button>` : ''}
      <button class="btn btn-danger btn-sm" onclick="deleteCampaign('${c.campaign_id}')">Delete</button>
    </td>
  </tr>`).join('');
}

async function createCampaign() {
  const siteId = document.getElementById('campaignSiteFilter').value;
  const payload = {
    website_id: siteId,
    title: document.getElementById('campaignTitle').value.trim(),
    channel: document.getElementById('campaignChannel').value,
    message: document.getElementById('campaignMessage').value.trim(),
  };
  if (!payload.title || !payload.message) { toast('Title and message required', false); return; }
  const r = await apiFetch('/commerce/campaigns', { method: 'POST', body: JSON.stringify(payload) });
  if (r) { toast('Campaign saved'); closeModal('campaignModal'); loadCampaigns(); }
  else toast('Failed to save campaign', false);
}

async function sendCampaign(id) {
  if (!confirm('Send this campaign to all subscribers?')) return;
  const r = await apiFetch(`/commerce/campaigns/${id}/send`, { method: 'POST' });
  if (r) { toast('Campaign sent!'); loadCampaigns(); }
  else toast('Send failed', false);
}

async function deleteCampaign(id) {
  if (!confirm('Delete this campaign?')) return;
  const r = await fetch(`${API}/commerce/campaigns/${id}`, { method: 'DELETE', headers: headers() });
  if (r.ok) { toast('Campaign deleted'); loadCampaigns(); }
  else toast('Failed', false);
}

// ── Team ──────────────────────────────────────────────────────────────────
async function loadTeam() {
  const tbody = document.getElementById('teamBody');
  tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';
  const members = await apiFetch('/team') || [];
  if (!members.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:24px">No team members yet.</td></tr>';
    return;
  }
  tbody.innerHTML = members.map(m => `<tr>
    <td>${m.email}</td>
    <td>${m.full_name || '—'}</td>
    <td style="color:var(--muted);font-size:.82rem">${(m.permissions || []).join(', ') || 'none'}</td>
    <td><button class="btn btn-danger btn-sm" onclick="removeTeamMember('${m.user_id}')">Remove</button></td>
  </tr>`).join('');
}

async function createTeamMember() {
  const perms = [...document.querySelectorAll('input[name="memberPerm"]:checked')].map(el => el.value);
  const payload = {
    email: document.getElementById('memberEmail').value.trim(),
    full_name: document.getElementById('memberName').value.trim(),
    password: document.getElementById('memberPassword').value,
    permissions: perms,
  };
  if (!payload.email || !payload.password) { toast('Email and password required', false); return; }
  const r = await apiFetch('/team', { method: 'POST', body: JSON.stringify(payload) });
  if (r) { toast('Team member added'); closeModal('teamModal'); loadTeam(); }
  else toast('Failed to add member', false);
}

async function removeTeamMember(id) {
  if (!confirm('Remove this team member? They will lose access.')) return;
  const r = await fetch(`${API}/team/${id}`, { method: 'DELETE', headers: headers() });
  if (r.ok) { toast('Member removed'); loadTeam(); }
  else toast('Failed', false);
}

// ── Cart Items page tab switcher ─────────────────────────────────────────────
const PLATFORM_SERVICES = [
  { key: 'build',         label: '✨ Build' },
  { key: 'monitoring',    label: '📊 Monitoring' },
  { key: 'notifications', label: '🔔 Notifications' },
  { key: 'feedback',      label: '💬 Feedback' },
];

function switchProdTab(tab) {
  const isEcomm = tab === 'ecomm';
  document.getElementById('prodPanel-ecomm').style.display    = isEcomm ? '' : 'none';
  document.getElementById('prodPanel-services').style.display = isEcomm ? 'none' : '';

  const eBtn = document.getElementById('prodTab-ecomm');
  const sBtn = document.getElementById('prodTab-services');
  eBtn.style.color        = isEcomm ? 'var(--accent)' : 'var(--muted)';
  eBtn.style.borderBottomColor = isEcomm ? 'var(--accent)' : 'transparent';
  sBtn.style.color        = isEcomm ? 'var(--muted)' : 'var(--accent)';
  sBtn.style.borderBottomColor = isEcomm ? 'transparent' : 'var(--accent)';

  if (!isEcomm) loadClientServices();
}

async function loadClientServices() {
  const tbody = document.getElementById('servicesBody');
  tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';

  const data = await apiFetch('/clients/?limit=200') || {};
  const clients = Array.isArray(data) ? data : (data.items || []);
  if (!clients.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">No clients onboarded yet. Go to <a href="javascript:showPage(\'clients\')" style="color:var(--accent)">Clients</a> to add one.</td></tr>';
    return;
  }

  tbody.innerHTML = clients.map(c => {
    const perms = Array.isArray(c.permissions) ? c.permissions : [];
    const cells = PLATFORM_SERVICES.map(svc => {
      const on = perms.includes(svc.key);
      return `<td style="text-align:center">
        <label class="svc-toggle" title="${on ? 'Enabled — click to disable' : 'Disabled — click to enable'}">
          <input type="checkbox" ${on ? 'checked' : ''}
            onchange="toggleClientService('${c.user_id}','${svc.key}',this.checked,this)"
            style="display:none">
          <span style="
            display:inline-flex;align-items:center;justify-content:center;
            width:42px;height:24px;border-radius:12px;cursor:pointer;transition:.2s;
            background:${on ? 'var(--accent)' : 'var(--border)'};
            font-size:.75rem;color:#fff;font-weight:700;
          ">${on ? 'ON' : 'OFF'}</span>
        </label>
      </td>`;
    }).join('');
    return `<tr>
      <td>
        <div style="font-weight:600;font-size:.88rem">${c.full_name || c.email}</div>
        <div style="color:var(--muted);font-size:.76rem">${c.email}</div>
      </td>
      <td style="font-size:.82rem;color:var(--muted)">${c.website_name || c.client_website_id || '—'}</td>
      ${cells}
    </tr>`;
  }).join('');
}

async function toggleClientService(clientId, service, enabled, checkboxEl) {
  // Optimistic UI: update the toggle span immediately
  const span = checkboxEl.nextElementSibling;
  span.style.background = enabled ? 'var(--accent)' : 'var(--border)';
  span.textContent = enabled ? 'ON' : 'OFF';

  const res = await apiFetch(`/clients/${clientId}/services`, {
    method: 'PATCH',
    body: JSON.stringify({ service, enabled }),
  });
  if (!res) {
    // Revert on failure
    checkboxEl.checked = !enabled;
    span.style.background = !enabled ? 'var(--accent)' : 'var(--border)';
    span.textContent = !enabled ? 'ON' : 'OFF';
    toast(`Failed to update ${service}`, false);
  } else {
    toast(`${service} ${enabled ? 'enabled' : 'disabled'} for client`);
  }
}

// ── Clients ────────────────────────────────────────────────────────────────
async function loadClients() {
  const tbody = document.getElementById('clientsBody');
  tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">Loading…</td></tr>';
  const data = await apiFetch('/clients/?limit=200') || {};
  const clients = Array.isArray(data) ? data : (data.items || []);
  if (!clients.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">No clients onboarded yet.</td></tr>';
    return;
  }
  tbody.innerHTML = clients.map(c => `<tr>
    <td>${c.email}</td>
    <td>${c.full_name || '—'}</td>
    <td>${c.website_name || c.client_website_id || '—'}</td>
    <td style="color:var(--muted);font-size:.82rem">${(c.permissions || []).join(', ') || 'all'}</td>
    <td><span class="tag ${c.is_active ? 'published' : 'draft'}">${c.is_active ? 'Active' : 'Inactive'}</span></td>
    <td>
      <button class="btn btn-danger btn-sm" onclick="removeClient('${c.user_id}')">Remove</button>
      ${c.is_active
        ? `<button class="btn btn-secondary btn-sm" style="margin-left:6px" onclick="toggleClient('${c.user_id}',false)">Deactivate</button>`
        : `<button class="btn btn-primary btn-sm" style="margin-left:6px" onclick="toggleClient('${c.user_id}',true)">Activate</button>`}
    </td>
  </tr>`).join('');
}

async function createClient() {
  // Populate website select if empty
  const perms = [...document.querySelectorAll('input[name="clientPerm"]:checked')].map(el => el.value);
  const payload = {
    email: document.getElementById('clientEmail').value.trim(),
    full_name: document.getElementById('clientName').value.trim(),
    password: document.getElementById('clientPassword').value,
    mobile: document.getElementById('clientMobile').value.trim(),
    website_id: document.getElementById('clientWebsite').value,
    permissions: perms,
  };
  if (!payload.email || !payload.password || !payload.website_id) {
    toast('Email, password and website are required', false); return;
  }
  const r = await apiFetch('/clients/', { method: 'POST', body: JSON.stringify(payload) });
  if (r) { toast('Client onboarded'); closeModal('clientModal'); loadClients(); }
  else toast('Failed to create client', false);
}

async function removeClient(id) {
  if (!confirm('Remove this client? They will lose access.')) return;
  const r = await fetch(`${API}/clients/${id}`, { method: 'DELETE', headers: headers() });
  if (r.ok) { toast('Client removed'); loadClients(); }
  else toast('Failed', false);
}

async function toggleClient(id, activate) {
  const r = await apiFetch(`/clients/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: activate }),
  });
  if (r) { toast(activate ? 'Client activated' : 'Client deactivated'); loadClients(); }
  else toast('Failed', false);
}

async function populateClientWebsiteSelect() {
  const sel = document.getElementById('clientWebsite');
  if (sel.options.length > 1) return;         // already populated
  const sites = await _fetchMyWebsites();
  sel.innerHTML = '<option value="">— select website —</option>' +
    sites.map(s => `<option value="${s.website_id}">${s.name}</option>`).join('');
}


// ── Chatbot Widget ─────────────────────────────────────────────────────────
function toggleChat() {
  document.getElementById('chat-box').classList.toggle('open');
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendChatMsg(msg, 'user');
  appendChatMsg('…', 'bot', 'chat-typing');

  const res = await apiFetch('/chatbot/chat', {
    method: 'POST',
    body: JSON.stringify({ message: msg, context: 'visitor' }),
  });
  document.getElementById('chat-typing')?.remove();
  appendChatMsg(res?.reply || 'Sorry, I could not process that.', 'bot');
}

function appendChatMsg(text, role, id = '') {
  const el = document.createElement('div');
  el.className = 'chat-msg ' + role;
  if (id) el.id = id;
  el.textContent = text;
  const box = document.getElementById('chatMessages');
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

init();

// ── Build page tabs ────────────────────────────────────────────────────────
function switchBuildTab(tab) {
  const isImport = tab === 'import';
  document.getElementById('buildPanel-import').style.display = isImport ? '' : 'none';
  document.getElementById('buildPanel-agent').style.display  = isImport ? 'none' : '';

  const iBtn = document.getElementById('buildTab-import');
  const aBtn = document.getElementById('buildTab-agent');
  iBtn.style.color             = isImport ? 'var(--accent)' : 'var(--muted)';
  iBtn.style.borderBottomColor = isImport ? 'var(--accent)' : 'transparent';
  aBtn.style.color             = isImport ? 'var(--muted)' : 'var(--accent)';
  aBtn.style.borderBottomColor = isImport ? 'transparent' : 'var(--accent)';

  if (!isImport) applyBuildPlanRestrictions();
}

// ── Staging Area ───────────────────────────────────────────────────────────
let stagedWebsiteId = null;
let currentStagingUrl = null;

function _normStatus(v) {
  return String(v || '').trim().toLowerCase();
}

function _previewUrlFromLocalPath(localPath) {
  const raw = String(localPath || '').trim();
  if (!raw) return null;

  // Accept both relative paths like "output/staging/site" and absolute paths
  // that contain "/output/...".
  const unix = raw.replace(/\\/g, '/');
  const outputIdx = unix.indexOf('/output/');
  const rel = outputIdx >= 0
    ? unix.slice(outputIdx + '/output/'.length)
    : unix.replace(/^output\//, '').replace(/^\.\//, '');

  const clean = rel.replace(/^\/+/, '').replace(/\/+$/, '');
  if (!clean) return null;
  return `/output/${clean}/index.html`;
}

async function loadStagingWebsites() {
  const sites = await _fetchMyWebsites();
  const sel = document.getElementById('stagingSiteSelect');
  if (!sel) return;
  const cur = sel.value;
  sel.innerHTML = '<option value="">— Choose a website —</option>';
  const eligible = sites.filter(s => {
    const buildStatus = _normStatus(s.build_status);
    const status = _normStatus(s.status);
    return Boolean(s.local_path) ||
      ['built', 'staged', 'live', 'published'].includes(buildStatus) ||
      ['built', 'staged', 'live', 'published'].includes(status);
  });
  eligible.forEach(w => {
    const state = _normStatus(w.build_status) || _normStatus(w.status) || 'draft';
    const label = `${w.name || w.website_id} · ${state}`;
    sel.innerHTML += `<option value="${w.website_id}" ${w.website_id === cur ? 'selected' : ''}>${label}</option>`;
  });

  if (!eligible.length) {
    document.getElementById('stagingStatusBar').textContent = 'No staged or built websites found for this account.';
  }

  // Re-load if a site was already selected
  if (cur && eligible.find(w => w.website_id === cur)) loadStagedSite(cur);
}

async function loadStagedSite(preselect) {
  const id = preselect || document.getElementById('stagingSiteSelect').value;
  if (preselect) {
    const sel = document.getElementById('stagingSiteSelect');
    if (sel) sel.value = preselect;
  }
  if (!id) return;
  stagedWebsiteId = id;

  // Show loading overlay
  const loading = document.getElementById('stagingLoading');
  loading.style.display = 'flex';

  // Find the site object (may have just been built; refresh if necessary)
  let w = (websites || []).find(x => x.website_id === id);
  if (!w) {
    const fresh = await _fetchMyWebsites();
    websites = fresh;
    w = fresh.find(x => x.website_id === id);
  }

  // Derive preview URL from local_path
  let previewUrl = null;
  if (w) {
    previewUrl = _previewUrlFromLocalPath(w.local_path);
    if (!previewUrl && w.name) {
      const slug = w.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/, '');
      previewUrl = `/output/staging/${slug}/index.html`;
    }
  }

  // Update status badge
  const badge = document.getElementById('stagingStatusBadge');
  if (badge) badge.innerHTML = w ? statusBadge(w.status) : '';

  // Load iframe
  const frame = document.getElementById('stagingIframe');
  const placeholder = document.getElementById('stagingPlaceholder');
  if (previewUrl) {
    currentStagingUrl = previewUrl;
    stagingOverlayOn = false;
    stagingSections = [];
    activeSectionIndex = null;
    const editBtn = document.getElementById('stagingEditBtn');
    if (editBtn) { editBtn.textContent = '🔢 Section Numbers'; editBtn.style.background = ''; }
    document.getElementById('secEditor').style.display = 'none';
    document.getElementById('secList').style.display = '';
    frame.onload = () => {
      loading.style.display = 'none';
      // Snapshot original state for Reset
      try {
        if (frame.contentDocument) {
          _injectResponsiveEnhancements(frame.contentDocument);
          _originalHTML = frame.contentDocument.documentElement.outerHTML;
          _historyStack = [];
          _updateUndoBtn();
        }
      } catch(_) {}
    };
    frame.src = previewUrl;
    frame.style.display = '';
    placeholder.style.display = 'none';
    document.getElementById('stagingStatusBar').textContent = `Preview: ${previewUrl}`;
  } else {
    loading.style.display = 'none';
    placeholder.style.display = 'flex';
    frame.style.display = 'none';
    document.getElementById('stagingStatusBar').textContent = 'No built output found for this website.';
  }

  // Enable controls
  ['stagingEditBtn', 'stagingFontBtn', 'stagingAddSecBtn', 'stagingUndoBtn', 'stagingResetBtn', 'stagingPopoutBtn', 'stagingRefreshBtn', 'stagingSaveBtn', 'stagingGoLiveBtn'].forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = false;
  });

  // iframe src is already set above; no need to preload HTML separately
}

// ── Staging overlay & visual section editor ────────────────────────────────
let stagingOverlayOn = false;
let activeSectionIndex = null;
let stagingSections = [];   // [{el, label}, …] in iframe DOM
let _historyStack = [];     // up to 5 HTML snapshots for undo
let _originalHTML  = null;  // snapshot taken on first preview load
const HISTORY_LIMIT = 5;

/* Call before any mutation to save a checkpoint */
function _historyPush() {
  const frame = document.getElementById('stagingIframe');
  if (!frame || !frame.contentDocument) return;
  const html = frame.contentDocument.documentElement.outerHTML;
  _historyStack.push(html);
  if (_historyStack.length > HISTORY_LIMIT) _historyStack.shift();
  _updateUndoBtn();
}

function _updateUndoBtn() {
  const btn = document.getElementById('stagingUndoBtn');
  if (btn) {
    const n = _historyStack.length;
    btn.textContent = n ? `↩ Undo (${n})` : '↩ Undo';
    btn.disabled = n === 0;
  }
}

/* Restore the iframe from a saved snapshot then re-inject overlay */
function _restoreSnapshot(html) {
  const frame = document.getElementById('stagingIframe');
  const doc   = frame.contentDocument;
  if (!doc) return;
  doc.open();
  doc.write(html);
  doc.close();
  // Re-inject overlay after a tick so the DOM settles
  setTimeout(() => {
    if (stagingOverlayOn) _injectOverlay(doc);
    else { stagingSections = []; document.getElementById('secList').innerHTML = ''; }
    closeSecEditor();
    _updateUndoBtn();
  }, 80);
}

function historyUndo() {
  if (!_historyStack.length) { toast('Nothing to undo', false); return; }
  const prev = _historyStack.pop();
  _restoreSnapshot(prev);
  toast('Undo applied', true);
}

function historyReset() {
  if (!_originalHTML) { toast('No original snapshot available', false); return; }
  if (!confirm('Reset all edits and return to the original loaded state?')) return;
  _historyStack = [];
  _restoreSnapshot(_originalHTML);
  toast('Reset to original', true);
}

/* Inject numbered badges into the iframe and listen for clicks via postMessage */
function _injectOverlay(doc) {
  // Remove any prior overlay
  doc.querySelectorAll('.__wb_badge').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_hi').forEach(n => {
    n.style.outline = '';
    n.classList.remove('__wb_hi');
  });

  // Query ALL structural elements in a single call so they come back in DOM order
  const LABEL_MAP = { NAV: 'Navigation / Menu', HEADER: 'Header', SECTION: 'Section', FOOTER: 'Footer' };

  stagingSections = [];
  let idx = 0;

  doc.querySelectorAll('nav, header, section, footer').forEach(el => {
    // Skip elements that are nested inside another tracked element
    if (el.closest('nav, header, section, footer') !== el) return;
    const label = LABEL_MAP[el.tagName] || 'Section';
    idx++;
    const i = idx;
      stagingSections.push({ el, label: `${i}. ${label}${el.id ? ' #' + el.id : ''}` });

      // Position badge at top-left of element
      el.style.position = el.style.position || 'relative';
      const badge = doc.createElement('button');
      badge.className = '__wb_badge';
      badge.textContent = String(i);
      badge.title = `Edit: ${label}${el.id ? ' #' + el.id : ''}`;
      badge.style.cssText = [
        'position:absolute','top:6px','left:6px','z-index:99999',
        'width:28px','height:28px','border-radius:50%',
        'background:#6366f1','color:#fff','border:2px solid #fff',
        'font-size:12px','font-weight:700','cursor:pointer',
        'display:flex','align-items:center','justify-content:center',
        'box-shadow:0 2px 8px rgba(0,0,0,.4)','line-height:1',
      ].join(';');
      badge.addEventListener('click', (e) => {
        e.stopPropagation();
        window.parent.postMessage({ type: 'wb_section_click', index: i - 1 }, '*');
      });
      el.appendChild(badge);
  });

  // Populate the section list in the sidebar + jump dropdown
  const list = document.getElementById('secList');
  const jump = document.getElementById('stagingJumpSelect');
  if (jump) {
    jump.innerHTML = '<option value="">— jump to section —</option>' +
      stagingSections.map((s, i) => `<option value="${i}">${s.label}</option>`).join('');
  }
  if (!stagingSections.length) {
    list.innerHTML = '<p style="font-size:.82rem;color:var(--muted);text-align:center;padding:24px">No identifiable sections found in this page.</p>';
    return;
  }
  _renderSecList();
}

/* ── Section list render (called by _injectOverlay and after reorder/delete) ── */
function _renderSecList() {
  const list = document.getElementById('secList');
  const jump = document.getElementById('stagingJumpSelect');
  if (jump) {
    jump.innerHTML = '<option value="">— jump to section —</option>' +
      stagingSections.map((s, i) => `<option value="${i}">${s.label}</option>`).join('');
  }
  list.innerHTML = stagingSections.map((s, i) => `
    <div id="secRow_${i}" draggable="true"
      ondragstart="_secDragStart(event,${i})" ondragover="_secDragOver(event,${i})" ondrop="_secDrop(event,${i})" ondragleave="_secDragLeave(event)"
      style="padding:7px 10px;border-radius:7px;margin-bottom:6px;display:flex;align-items:center;gap:8px;background:rgba(99,102,241,.07);border:1px solid rgba(99,102,241,.15);cursor:grab;user-select:none">
      <span style="color:var(--muted);font-size:.9rem;cursor:grab">⠿</span>
      <span onclick="openSecEditor(${i})" style="background:#6366f1;color:#fff;border-radius:50%;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;flex-shrink:0;cursor:pointer">${i+1}</span>
      <span onclick="openSecEditor(${i})" style="font-size:.82rem;color:var(--text);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer">${s.label}</span>
      <div style="display:flex;gap:3px;flex-shrink:0">
        <button onclick="moveSectionUp(${i})" title="Move up" style="background:none;border:1px solid var(--border);border-radius:5px;padding:2px 6px;font-size:.75rem;cursor:pointer;color:var(--muted)" ${i===0?'disabled':''}>▲</button>
        <button onclick="moveSectionDown(${i})" title="Move down" style="background:none;border:1px solid var(--border);border-radius:5px;padding:2px 6px;font-size:.75rem;cursor:pointer;color:var(--muted)" ${i===stagingSections.length-1?'disabled':''}>▼</button>
        <button onclick="deleteSection(${i})" title="Delete section" style="background:none;border:1px solid #ef4444;border-radius:5px;padding:2px 6px;font-size:.75rem;cursor:pointer;color:#ef4444">🗑</button>
      </div>
    </div>`).join('');

  // Add drag event listeners (they can't be inlined for all browsers)
  stagingSections.forEach((_, i) => {
    const row = document.getElementById(`secRow_${i}`);
    if (row) {
      row.addEventListener('dragstart', (e) => _secDragStart(e, i));
      row.addEventListener('dragover',  (e) => _secDragOver(e, i));
      row.addEventListener('drop',      (e) => _secDrop(e, i));
      row.addEventListener('dragleave', (e) => _secDragLeave(e));
    }
  });
}

let _dragSrcIdx = null;
function _secDragStart(e, i) {
  _dragSrcIdx = i;
  e.dataTransfer.effectAllowed = 'move';
  e.currentTarget.style.opacity = '.4';
}
function _secDragOver(e, i) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  document.querySelectorAll('[id^="secRow_"]').forEach(r => r.style.borderColor = 'rgba(99,102,241,.15)');
  const row = document.getElementById(`secRow_${i}`);
  if (row && i !== _dragSrcIdx) row.style.borderColor = '#6366f1';
}
function _secDragLeave(e) {
  if (e.currentTarget) e.currentTarget.style.borderColor = 'rgba(99,102,241,.15)';
}
function _secDrop(e, targetIdx) {
  e.preventDefault();
  document.querySelectorAll('[id^="secRow_"]').forEach(r => { r.style.opacity = '1'; r.style.borderColor = 'rgba(99,102,241,.15)'; });
  if (_dragSrcIdx === null || _dragSrcIdx === targetIdx) { _dragSrcIdx = null; return; }
  _reorderSection(_dragSrcIdx, targetIdx);
  _dragSrcIdx = null;
}

function _reorderSection(fromIdx, toIdx) {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) return;
  _historyPush();
  const src = stagingSections[fromIdx].el;
  const tgt = stagingSections[toIdx].el;
  const parent = src.parentNode;
  if (!parent) return;
  // Insert src before or after target depending on direction
  if (fromIdx < toIdx) {
    parent.insertBefore(src, tgt.nextSibling);
  } else {
    parent.insertBefore(src, tgt);
  }
  _injectOverlay(frame.contentDocument);
  toast('Section reordered — click 💾 Save to persist', true);
}

function moveSectionUp(idx) {
  if (idx === 0) return;
  _reorderSection(idx, idx - 1);
}
function moveSectionDown(idx) {
  if (idx >= stagingSections.length - 1) return;
  _reorderSection(idx, idx + 1);
}

let _pendingDeleteIdx = null;
function deleteSection(idx) {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) return;
  const s = stagingSections[idx];
  if (!s) return;
  _pendingDeleteIdx = idx;
  document.getElementById('deleteSectionMsg').textContent =
    `Are you sure you want to delete "${s.label}"? This can be undone with the ↩ Undo button.`;
  document.getElementById('deleteSectionModal').style.display = 'flex';
}
function _cancelDeleteSection() {
  _pendingDeleteIdx = null;
  document.getElementById('deleteSectionModal').style.display = 'none';
}
function _confirmDeleteSection() {
  document.getElementById('deleteSectionModal').style.display = 'none';
  const idx = _pendingDeleteIdx;
  _pendingDeleteIdx = null;
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || idx === null) return;
  const s = stagingSections[idx];
  if (!s) return;
  _historyPush();
  s.el.remove();
  _injectOverlay(frame.contentDocument);
  if (activeSectionIndex !== null) closeSecEditor();
  toast('Section deleted — click 💾 Save to persist', true);
}

/* ── Section templates for the Add Section modal ── */
const SEC_TEMPLATES = [
  { label: '📝 Text / Content', id: 'text-content', html: (id) => `<section id="${id}" style="padding:80px 5%;background:#fff"><div style="max-width:900px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:16px">Section Heading</h2><p style="font-size:1.05rem;line-height:1.8;color:#555">Add your content here. Click ✏️ to edit this section.</p></div></section>` },
  { label: '🖼 Image + Text',   id: 'image-text',   html: (id) => `<section id="${id}" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:1100px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center"><div><h2 style="font-size:1.8rem;margin-bottom:16px">Heading</h2><p style="font-size:1rem;line-height:1.8;color:#555">Your description goes here.</p></div><img src="https://placehold.co/600x400" alt="" style="width:100%;border-radius:12px"></div></section>` },
  { label: '🃏 Cards / Grid',   id: 'cards-grid',   html: (id) => `<section id="${id}" style="padding:80px 5%;background:#fff"><div style="max-width:1100px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:40px">Our Offerings</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px"><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card One</h3><p style="color:#666;font-size:.95rem">Description.</p></div><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card Two</h3><p style="color:#666;font-size:.95rem">Description.</p></div><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card Three</h3><p style="color:#666;font-size:.95rem">Description.</p></div></div></div></section>` },
  { label: '📬 Contact Form',  id: 'contact-form',  html: (id) => `<section id="${id}" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:600px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:24px">Get In Touch</h2><form onsubmit="return false" style="display:flex;flex-direction:column;gap:14px;text-align:left"><input type="text" placeholder="Your name" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem"><input type="email" placeholder="Email address" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem"><textarea placeholder="Your message" rows="4" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem;resize:vertical"></textarea><button type="submit" style="padding:13px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:700;cursor:pointer">Send Message</button></form></div></section>` },
  { label: '💬 Testimonials',  id: 'testimonials',  html: (id) => `<section id="${id}" style="padding:80px 5%;background:#fff"><div style="max-width:1000px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:40px">What People Say</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px"><div style="background:#f9f7f4;border-radius:12px;padding:28px"><p style="font-style:italic;color:#555;line-height:1.7;margin-bottom:16px">"An excellent experience. Highly recommended!"</p><strong style="font-size:.9rem">— Happy Customer</strong></div><div style="background:#f9f7f4;border-radius:12px;padding:28px"><p style="font-style:italic;color:#555;line-height:1.7;margin-bottom:16px">"Outstanding quality and service."</p><strong style="font-size:.9rem">— Another Customer</strong></div></div></div></section>` },
  { label: '📢 Call to Action', id: 'cta',           html: (id) => `<section id="${id}" style="padding:80px 5%;text-align:center;background:#6366f1;color:#fff"><div style="max-width:700px;margin:0 auto"><h2 style="font-size:2.2rem;margin-bottom:16px">Ready to Get Started?</h2><p style="opacity:.85;font-size:1.05rem;margin-bottom:32px">Join us today and experience the difference.</p><a href="#contact" style="display:inline-block;padding:14px 36px;background:#fff;color:#6366f1;border-radius:8px;font-weight:700;font-size:1rem;text-decoration:none">Get Started</a></div></section>` },
  { label: '❓ FAQ',            id: 'faq',            html: (id) => `<section id="${id}" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:800px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:32px">Frequently Asked Questions</h2><details style="background:#fff;border-radius:8px;padding:16px 20px;text-align:left;margin-bottom:10px"><summary style="font-weight:700;cursor:pointer">Question one?</summary><p style="margin-top:10px;color:#555">Answer goes here.</p></details><details style="background:#fff;border-radius:8px;padding:16px 20px;text-align:left;margin-bottom:10px"><summary style="font-weight:700;cursor:pointer">Question two?</summary><p style="margin-top:10px;color:#555">Answer goes here.</p></details></div></section>` },
  { label: '🖼 Gallery',        id: 'gallery',        html: (id) => `<section id="${id}" style="padding:80px 5%;background:#fff"><div style="max-width:1100px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:40px">Gallery</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"></div></div></section>` },
];

let _selectedTemplate = null;
function openAddSectionModal() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) { toast('Load a preview first', false); return; }
  _selectedTemplate = SEC_TEMPLATES[0];
  // Populate "insert after" dropdown
  const sel = document.getElementById('addSecAfter');
  sel.innerHTML = '<option value="-1">— At the beginning —</option>' +
    stagingSections.map((s, i) => `<option value="${i}">${s.label}</option>`).join('');
  if (stagingSections.length) sel.value = String(stagingSections.length - 1);
  // Populate template grid
  const grid = document.getElementById('addSecTemplates');
  grid.innerHTML = SEC_TEMPLATES.map((t, i) => `
    <div id="tplCard_${i}" onclick="_selectTemplate(${i})"
      style="padding:14px 12px;border:2px solid var(--border);border-radius:9px;cursor:pointer;font-size:.82rem;font-weight:600;color:var(--text);text-align:center;transition:border-color .15s${i===0?';border-color:#6366f1;background:rgba(99,102,241,.07)':''}">
      ${t.label}
    </div>`).join('');
  document.getElementById('addSectionModal').style.display = 'flex';
}
function _selectTemplate(i) {
  _selectedTemplate = SEC_TEMPLATES[i];
  document.querySelectorAll('[id^="tplCard_"]').forEach((c, j) => {
    c.style.borderColor = j === i ? '#6366f1' : 'var(--border)';
    c.style.background  = j === i ? 'rgba(99,102,241,.07)' : '';
  });
}
function closeAddSectionModal() {
  document.getElementById('addSectionModal').style.display = 'none';
}
function insertNewSection() {
  if (!_selectedTemplate) return;
  const frame = document.getElementById('stagingIframe');
  const doc = frame.contentDocument;
  if (!doc) return;
  _historyPush();
  // Generate unique id
  const uid = _selectedTemplate.id + '-' + Math.random().toString(36).slice(2,7);
  const html = _selectedTemplate.html(uid);
  const tmp = doc.createElement('div');
  tmp.innerHTML = html;
  const newEl = tmp.firstElementChild;
  const afterIdx = parseInt(document.getElementById('addSecAfter').value);
  if (afterIdx < 0 || stagingSections.length === 0) {
    doc.body.insertBefore(newEl, doc.body.firstElementChild);
  } else {
    const refEl = stagingSections[afterIdx].el;
    refEl.parentNode.insertBefore(newEl, refEl.nextSibling);
  }
  closeAddSectionModal();
  _injectOverlay(doc);
  // Open editor on newly added section
  const newIdx = stagingSections.findIndex(s => s.el === newEl);
  if (newIdx >= 0) { setTimeout(() => openSecEditor(newIdx), 100); }
  toast('Section added — click 💾 Save to persist', true);
}

function toggleStagingOverlay() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) { toast('Preview not loaded yet', false); return; }
  stagingOverlayOn = !stagingOverlayOn;
  const btn = document.getElementById('stagingEditBtn');

  if (stagingOverlayOn) {
    _injectOverlay(frame.contentDocument);
    btn.textContent = '🔢 Numbers ON';
    btn.style.background = 'rgba(99,102,241,.2)';
    document.getElementById('secEditorHint').textContent = 'Click a numbered badge on the preview';
  } else {
    frame.contentDocument.querySelectorAll('.__wb_badge').forEach(n => n.remove());
    frame.contentDocument.querySelectorAll('.__wb_hi').forEach(n => {
      n.style.outline = ''; n.classList.remove('__wb_hi');
    });
    stagingSections = [];
    btn.textContent = '🔢 Section Numbers';
    btn.style.background = '';
    closeSecEditor();
  }
}

/* Listen for postMessage from iframe badge clicks */
window.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'wb_section_click') {
    openSecEditor(e.data.index);
  }
});

/* Build the friendly field editor for the clicked section */
function openSecEditor(idx) {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || !stagingSections[idx]) return;

  activeSectionIndex = idx;
  const { el, label } = stagingSections[idx];

  // Highlight selected section
  frame.contentDocument.querySelectorAll('.__wb_hi').forEach(n => {
    n.style.outline = ''; n.classList.remove('__wb_hi');
  });
  el.style.outline = '3px solid #6366f1';
  el.classList.add('__wb_hi');

  // Scroll iframe section into view
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });

  document.getElementById('secEditorTitle').textContent = label;
  document.getElementById('secList').style.display = 'none';
  const editor = document.getElementById('secEditor');
  editor.style.display = 'flex';

  const fields = document.getElementById('secEditorFields');
  // Show shimmer immediately so the panel opens without blank flash
  fields.innerHTML = '<div style="padding:20px 0;text-align:center;color:var(--muted);font-size:.8rem">Loading fields…</div>';
  fields._sectionEl = el;
  editor._sectionEl = el;

  // Defer heavy DOM work one frame so the panel renders first
  requestAnimationFrame(() => {
    // Guard: user may have switched sections before the frame fired
    if (activeSectionIndex !== idx) return;

    // Helper: read computed styles from an iframe element into an init object for _styleBar
    const iframeView = el.ownerDocument.defaultView;
    function _elInit(domEl) {
      if (!domEl) return {};
      const cs = iframeView.getComputedStyle(domEl);
      const rawColor = domEl.style.color || cs.color || '';
      return {
        font:   domEl.style.fontFamily || '',
        size:   domEl.style.fontSize   || '',
        weight: domEl.style.fontWeight || '',
        color:  rawColor ? _rgbToHex(rawColor) : '#111827',
        bold:   (cs.fontWeight >= 600) || domEl.style.fontWeight === 'bold',
        italic: cs.fontStyle === 'italic' || domEl.style.fontStyle === 'italic',
      };
    }

    // ── Gather editable elements ───────────────────────────────────────────
    // Collect all HTML into one string — avoids O(n²) innerHTML re-parses
    const htmlChunks = [];
    let fieldIdx = 0;

    // Metadata to store on fields after single innerHTML set
    let brandEl = null, brandFid = '';

    // Always show Logo / Image + Brand Name only for the first section (nav/header)
    const logo = el.querySelector('img');
    if (activeSectionIndex === 0) {
      fieldIdx++;
      htmlChunks.push(_imgField(fieldIdx, 'Logo / Image', logo ? logo.src : '', logo ? logo.alt : '', `img-${fieldIdx}`));

      // Brand Name — either sibling of logo img, or text-only logo element
      if (logo) {
        const sib = logo.nextElementSibling;
        if (sib && sib.tagName !== 'IMG' && sib.textContent.trim().length > 0 && sib.textContent.trim().length < 120)
          brandEl = sib;
      }
      if (!brandEl) {
        const textLogo = el.querySelector('.logo, .brand, .site-title, [class*="logo"], [class*="brand"]');
        if (textLogo && textLogo.textContent.trim().length < 120) brandEl = textLogo;
      }
      fieldIdx++;
      brandFid = `txt-${fieldIdx}`;
      htmlChunks.push(_textField(fieldIdx, 'Brand Name / Site Title', brandEl ? brandEl.textContent.trim() : '', brandFid, _elInit(brandEl)));
    }

    // Headings — track each one so _getFidTargets can map by index
    const _headingEls = [...el.querySelectorAll('h1,h2,h3,h4')].filter(h => h.innerText.trim());
    const _headingStartField = fieldIdx + 1;
    _headingEls.forEach(h => {
      fieldIdx++;
      htmlChunks.push(_textField(fieldIdx, h.tagName, h.innerText.trim(), `txt-${fieldIdx}`, _elInit(h)));
    });

    // Paragraphs — track start field
    const _paraStartField = fieldIdx + 1;
    const _paraEls = [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3);
    _paraEls.forEach(p => {
      const text = p.innerText.trim();
      fieldIdx++;
      htmlChunks.push(_textareaField(fieldIdx, 'Paragraph', text.slice(0, 600), `para-${fieldIdx}`, _elInit(p)));
    });

    // Nav links / anchor texts — collect anchor refs before any innerHTML write
    const _linkFidToAnchor = new Map();
    el.querySelectorAll('a').forEach((a) => {
      const text = a.innerText.trim();
      const href = a.getAttribute('href') || '';
      if (!text || text.length > 60) return;
      fieldIdx++;
      const fid = `link-${fieldIdx}`;
      htmlChunks.push(_linkField(fieldIdx, 'Link', text, href, fid));
      _linkFidToAnchor.set(fid, a);
    });

    // Additional images (skip already-shown logo)
    el.querySelectorAll('img').forEach((img, i) => {
      if (i === 0 && activeSectionIndex === 0 && logo) return;
      fieldIdx++;
      htmlChunks.push(_imgField(fieldIdx, `Image ${i+1}`, img.src, img.alt, `img-${fieldIdx}`));
    });

    // ── Background editor (always shown at bottom) ──────────────────────────
    const computed = iframeView.getComputedStyle(el);
    const bgImage  = computed.backgroundImage !== 'none' ? computed.backgroundImage : (el.style.backgroundImage || '');
    const bgColor  = el.style.backgroundColor || computed.backgroundColor || '';
    const bgUrlMatch = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
    const bgUrl = bgUrlMatch ? bgUrlMatch[1] : '';
    htmlChunks.push(_bgField(bgUrl, bgColor));

    if (fieldIdx === 0 && !bgUrl && !bgColor) {
      fields.innerHTML = '<p style="font-size:.82rem;color:var(--muted);text-align:center;padding:24px">No editable text or images detected in this section.</p>';
    } else {
      // Single innerHTML write — eliminates O(n²) DOM rebuilds from repeated +=
      fields.innerHTML = htmlChunks.join('');
    }

    // Stamp metadata on stable DOM nodes (after innerHTML is final)
    if (brandEl) {
      fields._brandEl  = brandEl;
      fields._brandFid = brandFid;
    }
    fields._headingEls   = _headingEls;
    fields._headingStart = _headingStartField;
    fields._paraEls      = _paraEls;
    fields._paraStart    = _paraStartField;

    // Stamp _anchorEl on each link field div
    const _anchorElsList = [];
    _linkFidToAnchor.forEach((anchor, fid) => {
      const div = fields.querySelector(`[data-fid="${fid}"]`);
      if (div) {
        div._anchorEl = anchor;
        _anchorElsList.push(anchor);
      }
    });
    fields._anchorEls = _anchorElsList;

    fields._sectionEl = el;
    editor._sectionEl = el;
  }); // end requestAnimationFrame
}

function _bgField(bgUrl, bgColor) {
  const thumb = bgUrl ? `<img src="${_esc(bgUrl)}" style="width:100%;height:60px;object-fit:cover;border-radius:6px;margin-top:6px;border:1px solid var(--border)" id="bgThumb">` : `<div id="bgThumb"></div>`;
  const safeColor = (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') ? bgColor : '#ffffff';
  // Convert rgb() to hex for color input
  const hexColor = _rgbToHex(safeColor);
  return `<div data-type="bg" style="border-top:1px dashed var(--border);padding-top:12px;margin-top:4px">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:6px">🎨 Section Background</label>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Colour</label>
        <input type="color" id="secBgColor" value="${_esc(hexColor)}" oninput="_previewBgDebounced()" onchange="previewBg()"
          style="width:42px;height:32px;padding:2px;border:1.5px solid var(--border);border-radius:6px;cursor:pointer;background:var(--bg)">
      </div>
      <div style="flex:1">
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Colour opacity</label>
        <input type="range" id="secBgOpacity" min="0" max="100" value="100" oninput="document.getElementById('secBgOpacityVal').textContent=this.value+'%';_previewBgDebounced()"
          style="width:100%">
        <span id="secBgOpacityVal" style="font-size:.7rem;color:var(--muted)">100%</span>
      </div>
    </div>
    <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Background Image URL</label>
    <input type="text" id="secBgUrl" value="${_esc(bgUrl)}" placeholder="https://… or leave blank for colour only"
      oninput="_previewBgDebounced()"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;margin-bottom:6px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
    ${thumb}
    <div style="display:flex;gap:6px;margin-top:6px">
      <label class="btn btn-secondary btn-sm" style="cursor:pointer;flex:1;text-align:center">
        ⬆ Upload BG Image
        <input type="file" accept="image/*" style="display:none" onchange="uploadBgImage(this)">
      </label>
      <select id="secBgSize" onchange="previewBg()" style="padding:5px 7px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.78rem">
        <option value="cover">Cover</option>
        <option value="contain">Contain</option>
        <option value="auto">Auto</option>
        <option value="100% 100%">Stretch</option>
      </select>
      <button class="btn btn-secondary btn-sm" style="color:#ef4444;border-color:rgba(239,68,68,.4)" onclick="clearBg()" title="Remove background">🗑</button>
    </div>
    <div style="display:flex;gap:8px;margin-top:6px;align-items:center">
      <label style="font-size:.7rem;color:var(--muted)">Overlay darkness:</label>
      <input type="range" id="secBgOverlay" min="0" max="80" value="0" oninput="document.getElementById('secBgOverlayVal').textContent=this.value+'%';_previewBgDebounced()"
        style="flex:1">
      <span id="secBgOverlayVal" style="font-size:.7rem;color:var(--muted);white-space:nowrap">0%</span>
    </div>
  </div>`;
}

function _rgbToHex(rgb) {
  if (!rgb || rgb === 'transparent') return '#ffffff';
  if (rgb.startsWith('#')) return rgb;
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return '#ffffff';
  return '#' + [m[1],m[2],m[3]].map(x => parseInt(x).toString(16).padStart(2,'0')).join('');
}

function previewBg() {
  if (activeSectionIndex === null) return;
  const { el } = stagingSections[activeSectionIndex];
  _applyBgToEl(el);
  // Update thumb
  const url = document.getElementById('secBgUrl')?.value || '';
  const thumb = document.getElementById('bgThumb');
  if (thumb && url) { thumb.tagName === 'IMG' ? (thumb.src = url) : (thumb.outerHTML = `<img src="${url}" style="width:100%;height:60px;object-fit:cover;border-radius:6px;margin-top:6px;border:1px solid var(--border)" id="bgThumb">`); }
}

function _bgTarget(el) {
  // If the section itself has a transparent/default background but a direct child
  // has a solid background (e.g. .about-strip), apply to that child instead.
  const doc = el.ownerDocument;
  const elBg = doc.defaultView.getComputedStyle(el).backgroundColor;
  const isTransparent = !elBg || elBg === 'rgba(0, 0, 0, 0)' || elBg === 'transparent';
  if (isTransparent) {
    // Check direct children — skip injected overlay badges
    for (const child of el.children) {
      if (child.classList.contains('__wb_badge')) continue;
      const childBg = doc.defaultView.getComputedStyle(child).backgroundColor;
      if (childBg && childBg !== 'rgba(0, 0, 0, 0)' && childBg !== 'transparent') {
        return child;
      }
    }
  }
  return el;
}

/* Ensure element has a unique data-wb-bg attribute for CSS targeting */
function _ensureWbId(target) {
  if (!target.dataset.wbBg) {
    target.dataset.wbBg = 'wb' + Math.random().toString(36).slice(2, 8);
  }
  return target.dataset.wbBg;
}

function _applyBgToEl(el) {
  const doc    = el.ownerDocument;
  const target = _bgTarget(el);
  const wbId   = _ensureWbId(target);

  const url     = document.getElementById('secBgUrl')?.value?.trim() || '';
  const color   = document.getElementById('secBgColor')?.value || '#ffffff';
  const opacity = (document.getElementById('secBgOpacity')?.value ?? 100) / 100;
  const size    = document.getElementById('secBgSize')?.value || 'cover';
  const overlay = (document.getElementById('secBgOverlay')?.value ?? 0) / 100;

  const r = parseInt(color.slice(1,3),16), g = parseInt(color.slice(3,5),16), b = parseInt(color.slice(5,7),16);
  const rgba = `rgba(${r},${g},${b},${opacity})`;

  let css = '';
  if (url) {
    const overlayPart = overlay > 0 ? `linear-gradient(rgba(0,0,0,${overlay}),rgba(0,0,0,${overlay})),` : '';
    css = `[data-wb-bg="${wbId}"]{background-image:${overlayPart}url("${url}") !important;background-size:${size} !important;background-position:center !important;background-repeat:no-repeat !important;background-color:transparent !important;}`;
  } else {
    css = `[data-wb-bg="${wbId}"]{background-image:none !important;background-color:${rgba} !important;}`;
  }

  // Inject/update a persistent <style id="__wb_bg_overrides"> in the iframe <head>
  let styleEl = doc.getElementById('__wb_bg_overrides');
  if (!styleEl) {
    styleEl = doc.createElement('style');
    styleEl.id = '__wb_bg_overrides';
    doc.head.appendChild(styleEl);
  }
  // Replace existing rule for this wbId or append it
  const ruleRe = new RegExp(`\\[data-wb-bg="${wbId}"\\]\\{[^}]*\\}`, 'g');
  styleEl.textContent = styleEl.textContent.replace(ruleRe, '').trim() + '\n' + css;
}

async function uploadBgImage(inputEl) {
  const file = inputEl.files[0];
  if (!file) return;
  inputEl.value = '';
  openImageEditor(file, async blob => {
    const fd = new FormData();
    fd.append('file', blob, 'image.png');
    const r = await fetch(`${API}/shop/upload-image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (r.ok) {
      const data = await r.json();
      const url = window.location.origin + (data.full_url || data.thumb_url || '');
      const inp = document.getElementById('secBgUrl');
      if (inp) { inp.value = url; previewBg(); }
      toast('Background image uploaded ✅');
    } else {
      toast('Upload failed', false);
    }
  });
}

function clearBg() {
  if (activeSectionIndex === null) return;
  const { el } = stagingSections[activeSectionIndex];
  const doc    = el.ownerDocument;
  const target = _bgTarget(el);
  const wbId   = target.dataset.wbBg;
  if (wbId) {
    const styleEl = doc.getElementById('__wb_bg_overrides');
    if (styleEl) {
      const ruleRe = new RegExp(`\\[data-wb-bg="${wbId}"\\]\\{[^}]*\\}`, 'g');
      styleEl.textContent = styleEl.textContent.replace(ruleRe, '').trim();
    }
    delete target.dataset.wbBg;
  }
  const inp = document.getElementById('secBgUrl');
  if (inp) inp.value = '';
  const thumb = document.getElementById('bgThumb');
  if (thumb && thumb.tagName === 'IMG') thumb.src = '';
  document.getElementById('secBgColor').value = '#ffffff';
}

function _styleBar(fid, init = {}) {
  const fonts = [
    ['','Font…'],["'Inter',sans-serif",'Inter'],["'Poppins',sans-serif",'Poppins'],
    ["'Playfair Display',serif",'Playfair Display'],["'Roboto',sans-serif",'Roboto'],
    ["'Lato',sans-serif",'Lato'],["'Montserrat',sans-serif",'Montserrat'],
    ["'Merriweather',serif",'Merriweather'],["'Nunito',sans-serif",'Nunito'],
    ["'Open Sans',sans-serif",'Open Sans'],["'Raleway',sans-serif",'Raleway'],
    ["Georgia,serif",'Georgia'],["'Courier New',monospace",'Courier New'],
  ];
  const sizes = [
    ['','Size…'],['11px','11'],['12px','12'],['13px','13'],['14px','14'],
    ['15px','15'],['16px','16'],['18px','18'],['20px','20'],['22px','22'],
    ['24px','24'],['28px','28'],['32px','32'],['36px','36'],['42px','42'],
    ['48px','48'],['56px','56'],['64px','64'],['72px','72'],
  ];
  const fontOpts = fonts.map(([v,l]) => `<option value="${v}"${init.font===v?' selected':''}>${l}</option>`).join('');
  const sizeOpts = sizes.map(([v,l]) => `<option value="${v}"${init.size===v?' selected':''}>${l}</option>`).join('');
  const initColor = init.color || '#111827';
  const isBold    = init.bold   ? 'background:rgba(99,102,241,.25);font-weight:700' : '';
  const isItalic  = init.italic ? 'background:rgba(99,102,241,.25);font-style:italic' : '';
  const weights = [
    ['','Weight…'],['300','Light'],['400','Regular'],['500','Medium'],
    ['600','SemiBold'],['700','Bold'],['800','ExtraBold'],['900','Black'],
  ];
  const wOpts = weights.map(([v,l]) => `<option value="${v}"${init.weight===v?' selected':''}>${l}</option>`).join('');
  return `<div data-stylebar="${fid}" style="display:flex;gap:5px;flex-wrap:wrap;margin-top:6px;align-items:center;background:rgba(99,102,241,.04);border:1px solid var(--border);border-radius:7px;padding:7px 8px">
    <select data-fid="${fid}-font" title="Font family"
      style="padding:3px 5px;background:var(--bg);border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:.72rem;flex:2;min-width:110px"
      onchange="previewFieldStyle('${fid}')">${fontOpts}</select>
    <select data-fid="${fid}-size" title="Font size"
      style="padding:3px 5px;background:var(--bg);border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:.72rem;width:68px"
      onchange="previewFieldStyle('${fid}')">${sizeOpts}</select>
    <select data-fid="${fid}-weight" title="Font weight"
      style="padding:3px 5px;background:var(--bg);border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:.72rem;width:84px"
      onchange="previewFieldStyle('${fid}')">${wOpts}</select>
    <input type="color" data-fid="${fid}-color" value="${initColor}" title="Text colour"
      oninput="_previewFieldStyleDebounced('${fid}')" onchange="previewFieldStyle('${fid}')"
      style="width:30px;height:26px;padding:1px;border:1px solid var(--border);border-radius:5px;cursor:pointer;background:var(--bg)">
    <button data-fid="${fid}-bold" title="Bold" onclick="toggleStyleBtn(this,'${fid}','bold')"
      style="width:26px;height:26px;border:1px solid var(--border);border-radius:5px;background:var(--bg);cursor:pointer;font-weight:700;color:var(--text);font-size:.85rem;${isBold}">B</button>
    <button data-fid="${fid}-italic" title="Italic" onclick="toggleStyleBtn(this,'${fid}','italic')"
      style="width:26px;height:26px;border:1px solid var(--border);border-radius:5px;background:var(--bg);cursor:pointer;font-style:italic;color:var(--text);font-size:.85rem;${isItalic}"><em>I</em></button>
  </div>`;
}

function _textField(idx, tag, val, fid, init = {}) {
  return `<div data-fid="${fid}" data-type="text" data-tag="${tag}">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <input type="text" value="${_esc(val)}" data-fid="${fid}"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.88rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    ${_styleBar(fid, init)}
  </div>`;
}

function _textareaField(idx, tag, val, fid, init = {}) {
  return `<div data-fid="${fid}" data-type="para" data-tag="${tag}">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <textarea data-fid="${fid}" rows="3"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.85rem;resize:vertical;outline:none;font-family:inherit"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">${_esc(val)}</textarea>
    ${_styleBar(fid, init)}
  </div>`;
}

function _linkField(idx, tag, text, href, fid) {
  return `<div data-fid="${fid}" data-type="link" style="position:relative">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <input type="text" value="${_esc(text)}" data-fid="${fid}-text" placeholder="Link label"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.88rem;outline:none;margin-bottom:4px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <input type="text" value="${_esc(href)}" placeholder="href e.g. #section or https://…" data-fid="${fid}-href"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.8rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-secondary btn-sm" style="flex:1" onclick="addSectionLink(this)">＋ Add Link After</button>
      <button class="btn btn-secondary btn-sm" style="color:#ef4444;border-color:rgba(239,68,68,.4)" onclick="removeSectionLink(this, '${fid}')">🗑 Remove</button>
    </div>
  </div>`;
}

function removeSectionLink(btn, fid) {
  const wrap = btn.closest('[data-fid]');
  if (!wrap) return;
  wrap.remove();
  // renumber labels
  _renumberLinkFields();
}

function addSectionLink(btn) {
  const wrap = btn.closest('[data-fid]');
  if (!wrap) return;
  const existing = document.querySelectorAll('#secEditorFields [data-type="link"]');
  const newIdx = existing.length + 1;
  const fid = `link-new-${Date.now()}`;
  const newEl = document.createElement('div');
  newEl.innerHTML = _linkField(newIdx, 'New Link', '', '', fid);
  wrap.after(newEl.firstElementChild);
  _renumberLinkFields();
}

function _renumberLinkFields() {
  document.querySelectorAll('#secEditorFields [data-type="link"]').forEach((div, i) => {
    const lbl = div.querySelector('label span:first-child');
    if (lbl) lbl.textContent = lbl.textContent.replace(/^\d+\./, `${i + 1}.`);
  });
}

function moveLinkField(btn, dir) {
  const wrap = btn.closest('[data-type="link"]');
  if (!wrap) return;
  const all = [...document.querySelectorAll('#secEditorFields [data-type="link"]')];
  const idx = all.indexOf(wrap);
  const swapIdx = idx + dir;
  if (swapIdx < 0 || swapIdx >= all.length) return;
  const sibling = all[swapIdx];
  if (dir === -1) {
    wrap.parentNode.insertBefore(wrap, sibling);
  } else {
    wrap.parentNode.insertBefore(sibling, wrap);
  }
  _renumberLinkFields();
}

function _imgField(idx, tag, src, alt, fid) {
  const thumb = src ? `<img src="${_esc(src)}" style="height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px">` : '';
  return `<div data-fid="${fid}" data-type="img">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    ${thumb}
    <input type="text" value="${_esc(src)}" placeholder="Image URL" data-fid="${fid}-src"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;margin-top:6px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <input type="text" value="${_esc(alt)}" placeholder="Alt text (description)" data-fid="${fid}-alt"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.8rem;outline:none;margin-top:4px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <div style="display:flex;gap:6px;margin-top:6px">
      <label class="btn btn-secondary btn-sm" style="cursor:pointer;flex:1;text-align:center">
        ⬆ Upload Image
        <input type="file" accept="image/*" style="display:none" onchange="uploadSectionImage(this,'${fid}')">
      </label>
      <button class="btn btn-secondary btn-sm" onclick="clearSectionImage('${fid}')" title="Remove image">🗑 Remove</button>
    </div>
  </div>`;
}

function _esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* Set text on an element without destroying inner styling spans/em/strong.
   Walks down to the deepest single-child inline element that holds the text,
   so font classes on wrappers like <span class="fancy"> are preserved. */
function _setText(el, text) {
  // Walk into sole child inline elements (span, em, strong, b, i, a without href change)
  let target = el;
  while (target.children.length === 1) {
    const child = target.children[0];
    const tag = child.tagName;
    if (['SPAN','EM','STRONG','B','I','MARK','SMALL'].includes(tag)) {
      target = child;
    } else break;
  }
  // Only set textContent on the deepest target; preserves all ancestor element classes/styles
  target.textContent = text;
}

/* Apply style bar values from the editor panel onto a live DOM element */
function _applyStyleBarToEl(fieldsEl, fid, domEl) {
  const font   = fieldsEl.querySelector(`[data-fid="${fid}-font"]`)?.value   || '';
  const size   = fieldsEl.querySelector(`[data-fid="${fid}-size"]`)?.value   || '';
  const weight = fieldsEl.querySelector(`[data-fid="${fid}-weight"]`)?.value || '';
  const color  = fieldsEl.querySelector(`[data-fid="${fid}-color"]`)?.value  || '';
  const boldActive   = fieldsEl.querySelector(`[data-fid="${fid}-bold"]`)?.dataset.active === '1';
  const italicActive = fieldsEl.querySelector(`[data-fid="${fid}-italic"]`)?.dataset.active === '1';
  // Use setProperty with 'important' so styles override template !important CSS rules
  if (font)   domEl.style.setProperty('font-family',  font,               'important');
  if (size)   domEl.style.setProperty('font-size',    size,               'important');
  if (color)  domEl.style.setProperty('color',        color,              'important');
  if (weight) domEl.style.setProperty('font-weight',  weight,             'important');
  else if (boldActive) domEl.style.setProperty('font-weight', 'bold',     'important');
  if (italicActive) domEl.style.setProperty('font-style',    'italic',    'important');
}

/* Apply edits back into the live iframe DOM */
function applySecEdits() {
  try {
  const frame = document.getElementById('stagingIframe');
  const doc = frame.contentDocument;
  if (!doc || activeSectionIndex === null) return;
  _historyPush();

  const { el } = stagingSections[activeSectionIndex];
  const fieldsEl = document.getElementById('secEditorFields');

  // Rebuild editable element lists from the section
  const headings  = [...el.querySelectorAll('h1,h2,h3,h4')].filter(h => h.innerText.trim());
  const paras     = [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3);
  const links     = [...el.querySelectorAll('a')].filter(a => (a.innerText.trim().length > 0) && (a.innerText.trim().length <= 60));
  let imgs        = [...el.querySelectorAll('img')];

  let hIdx = 0, pIdx = 0, lIdx = 0, iIdx = 0;
  let fieldNum = 0;

  // Logo + Brand Name — only for first section
  if (activeSectionIndex === 0) {
    fieldNum++;
    const logoFid = `img-${fieldNum}`;
    const logoSrcEl = fieldsEl.querySelector(`input[data-fid="${logoFid}-src"]`);
    const logoAltEl = fieldsEl.querySelector(`input[data-fid="${logoFid}-alt"]`);
    if (logoSrcEl && logoSrcEl.value.trim()) {
      let logoImg = imgs[0];
      if (!logoImg) {
        logoImg = el.ownerDocument.createElement('img');
        logoImg.style.cssText = 'height:48px;object-fit:contain;vertical-align:middle;margin-right:10px';
        el.querySelector('.logo, .brand, [class*="logo"]')?.prepend(logoImg) || el.prepend(logoImg);
        imgs = [logoImg, ...imgs]; iIdx = 0;
      }
      logoImg.src = logoSrcEl.value;
      logoImg.setAttribute('src', logoSrcEl.value);
      if (logoAltEl) logoImg.alt = logoAltEl.value;
      iIdx = 1;
    }

    fieldNum++;
    const brandFid = `txt-${fieldNum}`;
    const brandInp = fieldsEl.querySelector(`input[data-fid="${brandFid}"]`);
    if (brandInp) {
      const brandEl = fieldsEl._brandEl || (() => {
        let b = null;
        if (imgs[0]) { const sib = imgs[0].nextElementSibling; if (sib && sib.tagName !== 'IMG') b = sib; }
        if (!b) b = el.querySelector('.logo, .brand, .site-title, [class*="logo"], [class*="brand"]');
        return b;
      })();
      if (brandEl) {
        _setText(brandEl, brandInp.value);
        _applyStyleBarToEl(fieldsEl, brandFid, brandEl);
      }
    }
  }

  // Headings — apply text + styles
  headings.forEach(h => {
    fieldNum++;
    const fid = `txt-${fieldNum}`;
    const inp = fieldsEl.querySelector(`input[data-fid="${fid}"]`);
    if (inp) _setText(h, inp.value);
    _applyStyleBarToEl(fieldsEl, fid, h);
  });

  // Paragraphs — apply text + styles
  paras.forEach(p => {
    fieldNum++;
    const fid = `para-${fieldNum}`;
    const ta = fieldsEl.querySelector(`textarea[data-fid="${fid}"]`);
    if (ta) _setText(p, ta.value);
    _applyStyleBarToEl(fieldsEl, fid, p);
  });

  // Links — iterate by current field order (supports add/remove/reorder)
  const linkDivs = [...fieldsEl.querySelectorAll('[data-type="link"]')];
  const originalAnchors = fieldsEl._anchorEls || [];

  // _wrapperOf: if anchor is in a <li>, return the <li>; else the <a> itself
  const _wrapperOf = (a) => {
    const li = a.parentElement;
    return (li && li.tagName === 'LI') ? li : a;
  };

  // listParent: shared <ul>/<ol> only if ALL anchors share it
  const listParent = (() => {
    if (!originalAnchors.length) return null;
    const p = _wrapperOf(originalAnchors[0]).parentNode;
    if (!p || (p.tagName !== 'UL' && p.tagName !== 'OL')) return null;
    if (originalAnchors.every(a => _wrapperOf(a).parentNode === p)) return p;
    return null;
  })();

  // sharedParent: all bare <a> in the same container (e.g. hero-btns)
  const sharedParent = (() => {
    if (listParent || !originalAnchors.length) return null;
    const p = originalAnchors[0].parentNode;
    if (p && originalAnchors.every(a => a.parentNode === p)) return p;
    return null;
  })();

  const orderedAnchors = [];
  linkDivs.forEach((div) => {
    const fid     = div.getAttribute('data-fid');
    // Prefer the direct JS reference (set in openSecEditor via appendChild)
    const anchor  = div._anchorEl || null;
    const tEl     = div.querySelector(`input[data-fid="${fid}-text"]`);
    const hEl     = div.querySelector(`input[data-fid="${fid}-href"]`);
    const newText = tEl ? tEl.value.trim() : '';
    const newHref = hEl ? hEl.value.trim() : '';
    if (anchor) {
      _setText(anchor, newText);
      anchor.setAttribute('href', newHref || '#');
      orderedAnchors.push(anchor);
    } else if (newText) {
      // Newly added field (no _anchorEl) — create fresh anchor
      const a = el.ownerDocument.createElement('a');
      a.textContent = newText;
      a.setAttribute('href', newHref || '#');
      a.style.cssText = 'display:inline-block;margin:4px 8px;color:var(--accent,#6366f1)';
      div._anchorEl = a; // bind for future applies
      orderedAnchors.push(a);
    }
  });

  // Remove anchors (and their <li> wrappers) whose field was deleted
  originalAnchors.forEach(a => {
    if (!orderedAnchors.includes(a)) {
      const w = listParent ? _wrapperOf(a) : a;
      w.remove();
    }
  });

  // Re-insert in the new field order — use node AFTER last original wrapper as stable ref
  if (listParent && orderedAnchors.length) {
    const marker = listParent.ownerDocument.createComment('__wb_reorder');
    const lastW = _wrapperOf(originalAnchors[originalAnchors.length - 1]);
    listParent.insertBefore(marker, lastW.nextSibling);
    orderedAnchors.forEach(a => {
      const w = _wrapperOf(a);
      if (w === a && (listParent.tagName === 'UL' || listParent.tagName === 'OL')) {
        const li = el.ownerDocument.createElement('li');
        li.appendChild(a);
        listParent.insertBefore(li, marker);
      } else {
        listParent.insertBefore(w, marker);
      }
    });
    marker.remove();
  } else if (sharedParent && orderedAnchors.length) {
    const marker = sharedParent.ownerDocument.createComment('__wb_reorder');
    const lastOrig = originalAnchors[originalAnchors.length - 1];
    sharedParent.insertBefore(marker, lastOrig.nextSibling);
    orderedAnchors.forEach(a => sharedParent.insertBefore(a, marker));
    marker.remove();
  }
  // Scattered anchors (different parents per anchor): text/href updated in-place above only

  // Update _anchorEls and _anchorEl stamps to reflect current state (for subsequent applies)
  fieldsEl._anchorEls = orderedAnchors.slice();
  linkDivs.forEach((div, i) => { if (orderedAnchors[i]) div._anchorEl = orderedAnchors[i]; });

  // Advance fieldNum past link fields so image fids align with openSecEditor numbering
  fieldNum += linkDivs.length;

  // Remaining images
  imgs.slice(iIdx).forEach(img => {
    fieldNum++;
    const fid = `img-${fieldNum}`;
    const srcEl = fieldsEl.querySelector(`input[data-fid="${fid}-src"]`);
    const altEl = fieldsEl.querySelector(`input[data-fid="${fid}-alt"]`);
    if (srcEl) { img.src = srcEl.value; img.setAttribute('src', srcEl.value); }
    if (altEl) img.alt = altEl.value;
  });

  // Apply background (colour + image) if the bg panel fields exist
  if (document.getElementById('secBgColor') || document.getElementById('secBgUrl')) {
    _applyBgToEl(el);
  }

  toast('Changes applied to preview ✅ — click 💾 Save Changes to persist');
  document.getElementById('stagingStatusBar').textContent = 'Preview updated — unsaved. Click 💾 Save Changes.';
  // Re-inject responsive enhancements in case hamburger was part of the edited section
  try { _injectResponsiveEnhancements(frame.contentDocument); } catch(_) {}
  } catch (err) {
    console.error('[applySecEdits]', err);
    toast('❌ Failed to apply edits: ' + (err.message || 'unknown error'), false);
  }
}

async function uploadSectionImage(inputEl, fid) {
  const file = inputEl.files[0];
  if (!file) return;
  // Reset file input so the same file can be re-picked after editing
  inputEl.value = '';
  openImageEditor(file, async blob => {
    const fd = new FormData();
    fd.append('file', blob, 'image.png');
    const base = window.location.origin;
    const r = await fetch(`${API}/shop/upload-image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (r.ok) {
      const data = await r.json();
      const url = base + (data.full_url || data.thumb_url || '');
      const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
      if (srcEl) srcEl.value = url;
      // Show thumbnail preview
      const wrap = srcEl?.closest('[data-fid]');
      if (wrap) {
        const existing = wrap.querySelector('img');
        if (existing) existing.src = url;
        else { const img = document.createElement('img'); img.src = url; img.style.cssText='height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px'; wrap.prepend(img); }
      }
      toast('Image uploaded ✅');
    } else {
      toast('Image upload failed', false);
    }
  });
}

function clearSectionImage(fid) {
  const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
  if (srcEl) srcEl.value = '';
  const wrap = srcEl?.closest('[data-fid]');
  if (wrap) { const img = wrap.querySelector('img'); if (img) img.src = ''; }
}

function closeSecEditor() {
  activeSectionIndex = null;
  document.getElementById('secEditor').style.display = 'none';
  document.getElementById('secList').style.display = '';
  // Remove highlight from iframe
  const frame = document.getElementById('stagingIframe');
  if (frame.contentDocument) {
    frame.contentDocument.querySelectorAll('.__wb_hi').forEach(n => {
      n.style.outline = ''; n.classList.remove('__wb_hi');
    });
  }
}

/* Inject full responsive CSS + fix hamburger into any loaded iframe document.
   This runs after iframe load so it survives regardless of what's saved in the HTML file. */
function _injectResponsiveEnhancements(doc) {
  if (!doc || !doc.head) return;

  // Remove any old injected style so we don't duplicate on re-load
  const old = doc.getElementById('__wb_responsive');
  if (old) old.remove();

  const style = doc.createElement('style');
  style.id = '__wb_responsive';
  style.textContent = `
    .hamburger { display: none !important; background: none; border: none;
      font-size: 1.6rem; cursor: pointer; color: #fff; padding: 4px 8px; z-index: 1001; position: relative; }

    /* ── Tablet ── */
    @media (max-width: 900px) {
      .about-strip, .contact-grid {
        grid-template-columns: 1fr !important; gap: 32px !important;
      }
      .about-strip img { height: 240px !important; }
      .footer-grid { grid-template-columns: 1fr 1fr !important; }
      .section { padding: 64px 5% !important; }
      .hero h1 { font-size: clamp(1.8rem, 5vw, 3rem) !important; }
      .cat-grid, .testi-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important; }
    }

    /* ── Mobile ── */
    @media (max-width: 640px) {
      nav { position: relative !important; }
      .nav-links { display: none !important; }
      .hamburger { display: block !important; }
      .section { padding: 48px 16px !important; }
      .hero { padding: 60px 16px !important; min-height: 70vh !important; }
      .hero h1 { font-size: clamp(1.6rem, 7vw, 2.4rem) !important; }
      .hero p  { font-size: .95rem !important; }
      .hero-btns { flex-direction: column !important; align-items: center !important; }
      .hero-btns .btn, .hero-btns a {
        width: 100% !important; max-width: 320px !important;
        text-align: center !important; box-sizing: border-box !important;
      }
      .cat-grid, .testi-grid { grid-template-columns: 1fr !important; }
      .footer-grid { grid-template-columns: 1fr !important; }
      .footer-bottom { flex-direction: column !important; gap: 12px !important; text-align: center !important; }
      .form-row { grid-template-columns: 1fr !important; }
      .section-header h2 { font-size: 1.6rem !important; }
      .booking-form { padding: 24px 16px !important; }
    }
  `;
  doc.head.appendChild(style);

  // Fix hamburger: use inline styles directly (beats any CSS specificity)
  const hamburger = doc.querySelector('.hamburger');
  const navLinks  = doc.querySelector('.nav-links');
  const nav       = doc.querySelector('nav');
  if (hamburger && navLinks) {
    navLinks._wbOpen = false;

    // ── open/close helpers ──────────────────────────────────────────────
    const openMenu = () => {
      navLinks._wbOpen = true;
      navLinks.style.setProperty('display',        'flex',               'important');
      navLinks.style.setProperty('flex-direction', 'column',             'important');
      navLinks.style.setProperty('position',       'absolute',           'important');
      navLinks.style.setProperty('top',            '72px',               'important');
      navLinks.style.setProperty('left',           '0',                  'important');
      navLinks.style.setProperty('right',          '0',                  'important');
      navLinks.style.setProperty('background',     'rgba(20,20,34,.97)', 'important');
      navLinks.style.setProperty('padding',        '20px 16px',          'important');
      navLinks.style.setProperty('z-index',        '1000',               'important');
      navLinks.style.setProperty('box-shadow',     '0 8px 24px rgba(0,0,0,.5)', 'important');
      hamburger.textContent = '✕';
    };
    const closeMenu = () => {
      navLinks._wbOpen = false;
      navLinks.style.removeProperty('display');
      navLinks.style.removeProperty('flex-direction');
      navLinks.style.removeProperty('position');
      navLinks.style.removeProperty('top');
      navLinks.style.removeProperty('left');
      navLinks.style.removeProperty('right');
      navLinks.style.removeProperty('background');
      navLinks.style.removeProperty('padding');
      navLinks.style.removeProperty('z-index');
      navLinks.style.removeProperty('box-shadow');
      hamburger.textContent = '☰';
    };

    hamburger.onclick = (e) => {
      e.stopPropagation();
      navLinks._wbOpen ? closeMenu() : openMenu();
    };
    hamburger.textContent = '☰';

    // Close when a nav link is clicked (use capture so it fires before navigation)
    navLinks.addEventListener('click', (e) => {
      if (e.target.closest('a')) { setTimeout(closeMenu, 50); }
    }, true);

    // Close when clicking outside the nav
    doc.addEventListener('click', (e) => {
      if (navLinks._wbOpen && !navLinks.contains(e.target) && e.target !== hamburger) {
        closeMenu();
      }
    });

    // Close on hash navigation
    try { doc.defaultView.addEventListener('hashchange', () => setTimeout(closeMenu, 50)); } catch(_) {}

    // ── ResizeObserver: show/hide hamburger based on iframe body width ──
    // (CSS media query only responds to iframe viewport; this also handles
    //  cases where the iframe is narrowed by the dashboard panel layout)
    const applyMobileMode = (isMobile) => {
      if (isMobile) {
        hamburger.style.setProperty('display', 'block', 'important');
        if (!navLinks._wbOpen) {
          navLinks.style.setProperty('display', 'none', 'important');
        }
      } else {
        hamburger.style.removeProperty('display');
        navLinks.style.removeProperty('display');
        if (navLinks._wbOpen) closeMenu();
      }
    };
    try {
      const ro = new doc.defaultView.ResizeObserver(entries => {
        const w = entries[0].contentRect.width;
        applyMobileMode(w <= 640);
      });
      ro.observe(doc.body);
      // Run once immediately
      applyMobileMode(doc.body.getBoundingClientRect().width <= 640);
    } catch(_) {}
  }
}

function stagingRefresh() {
  const frame = document.getElementById('stagingIframe');
  if (!currentStagingUrl) { toast('No preview loaded yet', false); return; }
  stagingOverlayOn = false; stagingSections = []; activeSectionIndex = null;
  _historyStack = []; _originalHTML = null; _updateUndoBtn();
  const editBtn = document.getElementById('stagingEditBtn');
  if (editBtn) { editBtn.textContent = '🔢 Section Numbers'; editBtn.style.background = ''; }
  document.getElementById('secEditor').style.display = 'none';
  document.getElementById('secList').style.display = '';
  const btn = document.getElementById('stagingRefreshBtn');
  btn.disabled = true; btn.textContent = '⟳ …';
  const loading = document.getElementById('stagingLoading');
  loading.style.display = 'flex';
  frame.onload = () => {
    loading.style.display = 'none'; btn.disabled = false; btn.textContent = '⟳ Refresh';
    try { if (frame.contentDocument) _injectResponsiveEnhancements(frame.contentDocument); } catch(_) {}
  };
  frame.src = currentStagingUrl.split('?')[0] + '?t=' + Date.now();
}

function stagingPopout() {
  if (currentStagingUrl) window.open(currentStagingUrl, '_blank');
  else toast('No preview URL available yet', false);
}

// ── Global Font Panel ──────────────────────────────────────────────────────
let globalFontPanelOpen = false;
function jumpToSection(idx) {
  if (idx === '' || idx === null) return;
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || !stagingSections[idx]) return;
  const { el } = stagingSections[idx];
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  // Also open the editor for that section
  openSecEditor(parseInt(idx));
  // Reset dropdown
  setTimeout(() => { document.getElementById('stagingJumpSelect').value = ''; }, 300);
}

function toggleGlobalFonts() {
  globalFontPanelOpen = !globalFontPanelOpen;
  const panel = document.getElementById('globalFontPanel');
  panel.style.display = globalFontPanelOpen ? 'flex' : 'none';
  document.getElementById('stagingFontBtn').style.background = globalFontPanelOpen ? 'rgba(99,102,241,.2)' : '';
}

function applyGlobalFont() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) { toast('Preview not loaded', false); return; }
  _historyPush();
  const doc = frame.contentDocument;

  const bodyFont  = document.getElementById('gfBodyFont').value;
  const headFont  = document.getElementById('gfHeadFont').value;
  const baseSize  = document.getElementById('gfBaseSize').value;
  const bodyColor = document.getElementById('gfBodyColor').value;
  const headColor = document.getElementById('gfHeadColor').value;

  // Inject/update a <style id="__wb_global_fonts"> in iframe <head>
  let styleEl = doc.getElementById('__wb_global_fonts');
  if (!styleEl) {
    styleEl = doc.createElement('style');
    styleEl.id = '__wb_global_fonts';
    doc.head.appendChild(styleEl);
  }

  // Load Google Font if needed
  const allFonts = [bodyFont, headFont].filter(Boolean);
  allFonts.forEach(f => {
    const name = f.match(/'([^']+)'/)?.[1] || f.split(',')[0].trim();
    if (name && !name.includes('serif') && !name.includes('sans') && !name.includes('mono') && name !== 'Georgia' && name !== 'Courier New') {
      const linkId = `__wb_gf_${name.replace(/\s/g,'_')}`;
      if (!doc.getElementById(linkId)) {
        const link = doc.createElement('link');
        link.id = linkId;
        link.rel = 'stylesheet';
        link.href = `https://fonts.googleapis.com/css2?family=${encodeURIComponent(name)}:wght@400;600;700&display=swap`;
        doc.head.appendChild(link);
      }
    }
  });

  const rules = [];
  if (bodyFont || baseSize || bodyColor) {
    rules.push(`body { ${bodyFont ? `font-family:${bodyFont} !important;` : ''} ${baseSize ? `font-size:${baseSize} !important;` : ''} ${bodyColor ? `color:${bodyColor} !important;` : ''} }`);
  }
  if (headFont || headColor) {
    rules.push(`h1,h2,h3,h4,h5,h6 { ${headFont ? `font-family:${headFont} !important;` : ''} ${headColor ? `color:${headColor} !important;` : ''} }`);
  }
  styleEl.textContent = rules.join('\n');
  document.getElementById('stagingStatusBar').textContent = 'Global fonts applied to preview — click 💾 Save Changes to persist.';
}

// ── Per-field style preview ────────────────────────────────────────────────
function previewFieldStyle(fid) {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || activeSectionIndex === null) return;
  const { el } = stagingSections[activeSectionIndex];
  const fieldsEl = document.getElementById('secEditorFields');

  const font   = fieldsEl.querySelector(`[data-fid="${fid}-font"]`)?.value   || '';
  const size   = fieldsEl.querySelector(`[data-fid="${fid}-size"]`)?.value   || '';
  const weight = fieldsEl.querySelector(`[data-fid="${fid}-weight"]`)?.value || '';
  const color  = fieldsEl.querySelector(`[data-fid="${fid}-color"]`)?.value  || '';
  const boldBtn   = fieldsEl.querySelector(`[data-fid="${fid}-bold"]`);
  const italicBtn = fieldsEl.querySelector(`[data-fid="${fid}-italic"]`);
  const isBold   = boldBtn?.dataset.active === '1';
  const isItalic = italicBtn?.dataset.active === '1';

  const targets = _getFidTargets(el, fid);
  targets.forEach(t => {
    // Use setProperty with 'important' so styles override template !important CSS rules
    if (font)   t.style.setProperty('font-family',  font,            'important');
    if (size)   t.style.setProperty('font-size',    size,            'important');
    if (color)  t.style.setProperty('color',        color,           'important');
    if (weight) t.style.setProperty('font-weight',  weight,          'important');
    else if (isBold) t.style.setProperty('font-weight', 'bold',      'important');
    if (isItalic) t.style.setProperty('font-style',    'italic',     'important');
    else if (t.style.fontStyle === 'italic' && !isItalic) t.style.setProperty('font-style', '', 'important');
  });
}

/* Returns the iframe DOM element(s) corresponding to a field id */
function _getFidTargets(el, fid) {
  const fieldsEl = document.getElementById('secEditorFields');
  const headings = fieldsEl._headingEls || [...el.querySelectorAll('h1,h2,h3,h4')].filter(h => h.innerText.trim());
  const paras    = fieldsEl._paraEls    || [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3);
  const headStart = fieldsEl._headingStart || 1;
  const paraStart = fieldsEl._paraStart   || (headStart + headings.length);

  // Brand Name field (section 0 only) — stored by reference, not in headings list
  if (fieldsEl._brandFid === fid && fieldsEl._brandEl) return [fieldsEl._brandEl];

  const m = fid.match(/^(txt|para)-(\d+)$/);
  if (!m) return [];
  const kind = m[1], num = parseInt(m[2]);

  if (kind === 'txt') {
    const hIdx = num - headStart;
    if (hIdx >= 0 && hIdx < headings.length) return [headings[hIdx]];
    return [];
  }
  if (kind === 'para') {
    const pIdx = num - paraStart;
    if (pIdx >= 0 && pIdx < paras.length) return [paras[pIdx]];
    return [];
  }
  return [];
}

function toggleStyleBtn(btn, fid, prop) {
  const active = btn.dataset.active === '1';
  btn.dataset.active = active ? '0' : '1';
  if (!active) {
    btn.style.background = 'rgba(99,102,241,.25)';
  } else {
    btn.style.background = 'var(--bg)';
  }
  previewFieldStyle(fid);
}

async function saveStaged() {
  if (!stagedWebsiteId) return;
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) { toast('Preview not loaded yet', false); return; }
  const doc = frame.contentDocument;
  // Remove injected overlay badges and highlights
  doc.querySelectorAll('.__wb_badge').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_hi').forEach(n => { n.style.outline = ''; n.classList.remove('__wb_hi'); });
  // Remove browser extension injected elements (Grammarly, etc.)
  doc.querySelectorAll('grammarly-desktop-integration, #PING_IFRAME_FORM_DETECTION, [id^="PING_"], [data-grammarly-shadow-root]').forEach(n => n.remove());
  const html = doc.documentElement.outerHTML;
  if (!html.trim()) { toast('Nothing in preview to save', false); return; }

  const btn = document.getElementById('stagingSaveBtn');
  btn.disabled = true; btn.textContent = '💾 Saving…';

  const r = await apiFetch(`/websites/${stagedWebsiteId}/staged-html`, {
    method: 'PUT',
    body: JSON.stringify({ html }),
  });
  btn.disabled = false; btn.textContent = '💾 Save Changes';

  if (r && r.saved) {
    toast('Changes saved ✅');
    // Force iframe reload to reflect saved changes
    const frame = document.getElementById('stagingIframe');
    const url = currentStagingUrl;
    frame.src = '';
    setTimeout(() => { frame.src = url + '?t=' + Date.now(); }, 100);
    document.getElementById('stagingStatusBar').textContent = `Saved to: ${r.path}`;
    // Update status badge
    const w = (websites || []).find(x => x.website_id === stagedWebsiteId);
    if (w) { w.build_status = 'staged'; }
    const badge = document.getElementById('stagingStatusBadge');
    if (badge) badge.innerHTML = `<span class="tag draft" style="background:rgba(245,158,11,.15);color:var(--warn)">🔧 Staged</span>`;
  } else {
    toast('Failed to save changes', false);
  }
}

async function goLive() {
  if (!stagedWebsiteId) return;
  const btn = document.getElementById('stagingGoLiveBtn');
  btn.disabled = true; btn.textContent = '🚀 Deploying…';

  const r = await apiFetch(`/websites/${stagedWebsiteId}/deploy`, { method: 'POST' });
  btn.disabled = false; btn.textContent = '🚀 Go Live';

  if (r && r.url) {
    const target = r.target === 's3' ? 'S3' : 'local output';
    toast(`🎉 Live on ${target}: ${r.url}`);
    const badge = document.getElementById('stagingStatusBadge');
    if (badge) badge.innerHTML = statusBadge('live');
    document.getElementById('stagingStatusBar').textContent = `Live URL: ${r.url}`;

    // Update in-memory site record
    const idx = (websites || []).findIndex(x => x.website_id === stagedWebsiteId);
    if (idx !== -1) {
      websites[idx].status = 'live';
      if (r.target === 's3') websites[idx].s3_url = r.url;
      else websites[idx].live_url = r.url;  // staging path untouched; live_url = published path
    }
    // Reload iframe to the live path
    currentStagingUrl = r.url;
    const frame = document.getElementById('stagingIframe');
    frame.src = r.url;
    document.getElementById('stagingStatusBar').textContent = `Live at: ${r.url}`;
  } else {
    toast('Deployment failed', false);
  }
}

// ── Edit Website ───────────────────────────────────────────────────────────
async function loadEditWebsiteOptions() {
  const sites = await _fetchMyWebsites();
  const sel = document.getElementById('editWebsitePicker');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Choose a website —</option>';
  sites.forEach(w => {
    sel.innerHTML += `<option value="${w.website_id}">${w.name || w.website_id} (${w.status || 'draft'})</option>`;
  });
}

async function loadEditWebsite() {
  const id = document.getElementById('editWebsitePicker').value;
  const form = document.getElementById('editWebsiteForm');
  if (!id) { form.style.display = 'none'; return; }

  const w = (websites || []).find(x => x.website_id === id)
    || await apiFetch(`/websites/my`).then(list => (list||[]).find(x => x.website_id === id));
  if (!w) return;

  document.getElementById('ewName').value  = w.name  || '';
  document.getElementById('ewTheme').value = w.theme || 'modern';
  document.getElementById('ewReq').value   = '';
  document.getElementById('editBuildProgress').style.display = 'none';
  document.getElementById('editBuildMsg').textContent = '';
  document.getElementById('editBuildBar').style.width = '5%';
  document.getElementById('editBuildSpinner').style.display = 'inline-block';
  form.style.display = '';
}

function cancelEditWebsite() {
  document.getElementById('editWebsitePicker').value = '';
  document.getElementById('editWebsiteForm').style.display = 'none';
}

async function rebuildWebsite() {
  const id = document.getElementById('editWebsitePicker').value;
  const requirements = document.getElementById('ewReq').value.trim();
  if (!id) { toast('Please select a website', false); return; }
  if (!requirements) { toast('Please describe the changes you want', false); return; }

  // Update metadata (name / theme)
  const name  = document.getElementById('ewName').value.trim();
  const theme = document.getElementById('ewTheme').value;
  await apiFetch(`/websites/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ ...(name && { name }), ...(theme && { theme }) }),
  });

  const progress  = document.getElementById('editBuildProgress');
  const msgEl     = document.getElementById('editBuildMsg');
  const barEl     = document.getElementById('editBuildBar');
  const spinnerEl = document.getElementById('editBuildSpinner');
  progress.style.display   = '';
  spinnerEl.style.display  = 'inline-block';
  msgEl.textContent        = '🔄 Queuing rebuild…';
  barEl.style.width        = '5%';

  const use_web_search = document.getElementById('ewWebSearch')?.checked ?? true;
  const result = await apiFetch(`/websites/${id}/build`, {
    method: 'POST',
    body: JSON.stringify({ requirements, use_web_search }),
  });

  if (!result || !result.job_id) {
    msgEl.textContent = `❌ ${apiFetch._lastError || 'Failed to queue rebuild.'}`;
    spinnerEl.style.display = 'none';
    return;
  }

  const stageLabels = {
    queued:  { msg: '⏳ Build queued — waiting for worker…', pct: 10 },
    running: { msg: '🤖 AI agents rebuilding your website…', pct: 55 },
    built:   { msg: '✅ Rebuild complete!',                   pct: 100 },
    error:   { msg: '❌ Rebuild failed.',                     pct: 100 },
    timeout: { msg: '⚠️ Taking longer than expected. Check My Websites for status.', pct: 100 },
  };

  await new Promise(resolve => {
    const es = new EventSource(
      `${API}/../api/v1/websites/${id}/build-stream?token=${encodeURIComponent(token)}`
    );
    es.onmessage = async (e) => {
      try {
        const data = JSON.parse(e.data);
        const status = data.build_status || 'queued';
        const s = stageLabels[status] || stageLabels.queued;
        msgEl.textContent = data.error ? `❌ ${data.error}` : s.msg;
        barEl.style.width = s.pct + '%';
        if (['built', 'error', 'timeout', 'not_found'].includes(status)) {
          es.close();
          spinnerEl.style.display = 'none';
          if (status === 'built') {
            toast('Rebuild complete! Opening Staging Area…');
            await loadAllSites();
            await loadStagingWebsites();
            setTimeout(() => { showPage('staging'); loadStagedSite(id); }, 1500);
          } else if (status === 'error') {
            toast(data.error || 'Rebuild failed. Please try again.', false);
          }
          resolve();
        }
      } catch (_) {}
    };
    es.onerror = () => { es.close(); spinnerEl.style.display = 'none'; resolve(); };
  });
}


// ═══════════════════════════════════════════════════
// IMAGE EDITOR STATE
// ═══════════════════════════════════════════════════
let _imgCropper     = null;   // Cropper.js instance
let _imgOrigBlob    = null;   // original File object
let _imgWorkingImg  = null;   // HTMLImageElement used for canvas ops
let _imgCallback    = null;   // fn(blob) called after Apply & Upload
let _imgCurrentTab  = 'crop';
let _imgFlipX       = 1;      // 1 or -1
let _imgFlipY       = 1;

/* Open the editor. callback(blob) will receive the processed image blob */
function openImageEditor(file, callback) {
  _imgCallback   = callback;
  _imgOrigBlob   = file;
  _imgFlipX      = 1; _imgFlipY = 1;

  const reader = new FileReader();
  reader.onload = e => {
    const src = e.target.result;
    // Load into crop img
    const cropImg = document.getElementById('_imgCropSrc');
    cropImg.src   = src;
    // Preload working image for canvas ops
    _imgWorkingImg = new Image();
    _imgWorkingImg.onload = () => {
      _imgUpdateInfo(_imgWorkingImg.naturalWidth, _imgWorkingImg.naturalHeight);
      // Init resize fields
      document.getElementById('_rsW').value = _imgWorkingImg.naturalWidth;
      document.getElementById('_rsH').value = _imgWorkingImg.naturalHeight;
    };
    _imgWorkingImg.src = src;

    const modal = document.getElementById('imgEditorModal');
    modal.style.display = 'flex';

    // Init cropper after image loads
    cropImg.onload = () => {
      if (_imgCropper) { _imgCropper.destroy(); _imgCropper = null; }
      _imgCropper = new Cropper(cropImg, { viewMode: 1, autoCropArea: 1, responsive: true });
    };
    // If already loaded (cached)
    if (cropImg.complete && cropImg.naturalWidth) cropImg.onload();
  };
  reader.readAsDataURL(file);
  _imgTab('crop');
}

function _imgEdClose() {
  document.getElementById('imgEditorModal').style.display = 'none';
  if (_imgCropper) { _imgCropper.destroy(); _imgCropper = null; }
}

function _imgTab(tab) {
  _imgCurrentTab = tab;
  const tabs = ['crop','resize','enhance'];
  tabs.forEach(t => {
    const btn  = document.querySelector(`._imgtab[data-tab="${t}"]`);
    const ctrl = document.getElementById(`_imgCtrl${t.charAt(0).toUpperCase()+t.slice(1)}`);
    const active = t === tab;
    if (btn)  { btn.style.background  = active ? 'var(--accent)' : 'var(--sidebar)'; btn.style.color = active ? '#fff' : 'var(--muted)'; }
    if (ctrl) ctrl.style.display = active ? 'flex' : 'none';
  });

  const canvas = document.getElementById('_imgCanvas');
  const cropWrap = document.getElementById('_imgCropWrap');
  if (tab === 'crop') {
    canvas.style.display   = 'none';
    cropWrap.style.display = '';
  } else {
    canvas.style.display   = 'block';
    cropWrap.style.display = 'none';
    _renderCanvas();
  }
}

function _imgUpdateInfo(w, h) {
  document.getElementById('_imgEdInfo').textContent = `${w} × ${h} px`;
}

// ── CROP ────────────────────────────────────────────
function _cropAR(w, h) {
  if (!_imgCropper) return;
  if (w === 'free') _imgCropper.setAspectRatio(NaN);
  else              _imgCropper.setAspectRatio(w / h);
}
function _cropRotate(deg)   { _imgCropper?.rotate(deg); }
function _cropFlip(axis) {
  if (!_imgCropper) return;
  if (axis === 'h') { _imgFlipX *= -1; _imgCropper.scaleX(_imgFlipX); }
  else              { _imgFlipY *= -1; _imgCropper.scaleY(_imgFlipY); }
}
function _cropCommit() {
  if (!_imgCropper) return;
  const croppedCanvas = _imgCropper.getCroppedCanvas({ imageSmoothingQuality: 'high' });
  croppedCanvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const newImg = new Image();
    newImg.onload = () => {
      _imgWorkingImg = newImg;
      _imgUpdateInfo(newImg.naturalWidth, newImg.naturalHeight);
      document.getElementById('_rsW').value = newImg.naturalWidth;
      document.getElementById('_rsH').value = newImg.naturalHeight;
      // Reinit cropper on the new cropped image
      const cropImg  = document.getElementById('_imgCropSrc');
      cropImg.src    = url;
      cropImg.onload = () => {
        if (_imgCropper) { _imgCropper.destroy(); _imgCropper = null; }
        _imgCropper = new Cropper(cropImg, { viewMode: 1, autoCropArea: 1, responsive: true });
      };
      if (cropImg.complete) cropImg.onload();
    };
    newImg.src = url;
    _imgOrigBlob = blob; // update working blob
  }, 'image/png');
}

// ── RESIZE ──────────────────────────────────────────
let _rsOrigW = 0, _rsOrigH = 0;
function _rsSync(changed) {
  if (!document.getElementById('_rsLock').checked) return;
  if (!_imgWorkingImg) return;
  const w = _imgWorkingImg.naturalWidth;
  const h = _imgWorkingImg.naturalHeight;
  const ratio = w / h;
  if (changed === 'w') {
    const nw = parseInt(document.getElementById('_rsW').value) || 0;
    document.getElementById('_rsH').value = Math.round(nw / ratio);
  } else {
    const nh = parseInt(document.getElementById('_rsH').value) || 0;
    document.getElementById('_rsW').value = Math.round(nh * ratio);
  }
}
function _rsPreset(w, h) {
  document.getElementById('_rsW').value = w;
  document.getElementById('_rsH').value = h;
}
function _rsApply() {
  if (!_imgWorkingImg) return;
  const w = parseInt(document.getElementById('_rsW').value) || _imgWorkingImg.naturalWidth;
  const h = parseInt(document.getElementById('_rsH').value) || _imgWorkingImg.naturalHeight;
  const offscreen = document.createElement('canvas');
  offscreen.width  = w; offscreen.height = h;
  offscreen.getContext('2d').drawImage(_imgWorkingImg, 0, 0, w, h);
  offscreen.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const ni   = new Image();
    ni.onload  = () => {
      _imgWorkingImg = ni;
      _imgUpdateInfo(w, h);
      _renderCanvas();
      // also refresh crop tab src
      const cropImg = document.getElementById('_imgCropSrc');
      cropImg.src   = url;
      if (_imgCropper) { _imgCropper.destroy(); _imgCropper = null; }
    };
    ni.src  = url;
    _imgOrigBlob = blob;
  }, 'image/png');
}

// ── ENHANCE ─────────────────────────────────────────
function _enhancePreview() { _renderCanvas(); }
function _enhPreset(br, co, sa, bl) {
  document.getElementById('_enBr').value = br; document.getElementById('_enBrVal').textContent = br + '%';
  document.getElementById('_enCo').value = co; document.getElementById('_enCoVal').textContent = co + '%';
  document.getElementById('_enSa').value = sa; document.getElementById('_enSaVal').textContent = sa + '%';
  document.getElementById('_enBl').value = bl; document.getElementById('_enBlVal').textContent = bl + 'px';
  _renderCanvas();
}

function _renderCanvas() {
  if (!_imgWorkingImg) return;
  const canvas  = document.getElementById('_imgCanvas');
  const ctx     = canvas.getContext('2d');
  canvas.width  = _imgWorkingImg.naturalWidth;
  canvas.height = _imgWorkingImg.naturalHeight;

  const br = document.getElementById('_enBr')?.value ?? 100;
  const co = document.getElementById('_enCo')?.value ?? 100;
  const sa = document.getElementById('_enSa')?.value ?? 100;
  const bl = document.getElementById('_enBl')?.value ?? 0;

  ctx.filter = `brightness(${br}%) contrast(${co}%) saturate(${sa}%) blur(${bl}px)`;
  ctx.drawImage(_imgWorkingImg, 0, 0);
  ctx.filter = 'none';
  _imgUpdateInfo(canvas.width, canvas.height);
}

// ── APPLY & UPLOAD ───────────────────────────────────
async function _imgEdApplyUpload() {
  // 1. Commit crop if on crop tab (or if cropper exists)
  const finalBlob = await new Promise(resolve => {
    if (_imgCurrentTab === 'crop' && _imgCropper) {
      _imgCropper.getCroppedCanvas({ imageSmoothingQuality: 'high' }).toBlob(resolve, 'image/png');
    } else {
      // Render canvas with enhancements onto the working image
      const canvas = document.createElement('canvas');
      const img    = _imgWorkingImg;
      if (!img) { resolve(_imgOrigBlob); return; }
      canvas.width  = img.naturalWidth;
      canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d');
      const br  = document.getElementById('_enBr')?.value ?? 100;
      const co  = document.getElementById('_enCo')?.value ?? 100;
      const sa  = document.getElementById('_enSa')?.value ?? 100;
      const bl  = document.getElementById('_enBl')?.value ?? 0;
      ctx.filter = `brightness(${br}%) contrast(${co}%) saturate(${sa}%) blur(${bl}px)`;
      ctx.drawImage(img, 0, 0);
      ctx.filter = 'none';
      canvas.toBlob(resolve, 'image/png');
    }
  });

  _imgEdClose();

  const cb = _imgCallback;
  _imgCallback = null;
  if (cb) cb(finalBlob);
}
