const API = '/api/v1';
let token = localStorage.getItem('wb_token');

// ── Observable state mutations (addresses race condition vulnerability) ────
// Global state is accessed/mutated across async operations. Logging all mutations
// makes race conditions detectable. Migrate to event-driven or single-object state
// in a future wave if needed.
let currentUser = null;
let __lastCurrentUserChange = 0;
let planFeatures = {};  // populated on init from /payments/plan-features
let __lastPlanFeaturesChange = 0;
let websites = [];
let __lastWebsitesChange = 0;

function _setCurrentUser(val) {
  const now = Date.now();
  if (now - __lastCurrentUserChange < 10) {
    console.debug('[state-race-warn] currentUser mutation within 10ms of previous; concurrent access risk', { prev: currentUser, new: val, deltaMs: now - __lastCurrentUserChange });
  }
  __lastCurrentUserChange = now;
  currentUser = val;
}

function _setPlanFeatures(val) {
  const now = Date.now();
  if (now - __lastPlanFeaturesChange < 10) {
    console.debug('[state-race-warn] planFeatures mutation within 10ms; concurrent access risk');
  }
  __lastPlanFeaturesChange = now;
  planFeatures = val;
}

function _setWebsites(val) {
  const now = Date.now();
  if (now - __lastWebsitesChange < 10) {
    console.debug('[state-race-warn] websites mutation within 10ms; concurrent access risk');
  }
  __lastWebsitesChange = now;
  websites = val;
}

const THEMES = [
  { id: 'modern',     label: 'Modern',      primary: '#667eea', secondary: '#764ba2', accent: '#f093fb', bg: '#f5f7fa', text: '#2d3748', gradient: 'linear-gradient(135deg,#667eea 0%,#764ba2 100%)', fontHeading: 'Poppins', fontBody: 'Inter',      desc: 'Clean & contemporary' },
  { id: 'classic',    label: 'Classic',     primary: '#1a365d', secondary: '#2b6cb0', accent: '#e53e3e', bg: '#ffffff', text: '#2d3748', gradient: 'linear-gradient(135deg,#1a365d 0%,#2b6cb0 100%)', fontHeading: 'Playfair Display', fontBody: 'Georgia', desc: 'Timeless & trustworthy' },
  { id: 'minimal',    label: 'Minimal',     primary: '#1a1a1a', secondary: '#555',    accent: '#f6c90e', bg: '#fafafa', text: '#222',    gradient: 'linear-gradient(135deg,#1a1a1a 0%,#444 100%)',    fontHeading: 'Space Grotesk',    fontBody: 'DM Sans',    desc: 'Less is more' },
  { id: 'dark',       label: 'Dark',        primary: '#7c3aed', secondary: '#4f46e5', accent: '#06b6d4', bg: '#0f172a', text: '#e2e8f0', gradient: 'linear-gradient(135deg,#7c3aed 0%,#4f46e5 100%)', fontHeading: 'Montserrat',       fontBody: 'Roboto',     desc: 'Bold & immersive' },
  { id: 'nature',     label: 'Nature',      primary: '#276749', secondary: '#38a169', accent: '#f6ad55', bg: '#f0fff4', text: '#1a202c', gradient: 'linear-gradient(135deg,#276749 0%,#38a169 100%)', fontHeading: 'Merriweather',     fontBody: 'Lato',       desc: 'Organic & calming' },
  { id: 'ecommerce',  label: 'E-Commerce',  primary: '#dd6b20', secondary: '#c05621', accent: '#3182ce', bg: '#ffffff', text: '#2d3748', gradient: 'linear-gradient(135deg,#dd6b20 0%,#c05621 100%)', fontHeading: 'Nunito',           fontBody: 'Open Sans',  desc: 'Conversion-focused' },
  { id: 'ocean',      label: 'Ocean',       primary: '#0f4c81', secondary: '#0a6fa6', accent: '#14b8a6', bg: '#f3fbff', text: '#12324a', gradient: 'linear-gradient(135deg,#0f4c81 0%,#0a6fa6 100%)', fontHeading: 'Manrope',          fontBody: 'Source Sans 3', desc: 'Crisp and professional' },
  { id: 'sunrise',    label: 'Sunrise',     primary: '#b45309', secondary: '#ea580c', accent: '#f59e0b', bg: '#fff9f1', text: '#3f2a1d', gradient: 'linear-gradient(135deg,#b45309 0%,#ea580c 100%)', fontHeading: 'Merriweather Sans', fontBody: 'Nunito Sans',  desc: 'Warm and welcoming' },
  { id: 'serene',     label: 'Serene',      primary: '#2563eb', secondary: '#0ea5e9', accent: '#10b981', bg: '#f8fbff', text: '#1f2937', gradient: 'linear-gradient(135deg,#2563eb 0%,#0ea5e9 100%)', fontHeading: 'IBM Plex Sans',    fontBody: 'Atkinson Hyperlegible', desc: 'High readability first' },
  { id: 'terra',      label: 'Terra',       primary: '#7c2d12', secondary: '#9a3412', accent: '#65a30d', bg: '#fff8f5', text: '#2f1e16', gradient: 'linear-gradient(135deg,#7c2d12 0%,#9a3412 100%)', fontHeading: 'Archivo',          fontBody: 'Noto Sans',    desc: 'Earthy and grounded' },
  { id: 'slate',      label: 'Slate',       primary: '#334155', secondary: '#475569', accent: '#0ea5e9', bg: '#f8fafc', text: '#0f172a', gradient: 'linear-gradient(135deg,#334155 0%,#475569 100%)', fontHeading: 'Barlow',           fontBody: 'Public Sans',  desc: 'Corporate and clean' },
  { id: 'blossom',    label: 'Blossom',     primary: '#be185d', secondary: '#db2777', accent: '#0ea5a4', bg: '#fff5fa', text: '#3c1f33', gradient: 'linear-gradient(135deg,#be185d 0%,#db2777 100%)', fontHeading: 'Plus Jakarta Sans', fontBody: 'Work Sans',    desc: 'Soft and lively' },
  { id: 'photography', label: 'Aurora',      primary: '#111827', secondary: '#374151', accent: '#f59e0b', bg: '#f9fafb', text: '#111827', gradient: 'linear-gradient(135deg,#111827 0%,#374151 100%)', fontHeading: 'DM Serif Display', fontBody: 'Source Sans 3', desc: 'High-contrast editorial look' },
  { id: 'school',      label: 'Summit',      primary: '#1d4ed8', secondary: '#2563eb', accent: '#f97316', bg: '#f8fbff', text: '#1f2937', gradient: 'linear-gradient(135deg,#1d4ed8 0%,#2563eb 100%)', fontHeading: 'Cabin',            fontBody: 'Nunito Sans',  desc: 'Clear and approachable tone' },
  { id: 'hospital',    label: 'Clarity',     primary: '#0f766e', secondary: '#0ea5a4', accent: '#2563eb', bg: '#f2fbfa', text: '#0f172a', gradient: 'linear-gradient(135deg,#0f766e 0%,#0ea5a4 100%)', fontHeading: 'PT Sans',          fontBody: 'Lato',         desc: 'Clean, calm, and trustworthy' },
  { id: 'student',     label: 'Pulse',       primary: '#7c3aed', secondary: '#8b5cf6', accent: '#f43f5e', bg: '#faf7ff', text: '#312e81', gradient: 'linear-gradient(135deg,#7c3aed 0%,#8b5cf6 100%)', fontHeading: 'Quicksand',        fontBody: 'Atkinson Hyperlegible', desc: 'Bright and readable energy' },
  { id: 'comic',       label: 'Spark',       primary: '#e11d48', secondary: '#f97316', accent: '#2563eb', bg: '#fffdf5', text: '#1f2937', gradient: 'linear-gradient(135deg,#e11d48 0%,#f97316 100%)', fontHeading: 'Baloo 2',          fontBody: 'Nunito Sans',  desc: 'Playful color-forward style' },
  { id: 'professional', label: 'Keystone',   primary: '#1f2937', secondary: '#374151', accent: '#0ea5e9', bg: '#f9fafb', text: '#111827', gradient: 'linear-gradient(135deg,#1f2937 0%,#374151 100%)', fontHeading: 'Manrope',          fontBody: 'Public Sans',  desc: 'Refined and business-ready' },
  { id: 'trendy',      label: 'Nova',        primary: '#db2777', secondary: '#9333ea', accent: '#06b6d4', bg: '#fff7fe', text: '#3f3f46', gradient: 'linear-gradient(135deg,#db2777 0%,#9333ea 100%)', fontHeading: 'Sora',             fontBody: 'Inter',        desc: 'Vibrant modern aesthetic' },
];
let selectedTheme = 'modern';
let selectedBuildMode = 'agentic_only';
let selectedOutputTarget = 'legacy';
let lastReferenceQuality = null;
let importFlowBuildStarted = false;

const IMPORT_FLOW_LABELS = {
  1: 'Add Site URL',
  2: 'Pick Type & Theme',
  3: 'Fetch & Review',
  4: 'Generate Website',
};

const CLASSIFICATIONS = [
  { id: 'b2b', group: 'business-model', groupLabel: 'Business Model & Commerce', icon: '🤝', label: 'B2B Services', desc: 'Business-to-business company', cta: 'Request a Demo', nav: ['Solutions','Case Studies','Pricing','About','Contact'], hero: 'Enterprise solutions that drive measurable ROI', sections: ['solutions','case-studies','stats','testimonials','integrations','contact'] },
  { id: 'b2c', group: 'business-model', groupLabel: 'Business Model & Commerce', icon: '🛍️', label: 'B2C Brand', desc: 'Direct-to-consumer business', cta: 'Shop Now', nav: ['Products','Offers','About','Reviews','Contact'], hero: 'Products your customers will love', sections: ['products','offers','reviews','gallery','contact'] },
  { id: 'ecommerce_store', group: 'business-model', groupLabel: 'Business Model & Commerce', icon: '🛒', label: 'E-Commerce Store', desc: 'Catalog and online selling', cta: 'Browse Catalog', nav: ['Products','Collections','Offers','Support','Contact'], hero: 'A storefront built for product discovery and conversion', sections: ['products','collections','offers','reviews','contact'] },
  { id: 'medical_practice', group: 'healthcare', groupLabel: 'Healthcare & Life Sciences', icon: '🩺', label: 'Medical Practice', desc: 'Doctor, clinic, patient care', cta: 'Book Appointment', nav: ['Services','Doctors','Patients','Testimonials','Contact'], hero: 'Compassionate care you can trust', sections: ['services','credentials','team','patient-info','testimonials','appointment'] },
  { id: 'diagnostics_lab', group: 'healthcare', groupLabel: 'Healthcare & Life Sciences', icon: '🧪', label: 'Diagnostics Lab', desc: 'Pathology, testing, reports', cta: 'Book a Test', nav: ['Tests','Packages','Process','Reports','Contact'], hero: 'Accurate diagnostics with dependable turnaround', sections: ['tests','packages','process','trust','contact'] },
  { id: 'medical_equipment', group: 'healthcare', groupLabel: 'Healthcare & Life Sciences', icon: '🔬', label: 'Medical Equipment', desc: 'Devices, analyzers, reseller', cta: 'Request Quote', nav: ['Products','Brands','Applications','Service','Contact'], hero: 'Reliable laboratory and diagnostic equipment for clinical workflows', sections: ['products','brands','applications','service','contact'] },
  { id: 'pharmacy_wellness', group: 'healthcare', groupLabel: 'Healthcare & Life Sciences', icon: '💊', label: 'Pharmacy / Wellness', desc: 'Retail pharmacy or wellness', cta: 'Talk to Us', nav: ['Products','Wellness','Support','Offers','Contact'], hero: 'Trusted healthcare products and wellness support', sections: ['products','wellness','support','offers','contact'] },
  { id: 'tutor', group: 'education', groupLabel: 'Education & Training', icon: '📚', label: 'Tutor / Coach', desc: 'Individual educator or tutor', cta: 'Book a Session', nav: ['Courses','About','Curriculum','Testimonials','Contact'], hero: 'Personalized learning that helps students progress', sections: ['courses','curriculum','testimonials','certifications','enroll'] },
  { id: 'school', group: 'education', groupLabel: 'Education & Training', icon: '🏫', label: 'School / Academy', desc: 'School, academy, institution', cta: 'Apply Now', nav: ['Programs','Admissions','Faculty','Campus','Contact'], hero: 'A learning environment built for student growth', sections: ['programs','admissions','faculty','campus','contact'] },
  { id: 'training_institute', group: 'education', groupLabel: 'Education & Training', icon: '🧑‍🏫', label: 'Training Institute', desc: 'Skills, coaching, certification', cta: 'Enroll Now', nav: ['Courses','Placements','Curriculum','Testimonials','Contact'], hero: 'Career-focused training with practical outcomes', sections: ['courses','placements','curriculum','testimonials','contact'] },
  { id: 'research_lab', group: 'education', groupLabel: 'Education & Training', icon: '🧬', label: 'Research Lab', desc: 'Academic or scientific research', cta: 'View Research', nav: ['Research','Publications','Lab','Collaborations','Contact'], hero: 'Advancing knowledge through rigorous research', sections: ['research','publications','lab','collaborations','contact'] },
  { id: 'law_firm', group: 'professional-services', groupLabel: 'Professional Services', icon: '⚖️', label: 'Law Firm', desc: 'Legal practice and advisory', cta: 'Free Consultation', nav: ['Practice Areas','Results','About','Team','Contact'], hero: 'Experienced legal counsel. Results that matter.', sections: ['practice-areas','results','team','testimonials','consultation'] },
  { id: 'engineering_services', group: 'professional-services', groupLabel: 'Professional Services', icon: '⚙️', label: 'Engineering Services', desc: 'Consulting, technical services', cta: 'Discuss a Project', nav: ['Services','Projects','Capabilities','About','Contact'], hero: 'Engineering expertise that turns ideas into delivery', sections: ['services','projects','capabilities','about','contact'] },
  { id: 'real_estate_agency', group: 'professional-services', groupLabel: 'Professional Services', icon: '🏠', label: 'Real Estate Agency', desc: 'Property sales and rentals', cta: 'View Properties', nav: ['Listings','Services','About','Testimonials','Contact'], hero: 'Finding you the perfect place to call home', sections: ['listings','services','team','testimonials','valuation','contact'] },
  { id: 'startup_saas', group: 'technology-industrial', groupLabel: 'Technology & Industrial', icon: '🚀', label: 'Startup / SaaS', desc: 'Software product or platform', cta: 'Start Free Trial', nav: ['Features','Pricing','Testimonials','Blog','Contact'], hero: 'The smarter way to grow your business', sections: ['features','how-it-works','pricing','testimonials','faq','cta'] },
  { id: 'manufacturer_distributor', group: 'technology-industrial', groupLabel: 'Technology & Industrial', icon: '🏭', label: 'Manufacturer / Distributor', desc: 'Industrial catalog and supply', cta: 'Request Catalog', nav: ['Products','Industries','Capabilities','Support','Contact'], hero: 'Products, supply, and support built for operational scale', sections: ['products','industries','capabilities','support','contact'] },
  { id: 'restaurant', group: 'hospitality-lifestyle', groupLabel: 'Hospitality & Lifestyle', icon: '🍽️', label: 'Restaurant', desc: 'Food and dining business', cta: 'Reserve a Table', nav: ['Menu','About','Gallery','Reservations','Contact'], hero: 'An unforgettable dining experience', sections: ['menu','gallery','specials','testimonials','reservation','contact'] },
  { id: 'salon_spa', group: 'hospitality-lifestyle', groupLabel: 'Hospitality & Lifestyle', icon: '💇', label: 'Salon / Spa', desc: 'Beauty and wellness services', cta: 'Book Treatment', nav: ['Services','Gallery','Team','Pricing','Contact'], hero: 'Your haven of beauty and relaxation', sections: ['services','gallery','team','pricing','testimonials','booking'] },
  { id: 'fitness_wellness', group: 'hospitality-lifestyle', groupLabel: 'Hospitality & Lifestyle', icon: '💪', label: 'Fitness / Wellness', desc: 'Gym, studio, personal training', cta: 'Join Now', nav: ['Programs','Trainers','Pricing','Success Stories','Contact'], hero: 'Transform your body and mind', sections: ['programs','trainers','pricing','success-stories','schedule','contact'] },
  { id: 'artist_portfolio', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '🎨', label: 'Artist / Portfolio', desc: 'Creative brand or portfolio', cta: 'Commission Work', nav: ['Gallery','Process','Exhibitions','About','Contact'], hero: 'Art that speaks without words', sections: ['gallery','process','exhibitions','press','commissions','contact'] },
  { id: 'photographer', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '📷', label: 'Photographer', desc: 'Photo studio, prints, bookings', cta: 'Book a Session', nav: ['Portfolio','Services','Prints','About','Contact'], hero: 'Capturing moments that last a lifetime', sections: ['portfolio','services','prints','packages','testimonials','booking'] },
  { id: 'musician_band', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '🎵', label: 'Musician / Band', desc: 'Discography, events, merch', cta: 'Listen Now', nav: ['Music','Events','Merch','About','Contact'], hero: 'Feel every note, live every beat', sections: ['music','events','merch','gallery','press','contact'] },
  { id: 'freelancer', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '💼', label: 'Freelancer / Consultant', desc: 'Services, rates, hire me', cta: 'Hire Me', nav: ['Services','Portfolio','Rates','About','Contact'], hero: 'Expert skills ready to work for you', sections: ['services','portfolio','rates','testimonials','faq','contact'] },
  { id: 'writer_blogger', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '✍️', label: 'Writer / Blogger', desc: 'Articles, books, newsletter', cta: 'Read My Work', nav: ['Blog','Books','Newsletter','About','Contact'], hero: 'Words that inspire, stories that matter', sections: ['featured-posts','books','newsletter','about','categories','contact'] },
  { id: 'student_portfolio', group: 'creative-personal', groupLabel: 'Creative & Personal Brand', icon: '🎓', label: 'Student Portfolio', desc: 'Resume, projects, profile', cta: 'View My Work', nav: ['Projects','Skills','About','Resume','Contact'], hero: 'Ready to build something great together', sections: ['projects','skills','education','certifications','contact'] },
  { id: 'ngo', group: 'community-nonprofit', groupLabel: 'Community & Nonprofit', icon: '🌍', label: 'NGO / Non-Profit', desc: 'Mission-driven organization', cta: 'Donate Now', nav: ['Mission','Impact','Programs','Volunteer','Donate'], hero: 'Together we can make a difference', sections: ['mission','impact-stats','programs','team','stories','donate'] },
  { id: 'religious_org', group: 'community-nonprofit', groupLabel: 'Community & Nonprofit', icon: '🕌', label: 'Religious / Spiritual Organization', desc: 'Events, services, donations', cta: 'Join Us', nav: ['About','Events','Services','Donate','Contact'], hero: 'A place of faith, community, and belonging', sections: ['about','events','services','gallery','donations','contact'] },
  { id: 'cultural_org', group: 'community-nonprofit', groupLabel: 'Community & Nonprofit', icon: '🏛️', label: 'Cultural Organization', desc: 'Events, heritage, programs', cta: 'Explore Events', nav: ['Events','Heritage','Programs','Gallery','Contact'], hero: 'Celebrating culture, preserving heritage', sections: ['events','heritage','programs','gallery','membership','contact'] },
  { id: 'charity_foundation', group: 'community-nonprofit', groupLabel: 'Community & Nonprofit', icon: '❤️', label: 'Charity / Foundation', desc: 'Campaigns, impact, fundraising', cta: 'Support a Cause', nav: ['Causes','Impact','Campaigns','Volunteer','Donate'], hero: 'Every contribution creates lasting change', sections: ['causes','impact','campaigns','team','stories','donate'] },
  { id: 'community_club', group: 'community-nonprofit', groupLabel: 'Community & Nonprofit', icon: '🏆', label: 'Community / Sports Club', desc: 'Events, membership, standings', cta: 'Join the Club', nav: ['Events','Members','Standings','About','Contact'], hero: 'United by passion, driven by community', sections: ['events','standings','members','gallery','news','contact'] },
  { id: 'generic', group: 'general', groupLabel: 'General', icon: '🌐', label: 'General Business', desc: 'Fallback for mixed businesses', cta: 'Get in Touch', nav: ['About','Services','Gallery','Testimonials','Contact'], hero: 'Welcome to our website', sections: ['services','about','gallery','testimonials','contact'] },
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
  const timeoutMs = Number(opts.timeoutMs || 15000);
  const ctrl = new AbortController();
  const timeoutId = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const { timeoutMs: _ignoreTimeout, ...restOpts } = opts;
    const r = await fetch(API + path, {
      headers: headers(),
      cache: 'no-store',
      signal: ctrl.signal,
      ...restOpts,
    });
    if (r.status === 401) { logout(); return null; }
    if (!r.ok) {
      try {
        const err = await r.json();
        apiFetch._lastError = err?.detail || `HTTP ${r.status}`;
      } catch (err) {
        console.debug('[apiFetch] Failed to parse error response JSON:', err);
        apiFetch._lastError = `HTTP ${r.status}`;
      }
      return null;
    }
    apiFetch._lastError = null;
    return r.json();
  } catch (err) {
    if (err && err.name === 'AbortError') {
      apiFetch._lastError = `Request timed out after ${Math.round(timeoutMs / 1000)}s`;
      toast('Request timed out. Please try again.', false);
      return null;
    }
    apiFetch._lastError = (err && err.message) ? err.message : 'Network request failed';
    toast('Network error. Please check your connection and retry.', false);
    return null;
  } finally {
    clearTimeout(timeoutId);
  }
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

function _systemDialogConfig({ icon = '', title = 'Confirm', msg = '', okLabel = 'Confirm', okClass = 'btn-primary', cancelLabel = 'Cancel', showCancel = true, inputConfig = null, onResult = null }) {
  document.getElementById('confirmIcon').textContent = icon;
  document.getElementById('confirmTitle').textContent = title;
  const msgEl = document.getElementById('confirmMsg');
  msgEl.textContent = msg;

  const okBtn = document.getElementById('confirmOkBtn');
  const cancelBtn = document.getElementById('confirmCancelBtn');
  const actionsRow = cancelBtn.parentElement;
  const existingInput = document.getElementById('confirmPromptInput');
  if (existingInput) existingInput.remove();
  let promptInput = null;
  if (inputConfig) {
    promptInput = document.createElement('input');
    promptInput.id = 'confirmPromptInput';
    promptInput.type = 'text';
    promptInput.value = String(inputConfig.initialValue || '');
    promptInput.placeholder = String(inputConfig.placeholder || '');
    promptInput.style.cssText = 'width:100%;padding:9px 12px;background:var(--bg);border:1.5px solid var(--border);border-radius:7px;color:var(--text);font-size:.9rem;outline:none;margin:-6px 0 14px';
    promptInput.onfocus = () => { promptInput.style.borderColor = 'var(--accent)'; };
    promptInput.onblur = () => { promptInput.style.borderColor = 'var(--border)'; };
    msgEl.insertAdjacentElement('afterend', promptInput);
  }

  const cleanup = () => {
    okBtn.onclick = null;
    cancelBtn.onclick = null;
    if (promptInput) {
      promptInput.onfocus = null;
      promptInput.onblur = null;
      promptInput.remove();
    }
  };
  okBtn.textContent = okLabel;
  okBtn.className = `btn ${okClass}`;
  cancelBtn.textContent = cancelLabel;
  cancelBtn.style.display = showCancel ? '' : 'none';

  okBtn.onclick = () => {
    if (promptInput && inputConfig?.required && !String(promptInput.value || '').trim()) {
      promptInput.focus();
      promptInput.style.borderColor = 'var(--danger)';
      return;
    }
    cleanup();
    closeModal('confirmModal');
    if (onResult) onResult(promptInput ? String(promptInput.value || '') : true);
  };
  cancelBtn.onclick = () => {
    cleanup();
    closeModal('confirmModal');
    if (onResult) onResult(promptInput ? null : false);
  };

  openModal('confirmModal');
  if (promptInput) {
    setTimeout(() => {
      promptInput.focus();
      promptInput.select();
    }, 10);
  }
}

function styledConfirm(msg, opts = {}) {
  return new Promise(resolve => {
    _systemDialogConfig({
      icon: opts.icon || '⚠️',
      title: opts.title || 'Please Confirm',
      msg,
      okLabel: opts.okLabel || 'Confirm',
      okClass: opts.okClass || 'btn-primary',
      cancelLabel: opts.cancelLabel || 'Cancel',
      showCancel: true,
      onResult: resolve,
    });
  });
}

function styledAlert(msg, opts = {}) {
  return new Promise(resolve => {
    _systemDialogConfig({
      icon: opts.icon || 'ℹ️',
      title: opts.title || 'Notice',
      msg,
      okLabel: opts.okLabel || 'OK',
      okClass: opts.okClass || 'btn-primary',
      showCancel: false,
      onResult: () => resolve(),
    });
  });
}

function styledPrompt(msg, opts = {}) {
  return new Promise(resolve => {
    _systemDialogConfig({
      icon: opts.icon || '✍️',
      title: opts.title || 'Enter Value',
      msg,
      okLabel: opts.okLabel || 'OK',
      okClass: opts.okClass || 'btn-primary',
      cancelLabel: opts.cancelLabel || 'Cancel',
      showCancel: true,
      inputConfig: {
        initialValue: opts.initialValue || '',
        placeholder: opts.placeholder || '',
        required: !!opts.required,
      },
      onResult: resolve,
    });
  });
}

window.wbConfirm = styledConfirm;
window.wbAlert = styledAlert;
window.wbPrompt = styledPrompt;

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  _setCurrentUser(await apiFetch('/auth/me'));
  if (!currentUser) return;
  _setPlanFeatures(await apiFetch('/payments/plan-features') || {});
  document.getElementById('userEmail').textContent = currentUser.email;
  document.getElementById('statPlan').textContent = (currentUser.plan || '—').toUpperCase();
  buildThemeGrid();
  buildClassGrids();
  _initNavTagInput();
  _initCatalogTagInput();
  _initImportFlowStepper();

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

function _setImportFlowStep(currentStep) {
  const wrap = document.getElementById('importFlowSteps');
  if (!wrap) return;
  const steps = [...wrap.querySelectorAll('.import-flow-step')];
  if (!steps.length) return;

  const step = Math.min(4, Math.max(1, Number(currentStep) || 1));
  const nextStep = step < 4 ? step + 1 : null;

  steps.forEach((el, idx) => {
    const n = idx + 1;
    el.classList.remove('complete', 'current', 'next');
    if (n < step) el.classList.add('complete');
    else if (n === step) el.classList.add('current');
    else if (nextStep && n === nextStep) el.classList.add('next');
  });

  const hint = document.getElementById('importFlowHint');
  if (!hint) return;
  const currentLabel = IMPORT_FLOW_LABELS[step] || 'Step';
  if (nextStep) {
    const nextLabel = IMPORT_FLOW_LABELS[nextStep] || 'Next';
    hint.textContent = `Current: ${currentLabel} • Next: ${nextLabel}`;
  } else {
    hint.textContent = `Current: ${currentLabel} • Next: Build is running`;
  }
}

function _updateImportFlowStepper() {
  const importPanel = document.getElementById('buildPanel-import');
  const isImportTab = importPanel ? importPanel.style.display !== 'none' : true;
  const primary = document.getElementById('existingUrl')?.value.trim() || '';
  const extra = document.getElementById('existingUrls')?.value.trim() || '';
  const hasAnyUrl = !!(primary || extra);
  const hasSelections = selectedClassification && selectedTheme;

  let step = 1;
  if (importFlowBuildStarted) step = 4;
  else if (!isImportTab) step = 3;
  else if (hasSelections) step = 3;
  else if (hasAnyUrl) step = 2;

  _setImportFlowStep(step);

  // Update Fetch button requirement indicator
  const reqIndicator = document.getElementById('fetchBtnRequirement');
  const fetchBtn = document.getElementById('fetchUrlBtn');
  if (reqIndicator && fetchBtn) {
    if (!hasSelections) {
      reqIndicator.style.display = '';
      fetchBtn.style.opacity = '0.55';
      fetchBtn.style.pointerEvents = 'none';
      fetchBtn.style.cursor = 'not-allowed';
    } else {
      reqIndicator.style.display = 'none';
      fetchBtn.style.opacity = '1';
      fetchBtn.style.pointerEvents = 'auto';
      fetchBtn.style.cursor = 'pointer';
    }
  }
}

function _initImportFlowStepper() {
  const existingUrlEl = document.getElementById('existingUrl');
  const existingUrlsEl = document.getElementById('existingUrls');

  if (existingUrlEl) {
    existingUrlEl.addEventListener('input', () => {
      importFlowBuildStarted = false;
      _updateImportFlowStepper();
    });
  }
  if (existingUrlsEl) {
    existingUrlsEl.addEventListener('input', () => {
      importFlowBuildStarted = false;
      _updateImportFlowStepper();
    });
  }

  _updateImportFlowStepper();
}

// ── Helpers ────────────────────────────────────────────────────────────────
/** Fetch all websites for the current user (unwraps paginated envelope). */
async function _fetchMyWebsites() {
  const data = await apiFetch('/websites/my?limit=200') || {};
  return Array.isArray(data) ? data : (data.items || []);
}

// ── Overview ───────────────────────────────────────────────────────────────
async function loadOverview() {
  _setWebsites(await _fetchMyWebsites());
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
  } catch (err) {
    console.debug('[featureBadges] Invalid cart_features payload:', err);
  }
  if (w.enable_livestream) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#fff0f0;color:#dc2626">🟥 Live</span>`);
  if (w.enable_blog) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#f0fdf4;color:#15803d">📝 Blog</span>`);
  if (w.enable_chatbot) badges.push(`<span class="tag" style="font-size:.72rem;padding:2px 8px;background:#e8f4fd;color:#1a73e8">💬 Bot</span>`);
  return badges.join(' ') || '<span style="color:var(--muted);font-size:.82rem">—</span>';
}

function statusBadge(status, buildStatus) {
  if (status === 'inactive') {
    return `<span class="tag" style="background:#fff3cd;color:#856404">⏸ Offline</span>`;
  }
  // If status is 'live', it's been deployed to production
  if (status === 'live' || status === 'published') {
    return `<span class="tag published">🟢 Live</span>`;
  }
  // If status is 'draft' but build_status is 'built', it's ready to deploy
  if ((status === 'draft' || status === 'built') && (buildStatus === 'built' || buildStatus === 'fallback')) {
    return `<span class="tag" style="background:#e0f2fe;color:#0369a1;border:1px solid #0369a1;white-space:nowrap">✓ Ready</span>`;
  }
  if (status === 'error' || buildStatus === 'error') {
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
    <td>${statusBadge(w.status, w.build_status)}</td>
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
    <td id="status-${w.website_id}">${statusBadge(w.status, w.build_status)}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${dateStr}</td>
    <td style="color:var(--muted);font-size:.82rem;white-space:nowrap">${changedStr}</td>
    <td id="actions-${w.website_id}" style="white-space:nowrap">
      <button class="btn btn-secondary btn-sm" ${isInactive?'disabled title="Activate the website to view"':"onclick=\"viewSite('" + w.website_id + "')\" title=\"Open website\""}>👁 View</button>
      <button class="btn btn-secondary btn-sm" style="margin-left:4px" ${isInactive?'disabled title="Activate the website to edit"':"onclick=\"editSite('" + w.website_id + "')\" title=\"Edit details\""}>✏️ Edit</button>
      <button class="btn btn-secondary btn-sm" style="margin-left:4px" onclick="openStorageSettings('${w.website_id}')" title="Per-website image storage settings">🗂 Storage</button>
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

function openStorageSettings(id) {
  const w = websites.find(x => x.website_id === id);
  if (!w) return;
  let cfg = {};
  try { cfg = typeof w.image_storage_config === 'string' ? JSON.parse(w.image_storage_config || '{}') : (w.image_storage_config || {}); }
  catch { cfg = {}; }

  const sid = document.getElementById('storageSiteId');
  const b = document.getElementById('storageImageBackend');
  const sa = document.getElementById('storageDriveServiceAccountFile');
  const fd = document.getElementById('storageDriveFolderId');
  if (sid) sid.value = id;
  const backend = w.image_storage_backend || 'auto';
  if (b) b.value = backend;
  if (backend === 's3') {
    if (sa) sa.value = cfg.s3_bucket || '';
    if (fd) fd.value = cfg.s3_prefix || '';
  } else if (backend === 'gdrive') {
    if (sa) sa.value = cfg.folder_id || '';
    if (fd) fd.value = cfg.gdrive_subfolder || '';
  } else if (backend === 'onedrive') {
    if (sa) sa.value = cfg.onedrive_folder || '';
    if (fd) fd.value = cfg.onedrive_subfolder || '';
  } else if (backend === 'ftp') {
    if (sa) sa.value = cfg.ftp_remote_dir || '';
    if (fd) fd.value = cfg.ftp_public_base_url || '';
  } else {
    if (sa) sa.value = cfg.folder_id || '';
    if (fd) fd.value = cfg.gdrive_subfolder || '';
  }
  updateStorageFieldsUi();
  openModal('storageSiteModal');
}

function updateStorageFieldsUi() {
  const backend = document.getElementById('storageImageBackend')?.value || 'auto';
  const f1Wrap = document.getElementById('storageField1Wrap');
  const f2Wrap = document.getElementById('storageField2Wrap');
  const f1Label = document.getElementById('storageField1Label');
  const f2Label = document.getElementById('storageField2Label');
  const f1 = document.getElementById('storageDriveServiceAccountFile');
  const f2 = document.getElementById('storageDriveFolderId');
  const help = document.getElementById('storageHelpText');
  if (!f1Wrap || !f2Wrap || !f1Label || !f2Label || !f1 || !f2 || !help) return;

  if (backend === 'local') {
    f1Wrap.style.display = 'none';
    f2Wrap.style.display = 'none';
    help.textContent = 'No extra configuration needed for local storage.';
    return;
  }

  f1Wrap.style.display = '';
  f2Wrap.style.display = '';

  if (backend === 's3') {
    f1Label.textContent = 'S3 Bucket (optional override)';
    f2Label.textContent = 'S3 Prefix (optional)';
    f1.placeholder = 'my-bucket-name';
    f2.placeholder = 'uploads/site-a';
    help.textContent = 'Uses AWS credentials from server env; bucket/prefix here are per-website overrides.';
    const sh = document.getElementById('storageSecretsHelp');
    if (sh) sh.textContent = 'Optional secrets JSON keys: aws_access_key_id, aws_secret_access_key, s3_bucket.';
    return;
  }

  if (backend === 'gdrive') {
    f1Label.textContent = 'Google Drive Folder ID';
    f2Label.textContent = 'Google Drive Subfolder (optional)';
    f1.placeholder = 'Drive folder id for this website';
    f2.placeholder = 'site-a/images';
    help.textContent = 'Google credentials are read from server env; only destination is configured here.';
    const sh = document.getElementById('storageSecretsHelp');
    if (sh) sh.textContent = 'Optional secrets JSON key: service_account_file (if different from server default).';
    return;
  }

  if (backend === 'onedrive') {
    f1Label.textContent = 'OneDrive Folder Path';
    f2Label.textContent = 'OneDrive Subfolder (optional)';
    f1.placeholder = 'uploads';
    f2.placeholder = 'site-a/images';
    help.textContent = 'OneDrive app credentials are read from server env; this sets folder destination for this website.';
    const sh = document.getElementById('storageSecretsHelp');
    if (sh) sh.textContent = 'Optional secrets JSON keys: onedrive_tenant_id, onedrive_client_id, onedrive_client_secret, onedrive_drive_id.';
    return;
  }

  if (backend === 'ftp') {
    f1Label.textContent = 'FTP Remote Directory';
    f2Label.textContent = 'Public Base URL (optional override)';
    f1.placeholder = '/public_html/uploads/site-a';
    f2.placeholder = 'https://cdn.example.com/uploads/site-a';
    help.textContent = 'FTP credentials are read from server env; set destination dir and optional public URL override.';
    const sh = document.getElementById('storageSecretsHelp');
    if (sh) sh.textContent = 'Optional secrets JSON keys: ftp_host, ftp_port, ftp_user, ftp_password, ftp_public_base_url.';
    return;
  }

  // auto
  f1Label.textContent = 'Preferred Folder ID / Bucket (optional)';
  f2Label.textContent = 'Preferred Subfolder / Prefix (optional)';
  f1.placeholder = 'optional destination hint';
  f2.placeholder = 'optional path hint';
  help.textContent = 'Auto mode tries S3, Google Drive, OneDrive, FTP, then local (based on server config).';
  const sh = document.getElementById('storageSecretsHelp');
  if (sh) sh.textContent = 'Optional encrypted secrets JSON can override env values per website.';
}

async function saveStorageSettings() {
  const id = document.getElementById('storageSiteId')?.value;
  if (!id) return;
  const backend = document.getElementById('storageImageBackend')?.value || 'auto';
  const v1 = document.getElementById('storageDriveServiceAccountFile')?.value.trim() || '';
  const v2 = document.getElementById('storageDriveFolderId')?.value.trim() || '';
  let image_storage_config = {};
  if (backend === 's3') image_storage_config = { s3_bucket: v1, s3_prefix: v2 };
  else if (backend === 'gdrive') image_storage_config = { folder_id: v1, gdrive_subfolder: v2 };
  else if (backend === 'onedrive') image_storage_config = { onedrive_folder: v1, onedrive_subfolder: v2 };
  else if (backend === 'ftp') image_storage_config = { ftp_remote_dir: v1, ftp_public_base_url: v2 };
  else image_storage_config = { folder_id: v1, gdrive_subfolder: v2 };
  const secretsRaw = document.getElementById('storageSecretsJson')?.value.trim() || '';
  let image_storage_secrets;
  if (secretsRaw) {
    try {
      image_storage_secrets = JSON.parse(secretsRaw);
      if (!image_storage_secrets || typeof image_storage_secrets !== 'object' || Array.isArray(image_storage_secrets)) {
        toast('Credentials JSON must be an object', false);
        return;
      }
    } catch {
      toast('Invalid credentials JSON', false);
      return;
    }
  }

  const payload = {
    image_storage_backend: backend,
    image_storage_config,
  };
  if (image_storage_secrets) payload.image_storage_secrets = image_storage_secrets;

  const r = await fetch(`${API}/websites/${id}`, {
    method: 'PATCH', headers: { ...headers(), 'Content-Type':'application/json' },
    body: JSON.stringify(payload)
  });
  if (r.ok) {
    const idx = websites.findIndex(x => x.website_id === id);
    if (idx !== -1) {
      websites[idx].image_storage_backend = payload.image_storage_backend;
      websites[idx].image_storage_config = JSON.stringify(payload.image_storage_config);
      websites[idx].updated_at = new Date().toISOString().replace('T', ' ').slice(0, 16);
    }
    closeModal('storageSiteModal');
    const sec = document.getElementById('storageSecretsJson');
    if (sec) sec.value = '';
    refreshRow(id);
    toast('Storage settings saved ✅');
  } else {
    let errMsg = 'Storage settings update failed';
    try { const j = await r.json(); if (j && j.detail) errMsg = j.detail; } catch {}
    toast(errMsg, false);
  }
}

function showConfirm({ icon, title, msg, btnLabel, btnClass, onConfirm }) {
  _systemDialogConfig({
    icon: icon || '⚠️',
    title: title || 'Please Confirm',
    msg: msg || '',
    okLabel: btnLabel || 'Confirm',
    okClass: btnClass || 'btn-primary',
    cancelLabel: 'Cancel',
    showCancel: true,
    onResult: (ok) => { if (ok) onConfirm(); },
  });
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
  _setWebsites(await _fetchMyWebsites());
  const tbody = document.getElementById('allSitesBody');
  if (!tbody) return;
  if (!websites.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="color:var(--muted);text-align:center;padding:24px">No websites yet — <a href="javascript:showPage('build')" style="color:var(--accent)">build one now</a>!</td></tr>`;
    return;
  }
  tbody.innerHTML = websites.map(siteRow).join('');
}

// ── Build Website ──────────────────────────────────────────────────────────
// ── Classification grid builders ───────────────────────────────────────────
function classCardHTML(c, gridId) {
  return `<div class="class-card ${c.id === selectedClassification ? 'selected' : ''}" id="${gridId}-cc-${c.id}" onclick="selectClassification('${c.id}')">
    <div class="class-icon">${c.icon}</div>
    <div class="class-label">${c.label}</div>
    <div class="class-desc">${c.desc}</div>
    <span class="selected-badge">✓</span>
  </div>`;
}

function classificationGroupsHTML(gridId) {
  const groups = [];
  const seen = new Set();
  for (const item of CLASSIFICATIONS) {
    if (seen.has(item.group)) continue;
    seen.add(item.group);
    groups.push({ id: item.group, label: item.groupLabel });
  }
  return groups.map(group => {
    const cards = CLASSIFICATIONS
      .filter(item => item.group === group.id)
      .map(item => classCardHTML(item, gridId))
      .join('');
    return `<section class="class-group"><div class="class-group-title">${group.label}</div><div class="class-group-grid">${cards}</div></section>`;
  }).join('');
}

function buildClassGrids() {
  ['importClassGrid','agentClassGrid'].forEach(gid => {
    const el = document.getElementById(gid);
    if (el) el.innerHTML = classificationGroupsHTML(gid);
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
  // Update import flow stepper when selection changes
  _updateImportFlowStepper();
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
  // Update import flow stepper when selection changes
  _updateImportFlowStepper();
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

async function _pollBuildStatusUntilTerminal(websiteId, { onUpdate, maxAttempts = 180, intervalMs = 5000 } = {}) {
  for (let i = 0; i < maxAttempts; i++) {
    const snap = await apiFetch(`/websites/${websiteId}/build-status`);
    const status = snap?.build_status || 'queued';
    const error = snap?.error || '';

    if (typeof onUpdate === 'function') onUpdate(status, error);
    if (['built', 'fallback', 'error', 'not_found'].includes(status)) {
      return { status, error };
    }

    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  return { status: 'timeout', error: '' };
}

function _parseReferenceUrlEntries(raw = '') {
  const lines = String(raw || '')
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);

  const entries = [];
  for (const line of lines) {
    const parts = line.split(/\s+-\s+/);
    const left = (parts[0] || '').trim();
    const usage = (parts.slice(1).join(' - ') || '').trim();
    const urlMatch = left.match(/https?:\/\/[^\s,]+/i) || line.match(/https?:\/\/[^\s,]+/i);
    if (!urlMatch) continue;
    entries.push({ url: urlMatch[0].trim(), usage });
  }
  return entries;
}

function useImportedSummaryReplace() {
  const src = document.getElementById('importedSummary')?.value?.trim() || '';
  const reqEl = document.getElementById('buildReq');
  if (!src || !reqEl) {
    toast('No imported summary available to apply', false);
    return;
  }
  reqEl.value = src;
  toast('Imported summary applied to Context');
}

function appendImportedSummaryToContext() {
  const src = document.getElementById('importedSummary')?.value?.trim() || '';
  const reqEl = document.getElementById('buildReq');
  if (!src || !reqEl) {
    toast('No imported summary available to append', false);
    return;
  }
  const cur = (reqEl.value || '').trim();
  reqEl.value = cur ? `${cur}\n\n${src}` : src;
  toast('Imported summary appended to Context');
}

function clearImportedSummary() {
  const el = document.getElementById('importedSummary');
  if (!el) return;
  el.value = '';
  toast('Imported summary cleared');
}

// ── Nav Sections Tag-chip Input (with drag-to-reorder) ────────────────────
let _navTags = [];
let _navDragIdx = null;
let _navEditedByUser = false;

function _syncNavHidden() {
  const el = document.getElementById('buildCategories');
  if (el) el.value = _navTags.join(', ');
}

function _renderNavChips() {
  const wrap = document.getElementById('navTagWrap');
  const input = document.getElementById('navTagInput');
  if (!wrap || !input) return;
  wrap.querySelectorAll('.tag-chip').forEach(c => c.remove());
  _navTags.forEach((tag, i) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.dataset.idx = i;
    chip.draggable = true;
    chip.style.cursor = 'grab';
    chip.innerHTML = `${_escHtml(tag)}<span class="chip-x" data-idx="${i}" title="Remove">×</span>`;
    // click to edit
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      if (e.target.classList.contains('chip-x')) { _navRemove(+e.target.dataset.idx); return; }
      _navEditChip(e.currentTarget, +e.currentTarget.dataset.idx);
    });
    // drag reorder
    chip.addEventListener('dragstart', (e) => {
      _navDragIdx = i;
      chip.style.opacity = '0.5';
      e.dataTransfer.effectAllowed = 'move';
    });
    chip.addEventListener('dragend', () => { chip.style.opacity = ''; _navDragIdx = null; });
    chip.addEventListener('dragover', (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
    chip.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = _navDragIdx;
      const to = +e.currentTarget.dataset.idx;
      if (from === null || from === to) return;
      const moved = _navTags.splice(from, 1)[0];
      _navTags.splice(to, 0, moved);
      _navEditedByUser = true;
      _renderNavChips();
    });
    wrap.insertBefore(chip, input);
  });
  _syncNavHidden();
}

function _navAddTag(raw) {
  const val = raw.trim();
  if (!val) return;
  if (_navTags.some(t => t.toLowerCase() === val.toLowerCase())) return;
  _navTags.push(val);
  _navEditedByUser = true;
  _renderNavChips();
}

function _navRemove(idx) {
  _navTags.splice(idx, 1);
  _navEditedByUser = true;
  _renderNavChips();
}

function _navEditChip(chip, idx) {
  const current = _navTags[idx];
  const editInput = document.createElement('input');
  editInput.className = 'tag-input-inner';
  editInput.value = current;
  editInput.style.minWidth = Math.max(80, current.length * 9) + 'px';
  chip.replaceWith(editInput);
  editInput.focus();
  editInput.select();
  let committed = false;
  const commit = () => {
    if (committed) return;
    committed = true;
    const newVal = editInput.value.trim();
    if (editInput.parentNode) editInput.remove();
    if (newVal) _navTags[idx] = newVal;
    else _navTags.splice(idx, 1);
    _navEditedByUser = true;
    _renderNavChips();
  };
  editInput.addEventListener('blur', commit);
  editInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(); }
    if (e.key === 'Escape') { committed = true; if (editInput.parentNode) editInput.remove(); _renderNavChips(); }
  });
}

function navTagWrapClick(e) {
  if (e.target.classList.contains('tag-chip') || e.target.classList.contains('chip-x')) return;
  document.getElementById('navTagInput')?.focus();
}

function _initNavTagInput() {
  const input = document.getElementById('navTagInput');
  if (!input) return;
  _navTags = [];
  _navEditedByUser = false;
  _renderNavChips();
  input.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ',') && input.value.trim()) {
      e.preventDefault();
      _navAddTag(input.value);
      input.value = '';
      return;
    }
    if (e.key === 'Backspace' && !input.value && _navTags.length) {
      _navRemove(_navTags.length - 1);
    }
  });
  input.addEventListener('input', () => {
    const v = input.value;
    if (v.endsWith(',')) { _navAddTag(v.slice(0, -1)); input.value = ''; }
  });
  input.addEventListener('paste', (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text');
    text.split(/[,\n]+/).forEach(p => _navAddTag(p));
    input.value = '';
  });
}
// ── End Nav Sections Tag-chip Input ─────────────────────────────────────────

// ── Catalog Tag-chip Input ──────────────────────────────────────────────────
const CATALOG_DEFAULT = [
  'Turbochem Optima','Jokoh Ex D','Jokoh Ex Ds','Dynacount 3D Plus',
  'Dynacount 5D PRO','Dynacount 5D Elite','Vision','Labscan 3D','Labscan 100',
  'PlexMAT8','AFIAS 2','AFIAS 3','AFIAS 6','AFIAS 10','Sprinter XL'
];

let _catalogTags = [];
let _catalogDragIdx = null;
let _catalogEditedByUser = false;

function _syncCatalogHidden() {
  const el = document.getElementById('buildCatalogItems');
  if (el) el.value = _catalogTags.join(', ');
}

function _renderCatalogChips() {
  const wrap = document.getElementById('catalogTagWrap');
  const input = document.getElementById('catalogTagInput');
  if (!wrap || !input) return;
  wrap.querySelectorAll('.tag-chip').forEach(c => c.remove());
  _catalogTags.forEach((tag, i) => {
    const chip = document.createElement('span');
    chip.className = 'tag-chip';
    chip.dataset.idx = i;
    chip.draggable = true;
    chip.style.cursor = 'grab';
    chip.innerHTML = `${_escHtml(tag)}<span class="chip-x" data-idx="${i}" title="Remove">×</span>`;
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      if (e.target.classList.contains('chip-x')) { _catalogRemove(+e.target.dataset.idx); return; }
      _catalogEditChip(e.currentTarget, +e.currentTarget.dataset.idx);
    });
    chip.addEventListener('dragstart', (e) => {
      _catalogDragIdx = i;
      chip.style.opacity = '0.5';
      e.dataTransfer.effectAllowed = 'move';
    });
    chip.addEventListener('dragend', () => { chip.style.opacity = ''; _catalogDragIdx = null; });
    chip.addEventListener('dragover', (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; });
    chip.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = _catalogDragIdx;
      const to = +e.currentTarget.dataset.idx;
      if (from === null || from === to) return;
      const moved = _catalogTags.splice(from, 1)[0];
      _catalogTags.splice(to, 0, moved);
      _catalogEditedByUser = true;
      _renderCatalogChips();
    });
    wrap.insertBefore(chip, input);
  });
  _syncCatalogHidden();
}

function _escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _catalogAddTag(raw) {
  const val = raw.trim();
  if (!val) return;
  const low = val.toLowerCase();
  if (_catalogTags.some(t => t.toLowerCase() === low)) return;
  _catalogTags.push(val);
  _catalogEditedByUser = true;
  _renderCatalogChips();
}

function _catalogRemove(idx) {
  _catalogTags.splice(idx, 1);
  _catalogEditedByUser = true;
  _renderCatalogChips();
}

function _catalogEditChip(chip, idx) {
  const current = _catalogTags[idx];
  const editInput = document.createElement('input');
  editInput.className = 'tag-input-inner';
  editInput.value = current;
  editInput.style.minWidth = Math.max(80, current.length * 9) + 'px';
  chip.replaceWith(editInput);
  editInput.focus();
  editInput.select();
  let committed = false;
  const commit = () => {
    if (committed) return;
    committed = true;
    const newVal = editInput.value.trim();
    if (editInput.parentNode) editInput.remove();
    if (newVal) _catalogTags[idx] = newVal;
    else _catalogTags.splice(idx, 1);
    _catalogEditedByUser = true;
    _renderCatalogChips();
  };
  editInput.addEventListener('blur', commit);
  editInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(); }
    if (e.key === 'Escape') { committed = true; if (editInput.parentNode) editInput.remove(); _renderCatalogChips(); }
  });
}

function catalogTagWrapClick(e) {
  if (e.target.classList.contains('tag-chip') || e.target.classList.contains('chip-x')) return;
  document.getElementById('catalogTagInput')?.focus();
}

function _initCatalogTagInput() {
  const input = document.getElementById('catalogTagInput');
  if (!input) return;
  // Start empty — values are populated from URL fetch or typed by user
  _catalogTags = [];
  _catalogEditedByUser = false;
  _renderCatalogChips();

  input.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ',') && input.value.trim()) {
      e.preventDefault();
      _catalogAddTag(input.value);
      input.value = '';
      return;
    }
    if (e.key === 'Backspace' && !input.value && _catalogTags.length) {
      _catalogRemove(_catalogTags.length - 1);
    }
  });

  input.addEventListener('input', () => {
    const v = input.value;
    if (v.endsWith(',')) {
      _catalogAddTag(v.slice(0, -1));
      input.value = '';
    }
  });

  input.addEventListener('paste', (e) => {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text');
    text.split(/[,\n]+/).forEach(p => _catalogAddTag(p));
    input.value = '';
  });
}
// ── End Catalog Tag-chip Input ──────────────────────────────────────────────

function resetBuildForm() {
  ['buildName', 'buildNiche', 'buildReq'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('buildDepth').value = 'standard';
  document.getElementById('buildColor').value = '#6366f1';
  document.getElementById('buildCart').checked = false;
  document.getElementById('cartFeaturesPanel').style.display = 'none';
  document.getElementById('buildWebSearch').checked = true;
  document.getElementById('buildLivestream').checked = false;
  document.getElementById('buildBlog').checked = false;
  document.getElementById('buildChatbot').checked = false;
  document.getElementById('buildMode').value = 'agentic_only';
  document.getElementById('buildOutputTarget').value = 'legacy';
  document.getElementById('buildBookingPrefix').value = '';
  const existingUrlEl = document.getElementById('existingUrl');
  const existingUrlsEl = document.getElementById('existingUrls');
  const importOwnEl = document.getElementById('importIsOwnUrl');
  const importedSummaryEl = document.getElementById('importedSummary');
  if (existingUrlEl) existingUrlEl.value = '';
  if (existingUrlsEl) existingUrlsEl.value = '';
  if (importOwnEl) importOwnEl.checked = false;
  if (importedSummaryEl) importedSummaryEl.value = '';
  importFlowBuildStarted = false;
  selectedBuildMode = 'agentic_only';
  selectedOutputTarget = 'legacy';
  selectedTheme = 'modern';
  selectedClassification = 'generic';
  _navTags = [];
  _navEditedByUser = false;
  _renderNavChips();
  _catalogTags = [];
  _catalogEditedByUser = false;
  _renderCatalogChips();
  buildThemeGrid();
  buildClassGrids();
  _updateImportFlowStepper();
}

function selectedClassificationMeta() {
  return CLASSIFICATIONS.find(c => c.id === selectedClassification)
    || { id: selectedClassification || 'generic', label: selectedClassification || 'Generic', group: 'general', groupLabel: 'General' };
}

function _referenceQualityMetrics(data = {}) {
  const description = String(data.description || '').trim();
  const headings = Array.isArray(data.headings) ? data.headings.length : 0;
  const paragraphs = Array.isArray(data.paragraphs) ? data.paragraphs.length : 0;
  const images = Array.isArray(data.images) ? data.images.length : 0;
  const navLinks = Array.isArray(data.nav_links)
    ? data.nav_links.filter(n => (typeof n === 'object' ? !!n.text : !!n)).length
    : 0;
  const title = String(data.title || '').trim();

  return {
    title,
    description_len: description.length,
    headings,
    paragraphs,
    nav_links: navLinks,
    images,
  };
}

function _referenceIsUsable(metrics) {
  const hasTextStructure = metrics.headings >= 2 || metrics.paragraphs >= 2 || metrics.description_len >= 80;
  const hasStructureOrMedia = metrics.images >= 1 || metrics.nav_links >= 1;
  return hasTextStructure && hasStructureOrMedia;
}

function renderReferenceQualityIndicator(items = [], failed = 0, total = 0) {
  const box = document.getElementById('referenceQualityIndicator');
  const summary = document.getElementById('referenceQualitySummary');
  const details = document.getElementById('referenceQualityDetails');
  if (!box || !summary || !details) return;

  if (!items.length && !failed) {
    box.style.display = 'none';
    summary.textContent = '';
    details.innerHTML = '';
    lastReferenceQuality = null;
    return;
  }

  const usable = items.filter(i => _referenceIsUsable(i.metrics));
  const agg = items.reduce((a, i) => ({
    headings: a.headings + i.metrics.headings,
    paragraphs: a.paragraphs + i.metrics.paragraphs,
    nav_links: a.nav_links + i.metrics.nav_links,
    images: a.images + i.metrics.images,
  }), { headings: 0, paragraphs: 0, nav_links: 0, images: 0 });

  const status = usable.length === items.length && failed === 0
    ? 'good'
    : usable.length > 0
      ? 'warn'
      : 'bad';

  const badge = status === 'good' ? '✅ GOOD' : (status === 'warn' ? '⚠️ PARTIAL' : '❌ SPARSE');
  const color = status === 'good' ? '#16a34a' : (status === 'warn' ? '#f59e0b' : '#ef4444');

  summary.style.color = color;
  summary.textContent = `${badge} · usable refs: ${usable.length}/${items.length} · failed fetches: ${failed}/${total}`;

  details.innerHTML = [
    `Aggregate: headings=${agg.headings}, paragraphs=${agg.paragraphs}, nav_links=${agg.nav_links}, images=${agg.images}`,
    ...items.map((i, idx) => {
      const m = i.metrics;
      const ok = _referenceIsUsable(m) ? '✅' : '⚠️';
      return `${ok} Ref ${idx + 1}: ${i.url} — title=${m.title ? 'yes' : 'no'}, desc_len=${m.description_len}, headings=${m.headings}, paras=${m.paragraphs}, nav=${m.nav_links}, images=${m.images}`;
    }),
    status !== 'good'
      ? 'Tip: add a richer reference URL (with visible headings/content/images) or provide explicit product categories in requirements.'
      : '',
  ].filter(Boolean).join('<br>');

  box.style.display = 'block';
  lastReferenceQuality = {
    status,
    usable: usable.length,
    total: items.length,
    failed,
    aggregate: agg,
    perRef: items,
  };
}

function _cleanCategoryCandidate(raw) {
  const s = String(raw || '').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  const low = s.toLowerCase();
  const lowNormalized = low.replace(/[’]/g, "'");

  // Remove clearly generic/navigation phrases.
  const blockedExact = new Set([
    'home', 'about', 'about us', 'contact', 'contact us', 'services', 'service',
    'welcome', 'welcome!', 'welcome to drg', 'blog', 'news', 'careers', 'login',
    'register', 'resources', 'resource center', 'case studies', 'testimonial', 'testimonials',
    'privacy policy', 'terms', 'terms of service', 'faq', 'faqs', 'our team',
    'our mission', 'our vision', 'products', 'our solutions', "what's new", 'whats new',
    'latest news', 'latest updates', 'intent', 'plus1'
  ]);
  if (blockedExact.has(lowNormalized)) return '';
  if (/^product\s*\d+\b/i.test(lowNormalized)) return '';
  if (/^c\d{2,}\s+[a-z]{3,}$/i.test(lowNormalized)) return '';
  if (/^(welcome|discover|learn more|read more|request|book|explore)\b/i.test(s)) return '';
  if (/^(view|shop|browse|get|start|order|buy)\s+(all|now|more|products?|services?)\b/i.test(s)) return '';
  if (/^(menu|search|cart|wishlist|checkout|track order|account|sign in|sign up|register|login)\b/i.test(s)) return '';
  if (/^(next|previous|prev|back|top|more|all)$/.test(lowNormalized)) return '';
  if (/^(home|about|contact|blog|careers|news|faq|resources?)\b/i.test(s) && s.length < 35) return '';
  if (/^(dr|mr|mrs|ms|miss|prof)\.?\s+[a-z]/i.test(s)) return '';
  if (/\b(testimonial|testimonials|review|reviews)\b/i.test(s) && s.length < 50) return '';
  if (/\b(private limited|pvt\.?\s*ltd\.?|ltd\.?|inc\.?|llc|corp\.?|company)\b/i.test(s)) return '';
  if (/^(our|latest)\s+(solutions|news|updates)\b/i.test(s)) return '';

  // Strip punctuation noise and bullet chars.
  const cleaned = s.replace(/^[•\-–—\s]+/, '').replace(/[|:]+$/, '').trim();
  if (!cleaned) return '';

  // Keep category-sized labels only.
  if (cleaned.length < 3 || cleaned.length > 55) return '';
  return cleaned;
}

function _cleanImportedProductCandidate(raw) {
  const s = String(raw || '').replace(/\s+/g, ' ').trim();
  if (!s) return '';
  const cleaned = s.replace(/^[•\-–—#>\s]+/, '').replace(/[|:]+$/, '').trim();
  if (!cleaned) return '';
  const low = cleaned.toLowerCase().replace(/[’]/g, "'");
  const blockedExact = new Set([
    'home', 'about', 'contact', 'services', 'products', 'blog', 'news', 'menu',
    'shop', 'shop now', 'view all', 'learn more', 'read more', 'more', 'all',
    'search', 'cart', 'checkout', 'wishlist', 'login', 'register', 'account'
  ]);
  if (blockedExact.has(low)) return '';
  if (/^(home|about|contact|services?|products?|blog|news|menu|search|cart|checkout|wishlist)\b/i.test(cleaned)) return '';
  if (/^(learn more|read more|view all|shop now|buy now|book now|request|explore)\b/i.test(cleaned)) return '';
  if (/^(next|previous|prev|back|top)$/i.test(cleaned)) return '';
  if (/^\d+\s*(items?|products?)$/i.test(cleaned)) return '';
  if (cleaned.length < 2 || cleaned.length > 80) return '';
  return cleaned;
}

function _extractImportedWebsiteName(rawTitle = '') {
  const title = String(rawTitle || '').replace(/\s+/g, ' ').trim();
  if (!title) return '';

  const blocked = new Set([
    'home', 'welcome', 'about', 'contact', 'services', 'products', 'blog', 'news'
  ]);
  const industryWords = /\b(diagnostics?|diagnostic|laboratory|lab|medical|clinic|hospital|health|equipment|supplier|distributor|manufacturer|salon|hotel|mall|store|law|legal|bakery|restaurant|school|academy|teacher|doctor)\b/i;
  const locationWords = /\b(mumbai|kolkata|delhi|chennai|bangalore|hyderabad|pune|coimbatore|madurai|trichy|india|usa|uk|uae|singapore)\b/i;

  const parts = title.split(/[|\-–—]+/).map(p => p.trim()).filter(Boolean);
  const filtered = parts.filter(part => !blocked.has(part.toLowerCase()));
  const businessLike = filtered.filter(part => industryWords.test(part) && !locationWords.test(part));
  if (businessLike.length) return businessLike[0];

  const nonLocation = filtered.filter(part => !locationWords.test(part));
  if (nonLocation.length) return nonLocation[0];

  return filtered[0] || title;
}

function _extractIndustryPhrase(raw = '') {
  const text = String(raw || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';

  const phrases = text.split(/[.!?\n|]+/).map(p => p.trim()).filter(Boolean);
  const industryPatterns = [
    /\b([a-z][a-z&/\-\s]{2,70}?(?:medical equipment supplier|laboratory equipment supplier|diagnostic equipment supplier|medical laboratory equipment supplier|equipment supplier|equipment distributor|supplier|distributor|manufacturer|provider|dealer|exporter))\b/i,
    /\b([a-z][a-z&/\-\s]{2,70}?(?:medical equipment|diagnostic centre|diagnostic center|healthcare provider|law firm))\b/i,
    /\b([a-z][a-z&/\-\s]{2,70}?(?:diagnostics?|laboratory|healthcare|clinic|hospital|salon|hotel|bakery|restaurant|academy|school|store|mall))\b/i,
  ];
  for (const phrase of phrases) {
    const candidates = [
      phrase.replace(/^.*?\b(?:is|are|offers|provides|specializes in|specialises in)\b\s*(?:a|an|the)?\s*/i, '').trim(),
      phrase.split(/\b(?:for|with|serving|serves|specializing in|specialises in)\b/i)[0].trim(),
      phrase,
    ];
    for (const candidate of candidates) {
      for (const industryPattern of industryPatterns) {
        const match = candidate.match(industryPattern);
        if (!match) continue;
        const cleaned = _cleanCategoryCandidate(match[1]);
        if (cleaned) return cleaned;
      }
    }
  }
  return '';
}

function _dedupeImportCandidates(candidates, cleaner, limit) {
  const deduped = [];
  const seen = new Set();
  for (const candidate of candidates) {
    const cleaned = cleaner(candidate);
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(cleaned);
    if (deduped.length >= limit) break;
  }
  return deduped;
}

function _extractImportNavSections(successes) {
  // Primary source: actual navigation links from the scraped site.
  // These directly map to page sections. Product names, keywords,
  // carousels and headings are intentionally excluded here.
  const candidates = [];

  for (const s of successes) {
    const d = s?.data || {};
    const navTexts = Array.isArray(d.nav_links)
      ? d.nav_links.map(n => (typeof n === 'object' ? n.text : n)).filter(Boolean)
      : [];
    const subpageNames = Array.isArray(d.subpages)
      ? d.subpages.map(p => p?.page).filter(Boolean)
      : [];

    // Fallback: use headings and scraped subpage names when nav is sparse.
    const headings = navTexts.length < 2 && Array.isArray(d.headings)
      ? d.headings.slice(0, 10)
      : [];

    candidates.push(...navTexts, ...subpageNames, ...headings);
  }

  return _dedupeImportCandidates(candidates, _cleanCategoryCandidate, 12);
}

function _extractNicheHint(successes, categoryHints = []) {
  for (const s of successes) {
    const d = s?.data || {};
    const industryFromDescription = _extractIndustryPhrase(d.description || '');
    if (industryFromDescription) return industryFromDescription;
    const industryFromHeadings = Array.isArray(d.headings)
      ? d.headings.map(h => _extractIndustryPhrase(h)).find(Boolean)
      : '';
    if (industryFromHeadings) return industryFromHeadings;
    const industryFromTitle = _extractIndustryPhrase(d.title || '');
    if (industryFromTitle) return industryFromTitle;
  }

  const kw = [];
  for (const s of successes) {
    const d = s?.data || {};
    const raw = String(d.keywords || '').trim();
    if (!raw) continue;
    raw.split(/[,|/;]+/).map(x => x.trim()).filter(Boolean).forEach(x => kw.push(x));
  }

  const cleanedKw = [];
  const seen = new Set();
  for (const k of kw) {
    const c = _cleanCategoryCandidate(k);
    if (!c) continue;
    const low = c.toLowerCase();
    if (seen.has(low)) continue;
    seen.add(low);
    cleanedKw.push(c);
  }

  const keywordIndustry = cleanedKw.find(k => _extractIndustryPhrase(k) || /\b(diagnostics?|laboratory|medical|equipment|supplier|distributor|manufacturer|clinic|hospital|healthcare|salon|hotel|bakery|restaurant|academy|school|law|store|mall)\b/i.test(k));
  if (keywordIndustry) return keywordIndustry;
  if (cleanedKw.length) return cleanedKw.slice(0, 3).join(', ');

  const firstTitle = String(successes?.[0]?.data?.title || '').trim();
  if (firstTitle) {
    const maybeIndustry = _extractIndustryPhrase(firstTitle);
    if (maybeIndustry) return maybeIndustry;
    const maybe = _cleanCategoryCandidate(_extractImportedWebsiteName(firstTitle));
    if (maybe) return maybe;
  }

  if (categoryHints.length) return categoryHints.slice(0, 3).join(', ');

  const firstDescription = String(successes?.[0]?.data?.description || '').trim();
  if (firstDescription) {
    const sentence = firstDescription.split(/[.!?\n]/).map(s => s.trim()).find(Boolean);
    const maybeDescription = _cleanCategoryCandidate(sentence || firstDescription);
    if (maybeDescription) return maybeDescription;
  }
  return '';
}

function _extractImportProducts(successes) {
  const candidates = [];
  for (const s of successes) {
    const d = s?.data || {};
    const fromCarousel = Array.isArray(d.carousel_products)
      ? d.carousel_products.map(p => (typeof p === 'object' ? (p.name || p.title || '') : p)).filter(Boolean)
      : [];
    const fromProducts = Array.isArray(d.products)
      ? d.products.map(p => (typeof p === 'object' ? (p.name || p.title || '') : p)).filter(Boolean)
      : [];
    // Prefer explicit product lists. Heading/subpage text can be mostly navigation noise.
    const hasExplicitProducts = fromCarousel.length > 0 || fromProducts.length > 0;
    const fromHeadings = !hasExplicitProducts && Array.isArray(d.headings)
      ? d.headings.slice(0, 12)
      : [];
    const fromSubpages = !hasExplicitProducts && Array.isArray(d.subpages)
      ? d.subpages.map(p => p?.page).filter(Boolean)
      : [];
    candidates.push(...fromCarousel, ...fromProducts, ...fromHeadings, ...fromSubpages);
  }
  return _dedupeImportCandidates(candidates, _cleanImportedProductCandidate, 30);
}

async function fetchWebsiteInfo() {
  importFlowBuildStarted = false;
  _updateImportFlowStepper();
  const primaryRaw = document.getElementById('existingUrl')?.value.trim() || '';
  const isOwnUrl = !!document.getElementById('importIsOwnUrl')?.checked;
  const additionalRaw = document.getElementById('existingUrls')?.value || '';

  const parseUrlForFetch = (raw = '') => {
    const line = String(raw || '').trim();
    if (!line) return '';
    const left = (line.split(/\s+-\s+/)[0] || '').trim();
    const candidate = left || line;
    const urlMatch = candidate.match(/https?:\/\/[^\s,]+/i) || line.match(/https?:\/\/[^\s,]+/i);
    if (urlMatch?.[0]) return urlMatch[0].trim();
    if (/^[a-z0-9.-]+\.[a-z]{2,}(?:\/[^\s]*)?$/i.test(candidate)) return candidate;
    return '';
  };

  const primaryUrl = parseUrlForFetch(primaryRaw);
  const additionalUrls = [];
  const malformedLines = [];
  const lines = String(additionalRaw)
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const parsed = parseUrlForFetch(line);
    if (parsed) {
      additionalUrls.push(parsed);
      continue;
    }
    malformedLines.push({ line: i + 1, text: line });
  }

  const urls = [
    ...(primaryUrl ? [primaryUrl] : []),
    ...additionalUrls,
  ].filter((url, idx, arr) => arr.indexOf(url) === idx);

  const detailEl = document.getElementById('fetchUrlDetails');

  if (!primaryUrl && primaryRaw) {
    if (detailEl) {
      detailEl.style.display = 'block';
      detailEl.style.color = '#f59e0b';
      detailEl.innerHTML = `⚠️ Primary URL looks invalid and was ignored: ${_escHtml(primaryRaw)}`;
    }
    toast('Primary URL is invalid. Please use a valid URL.', false);
  }

  if (!urls.length) {
    if (detailEl && malformedLines.length) {
      detailEl.style.display = 'block';
      detailEl.style.color = '#f59e0b';
      detailEl.innerHTML = [
        `⚠️ Could not parse ${malformedLines.length} reference line(s).`,
        ...malformedLines.slice(0, 8).map(item => `Line ${item.line}: ${_escHtml(item.text)}`),
        malformedLines.length > 8 ? '...and more. Use format: URL - usage note' : 'Use format: URL - usage note',
      ].join('<br>');
    }
    toast('Please enter at least one valid URL', false);
    return;
  }

  if (!primaryUrl && document.getElementById('existingUrl')) {
    document.getElementById('existingUrl').value = urls[0];
  }

  const btn = document.getElementById('fetchUrlBtn');
  const statusEl = document.getElementById('fetchUrlStatus');
  renderReferenceQualityIndicator([], 0, urls.length);
  btn.disabled = true;
  btn.textContent = '⏳ Fetching…';
  statusEl.style.display = 'block';
  statusEl.style.color = 'var(--muted)';
  statusEl.textContent = `Scraping ${urls.length} website(s)…`;
  if (detailEl) {
    detailEl.style.display = 'none';
    detailEl.innerHTML = '';
  }

  const malformedHintHtml = malformedLines.length
    ? [
        `⚠️ Ignored ${malformedLines.length} malformed reference line(s).`,
        ...malformedLines.slice(0, 5).map(item => `Line ${item.line}: ${_escHtml(item.text)}`),
        malformedLines.length > 5 ? '...and more.' : '',
      ].filter(Boolean).join('<br>')
    : '';
  if (malformedLines.length) {
    toast(`Ignored ${malformedLines.length} malformed line(s). Fetching valid URLs only.`, false);
  }

  try {
    const successes = [];
    const failures = [];
    const perUrlResults = [];
    const qualityItems = [];

    for (let i = 0; i < urls.length; i++) {
      const thisUrl = urls[i];
      statusEl.textContent = `Scraping ${i + 1}/${urls.length}: ${thisUrl}`;
      const data = await apiFetch('/websites/scrape-url', {
        method: 'POST',
        body: JSON.stringify({ url: thisUrl }),
      });

      if (!data) {
        failures.push(thisUrl);
        perUrlResults.push({ url: thisUrl, ok: false, reason: apiFetch._lastError || 'No data returned' });
        continue;
      }
      successes.push({ url: thisUrl, data });
      perUrlResults.push({ url: thisUrl, ok: true, title: data.title || '' });
      qualityItems.push({ url: thisUrl, metrics: _referenceQualityMetrics(data) });
    }

    if (!successes.length) {
      throw new Error('Failed to fetch data from all provided URLs.');
    }

    const ownPick = successes.find(s => s.url === primaryUrl) || successes[0];
    const first = ownPick.data;

    // Only import the website name when the user confirms this is their own site.
    if (isOwnUrl && first.title)
      document.getElementById('buildName').value = _extractImportedWebsiteName(first.title);

    // Keep Context user-owned by default. Put imported text into separate summary box.
    const importedSummaryEl = document.getElementById('importedSummary');
    if (importedSummaryEl) {
      const mergedSummary = successes
        .map(s => String(s?.data?.description || '').trim())
        .filter(Boolean)
        .filter((v, i, arr) => arr.indexOf(v) === i)
        .slice(0, 3)
        .join('\n\n');
      importedSummaryEl.value = mergedSummary;
    }

    // Prefill contact fields only when user explicitly marks the imported URL
    // as their own site. Reference URLs should not overwrite contact identity.
    if (isOwnUrl) {
      if (first.emails?.length && !document.getElementById('buildEmail').value)
        document.getElementById('buildEmail').value = first.emails[0];

      if (first.phones?.length && !document.getElementById('buildPhone').value)
        document.getElementById('buildPhone').value = first.phones[0];
    }

    // Populate Page Sections & Nav Groups from scraped nav links.
    // Respect manual edits: only auto-replace when user has not customized chips.
    let navImportSkippedDueToManualEdits = false;
    const hints = _extractImportNavSections(successes);
    if (hints.length) {
      const canReplaceNav = !_navEditedByUser || !_navTags.length;
      if (canReplaceNav) {
        _navTags = [...hints];
        _navEditedByUser = false;
        _renderNavChips();
      } else {
        navImportSkippedDueToManualEdits = true;
      }
    }

    // Populate Product / Model Names tag chips from scraped products/carousels.
    // Respect manual edits: only auto-replace when user has not customized chips.
    let catalogImportSkippedDueToManualEdits = false;
    const uniqueProducts = _extractImportProducts(successes);
    if (uniqueProducts.length) {
      const canReplaceCatalog = !_catalogEditedByUser || !_catalogTags.length;
      if (canReplaceCatalog) {
        _catalogTags = uniqueProducts.slice(0, 30);
        _catalogEditedByUser = false;
        _renderCatalogChips();
      } else {
        catalogImportSkippedDueToManualEdits = true;
      }
    }

    // Prefill niche/category field from merged import signals if user hasn't set it.
    const nicheEl = document.getElementById('buildNiche');
    if (nicheEl && !String(nicheEl.value || '').trim()) {
      const niche = _extractNicheHint(successes, hints);
      if (niche) nicheEl.value = niche;
    }

    const summary = [
      `✅ Imported ${successes.length}/${urls.length} URL(s)`,
      failures.length ? `⚠️ Failed ${failures.length}` : null,
      first.title ? `Title: ${first.title}` : null,
      isOwnUrl && first.emails?.length ? `📧 ${first.emails[0]}` : null,
      isOwnUrl && first.phones?.length ? `📞 ${first.phones[0]}` : null,
    ].filter(Boolean).join(' · ');

    statusEl.style.color = failures.length ? '#f59e0b' : '#22c55e';
    statusEl.textContent = summary;
    if (detailEl) {
      detailEl.style.display = 'block';
      const details = perUrlResults
        .map(r => r.ok
          ? `✅ ${r.url}${r.title ? ` — ${r.title}` : ''}`
          : `❌ ${r.url} — ${r.reason}`)
        .join('<br>');
      const importHints = [
        navImportSkippedDueToManualEdits ? 'ℹ️ Kept your Page Sections & Nav Groups chips (manual edits were preserved).' : null,
        catalogImportSkippedDueToManualEdits ? 'ℹ️ Kept your Product / Model Names chips (manual edits were preserved).' : null,
      ].filter(Boolean).join('<br>');
      detailEl.innerHTML = [malformedHintHtml, details, importHints].filter(Boolean).join('<br>');
    }
    renderReferenceQualityIndicator(qualityItems, failures.length, urls.length);

    const modeSel = document.getElementById('buildMode');
    if (modeSel) modeSel.value = 'combined';
    selectedBuildMode = 'combined';

    const preservedHints = [];
    if (navImportSkippedDueToManualEdits) preservedHints.push('kept your manual nav chips');
    if (catalogImportSkippedDueToManualEdits) preservedHints.push('kept your manual product chips');
    const preservedText = preservedHints.length ? ` (${preservedHints.join('; ')})` : '';
    toast(`Reference URLs imported. Switching to Agentic Build (Combined mode)…${preservedText}`);
    setTimeout(() => switchBuildTab('agent'), 800);
  } catch (err) {
    statusEl.style.color = '#ef4444';
    statusEl.textContent = `❌ ${err.message || 'Failed to fetch website info.'}`;
    if (detailEl) {
      detailEl.style.display = 'none';
      detailEl.innerHTML = '';
    }
    renderReferenceQualityIndicator([], urls.length, urls.length);
    toast('Failed to fetch website info', false);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 Fetch Info';
  }
}

async function buildWebsite() {
  const name = document.getElementById('buildName').value.trim();
  const requirements = document.getElementById('buildReq').value.trim();
  const niche = document.getElementById('buildNiche')?.value.trim() || undefined;
  const content_depth = document.getElementById('buildDepth')?.value || 'standard';
  if (!name || !requirements) { toast('Name and requirements are required', false); return; }

  const categories = _navTags.length ? [..._navTags] : undefined;
  const catalog_items = _catalogTags.length ? [..._catalogTags] : undefined;
  const location = document.getElementById('buildLocation')?.value.trim() || undefined;
  const email = document.getElementById('buildEmail')?.value.trim() || undefined;
  const phone = document.getElementById('buildPhone')?.value.trim() || undefined;
  const booking_prefix = document.getElementById('buildBookingPrefix')?.value.trim() || undefined;
  selectedBuildMode = document.getElementById('buildMode')?.value || 'agentic_only';
  selectedOutputTarget = document.getElementById('buildOutputTarget')?.value || 'legacy';
  const classMeta = selectedClassificationMeta();

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
  const existingUrlSingle = document.getElementById('existingUrl')?.value.trim() || '';
  const existingUrlsRaw = document.getElementById('existingUrls')?.value || '';
  const referenceEntries = _parseReferenceUrlEntries(existingUrlsRaw);
  const existing_website_urls = [
    ...(existingUrlSingle ? [existingUrlSingle] : []),
    ...referenceEntries.map(e => e.url),
  ].filter((url, idx, arr) => arr.indexOf(url) === idx);
  const existing_website_url = existing_website_urls[0] || undefined;
  const reference_usage_by_url = referenceEntries
    .filter(e => e.url && e.usage)
    .map(e => ({ url: e.url, usage: e.usage }));

  if (selectedBuildMode === 'combined' && existing_website_urls.length === 0) {
    toast('Combined mode requires at least one reference URL in Import tab', false);
    return;
  }

  if (selectedBuildMode === 'combined') {
    if (!lastReferenceQuality) {
      toast('Please click Fetch Info first to evaluate reference quality before Combined build.', false);
      return;
    }
    if (lastReferenceQuality.status === 'bad') {
      toast('Reference quality is too sparse for Combined mode. Add a richer URL or stronger product/category details.', false);
      return;
    }
  }

  importFlowBuildStarted = true;
  _updateImportFlowStepper();

  document.getElementById('buildProgress').style.display = 'block';
  // Always show spinner at build start
  document.getElementById('buildSpinner').style.display = 'inline-block';
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
    classification_label: classMeta.label,
    classification_group: classMeta.group,
    build_mode: selectedBuildMode,
    output_target: selectedOutputTarget,
    hosting_env: 's3',
    include_shopping_cart: cartEnabled,
    cart_features: cartEnabled ? getSelectedCartFeatures() : [],
    enable_chatbot: document.getElementById('buildChatbot').checked,
    enable_blog: document.getElementById('buildBlog').checked,
    enable_livestream: document.getElementById('buildLivestream').checked,
    content_depth,
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
    build_mode: selectedBuildMode,
    output_target: selectedOutputTarget,
    classification_label: classMeta.label,
    classification_group: classMeta.group,
    content_depth,
    include_shopping_cart: cartEnabled,
    ...(niche && { niche }),
    ...(categories?.length && { categories }),
    ...(catalog_items?.length && { catalog_items }),
    ...(location && { location }),
    ...(email && { email }),
    ...(phone && { phone }),
    ...(booking_prefix && { booking_prefix }),
    ...(social_links && { social_links }),
    ...(existing_website_url && { existing_website_url }),
    ...(existing_website_urls.length && { existing_website_urls }),
    ...(reference_usage_by_url.length && { reference_usage_by_url }),
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
    fallback:{ msg: '✅ Website generated (fallback mode).',      pct: 100 },
    error:   { msg: '❌ Build failed.',                           pct: 100 },
    timeout: { msg: '⚠️ Build is taking longer than expected. Check My Websites for status.', pct: 100 },
  };


  const setStage = (status, errorMsg) => {
    const s = stageLabels[status] || stageLabels.queued;
    document.getElementById('buildProgressMsg').textContent = errorMsg ? `❌ ${errorMsg}` : s.msg;
    document.getElementById('buildProgressBar').style.width = s.pct + '%';
    document.getElementById('buildStageLabel').textContent  = 'Stage: ' + status;
    if (['built', 'fallback', 'error', 'timeout'].includes(status)) {
      document.getElementById('buildSpinner').style.display = 'none';
    }
  };

  setStage('queued');

  await new Promise(resolve => {
    const es = new EventSource(
      `${API}/websites/${created.website_id}/build-stream?token=${encodeURIComponent(token)}`
    );
    es.onmessage = async (e) => {
      try {
        const data = JSON.parse(e.data);
        const status = data.build_status || 'queued';
        setStage(status, data.error);
        if (['built', 'fallback', 'error', 'timeout', 'not_found'].includes(status)) {
          es.close();
          if (status === 'built' || status === 'fallback') {
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
          } else if (status === 'timeout') {
            document.getElementById('buildSpinner').style.display = 'inline-block';
            document.getElementById('buildProgressMsg').textContent = '⏳ Still running in background. Continuing to check status…';
            toast('Build is still running. Continuing to check automatically…');

            const finalState = await _pollBuildStatusUntilTerminal(created.website_id, {
              onUpdate: (s, err) => setStage(s, err),
              maxAttempts: 180,
              intervalMs: 5000,
            });

            document.getElementById('buildSpinner').style.display = 'none';

            if (finalState.status === 'built' || finalState.status === 'fallback') {
              toast('Website built! Opening Staging Area…');
              setTimeout(async () => {
                resetBuildForm();
                await loadAllSites();
                await loadStagingWebsites();
                showPage('staging');
                loadStagedSite(created.website_id);
              }, 1500);
            } else if (finalState.status === 'error') {
              toast(finalState.error || 'Build failed. Please try again.', false);
            } else {
              setStage('timeout');
              toast('Build is still running. You can continue from My Websites or Staging.', false);
            }
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
  _setWebsites(await _fetchMyWebsites());

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
  if (!(await styledConfirm('Permanently remove this cart item? This cannot be undone.', {
    title: 'Remove Cart Item?',
    icon: '🗑',
    okLabel: 'Remove',
    okClass: 'btn-danger',
  }))) return;
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
  const siteId = document.getElementById('prodSite')?.value || stagedWebsiteId || '';
  if (siteId) formData.append('website_id', siteId);

  try {
    const resp = await fetch(`${API}/media/upload-image`, {
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
  if (!(await styledConfirm('Delete this coupon?', {
    title: 'Delete Coupon?',
    icon: '🗑',
    okLabel: 'Delete',
    okClass: 'btn-danger',
  }))) return;
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
  if (!(await styledConfirm('Send this campaign to all subscribers?', {
    title: 'Send Campaign?',
    icon: '📣',
    okLabel: 'Send',
    okClass: 'btn-primary',
  }))) return;
  const r = await apiFetch(`/commerce/campaigns/${id}/send`, { method: 'POST' });
  if (r) { toast('Campaign sent!'); loadCampaigns(); }
  else toast('Send failed', false);
}

async function deleteCampaign(id) {
  if (!(await styledConfirm('Delete this campaign?', {
    title: 'Delete Campaign?',
    icon: '🗑',
    okLabel: 'Delete',
    okClass: 'btn-danger',
  }))) return;
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
  if (!(await styledConfirm('Remove this team member? They will lose access.', {
    title: 'Remove Team Member?',
    icon: '👤',
    okLabel: 'Remove',
    okClass: 'btn-danger',
  }))) return;
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
  if (!(await styledConfirm('Remove this client? They will lose access.', {
    title: 'Remove Client?',
    icon: '🤝',
    okLabel: 'Remove',
    okClass: 'btn-danger',
  }))) return;
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

  const modeSel = document.getElementById('buildMode');
  if (modeSel) {
    if (isImport && modeSel.value !== 'combined') modeSel.value = 'combined';
    if (!isImport && modeSel.value !== 'combined' && modeSel.value !== 'agentic_only') modeSel.value = 'agentic_only';
    selectedBuildMode = modeSel.value;
  }

  if (!isImport) applyBuildPlanRestrictions();

  _updateImportFlowStepper();
}

// ── Staging Area ───────────────────────────────────────────────────────────
let stagedWebsiteId = null;
let currentStagingUrl = null;
let currentStagingEntryPath = 'index.html';
let _siteImageLabelByPath = new Map();
let _siteImageMetaByPath = new Map();
let _siteImageItems = [];
let _siteMediaById = new Map();
let _selectedExistingMediaPath = '';
let _mediaPickerContext = { mode: 'manage', fid: '' };
let _mediaLibraryTypeFilter = 'all';
let currentStagingHomeEntryPath = 'index.html';
let currentStagingHtmlHash = '';
let currentStagingManifestEtag = '';
let currentStagingArtifactCount = 0;
let currentStagingArtifacts = [];
let stagingMetadataPanelOpen = false;
let _metadataBaseline = { title: '', description: '' };

function _metaInput(id) {
  return document.getElementById(id);
}

function _setStagingMetadataEnabled(enabled) {
  [
    'metaTitleInput',
    'metaOgUrlInput',
    'metaDescriptionInput',
    'metaImageInput',
    'metaPickFromLibraryBtn',
    'metaTwitterCardInput',
    'metaPresetSelect',
    'metaPresetCustomInput',
    'metaPresetBtn',
    'metaPresetResetBtn',
    'metaSmartDefaultsBtn',
    'metaFillAboutBtn',
    'metaFillHeroBtn',
    'metaReloadBtn',
    'metaApplyBtn',
  ].forEach(id => {
    const el = _metaInput(id);
    if (el) el.disabled = !enabled;
  });
}

function _shortImageLabel(url) {
  const raw = String(url || '').trim();
  if (!raw) return 'image';
  const clean = raw.split('?')[0].split('#')[0];
  const seg = clean.split('/').filter(Boolean).pop() || clean;
  return seg.length > 58 ? `${seg.slice(0, 55)}...` : seg;
}

function _applySelectedMediaToMetadata(media) {
  if (!media) return;
  const mediaType = String(media.media_type || 'image').trim().toLowerCase();
  if (mediaType !== 'image') {
    toast('Please select an image for metadata preview', false);
    return;
  }
  const rawSource = String(media.url || media.path || '').trim();
  if (!rawSource) {
    toast('Selected media has no URL', false);
    return;
  }
  const imageInput = _metaInput('metaImageInput');
  if (!imageInput) return;
  const normalized = _normalizeStagingAssetUrl(rawSource);
  const frame = document.getElementById('stagingIframe');
  imageInput.value = _toAbsoluteMetaUrl(normalized, frame?.src || window.location.origin);
  refreshStagingMetaImagePreview();
  _updateMetadataGuides();
  const displayName = String(media.name || '').trim() || _shortImageLabel(normalized);
  toast(`Selected ${displayName} for metadata ✅`);
}

function openMetadataImageLibrary() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  _mediaPickerContext = { mode: 'metadata-image', fid: '' };
  _mediaLibraryTypeFilter = 'image';
  _refreshMediaPickerHeader();
  openModal('existingBgImageModal');
  loadExistingBgImages();
  renderExistingBgImagePicker();
}

function _truncateSmart(text, maxLen) {
  const raw = String(text || '').replace(/\s+/g, ' ').trim();
  if (!raw || raw.length <= maxLen) return raw;
  const trimmed = raw.slice(0, maxLen - 1);
  const cut = trimmed.lastIndexOf(' ');
  return `${(cut > 40 ? trimmed.slice(0, cut) : trimmed).trim()}.`;
}

function _appendUniqueChunk(base, chunk, joiner = ' ') {
  const lhs = String(base || '').trim();
  const rhs = String(chunk || '').trim();
  if (!rhs) return lhs;
  if (!lhs) return rhs;
  if (lhs.toLowerCase().includes(rhs.toLowerCase())) return lhs;
  return `${lhs}${joiner}${rhs}`.trim();
}

function _stripPresetSuffixesTitle(value) {
  let out = String(value || '').trim();
  const suffixes = [
    'Trusted Solutions',
    'Reliable Since 2010',
    'Local Service Experts',
  ];
  suffixes.forEach(sfx => {
    const re = new RegExp(`\\s*\\|\\s*${sfx.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}`, 'ig');
    out = out.replace(re, '');
  });
  out = out.replace(/(\|\s*){2,}/g, ' | ').replace(/\s+\|\s+$/g, '').trim();
  return out;
}

function _stripPresetSuffixesDescription(value) {
  let out = String(value || '').trim();
  const suffixes = [
    'Contact us today for expert guidance and fast support.',
    'Trusted quality, experienced team, and consistent service delivery.',
  ];
  suffixes.forEach(sfx => {
    const re = new RegExp(`\\s*${sfx.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')}`, 'ig');
    out = out.replace(re, '').trim();
  });
  return out.replace(/\s{2,}/g, ' ').trim();
}

function _metadataScore(title, description, image) {
  let score = 0;
  if (title.length >= 30 && title.length <= 60) score += 1;
  else if (title.length >= 16) score += 0.5;
  if (description.length >= 110 && description.length <= 160) score += 1;
  else if (description.length >= 70) score += 0.5;
  if (image) score += 1;
  return score;
}

function _updateMetadataGuides() {
  const title = (_metaInput('metaTitleInput')?.value || '').trim();
  const description = (_metaInput('metaDescriptionInput')?.value || '').trim();
  const image = (_metaInput('metaImageInput')?.value || '').trim();
  const titleGuide = _metaInput('metaTitleGuide');
  const descGuide = _metaInput('metaDescriptionGuide');
  const quality = _metaInput('metaQualityBar');

  if (titleGuide) {
    const ok = title.length >= 30 && title.length <= 60;
    titleGuide.textContent = `${title.length} chars • Suggested 30-60`;
    titleGuide.style.color = ok || title.length === 0 ? 'var(--muted)' : '#f59e0b';
  }

  if (descGuide) {
    const ok = description.length >= 110 && description.length <= 160;
    descGuide.textContent = `${description.length} chars • Suggested 110-160`;
    descGuide.style.color = ok || description.length === 0 ? 'var(--muted)' : '#f59e0b';
  }

  if (quality) {
    const score = _metadataScore(title, description, image);
    if (score >= 2.5) {
      quality.textContent = 'Quality check: Great. Metadata is likely to render well on WhatsApp and social platforms.';
      quality.style.borderColor = '#16a34a';
      quality.style.color = '#bbf7d0';
    } else if (score >= 1.5) {
      quality.textContent = 'Quality check: Good. Add or refine remaining fields for stronger preview quality.';
      quality.style.borderColor = '#f59e0b';
      quality.style.color = '#fde68a';
    } else {
      quality.textContent = 'Quality check: Fill Title, Description, and Image URL for best social previews.';
      quality.style.borderColor = 'var(--border)';
      quality.style.color = 'var(--muted)';
    }
  }

  refreshMetadataLiveCard();
}

function _wireMetadataGuideListeners() {
  ['metaTitleInput', 'metaDescriptionInput', 'metaImageInput'].forEach(id => {
    const el = _metaInput(id);
    if (!el || el.dataset.metaGuideBound === '1') return;
    el.dataset.metaGuideBound = '1';
    el.addEventListener('input', _updateMetadataGuides);
  });
}

function _metaContent(doc, selector) {
  return (doc.querySelector(selector)?.getAttribute('content') || '').trim();
}

function _extractStagingMetadata(doc) {
  return {
    title: (doc.querySelector('title')?.textContent || '').trim(),
    description: _metaContent(doc, 'meta[name="description"]'),
    ogTitle: _metaContent(doc, 'meta[property="og:title"]'),
    ogDescription: _metaContent(doc, 'meta[property="og:description"]'),
    ogImage: _metaContent(doc, 'meta[property="og:image"]'),
    ogUrl: _metaContent(doc, 'meta[property="og:url"]'),
    twitterCard: _metaContent(doc, 'meta[name="twitter:card"]') || 'summary_large_image',
    twitterTitle: _metaContent(doc, 'meta[name="twitter:title"]'),
    twitterDescription: _metaContent(doc, 'meta[name="twitter:description"]'),
    twitterImage: _metaContent(doc, 'meta[name="twitter:image"]'),
  };
}

function refreshStagingMetaImagePreview() {
  const img = _metaInput('metaOgImagePreview');
  const val = (_metaInput('metaImageInput')?.value || '').trim();
  if (!img) return;
  if (!val) {
    img.style.display = 'none';
    img.removeAttribute('src');
    return;
  }
  img.src = val;
  img.style.display = '';
}

function _hostnamePreview(rawUrl) {
  const url = String(rawUrl || '').trim();
  if (!url) return 'example.com';
  try {
    return new URL(url).hostname.replace(/^www\./i, '') || 'example.com';
  } catch (_) {
    return url.replace(/^https?:\/\//i, '').split('/')[0] || 'example.com';
  }
}

function refreshMetadataLiveCard() {
  const title = (_metaInput('metaTitleInput')?.value || '').trim();
  const description = (_metaInput('metaDescriptionInput')?.value || '').trim();
  const image = (_metaInput('metaImageInput')?.value || '').trim();
  const ogUrl = (_metaInput('metaOgUrlInput')?.value || '').trim();

  const titleEl = _metaInput('metaLiveCardTitle');
  const descEl = _metaInput('metaLiveCardDescription');
  const urlEl = _metaInput('metaLiveCardUrl');
  const imgEl = _metaInput('metaLiveCardImage');
  const imgFallback = _metaInput('metaLiveCardImageFallback');

  if (titleEl) titleEl.textContent = title || 'Preview title';
  if (descEl) descEl.textContent = description || 'Preview description will appear here.';
  if (urlEl) urlEl.textContent = _hostnamePreview(ogUrl || currentStagingUrl || window.location.origin);

  if (imgEl && imgFallback) {
    if (image) {
      imgEl.src = image;
      imgEl.style.display = '';
      imgFallback.style.display = 'none';
      imgEl.onerror = () => {
        imgEl.style.display = 'none';
        imgFallback.style.display = '';
        imgFallback.textContent = 'Image unavailable';
      };
    } else {
      imgEl.style.display = 'none';
      imgEl.removeAttribute('src');
      imgFallback.style.display = '';
      imgFallback.textContent = 'No image';
    }
  }
}

function toggleStagingMetadataPanel() {
  stagingMetadataPanelOpen = !stagingMetadataPanelOpen;
  const panel = _metaInput('stagingMetaPanel');
  const btn = _metaInput('stagingMetaBtn');
  if (panel) panel.style.display = stagingMetadataPanelOpen ? 'flex' : 'none';
  if (btn) btn.style.background = stagingMetadataPanelOpen ? 'rgba(16,185,129,.2)' : '';
  if (stagingMetadataPanelOpen) {
    loadStagingMetadataFromPreview();
    setTimeout(() => {
      panel?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      _metaInput('metaTitleInput')?.focus();
    }, 40);
    toast('Metadata editor opened below the top toolbar');
  } else {
    toast('Metadata editor hidden');
  }
}

function loadStagingMetadataFromPreview() {
  const frame = document.getElementById('stagingIframe');
  const hint = _metaInput('stagingMetaHint');
  if (!frame || !frame.contentDocument) {
    _setStagingMetadataEnabled(false);
    if (hint) hint.textContent = 'Load a staged page to edit metadata.';
    return;
  }
  const doc = frame.contentDocument;
  const meta = _extractStagingMetadata(doc);
  const title = meta.title || '';
  const description = meta.description || meta.ogDescription || meta.twitterDescription || '';
  const image = meta.ogImage || meta.twitterImage || '';

  const titleInput = _metaInput('metaTitleInput');
  const urlInput = _metaInput('metaOgUrlInput');
  const descInput = _metaInput('metaDescriptionInput');
  const imageInput = _metaInput('metaImageInput');
  const cardInput = _metaInput('metaTwitterCardInput');
  const presetSel = _metaInput('metaPresetSelect');
  const presetCustom = _metaInput('metaPresetCustomInput');

  if (titleInput) titleInput.value = title;
  if (urlInput) urlInput.value = meta.ogUrl || '';
  if (descInput) descInput.value = description;
  if (imageInput) imageInput.value = image;
  if (cardInput) cardInput.value = meta.twitterCard || 'summary_large_image';
  if (presetSel) presetSel.value = '';
  if (presetCustom) presetCustom.value = '';
  _metadataBaseline = {
    title: title,
    description: description,
  };

  _setStagingMetadataEnabled(true);
  _wireMetadataGuideListeners();
  refreshStagingMetaImagePreview();
  _updateMetadataGuides();
  refreshMetadataLiveCard();
  if (hint) hint.textContent = 'Edit fields, apply to preview, then click Save Changes.';
}

function _setMetaTag(doc, attr, key, content) {
  const selector = `meta[${attr}="${key}"]`;
  let node = doc.querySelector(selector);
  const value = String(content || '').trim();
  if (!value) {
    if (node) node.remove();
    return;
  }
  if (!node) {
    node = doc.createElement('meta');
    node.setAttribute(attr, key);
    doc.head.appendChild(node);
  }
  node.setAttribute('content', value);
}

function _bestAboutParagraph(doc) {
  const candidates = [
    ...doc.querySelectorAll('#about-us p, #about p, section[id*="about"] p, .about p, .about-section p'),
  ].map(el => (el.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
  if (!candidates.length) return '';
  const preferred = candidates.find(t => t.length >= 80 && t.length <= 220);
  return preferred || candidates.sort((a, b) => b.length - a.length)[0] || '';
}

function _bestHeadline(doc) {
  const h = doc.querySelector('h1, header h2, .hero h1, .hero h2');
  return (h?.textContent || '').replace(/\s+/g, ' ').trim();
}

function _bestLocationText(doc) {
  const el = doc.querySelector('[class*="address"], [id*="address"], [class*="location"], [id*="location"]');
  const txt = (el?.textContent || '').replace(/\s+/g, ' ').trim();
  return txt.length > 120 ? txt.slice(0, 120).trim() : txt;
}

function _toAbsoluteMetaUrl(raw, frameUrl) {
  const val = String(raw || '').trim();
  if (!val) return '';
  try {
    return new URL(val, frameUrl || window.location.origin).href;
  } catch (_) {
    return val;
  }
}

function autofillMetadataFromAbout() {
  const frame = document.getElementById('stagingIframe');
  if (!frame || !frame.contentDocument) {
    toast('Preview not loaded', false);
    return;
  }
  const text = _bestAboutParagraph(frame.contentDocument);
  if (!text) {
    toast('No About text found in this page', false);
    return;
  }
  const descInput = _metaInput('metaDescriptionInput');
  if (descInput) descInput.value = _truncateSmart(text, 160);
  _updateMetadataGuides();
  toast('Description filled from About section');
}

function autofillMetadataImageFromHero() {
  const frame = document.getElementById('stagingIframe');
  if (!frame || !frame.contentDocument) {
    toast('Preview not loaded', false);
    return;
  }
  const doc = frame.contentDocument;
  const heroImg = doc.querySelector('header img, .hero img, section.hero img, [class*="hero"] img');
  const firstImg = doc.querySelector('img');
  const src = (heroImg?.getAttribute('src') || firstImg?.getAttribute('src') || '').trim();
  if (!src) {
    toast('No image found in this page', false);
    return;
  }
  const imageInput = _metaInput('metaImageInput');
  if (imageInput) imageInput.value = _toAbsoluteMetaUrl(src, frame.src);
  refreshStagingMetaImagePreview();
  _updateMetadataGuides();
  toast('Image filled from page media');
}

function applyMetadataPreset() {
  const preset = (_metaInput('metaPresetSelect')?.value || '').trim();
  const customPreset = (_metaInput('metaPresetCustomInput')?.value || '').trim();
  const titleInput = _metaInput('metaTitleInput');
  const descInput = _metaInput('metaDescriptionInput');
  const baseTitle = _stripPresetSuffixesTitle((titleInput?.value || '').trim());
  const baseDesc = _stripPresetSuffixesDescription((descInput?.value || '').trim());

  if (!preset && !customPreset) {
    toast('Preset is optional. Select one or enter custom text.', false);
    return;
  }

  const variants = {
    balanced: {
      title: baseTitle,
      description: baseDesc,
    },
    sales: {
      title: baseTitle ? `${baseTitle} | Trusted Solutions` : baseTitle,
      description: baseDesc ? `${baseDesc} Contact us today for expert guidance and fast support.` : baseDesc,
    },
    trust: {
      title: baseTitle ? `${baseTitle} | Reliable Since 2010` : baseTitle,
      description: baseDesc ? `${baseDesc} Trusted quality, experienced team, and consistent service delivery.` : baseDesc,
    },
    local: {
      title: baseTitle ? `${baseTitle} | Local Service Experts` : baseTitle,
      description: baseDesc,
    },
  };

  const selected = variants[preset] || variants.balanced;
  let nextTitle = selected.title || baseTitle;
  let nextDesc = selected.description || baseDesc;

  if (customPreset) {
    nextTitle = _appendUniqueChunk(_stripPresetSuffixesTitle(nextTitle), customPreset, ' | ');
    nextDesc = _appendUniqueChunk(_stripPresetSuffixesDescription(nextDesc), customPreset, ' ');
  }

  if (titleInput) titleInput.value = _truncateSmart(nextTitle, 60);
  if (descInput) descInput.value = _truncateSmart(nextDesc, 160);
  _updateMetadataGuides();
  toast('Optional preset applied');
}

function resetMetadataPresetEffects() {
  const titleInput = _metaInput('metaTitleInput');
  const descInput = _metaInput('metaDescriptionInput');
  const presetSel = _metaInput('metaPresetSelect');
  const presetCustom = _metaInput('metaPresetCustomInput');

  const hasBaseline = String(_metadataBaseline.title || _metadataBaseline.description || '').trim().length > 0;
  if (!hasBaseline) {
    toast('No baseline metadata found. Use Reload Metadata first.', false);
    return;
  }

  if (titleInput) titleInput.value = String(_metadataBaseline.title || '');
  if (descInput) descInput.value = String(_metadataBaseline.description || '');
  if (presetSel) presetSel.value = '';
  if (presetCustom) presetCustom.value = '';

  _updateMetadataGuides();
  toast('Preset effects reset to last loaded metadata');
}

function applyMetadataSmartDefaults() {
  const frame = document.getElementById('stagingIframe');
  if (!frame || !frame.contentDocument) {
    toast('Preview not loaded', false);
    return;
  }
  const doc = frame.contentDocument;
  const titleInput = _metaInput('metaTitleInput');
  const descInput = _metaInput('metaDescriptionInput');
  const imageInput = _metaInput('metaImageInput');
  const urlInput = _metaInput('metaOgUrlInput');

  const headline = _bestHeadline(doc);
  const about = _bestAboutParagraph(doc);
  const location = _bestLocationText(doc);

  if (titleInput && !String(titleInput.value || '').trim()) {
    titleInput.value = _truncateSmart(headline || (doc.querySelector('title')?.textContent || ''), 60);
  }

  if (descInput && !String(descInput.value || '').trim()) {
    const source = about || headline;
    const enriched = location ? `${source} Serving ${location}.` : source;
    descInput.value = _truncateSmart(enriched, 160);
  }

  if (imageInput && !String(imageInput.value || '').trim()) {
    const heroImg = doc.querySelector('header img, .hero img, section.hero img, [class*="hero"] img, img');
    const src = (heroImg?.getAttribute('src') || '').trim();
    if (src) imageInput.value = _toAbsoluteMetaUrl(src, frame.src);
  }

  if (urlInput && !String(urlInput.value || '').trim()) {
    const clean = String(frame.src || '').split('?')[0].split('#')[0];
    urlInput.value = clean || window.location.origin;
  }

  refreshStagingMetaImagePreview();
  _updateMetadataGuides();
  toast('Smart defaults applied');
}

function applyStagingMetadata() {
  const frame = document.getElementById('stagingIframe');
  if (!frame || !frame.contentDocument) {
    toast('Preview not loaded', false);
    return;
  }
  const doc = frame.contentDocument;
  const title = (_metaInput('metaTitleInput')?.value || '').trim();
  const description = (_metaInput('metaDescriptionInput')?.value || '').trim();
  const ogUrlRaw = (_metaInput('metaOgUrlInput')?.value || '').trim();
  const imageRaw = (_metaInput('metaImageInput')?.value || '').trim();
  const twitterCard = (_metaInput('metaTwitterCardInput')?.value || 'summary_large_image').trim();

  _historyPush();

  if (!doc.querySelector('title')) {
    const t = doc.createElement('title');
    doc.head.appendChild(t);
  }
  doc.querySelector('title').textContent = title || doc.querySelector('title').textContent || '';

  _setMetaTag(doc, 'name', 'description', description);
  _setMetaTag(doc, 'property', 'og:type', 'website');
  _setMetaTag(doc, 'property', 'og:title', title);
  _setMetaTag(doc, 'property', 'og:description', description);
  _setMetaTag(doc, 'property', 'og:url', _toAbsoluteMetaUrl(ogUrlRaw, frame.src));
  _setMetaTag(doc, 'property', 'og:image', _toAbsoluteMetaUrl(imageRaw, frame.src));
  _setMetaTag(doc, 'name', 'twitter:card', twitterCard || 'summary_large_image');
  _setMetaTag(doc, 'name', 'twitter:title', title);
  _setMetaTag(doc, 'name', 'twitter:description', description);
  _setMetaTag(doc, 'name', 'twitter:image', _toAbsoluteMetaUrl(imageRaw, frame.src));

  const hint = _metaInput('stagingMetaHint');
  if (hint) hint.textContent = 'Metadata applied to preview. Click Save Changes to persist.';
  refreshStagingMetaImagePreview();
  _updateMetadataGuides();
  document.getElementById('stagingStatusBar').textContent = 'Metadata updated in preview — click Save Changes to persist.';
  toast('Metadata applied to preview');
}

function _cacheBustUrl(url) {
  const base = String(url || '').trim();
  if (!base) return '';
  return `${base.split('?')[0]}?t=${Date.now()}`;
}

function _normalizeStagingPagePath(rawPath) {
  let p = String(rawPath || '').trim().replace(/\\/g, '/');
  p = p.replace(/^\/+/, '');
  p = p.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9._/-]/g, '-').replace(/-+/g, '-');
  p = p.split('/').filter(seg => seg && seg !== '.' && seg !== '..').join('/');
  if (!p) return '';
  if (!/\.html?$/i.test(p)) p += '.html';
  return p;
}

function _pageDisplayNameFromPath(pagePath) {
  const p = String(pagePath || '').trim().replace(/^\/+/, '');
  if (!p) return 'Page';
  if (p.toLowerCase() === 'index.html') return 'Home';
  const tail = p.split('/').pop() || p;
  const stem = tail.replace(/\.html?$/i, '');
  const pretty = stem.replace(/[-_]+/g, ' ').trim();
  if (!pretty) return 'Page';
  return pretty.replace(/\b\w/g, c => c.toUpperCase());
}

function _entryPathFromPageName(rawName) {
  let name = String(rawName || '').trim();
  name = name.replace(/\.html?$/i, '');
  name = name.replace(/[\\/]+/g, ' ');
  name = name.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9._-]/g, '-').replace(/-+/g, '-');
  name = name.replace(/^-+|-+$/g, '');
  if (!name) name = 'new-page';
  return `pages/${name}.html`;
}

function _stagingHtmlPages(artifacts, fallbackEntry = 'index.html') {
  const pages = new Set();
  (artifacts || []).forEach(a => {
    const p = String(a || '').trim().replace(/^\/+/, '');
    if (!/\.html?$/i.test(p)) return;
    // Partials are shared include fragments, not top-level editable pages.
    if (/^partials\//i.test(p) || /\/partials\//i.test(p)) return;
    pages.add(p);
  });
  const fallback = String(fallbackEntry || '').trim().replace(/^\/+/, '');
  if (fallback && /\.html?$/i.test(fallback)) pages.add(fallback);
  if (!pages.size) pages.add('index.html');
  return Array.from(pages).sort((a, b) => a.localeCompare(b));
}

function _renderStagingPagePicker(selectedPath) {
  const sel = document.getElementById('stagingPageSelect');
  const addBtn = document.getElementById('stagingAddPageBtn');
  const setHomeBtn = document.getElementById('stagingSetHomeBtn');
  if (!sel || !addBtn || !setHomeBtn) return;

  const pages = _stagingHtmlPages(currentStagingArtifacts, currentStagingEntryPath);
  const selected = String(selectedPath || currentStagingEntryPath || pages[0] || 'index.html').trim();
  const home = String(currentStagingHomeEntryPath || '').trim();
  sel.innerHTML = pages.map(p => `<option value="${_esc(p)}">${_esc(_pageDisplayNameFromPath(p))}${p === home ? ' (home)' : ''}</option>`).join('');
  if (selected) sel.value = selected;
  if (!sel.value && pages.length) sel.value = pages[0];

  const hasSite = !!stagedWebsiteId;
  sel.disabled = !hasSite || !pages.length;
  addBtn.disabled = !hasSite;
  setHomeBtn.disabled = !hasSite || !sel.value;
}

function onStagingPageChange() {
  const pageSel = document.getElementById('stagingPageSelect');
  const path = String(pageSel?.value || '').trim();
  if (!stagedWebsiteId || !path) return;
  loadStagedSite(stagedWebsiteId, path);
}

let createPageTemplateCatalog = null;
let createPageSelectedTemplateKey = '';

function _templateCardMarkup(t, isSelected = false) {
  const title = _esc(t?.template_name || t?.template_key || 'Template');
  const desc = _esc(t?.description || '');
  const badge = _esc((t?.classification_key || '').replace(/_/g, ' '));
  const base = _esc((t?.base_type || '').replace(/_/g, ' '));
  return `<button data-template-key="${_esc(t?.template_key || '')}" onclick="selectCreatePageTemplate('${_esc(t?.template_key || '')}')"
    style="text-align:left;border:1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'};background:${isSelected ? 'rgba(99,102,241,.16)' : 'rgba(99,102,241,.05)'};border-radius:9px;padding:8px;cursor:pointer;display:grid;gap:5px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">
        <strong style="font-size:.83rem;color:var(--text)">${title}</strong>
        <span style="font-size:.66rem;color:var(--muted);text-transform:uppercase">${base}</span>
      </div>
      <div style="font-size:.75rem;color:var(--muted)">${desc}</div>
      <div style="font-size:.66rem;color:var(--accent)">${badge}</div>
    </button>`;
}

function _renderCreatePageTemplateLists() {
  const recWrap = document.getElementById('createPageRecommendedTemplates');
  const allWrap = document.getElementById('createPageAllTemplates');
  const hint = document.getElementById('createPageTemplateHint');
  const submit = document.getElementById('createPageSubmitBtn');
  if (!recWrap || !allWrap || !hint || !submit) return;
  const rec = Array.isArray(createPageTemplateCatalog?.recommended) ? createPageTemplateCatalog.recommended : [];
  const all = Array.isArray(createPageTemplateCatalog?.all_templates) ? createPageTemplateCatalog.all_templates : [];
  const blank = createPageTemplateCatalog?.blank_template || { template_key: 'blank', template_name: 'Blank Starter Page', description: 'Start from a clean page shell.' };

  recWrap.innerHTML = rec.length
    ? rec.map(t => _templateCardMarkup(t, t.template_key === createPageSelectedTemplateKey)).join('')
    : '<div style="font-size:.76rem;color:var(--muted)">No recommended templates found.</div>';

  const allWithBlank = [blank, ...all];
  allWrap.innerHTML = allWithBlank.map(t => _templateCardMarkup(t, t.template_key === createPageSelectedTemplateKey)).join('');

  if (createPageSelectedTemplateKey) {
    const selected = allWithBlank.find(t => t.template_key === createPageSelectedTemplateKey) || rec.find(t => t.template_key === createPageSelectedTemplateKey);
    hint.textContent = selected ? `${selected.template_name} selected.` : 'Template selected.';
    submit.disabled = false;
  } else {
    hint.textContent = 'Select a template to continue.';
    submit.disabled = true;
  }
}

function selectCreatePageTemplate(templateKey) {
  createPageSelectedTemplateKey = String(templateKey || '').trim();
  _renderCreatePageTemplateLists();
}

async function openCreatePageModal() {
  if (!stagedWebsiteId) {
    toast('Select a website first', false);
    return;
  }
  const catalog = await apiFetch(`/websites/${stagedWebsiteId}/page-templates`);
  if (!catalog) {
    toast('Failed to load templates', false);
    return;
  }
  createPageTemplateCatalog = catalog;
  createPageSelectedTemplateKey = '';
  const nameEl = document.getElementById('createPageName');
  const classEl = document.getElementById('createPageClassification');
  const conflictEl = document.getElementById('createPageConflictMode');
  const keepHeader = document.getElementById('createPageRetainHeader');
  const keepMenu = document.getElementById('createPageRetainMenu');
  const keepFooter = document.getElementById('createPageRetainFooter');
  if (nameEl) nameEl.value = 'New Page';
  if (classEl) classEl.value = String(catalog.classification || 'generic').replace(/_/g, ' ');
  if (conflictEl) conflictEl.value = 'overwrite';
  if (keepHeader) keepHeader.checked = true;
  if (keepMenu) keepMenu.checked = true;
  if (keepFooter) keepFooter.checked = true;
  _renderCreatePageTemplateLists();
  const modal = document.getElementById('createPageModal');
  if (modal) modal.style.display = 'flex';
}

function closeCreatePageModal() {
  const modal = document.getElementById('createPageModal');
  if (modal) modal.style.display = 'none';
  createPageTemplateCatalog = null;
  createPageSelectedTemplateKey = '';
}

async function submitCreatePage() {
  if (!stagedWebsiteId) return;
  const pageNameRaw = document.getElementById('createPageName')?.value || '';
  const entryPath = _entryPathFromPageName(pageNameRaw);
  if (!entryPath) {
    toast('Enter a valid page name', false);
    return;
  }
  if (!createPageSelectedTemplateKey) {
    toast('Choose a template first', false);
    return;
  }

  const conflictMode = document.getElementById('createPageConflictMode')?.value || 'overwrite';
  const retainHeader = !!document.getElementById('createPageRetainHeader')?.checked;
  const retainMenu = !!document.getElementById('createPageRetainMenu')?.checked;
  const retainFooter = !!document.getElementById('createPageRetainFooter')?.checked;
  const submitBtn = document.getElementById('createPageSubmitBtn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';
  }

  const r = await apiFetch(`/websites/${stagedWebsiteId}/pages/create`, {
    method: 'POST',
    body: JSON.stringify({
      entry_path: entryPath,
      template_key: createPageSelectedTemplateKey,
      conflict_mode: conflictMode,
      retain_header: retainHeader,
      retain_menu: retainMenu,
      retain_footer: retainFooter,
      expected_manifest_etag: currentStagingManifestEtag || undefined,
    }),
  });

  if (submitBtn) {
    submitBtn.textContent = 'Create Page';
    submitBtn.disabled = false;
  }

  if (r && r.saved) {
    const createdPath = r.entry_path || entryPath;
    toast(`Page created: ${_pageDisplayNameFromPath(createdPath)}`);
    currentStagingManifestEtag = String(r?.staging?.manifest_etag || '').trim();
    currentStagingArtifacts = Array.isArray(r?.staging?.artifacts) ? r.staging.artifacts : currentStagingArtifacts;
    closeCreatePageModal();
    await loadStagedSite(stagedWebsiteId, createdPath);
  } else {
    const err = String(apiFetch._lastError || '');
    if (err.toLowerCase().includes('manifest changed since last load')) {
      toast('Staging changed elsewhere. Refresh and retry creating the page.', false);
    } else {
      toast('Failed to create page', false);
    }
  }
}

async function setStagingHomePage() {
  if (!stagedWebsiteId) {
    toast('Select a website first', false);
    return;
  }
  const pageSel = document.getElementById('stagingPageSelect');
  const entryPath = String(pageSel?.value || '').trim();
  const pageLabel = _pageDisplayNameFromPath(entryPath);
  if (!entryPath) {
    toast('Select a page first', false);
    return;
  }

  if (!(await styledConfirm(`Set ${pageLabel} as the default home page for this website?`, {
    title: 'Set Home Page?',
    icon: '🏠',
    okLabel: 'Set Home',
    okClass: 'btn-primary',
  }))) return;

  const r = await apiFetch(`/websites/${stagedWebsiteId}/staged-home`, {
    method: 'POST',
    body: JSON.stringify({
      entry_path: entryPath,
      expected_manifest_etag: currentStagingManifestEtag || undefined,
    }),
  });

  if (r && r.saved) {
    currentStagingManifestEtag = String(r?.staging?.manifest_etag || '').trim();
    currentStagingHomeEntryPath = (r?.staging?.entry_html || entryPath).trim();
    currentStagingArtifactCount = Number(r?.staging?.artifact_count) || currentStagingArtifactCount;
    currentStagingArtifacts = Array.isArray(r?.staging?.artifacts) ? r.staging.artifacts : currentStagingArtifacts;
    _renderStagingPagePicker(currentStagingEntryPath);
    _renderStagingSummary((websites || []).find(x => x.website_id === stagedWebsiteId), r?.staging || null, currentStagingUrl);
    toast(`Home page set to ${_pageDisplayNameFromPath(currentStagingHomeEntryPath)}`);
  } else {
    const err = String(apiFetch._lastError || '');
    if (err.toLowerCase().includes('manifest changed since last load')) {
      toast('Staging changed elsewhere. Refresh and retry setting home page.', false);
    } else {
      toast('Failed to set home page', false);
    }
  }
}

async function loadBuildNarrative(websiteId) {
  const card = document.getElementById('stagingNarrativeCard');
  const meta = document.getElementById('stagingNarrativeMeta');
  const body = document.getElementById('stagingNarrativeBody');
  const badge = document.getElementById('stagingNarrativeBadge');
  const badgeText = document.getElementById('stagingNarrativeBadgeText');
  const classifBox = document.getElementById('stagingNarrativeClassification');
  const classifKey = document.getElementById('stagingNarrativeClassKey');
  const classifLabel = document.getElementById('stagingNarrativeClassLabel');
  const classifGroup = document.getElementById('stagingNarrativeClassGroup');
  if (!card || !meta || !body || !badge || !badgeText) return;

  if (!websiteId) {
    card.style.display = 'none';
    return;
  }

  card.style.display = '';
  meta.textContent = 'Loading narrative…';
  body.textContent = 'Fetching post-build diagnostics…';
  badge.textContent = '⌛ Evaluating';
  badge.style.color = 'var(--muted)';
  badge.style.borderColor = 'var(--border)';
  badge.style.background = 'rgba(99,102,241,.08)';
  badgeText.textContent = '';

  const res = await apiFetch(`/websites/${websiteId}/build-narrative`);
  if (!res || !res.narrative) {
    meta.textContent = 'Narrative unavailable';
    body.textContent = apiFetch._lastError || 'No narrative details available yet.';
    badge.textContent = '⚠️ Unavailable';
    badge.style.color = '#f59e0b';
    badge.style.borderColor = '#f59e0b';
    badge.style.background = 'rgba(245,158,11,.12)';
    badgeText.textContent = 'Could not compute quality summary for this build.';
    if (classifBox) classifBox.style.display = 'none';
    return;
  }

  const n = res.narrative || {};
  const checks = Array.isArray(n.checks) ? n.checks : [];
  const canDo = Array.isArray(n.can_do) ? n.can_do : [];
  const cannotDo = Array.isArray(n.cannot_do) ? n.cannot_do : [];
  const expected = Array.isArray(n.user_expected_inputs) ? n.user_expected_inputs : [];
  const inputs = n.inputs_used || {};

  const checkByName = (name) => checks.find(c => String(c.name || '').toLowerCase() === name.toLowerCase());
  const refCheck = checkByName('Reference Data Richness');
  const warnCount = checks.filter(c => String(c.status || '').toLowerCase() === 'warning').length;
  const errCount = checks.filter(c => ['error', 'fail', 'failed'].includes(String(c.status || '').toLowerCase())).length;

  if (errCount > 0 || (refCheck && String(refCheck.status || '').toLowerCase() === 'warning' && warnCount >= 2)) {
    badge.textContent = '❌ Sparse Inputs';
    badge.style.color = '#ef4444';
    badge.style.borderColor = '#ef4444';
    badge.style.background = 'rgba(239,68,68,.12)';
    badgeText.textContent = 'High drift risk. Add richer references and explicit product/category details.';
  } else if (warnCount > 0 || (refCheck && String(refCheck.status || '').toLowerCase() === 'warning')) {
    badge.textContent = '⚠️ Partial Quality';
    badge.style.color = '#f59e0b';
    badge.style.borderColor = '#f59e0b';
    badge.style.background = 'rgba(245,158,11,.12)';
    badgeText.textContent = 'Usable with caution. Improve references for stronger domain relevance.';
  } else {
    badge.textContent = '✅ Good Quality';
    badge.style.color = '#16a34a';
    badge.style.borderColor = '#16a34a';
    badge.style.background = 'rgba(22,163,74,.12)';
    badgeText.textContent = 'Inputs and extracted context look healthy for generation.';
  }

  // Populate classification display
  if (classifBox && inputs.classification) {
    classifBox.style.display = '';
    classifKey.textContent = inputs.classification || '—';
    classifLabel.textContent = inputs.classification_label || '—';
    classifGroup.textContent = inputs.classification_group || '—';
  } else if (classifBox) {
    classifBox.style.display = 'none';
  }

  const lines = [];
  lines.push('Summary');
  lines.push(`- ${n.summary || 'No summary provided.'}`);
  lines.push('');
  lines.push('Inputs Used');
  lines.push(`- Build mode: ${inputs.build_mode || '-'}`);
  lines.push(`- Classification: ${inputs.classification || '-'} (${inputs.classification_label || '-'})`);
  lines.push(`- Classification Group: ${inputs.classification_group || '-'}`);
  lines.push(`- Requirements: ${inputs.requirements || '-'}`);
  lines.push(`- Reference URLs: ${Array.isArray(inputs.reference_urls) ? inputs.reference_urls.join(', ') : '-'}`);
  lines.push(`- Web search: ${inputs.use_web_search ? 'enabled' : 'disabled'}`);
  lines.push(`- Social search: ${inputs.use_social_search ? 'enabled' : 'disabled'}`);
  lines.push('');
  lines.push('Checks');
  checks.forEach(c => {
    lines.push(`- [${String(c.status || 'info').toUpperCase()}] ${c.name || 'Check'}`);
    lines.push(`  ${c.details || ''}`);
  });
  if (!checks.length) lines.push('- No checks recorded.');

  lines.push('');
  lines.push('What Agentic AI Can Do');
  canDo.forEach(v => lines.push(`- ${v}`));
  if (!canDo.length) lines.push('- No explicit capabilities listed.');

  lines.push('');
  lines.push('What It Cannot Reliably Do');
  cannotDo.forEach(v => lines.push(`- ${v}`));
  if (!cannotDo.length) lines.push('- No explicit limitations listed.');

  lines.push('');
  lines.push('Expected From User For Better Output');
  expected.forEach(v => lines.push(`- ${v}`));
  if (!expected.length) lines.push('- No explicit user expectations listed.');

  meta.textContent = `Generated: ${n.generated_at || 'unknown'}`;
  body.textContent = lines.join('\n');
}

function _normStatus(v) {
  return String(v || '').trim().toLowerCase();
}

function _previewUrlFromLocalPath(localPath, entryPath = 'index.html') {
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
  const entry = String(entryPath || 'index.html').trim().replace(/^\/+/, '');
  return `/output/${clean}/${entry || 'index.html'}`;
}

function _renderStagingSummary(w, staging, previewUrl) {
  const statusBar = document.getElementById('stagingStatusBar');
  if (!statusBar) return;

  const parts = [];
  if (previewUrl) parts.push(`Preview: ${previewUrl}`);
  if (currentStagingEntryPath) parts.push(`Editing: ${_pageDisplayNameFromPath(currentStagingEntryPath)}`);
  if (currentStagingHomeEntryPath) parts.push(`Home: ${_pageDisplayNameFromPath(currentStagingHomeEntryPath)}`);
  if (Number.isFinite(Number(staging?.artifact_count))) {
    parts.push(`${Number(staging.artifact_count)} artifact(s)`);
  } else if (Number.isFinite(Number(currentStagingArtifactCount)) && currentStagingArtifactCount > 0) {
    parts.push(`${currentStagingArtifactCount} artifact(s)`);
  }
  if (w && (w.status || w.build_status)) {
    parts.push(`State: ${_normStatus(w.status || w.build_status) || 'draft'}`);
  }
  statusBar.textContent = parts.join(' • ') || 'Staging ready.';
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

  if (!cur) {
    stagedWebsiteId = null;
    currentStagingHomeEntryPath = 'index.html';
    currentStagingHtmlHash = '';
    currentStagingManifestEtag = '';
    _setStagingMetadataEnabled(false);
    const metaHint = _metaInput('stagingMetaHint');
    if (metaHint) metaHint.textContent = 'Load a staged page to edit metadata.';
    _renderStagingPagePicker('');
  }

  // Re-load if a site was already selected
  if (cur && eligible.find(w => w.website_id === cur)) loadStagedSite(cur);
}

async function loadStagedSite(preselect, entryPathOverride = null) {
  const id = preselect || document.getElementById('stagingSiteSelect').value;
  if (preselect) {
    const sel = document.getElementById('stagingSiteSelect');
    if (sel) sel.value = preselect;
  }
  if (!id) return;
  stagedWebsiteId = id;
  loadBuildNarrative(id);

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

  let staging = null;
  try {
    const stagedRes = await apiFetch(`/websites/${id}/staged-html`);
    staging = stagedRes && stagedRes.staging ? stagedRes.staging : null;
    currentStagingHtmlHash = String(stagedRes?.html_hash || '').trim();
    currentStagingManifestEtag = String(stagedRes?.staging?.manifest_etag || '').trim();
  } catch (_) {
    staging = null;
    currentStagingHtmlHash = '';
    currentStagingManifestEtag = '';
  }

  const homeEntry = ((staging && staging.entry_html) || 'index.html');
  currentStagingHomeEntryPath = String(homeEntry || 'index.html').trim().replace(/^\/+/, '') || 'index.html';
  const forcedEntry = String(entryPathOverride || '').trim().replace(/^\/+/, '');
  currentStagingEntryPath = forcedEntry || currentStagingHomeEntryPath;
  currentStagingArtifactCount = Number(staging && staging.artifact_count) || 0;
  currentStagingArtifacts = Array.isArray(staging && staging.artifacts) ? staging.artifacts : [];
  _renderStagingPagePicker(currentStagingEntryPath);

  // Derive preview URL from local_path
  let previewUrl = null;
  if (w) {
    previewUrl = _previewUrlFromLocalPath(w.local_path, currentStagingEntryPath);
    if (!previewUrl && w.name) {
      const slug = w.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/, '');
      previewUrl = `/output/staging/${slug}/${currentStagingEntryPath || 'index.html'}`;
    }
  }

  // Update status badge
  const badge = document.getElementById('stagingStatusBadge');
  if (badge) badge.innerHTML = w ? statusBadge(w.status, w.build_status) : '';

  // Load iframe
  const frame = document.getElementById('stagingIframe');
  const placeholder = document.getElementById('stagingPlaceholder');
  if (previewUrl) {
    currentStagingUrl = previewUrl;
    stagingOverlayOn = false;
    stagingSections = [];
    activeSectionIndex = null;
    _anchorsVisible = true;
    const editBtn = document.getElementById('stagingEditBtn');
    if (editBtn) { editBtn.textContent = '🔢 Section Numbers'; editBtn.style.background = ''; }
    const anchorBtn = document.getElementById('stagingAnchorBtn');
    if (anchorBtn) { anchorBtn.textContent = '⚓ Anchors'; anchorBtn.style.opacity = ''; }
    document.getElementById('secEditor').style.display = 'none';
    document.getElementById('secList').style.display = '';
    frame.onload = () => {
      loading.style.display = 'none';
      // Snapshot original state for Reset
      try {
        if (frame.contentDocument) {
          _injectResponsiveEnhancements(frame.contentDocument);
          _ensureMediaCardCarouselRuntime(frame.contentDocument);
          frame.contentDocument.defaultView?.wbMediaCardCarouselInitAll?.(frame.contentDocument);
          _originalHTML = frame.contentDocument.documentElement.outerHTML;
          _historyStack = [];
          _updateUndoBtn();
          // Rebuild section bindings after any iframe reload (save/refresh/popout source changes)
          // so reorder/delete never points to stale DOM nodes.
          if (stagingOverlayOn) {
            _injectOverlay(frame.contentDocument);
          } else {
            stagingSections = [];
            const secList = document.getElementById('secList');
            if (secList) secList.innerHTML = '';
            const jump = document.getElementById('stagingJumpSelect');
            if (jump) jump.innerHTML = '<option value="">— jump to section —</option>';
          }
          loadStagingMetadataFromPreview();
        }
      } catch(_) {}
    };
      frame.src = _cacheBustUrl(previewUrl);
    frame.style.display = '';
    placeholder.style.display = 'none';
    _renderStagingSummary(w, staging, previewUrl);
  } else {
    loading.style.display = 'none';
    placeholder.style.display = 'flex';
    frame.style.display = 'none';
    _setStagingMetadataEnabled(false);
    const metaHint = _metaInput('stagingMetaHint');
    if (metaHint) metaHint.textContent = 'No preview found for this website yet.';
    document.getElementById('stagingStatusBar').textContent = 'No built output found for this website.';
  }

  // Enable controls
  ['stagingEditBtn', 'stagingFontBtn', 'stagingMetaBtn', 'stagingMediaBtn', 'stagingAddSecBtn', 'stagingUndoBtn', 'stagingResetBtn', 'stagingPopoutBtn', 'stagingRefreshBtn', 'stagingSaveBtn', 'stagingGoLiveBtn', 'stagingAnchorBtn', 'stagingAddPageBtn', 'stagingSetHomeBtn'].forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = false;
  });
  const pageSel = document.getElementById('stagingPageSelect');
  if (pageSel) pageSel.disabled = false;

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

async function historyReset() {
  if (!_originalHTML) { toast('No original snapshot available', false); return; }
  if (!(await styledConfirm('Reset all edits and return to the original loaded state?', {
    title: 'Reset All Edits?',
    icon: '↺',
    okLabel: 'Reset',
    okClass: 'btn-danger',
  }))) return;
  _historyStack = [];
  _restoreSnapshot(_originalHTML);
  toast('Reset to original', true);
}

/* Inject numbered badges into the iframe and listen for clicks via postMessage */
function _injectOverlay(doc) {
  // Remove any prior overlay
  doc.querySelectorAll('.__wb_badge').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_badge_anchor').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_hi').forEach(n => {
    n.style.outline = '';
    n.classList.remove('__wb_hi');
  });

  // Query ALL structural elements in a single call so they come back in DOM order
  const LABEL_MAP = { NAV: 'Navigation / Menu', HEADER: 'Header', SECTION: 'Section', FOOTER: 'Footer' };

  const slugify = (value) => String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  const ensureSectionId = (el, index, label) => {
    if (el.id) return el.id;
    const headingText = el.querySelector('h1,h2,h3,h4,h5,h6')?.textContent || '';
    const labelBase = (label || '').replace(/\s*\/\s*/g, ' ').replace(/\s+/g, ' ').trim();
    const base = slugify(headingText) || slugify(labelBase) || `${el.tagName.toLowerCase()}-${index}`;
    let candidate = base;
    let counter = 2;
    while (doc.getElementById(candidate)) {
      candidate = `${base}-${counter}`;
      counter++;
    }
    el.id = candidate;
    return candidate;
  };

  stagingSections = [];
  let idx = 0;

  doc.querySelectorAll('nav, header, section, footer').forEach(el => {
    // Skip elements that are nested inside another tracked element
    if (el.closest('nav, header, section, footer') !== el) return;
    const label = LABEL_MAP[el.tagName] || 'Section';
    // Ensure every section has a stable anchor target for menu links.
    const id = ensureSectionId(el, idx + 1, label);
    const anchor = id ? `#${id}` : '';
    idx++;
    const i = idx;
      stagingSections.push({
        el,
        baseLabel: label,
        anchorId: String(id || '').trim(),
        label: _sectionEntryLabel(i - 1, label, id),
      });

      // Position badge at top-left of element
      el.style.position = el.style.position || 'relative';
      const badge = doc.createElement('button');
      badge.className = '__wb_badge';
      badge.textContent = String(i);
      badge.title = `Edit: ${label}${anchor ? ' ' + anchor : ''}`;
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

      if (anchor) {
        const anchorChip = doc.createElement('button');
        anchorChip.className = '__wb_badge_anchor';
        anchorChip.textContent = anchor;
        anchorChip.title = `Anchor target: ${anchor}`;
        anchorChip.style.cssText = [
          'position:absolute','top:8px','left:40px','z-index:99999',
          'max-width:180px','padding:3px 8px','border-radius:999px',
          'background:rgba(17,24,39,.88)','color:#fff','border:1px solid rgba(255,255,255,.25)',
          'font-size:11px','font-weight:600','cursor:pointer',
          'line-height:1.2','white-space:nowrap','overflow:hidden','text-overflow:ellipsis',
          'box-shadow:0 2px 8px rgba(0,0,0,.35)',
        ].join(';');
        anchorChip.addEventListener('click', (e) => {
          e.stopPropagation();
          window.parent.postMessage({ type: 'wb_section_click', index: i - 1 }, '*');
        });
        el.appendChild(anchorChip);
      }
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
  const srcParent = src ? src.parentNode : null;
  const tgtParent = tgt ? tgt.parentNode : null;
  if (!srcParent || !tgtParent) return;
  // Support reordering across different parent containers (e.g. body vs main).
  if (fromIdx < toIdx) {
    tgtParent.insertBefore(src, tgt.nextSibling);
  } else {
    tgtParent.insertBefore(src, tgt);
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

  const structural = Array.from(
    frame.contentDocument.querySelectorAll('nav, header, section, footer')
  ).filter(el => el.closest('nav, header, section, footer') === el);

  let targetEl = null;
  if (s && s.el && s.el.isConnected) {
    targetEl = s.el;
  } else if (idx >= 0 && idx < structural.length) {
    targetEl = structural[idx];
  }

  if (!targetEl) {
    toast('Unable to delete section: preview changed. Refresh and try again.', false);
    return;
  }

  _historyPush();
  targetEl.remove();
  _injectOverlay(frame.contentDocument);
  if (activeSectionIndex !== null) closeSecEditor();
  toast('Section deleted — click 💾 Save to persist', true);
}

/* ── Section templates for the Add Section modal ── */
const SEC_TEMPLATES = [
  { label: '📝 Text / Content', id: 'text-content', html: (id) => `<section id="${id}" data-wb-sec-template="text-content" style="padding:80px 5%;background:#fff"><div style="max-width:900px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:16px">Section Heading</h2><p style="font-size:1.05rem;line-height:1.8;color:#555">Add your content here. Click ✏️ to edit this section.</p></div></section>` },
  { label: '🖼 Image + Text',   id: 'image-text',   html: (id) => `<section id="${id}" data-wb-sec-template="image-text" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:1100px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center"><div><h2 style="font-size:1.8rem;margin-bottom:16px">Heading</h2><p style="font-size:1rem;line-height:1.8;color:#555">Your description goes here.</p></div><img src="https://placehold.co/600x400" alt="" style="width:100%;border-radius:12px"></div></section>` },
  { label: '🃏 Cards / Grid',   id: 'cards-grid',   html: (id) => `<section id="${id}" data-wb-sec-template="cards-grid" style="padding:80px 5%;background:#fff"><div style="max-width:1100px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:40px">Our Offerings</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px"><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card One</h3><p style="color:#666;font-size:.95rem">Description.</p></div><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card Two</h3><p style="color:#666;font-size:.95rem">Description.</p></div><div style="background:#f5f3ef;border-radius:12px;padding:28px;text-align:center"><h3 style="margin-bottom:10px">Card Three</h3><p style="color:#666;font-size:.95rem">Description.</p></div></div></div></section>` },
  { label: '🖼 Media Card Carousel', id: 'media-card-carousel', html: (id) => `<section id="${id}" data-wb-sec-template="media-card-carousel" style="padding:80px 5%;background:#fff"><div style="max-width:1160px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:12px">Media Showcase</h2><p style="text-align:center;color:#64748b;margin:0 0 24px">Horizontal media cards with aligned image sizing and bottom carousel controls.</p><div style="display:grid;grid-auto-flow:column;grid-auto-columns:minmax(230px,270px);gap:16px;overflow-x:hidden;scroll-snap-type:x mandatory;padding-bottom:8px;scrollbar-width:none"><article id="${id}-item-1" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-1/640/420" alt="Media item 1" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight One</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article><article id="${id}-item-2" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-2/640/420" alt="Media item 2" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight Two</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article><article id="${id}-item-3" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-3/640/420" alt="Media item 3" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight Three</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article><article id="${id}-item-4" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-4/640/420" alt="Media item 4" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight Four</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article><article id="${id}-item-5" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-5/640/420" alt="Media item 5" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight Five</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article><article id="${id}-item-6" style="scroll-snap-align:start;background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px"><img src="https://picsum.photos/seed/${id}-6/640/420" alt="Media item 6" style="width:100%;height:clamp(170px,22vw,260px);object-fit:cover;border-radius:10px"><h3 style="margin:12px 0 6px;font-size:1.05rem">Featured Highlight Six</h3><p style="margin:0;color:#475569;font-size:.92rem;line-height:1.55">Short description for this media card and supporting context.</p></article></div><div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-top:14px"><a href="#${id}-item-1" aria-label="Scroll left" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid #cbd5e1;border-radius:999px;text-decoration:none;color:#0f172a">◀</a><a href="#${id}-item-1" aria-label="Slide 1" style="width:9px;height:9px;background:#2563eb;border-radius:999px;display:inline-block"></a><a href="#${id}-item-2" aria-label="Slide 2" style="width:9px;height:9px;background:#94a3b8;border-radius:999px;display:inline-block"></a><a href="#${id}-item-3" aria-label="Slide 3" style="width:9px;height:9px;background:#94a3b8;border-radius:999px;display:inline-block"></a><a href="#${id}-item-4" aria-label="Slide 4" style="width:9px;height:9px;background:#94a3b8;border-radius:999px;display:inline-block"></a><a href="#${id}-item-5" aria-label="Slide 5" style="width:9px;height:9px;background:#94a3b8;border-radius:999px;display:inline-block"></a><a href="#${id}-item-6" aria-label="Slide 6" style="width:9px;height:9px;background:#94a3b8;border-radius:999px;display:inline-block"></a><a href="#${id}-item-6" aria-label="Scroll right" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid #cbd5e1;border-radius:999px;text-decoration:none;color:#0f172a">▶</a></div></div></section>` },
  { label: '📬 Contact Form',  id: 'contact-form',  html: (id) => `<section id="${id}" data-wb-sec-template="contact-form" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:600px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:24px">Get In Touch</h2><form onsubmit="return false" style="display:flex;flex-direction:column;gap:14px;text-align:left"><input type="text" placeholder="Your name" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem"><input type="email" placeholder="Email address" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem"><textarea placeholder="Your message" rows="4" style="padding:12px 16px;border:1.5px solid #ddd;border-radius:8px;font-size:1rem;resize:vertical"></textarea><button type="submit" style="padding:13px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:700;cursor:pointer">Send Message</button></form></div></section>` },
  { label: '💬 Testimonials',  id: 'testimonials',  html: (id) => `<section id="${id}" data-wb-sec-template="testimonials" style="padding:80px 5%;background:#fff"><div style="max-width:1000px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:40px">What People Say</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px"><div style="background:#f9f7f4;border-radius:12px;padding:28px"><p style="font-style:italic;color:#555;line-height:1.7;margin-bottom:16px">"An excellent experience. Highly recommended!"</p><strong style="font-size:.9rem">— Happy Customer</strong></div><div style="background:#f9f7f4;border-radius:12px;padding:28px"><p style="font-style:italic;color:#555;line-height:1.7;margin-bottom:16px">"Outstanding quality and service."</p><strong style="font-size:.9rem">— Another Customer</strong></div></div></div></section>` },
  { label: '📢 Call to Action', id: 'cta',           html: (id) => `<section id="${id}" data-wb-sec-template="cta" style="padding:80px 5%;text-align:center;background:#6366f1;color:#fff"><div style="max-width:700px;margin:0 auto"><h2 style="font-size:2.2rem;margin-bottom:16px">Ready to Get Started?</h2><p style="opacity:.85;font-size:1.05rem;margin-bottom:32px">Join us today and experience the difference.</p><a href="#contact" style="display:inline-block;padding:14px 36px;background:#fff;color:#6366f1;border-radius:8px;font-weight:700;font-size:1rem;text-decoration:none">Get Started</a></div></section>` },
  { label: '❓ FAQ',            id: 'faq',            html: (id) => `<section id="${id}" data-wb-sec-template="faq" style="padding:80px 5%;background:#f9f7f4"><div style="max-width:800px;margin:0 auto;text-align:center"><h2 style="font-size:2rem;margin-bottom:32px">Frequently Asked Questions</h2><details style="background:#fff;border-radius:8px;padding:16px 20px;text-align:left;margin-bottom:10px"><summary style="font-weight:700;cursor:pointer">Question one?</summary><p style="margin-top:10px;color:#555">Answer goes here.</p></details><details style="background:#fff;border-radius:8px;padding:16px 20px;text-align:left;margin-bottom:10px"><summary style="font-weight:700;cursor:pointer">Question two?</summary><p style="margin-top:10px;color:#555">Answer goes here.</p></details></div></section>` },
  { label: '🖼 Gallery',        id: 'gallery',        html: (id) => `<section id="${id}" data-wb-sec-template="gallery" style="padding:80px 5%;background:#fff"><div style="max-width:1100px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:40px">Gallery</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"><img src="https://placehold.co/400x300" alt="" style="width:100%;border-radius:10px"></div></div></section>` },
  { label: '🧩 Photo Mosaic Mix', id: 'photo-mosaic-mix', html: (id) => `<section id="${id}" data-wb-sec-template="photo-mosaic-mix" data-wb-collage="1" style="padding:80px 5%;background:#fff"><div style="max-width:1120px;margin:0 auto"><h2 style="text-align:center;font-size:2rem;margin-bottom:10px">Photo Mosaic Mix</h2><p style="text-align:center;color:#64748b;margin:0 0 24px">Blend multiple photos in one expressive collage with variable emphasis.</p><div data-wb-collage-grid="1" style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));grid-auto-rows:clamp(70px,9vw,110px);gap:10px"><figure data-wb-collage-item="1" data-wb-collage-weight="4" style="margin:0;grid-column:span 2;grid-row:span 2;border-radius:14px;overflow:hidden;background:#e2e8f0"><img src="https://picsum.photos/seed/${id}-a/920/740" alt="Mosaic highlight" style="width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block"></figure><figure data-wb-collage-item="1" data-wb-collage-weight="2" style="margin:0;grid-column:span 2;grid-row:span 1;border-radius:14px;overflow:hidden;background:#e2e8f0"><img src="https://picsum.photos/seed/${id}-b/920/700" alt="Mosaic frame" style="width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block"></figure><figure data-wb-collage-item="1" data-wb-collage-weight="3" style="margin:0;grid-column:span 1;grid-row:span 2;border-radius:14px;overflow:hidden;background:#e2e8f0"><img src="https://picsum.photos/seed/${id}-c/640/920" alt="Mosaic portrait" style="width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block"></figure><figure data-wb-collage-item="1" data-wb-collage-weight="1" style="margin:0;grid-column:span 1;grid-row:span 1;border-radius:14px;overflow:hidden;background:#e2e8f0"><img src="https://picsum.photos/seed/${id}-d/680/620" alt="Mosaic detail" style="width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block"></figure><figure data-wb-collage-item="1" data-wb-collage-weight="2" style="margin:0;grid-column:span 2;grid-row:span 1;border-radius:14px;overflow:hidden;background:#e2e8f0"><img src="https://picsum.photos/seed/${id}-e/920/680" alt="Mosaic landscape" style="width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block"></figure></div></div></section>` },
];

let _selectedTemplate = null;

function _applyUniformSectionContainerStyle(newEl, refEl) {
  if (!newEl || !refEl) return;
  try {
    const cs = window.getComputedStyle(refEl);
    // Match spacing + container border/shape with existing sections.
    newEl.style.marginTop = cs.marginTop;
    newEl.style.marginBottom = cs.marginBottom;
    newEl.style.paddingTop = cs.paddingTop;
    newEl.style.paddingRight = cs.paddingRight;
    newEl.style.paddingBottom = cs.paddingBottom;
    newEl.style.paddingLeft = cs.paddingLeft;
    newEl.style.borderTop = cs.borderTop;
    newEl.style.borderRight = cs.borderRight;
    newEl.style.borderBottom = cs.borderBottom;
    newEl.style.borderLeft = cs.borderLeft;
    newEl.style.borderRadius = cs.borderRadius;
    newEl.style.boxShadow = cs.boxShadow;
    newEl.style.background = cs.background;
  } catch (_) {}
}

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
  const refEl = (afterIdx >= 0 && stagingSections[afterIdx])
    ? stagingSections[afterIdx].el
    : (stagingSections.find(s => s && s.el && s.el.tagName === 'SECTION') || {}).el;

  if (newEl && newEl.tagName === 'SECTION' && refEl && refEl.tagName === 'SECTION') {
    _applyUniformSectionContainerStyle(newEl, refEl);
  }

  if (afterIdx < 0 || stagingSections.length === 0) {
    doc.body.insertBefore(newEl, doc.body.firstElementChild);
  } else {
    const insertAfter = stagingSections[afterIdx].el;
    insertAfter.parentNode.insertBefore(newEl, insertAfter.nextSibling);
  }
  closeAddSectionModal();
  _injectOverlay(doc);
  // Open editor on newly added section
  const newIdx = stagingSections.findIndex(s => s.el === newEl);
  if (newIdx >= 0) { setTimeout(() => openSecEditor(newIdx), 100); }
  toast('Section added — click 💾 Save to persist', true);
}

let _anchorsVisible = true;

function toggleAnchorVisibility() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument) return;
  _anchorsVisible = !_anchorsVisible;
  frame.contentDocument.querySelectorAll('.__wb_badge_anchor').forEach(n => {
    n.style.display = _anchorsVisible ? '' : 'none';
  });
  const btn = document.getElementById('stagingAnchorBtn');
  if (btn) {
    btn.textContent = _anchorsVisible ? '⚓ Anchors' : '⚓ Anchors (off)';
    btn.style.opacity = _anchorsVisible ? '' : '0.5';
  }
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
  const sectionEntry = stagingSections[idx];
  const { el } = sectionEntry;
  const sectionLabel = _sectionEntryLabel(idx, sectionEntry.baseLabel || 'Section', el.id || sectionEntry.anchorId || '');
  const label = sectionLabel;
  sectionEntry.anchorId = String(el.id || sectionEntry.anchorId || '').trim();
  sectionEntry.label = sectionLabel;

  // Highlight selected section
  frame.contentDocument.querySelectorAll('.__wb_hi').forEach(n => {
    n.style.outline = ''; n.classList.remove('__wb_hi');
  });
  el.style.outline = '3px solid #6366f1';
  el.classList.add('__wb_hi');

  // Scroll iframe section into view
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });

  document.getElementById('secEditorTitle').textContent = sectionLabel;
  const anchorBarEl = document.getElementById('secEditorAnchorBar');
  const anchorInputEl = document.getElementById('secEditorAnchorName');
  const anchorPreviewEl = document.getElementById('secEditorAnchorPreview');
  const currentAnchorId = String(el.id || sectionEntry.anchorId || '').trim();
  const currentAnchorName = String(el.dataset?.wbAnchorName || '').trim() || _friendlyAnchorName(currentAnchorId || sectionEntry.baseLabel || 'section');
  if (anchorBarEl) anchorBarEl.style.display = '';
  if (anchorInputEl) {
    anchorInputEl.value = _sanitizeAnchorFriendlyName(currentAnchorName);
    anchorInputEl.setAttribute('maxlength', '60');
    anchorInputEl.setAttribute('pattern', '[A-Za-z0-9 -]+');
    anchorInputEl.onbeforeinput = (ev) => {
      const t = String(ev?.data || '');
      if (!t) return;
      if (/[^A-Za-z0-9\s-]/.test(t)) ev.preventDefault();
    };
    anchorInputEl.onpaste = (ev) => {
      ev.preventDefault();
      const pasted = ev.clipboardData?.getData('text') || '';
      const sanitized = _sanitizeAnchorFriendlyName(pasted);
      const start = anchorInputEl.selectionStart ?? anchorInputEl.value.length;
      const end = anchorInputEl.selectionEnd ?? anchorInputEl.value.length;
      const combined = `${anchorInputEl.value.slice(0, start)}${sanitized}${anchorInputEl.value.slice(end)}`;
      anchorInputEl.value = _sanitizeAnchorFriendlyName(combined);
      anchorInputEl.dispatchEvent(new Event('input'));
    };
    anchorInputEl.oninput = () => {
      const cleaned = _sanitizeAnchorFriendlyName(anchorInputEl.value || '');
      if (cleaned !== anchorInputEl.value) anchorInputEl.value = cleaned;
      const raw = String(anchorInputEl.value || '').trim();
      const previewId = _slugifyAnchorName(raw || currentAnchorId || `section-${idx + 1}`) || `section-${idx + 1}`;
      if (anchorPreviewEl) anchorPreviewEl.textContent = `#${previewId}`;
    };
    anchorInputEl.oninput();
  }
  const modeNoteEl = document.getElementById('secEditorModeNote');
  const isMediaCardMode = _isMediaCardCarouselSection(el);
  if (modeNoteEl) {
    modeNoteEl.style.display = isMediaCardMode ? '' : 'none';
  }
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
        align:  _normalizeTextAlignValue(domEl.style.textAlign || cs.textAlign || 'left'),
        color:  rawColor ? _rgbToHex(rawColor) : '#111827',
        bold:   (cs.fontWeight >= 600) || domEl.style.fontWeight === 'bold',
        italic: cs.fontStyle === 'italic' || domEl.style.fontStyle === 'italic',
      };
    }

    function _linkInit(domEl) {
      if (!domEl) {
        return {
          bgEnabled: false,
          bgColor: '#111827',
          textColor: '#ffffff',
          hoverEnabled: false,
          hoverBgColor: '#374151',
          hoverTextColor: '#ffffff',
        };
      }
      const cs = iframeView.getComputedStyle(domEl);
      const bgRaw = domEl.style.backgroundColor || cs.backgroundColor || '';
      const textRaw = domEl.style.color || cs.color || '';
      const hasBg = !!bgRaw && bgRaw !== 'rgba(0, 0, 0, 0)' && bgRaw !== 'transparent';
      const bgHex = hasBg ? _rgbToHex(bgRaw) : '#111827';
      const textHex = _rgbToHex(textRaw || '#ffffff');
      return {
        bgEnabled: hasBg,
        bgColor: bgHex,
        textColor: textHex,
        hoverEnabled: false,
        hoverBgColor: _shadeHex(bgHex, -18),
        hoverTextColor: textHex,
      };
    }

    function _imgAnimInit(domEl) {
      const mode = domEl?.dataset?.wbImgAnim || 'none';
      return { mode };
    }

    function _clickInit(domEl) {
      return {
        enabled: domEl?.dataset?.wbClickEnabled === '1',
        url: domEl?.dataset?.wbClickUrl || '',
        mode: domEl?.dataset?.wbClickMode || 'popup',
      };
    }

    function _textWithoutEditorBadges(domEl, opts = {}) {
      if (!domEl) return '';
      const clone = domEl.cloneNode(true);
      clone.querySelectorAll('.__wb_badge, .__wb_badge_anchor').forEach(n => n.remove());
      if (opts.excludeAnchors) clone.querySelectorAll('a').forEach(n => n.remove());
      return (clone.innerText || '').trim();
    }

    function _ensureFooterParagraph(sectionEl) {
      if (!sectionEl) return;
      const _singleLine = (txt) => String(txt || '')
        .replace(/\s*\r?\n+\s*/g, ' ')
        .replace(/\s{2,}/g, ' ')
        .trim();
      const existing = [...sectionEl.querySelectorAll('p')].find((p) => {
        const txt = _singleLine(_textWithoutEditorBadges(p, { excludeAnchors: true }));
        return txt.length >= 2;
      });
      if (existing) {
        existing.dataset.wbFooterText = '1';
        existing.textContent = _singleLine(_textWithoutEditorBadges(existing, { excludeAnchors: true }));
        existing.style.setProperty('white-space', 'normal', 'important');
        return;
      }

      const candidates = [...sectionEl.querySelectorAll('div,span,small,strong,em,b')].filter((node) => {
        const txt = _textWithoutEditorBadges(node, { excludeAnchors: true });
        if (!txt || txt.length < 2 || txt.length > 260) return false;
        if (node.querySelector('a,button,input,select,textarea,table,ul,ol,form')) return false;
        const blockKids = [...node.children].filter(c => ['DIV', 'SECTION', 'ARTICLE', 'TABLE', 'UL', 'OL', 'FORM'].includes(c.tagName));
        if (blockKids.length > 0) return false;
        return true;
      }).sort((a, b) => {
        const aLen = _textWithoutEditorBadges(a, { excludeAnchors: true }).length;
        const bLen = _textWithoutEditorBadges(b, { excludeAnchors: true }).length;
        return bLen - aLen;
      });

      const best = candidates[0] || null;
      if (best) {
        const txt = _singleLine(_textWithoutEditorBadges(best, { excludeAnchors: true }));
        if (!txt) return;
        const p = sectionEl.ownerDocument.createElement('p');
        p.dataset.wbFooterText = '1';
        p.textContent = txt;
        p.style.cssText = best.style.cssText || '';
        p.style.setProperty('white-space', 'normal', 'important');
        best.replaceWith(p);
        return;
      }

      const rootTxt = _singleLine(_textWithoutEditorBadges(sectionEl, { excludeAnchors: true }));
      if (rootTxt && rootTxt.length <= 260 && !sectionEl.querySelector('a')) {
        const p = sectionEl.ownerDocument.createElement('p');
        p.dataset.wbFooterText = '1';
        p.textContent = rootTxt;
        p.style.setProperty('white-space', 'normal', 'important');
        sectionEl.prepend(p);
      }
    }

    // ── Gather editable elements ───────────────────────────────────────────
    // Collect all HTML into one string — avoids O(n²) innerHTML re-parses
    const htmlChunks = [];
    let fieldIdx = 0;
    let allianceMeta = null;
    let gridMeta = null;
    let collageMeta = null;
    let heroMeta = null;
    let sectionBoxMeta = null;
    let sectionAnchorMeta = { target: el };
    const isMediaCardCarousel = _isMediaCardCarouselSection(el);
    const isImageCollage = _isImageCollageSection(el);
    const isFooterSection = (
      String(el.tagName || '').toUpperCase() === 'FOOTER'
      || /footer/i.test(String(el.id || ''))
      || /footer/i.test(String(el.className || ''))
      || /footer/i.test(String(label || ''))
    );
    if (isFooterSection) {
      _ensureFooterParagraph(el);
    }
    const _imgFidToEl = new Map();

    // Metadata to store on fields after single innerHTML set
    let brandEl = null, brandFid = '';

    // Always show Logo / Image + Brand Name only for the first section (nav/header)
    const logo = activeSectionIndex === 0 ? _findSectionLogoTarget(el) : null;
    if (activeSectionIndex === 0) {
      fieldIdx++;
      const logoFid = `img-${fieldIdx}`;
      const logoSrc = logo ? (logo.getAttribute('src') || logo.src || '') : '';
      htmlChunks.push(_imgField(fieldIdx, 'Logo / Image', _normalizeStagingAssetUrl(logoSrc), logo ? logo.alt : '', logoFid, { click: _clickInit(logo) }));
      if (logo) _imgFidToEl.set(logoFid, logo);

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

    // Headings — track each one so _getFidTargets can map by index.
    // For media-card carousel sections, expose only the intro heading above the card rail.
    const _allHeadingEls = [...el.querySelectorAll('h1,h2,h3,h4')].filter(h => h.innerText.trim());
    const _mediaCarouselContainer = isMediaCardCarousel ? _findMediaCardCarouselContainer(el) : null;
    const _headingEls = isMediaCardCarousel
      ? _allHeadingEls.filter(h => !_mediaCarouselContainer || !_mediaCarouselContainer.contains(h)).slice(0, 1)
      : _allHeadingEls;
    const _headingStartField = fieldIdx + 1;
    _headingEls.forEach(h => {
      fieldIdx++;
      const headingTag = isMediaCardCarousel ? 'Carousel Title' : h.tagName;
      htmlChunks.push(_textField(fieldIdx, headingTag, h.innerText.trim(), `txt-${fieldIdx}`, _elInit(h), { clickable: true, clickInit: _clickInit(h) }));
    });

    // Paragraphs — track start field.
    // For media-card carousel sections, expose only the intro paragraph above the card rail.
    const _paraStartField = fieldIdx + 1;
    let _allParaEls = [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3);
    if (isFooterSection) {
      const _footerRootText = _textWithoutEditorBadges(el);
      const _footerTextEls = [...el.querySelectorAll('div,span,small,strong,em,b')].filter((node) => {
        const txt = _textWithoutEditorBadges(node);
        if (!txt || txt.length < 2 || txt.length > 260) return false;
        if (node.closest('a,button,input,select,textarea,script,style,table,thead,tbody,tr,td,th')) return false;
        // Allow light inline children so full footer lines like "© 2026 ..." are editable as one field.
        if (node.querySelector('a,button,input,select,textarea,table,ul,ol,form')) return false;
        const blockKids = [...node.children].filter(c => ['DIV', 'SECTION', 'ARTICLE', 'TABLE', 'UL', 'OL', 'FORM'].includes(c.tagName));
        if (blockKids.length > 0) return false;
        return true;
      });

      const _rootContentChildren = [...el.children].filter((c) => {
        const cls = String(c.className || '');
        if (cls.includes('__wb_badge') || cls.includes('__wb_badge_anchor')) return false;
        return true;
      });

      // Prefer broader line containers and suppress nested leaf duplicates (like year-only span).
      const _footerCandidates = [...new Set([
        ..._allParaEls,
        ..._footerTextEls,
        ...((_footerRootText && _footerRootText.length <= 260 && !el.querySelector('a') && _rootContentChildren.length === 0) ? [el] : []),
      ])]
        .sort((a, b) => {
          const aLen = _textWithoutEditorBadges(a).length;
          const bLen = _textWithoutEditorBadges(b).length;
          return bLen - aLen;
        });
      const _footerSelected = [];
      _footerCandidates.forEach((node) => {
        const txt = _textWithoutEditorBadges(node);
        const covered = _footerSelected.some(parent => {
          if (!parent.contains(node)) return false;
          const pTxt = _textWithoutEditorBadges(parent);
          return pTxt.length >= txt.length;
        });
        if (!covered) _footerSelected.push(node);
      });
      _allParaEls = _footerSelected;

      if (!_allParaEls.length) {
        const rawFooterText = _textWithoutEditorBadges(el);
        if (rawFooterText && rawFooterText.length <= 260 && !el.querySelector('a')) {
          _allParaEls = [el];
        }
      }
    }
    const _paraEls = isMediaCardCarousel
      ? _allParaEls.filter(p => !_mediaCarouselContainer || !_mediaCarouselContainer.contains(p)).slice(0, 1)
      : _allParaEls;
    const _paraEntries = [];
    _paraEls.forEach(p => {
      const rawText = isFooterSection ? _textWithoutEditorBadges(p) : p.innerText.trim();
      const parts = isFooterSection ? [rawText] : (_getLogicalParagraphText(p).length > 1 ? _getLogicalParagraphText(p) : [rawText]);
      parts.forEach((partText, partIndex) => {
        fieldIdx++;
        const paraTag = isMediaCardCarousel
          ? 'Carousel Subtitle'
          : (isFooterSection
            ? 'Footer Text'
            : (parts.length > 1 ? `Paragraph ${partIndex + 1}` : 'Paragraph'));
        const fid = `para-${fieldIdx}`;
        htmlChunks.push(_textareaField(fieldIdx, paraTag, String(partText || '').slice(0, 600), fid, _elInit(p)));
        _paraEntries.push({ el: p, fid, parts, partIndex, isSplit: parts.length > 1 });
      });
    });

    // Nav links / anchor texts — collect anchor refs before any innerHTML write
    const _linkFidToAnchor = new Map();
    if (!isMediaCardCarousel && !isImageCollage && !isFooterSection) {
      el.querySelectorAll('a').forEach((a) => {
        if (String(a?.dataset?.wbMediaType || '').toLowerCase() === 'social') return;
        const text = (a.textContent || '').trim();
        const href = a.getAttribute('href') || '';
        if (!text || text.length > 60) return;
        fieldIdx++;
        const fid = `link-${fieldIdx}`;
        htmlChunks.push(_linkField(fieldIdx, 'Link', text, href, fid, _linkInit(a)));
        _linkFidToAnchor.set(fid, a);
      });
    }

    // Additional media blocks (skip already-shown logo image only on section 0)
    if (!isMediaCardCarousel && !isImageCollage) {
      const mediaNodes = [...el.querySelectorAll('img,video,a[data-wb-media-type="social"]')];
      let mediaIdx = 0;
      mediaNodes.forEach((mediaNode) => {
        if (activeSectionIndex === 0 && mediaNode === logo) return;
        fieldIdx++;
        const fid = `img-${fieldIdx}`;
        mediaIdx++;
        const tag = (mediaNode.tagName || '').toUpperCase();
        const mediaType = String(mediaNode?.dataset?.wbMediaType || (tag === 'VIDEO' ? 'video' : (tag === 'A' ? 'social' : 'image'))).toLowerCase();
        const src = mediaType === 'video'
          ? (mediaNode.getAttribute('src') || mediaNode.querySelector('source')?.getAttribute('src') || mediaNode.src || '')
          : (mediaType === 'social'
            ? (mediaNode.getAttribute('href') || '')
            : (mediaNode.getAttribute('src') || mediaNode.src || ''));
        const mediaInit = _imgAnimInit(mediaNode);
        mediaInit.click = _clickInit(mediaNode);
        mediaInit.mediaType = mediaType;
        const altText = mediaType === 'social'
          ? ((mediaNode.textContent || '').trim() || mediaNode.getAttribute('aria-label') || '')
          : (mediaNode.alt || mediaNode.getAttribute('aria-label') || '');
        htmlChunks.push(_imgField(fieldIdx, `Media ${mediaIdx}`, (mediaType === 'social' ? src : _normalizeStagingAssetUrl(src)), altText, fid, mediaInit));
        _imgFidToEl.set(fid, mediaNode);
      });
    }

    let borderWidth = 0;
    let borderRadius = 0;
    let borderStyle = 'none';
    let borderColor = '#d1d5db';
    let widthPct = 100;
    let align = 'center';

    if (!isMediaCardCarousel && !isImageCollage) {
      // Section layout controls (available for standard sections)
      const textTarget = _findHeroTextTarget(el) || el;
      const imageTarget = _findHeroImageTarget(el);
      const textCs = textTarget ? iframeView.getComputedStyle(textTarget) : null;
      const rawAlign = textTarget ? (textTarget.style.textAlign || textCs.textAlign || 'left') : 'left';
      const rawV = textTarget ? (textTarget.dataset.wbValign || textTarget.style.justifyContent || textCs.justifyContent || 'flex-start') : 'flex-start';
      const vAlign = String(rawV).includes('center') ? 'center' : (String(rawV).includes('end') ? 'bottom' : 'top');
      const layoutMode = textTarget ? (textTarget.dataset.wbLayoutMode || 'preserve') : 'preserve';
      const imageCs = imageTarget ? iframeView.getComputedStyle(imageTarget) : null;
      const showImage = imageTarget ? ((imageTarget.style.display || imageCs.display) !== 'none') : false;
      htmlChunks.push(_heroLayoutField({
        showImage,
        hasImage: !!imageTarget,
        textAlign: rawAlign,
        vAlign,
        layoutMode,
      }));
      heroMeta = { textTarget, imageTarget, sectionEl: el };

      // Section box controls
      const secCs = iframeView.getComputedStyle(el);
      borderWidth = parseFloat(el.style.borderTopWidth || secCs.borderTopWidth || '0') || 0;
      borderRadius = parseFloat(el.style.borderTopLeftRadius || secCs.borderTopLeftRadius || '0') || 0;
      borderStyle = (el.style.borderTopStyle || secCs.borderTopStyle || 'none').toLowerCase();
      borderColor = _rgbToHex(el.style.borderTopColor || secCs.borderTopColor || '#d1d5db');
      const hasPctWidth = /%$/.test(String(el.style.width || '').trim());
      const parentEl = el.parentElement;
      const parentRect = parentEl ? parentEl.getBoundingClientRect() : null;
      const elRect = el.getBoundingClientRect();
      const derivedPct = (parentRect && parentRect.width > 0)
        ? Math.round(Math.max(20, Math.min(100, (elRect.width / parentRect.width) * 100)))
        : 100;
      widthPct = hasPctWidth
        ? (parseFloat(String(el.style.width).replace('%','')) || derivedPct)
        : derivedPct;
      align = 'center';
      const ml = String(el.style.marginLeft || '').trim().toLowerCase();
      const mr = String(el.style.marginRight || '').trim().toLowerCase();
      if (ml === '0px' || ml === '0') align = 'left';
      if (mr === '0px' || mr === '0') align = 'right';
      if (ml === 'auto' && mr === 'auto') align = 'center';

      htmlChunks.push(_sectionBoxField({
        borderWidth,
        borderRadius,
        borderStyle,
        borderColor,
        widthPct,
        align,
      }));
      sectionBoxMeta = { target: el };
    }

    // Alliance table rows (existing rows + add-new inputs)
    const allianceTable = el.querySelector('table');
    if (allianceTable) {
      const body = allianceTable.tBodies[0] || allianceTable;
      const rowEls = [...body.querySelectorAll('tr')].filter(r => r.querySelectorAll('td').length >= 1);
      if (rowEls.length) {
        allianceMeta = { table: allianceTable, rows: rowEls };
        htmlChunks.push('<div style="border-top:1px dashed var(--border);padding-top:10px;margin-top:6px"><label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:8px">🤝 Alliance Table Rows</label></div>');
        rowEls.forEach((tr, rowIdx) => {
          const cells = [...tr.querySelectorAll('td')];
          const c0 = cells[0];
          const c1 = cells[1];
          const c2 = cells[2];
          const logoImg = c0 ? c0.querySelector('img') : null;
          const brandEl = c0 ? (c0.querySelector('strong') || c0) : null;
          htmlChunks.push(_allianceRowEditor(rowIdx, {
            logo: logoImg ? (logoImg.getAttribute('src') || logoImg.src || '') : '',
            brand: brandEl ? (brandEl.textContent || '').trim() : '',
            category: c1 ? (c1.textContent || '').trim() : '',
            support: c2 ? (c2.textContent || '').trim() : '',
          }));
        });
        htmlChunks.push(_allianceAddRowEditor());
      }
    }

    // Generic grid/card item editing (for repeated info cards)
    const gridCandidates = isImageCollage
      ? []
      : (isMediaCardCarousel
      ? [_findMediaCardCarouselContainer(el)].filter(Boolean)
      : [...el.querySelectorAll('div,section,article,ul,ol')].filter(container => {
          const cs = iframeView.getComputedStyle(container);
          const isLayout = cs.display.includes('grid') || cs.display.includes('flex');
          if (!isLayout) return false;
          const kids = [...container.children].filter(k => ['DIV', 'ARTICLE', 'LI', 'SECTION'].includes(k.tagName));
          if (kids.length < 2 || kids.length > 12) return false;
          const populated = kids.filter(k => (k.innerText || '').trim().length >= 2);
          return populated.length >= 2;
        }));

    if (gridCandidates.length) {
      const scored = gridCandidates.map(c => {
        const kids = [...c.children].filter(k => ['DIV', 'ARTICLE', 'LI', 'SECTION'].includes(k.tagName));
        const populated = kids.filter(k => (k.innerText || '').trim().length >= 2).length;
        return { c, score: populated, kids };
      }).sort((a, b) => b.score - a.score);

      const best = scored[0];
      const items = [];
      best.kids.forEach((cardEl) => {
        const titleEl = cardEl.querySelector('h1,h2,h3,h4,h5,strong,b,.title,[class*="title"],[class*="label"]');
        let bodyEl = cardEl.querySelector('p,small');
        const imageEl = cardEl.querySelector('img');
        if (!bodyEl) {
          const textEls = [...cardEl.querySelectorAll('span,div')].filter(x => (x.textContent || '').trim().length > 0);
          bodyEl = textEls.find(x => x !== titleEl) || null;
        }
        const title = titleEl ? (titleEl.textContent || '').trim() : '';
        // Preserve manual line breaks when reopening the editor.
        let body = bodyEl ? (bodyEl.innerText || '').trim() : '';
        // Some info-cards store value text as a direct text node (no <p>/<div> wrapper).
        // Capture that text so reopening the editor does not show an empty body.
        if (!body) {
          const directText = [...cardEl.childNodes]
            .filter(node => node && node.nodeType === 3)
            .map(node => String(node.textContent || '').trim())
            .filter(Boolean)
            .join(' ')
            .trim();
          if (directText) body = directText;
        }
        const imageSrc = imageEl ? (imageEl.getAttribute('src') || imageEl.src || '') : '';
        const imageAlt = imageEl ? (imageEl.alt || imageEl.getAttribute('aria-label') || '') : '';
        const titleInit = titleEl ? _elInit(titleEl) : {};
        const titleAlign = titleEl
          ? _normalizeTextAlignValue(titleEl.style.textAlign || iframeView.getComputedStyle(titleEl).textAlign || 'left')
          : 'left';
        const titleClick = titleEl ? _clickInit(titleEl) : {};
        const imageClick = imageEl ? _clickInit(imageEl) : {};
        if (title || body) {
          items.push({
            cardEl,
            titleEl,
            bodyEl,
            imageEl,
            title,
            body,
            imageSrc,
            imageAlt,
            titleInit,
            titleAlign,
            titleClick,
            imageClick,
          });
        }
      });

      if (items.length >= 2) {
        gridMeta = { container: best.c, items, isMediaCarousel: isMediaCardCarousel };
        const showImageFields = isMediaCardCarousel || items.some(item => !!item.imageEl);
        htmlChunks.push('<div style="border-top:1px dashed var(--border);padding-top:10px;margin-top:6px"><label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:8px">🔳 Grid / Card Content</label></div>');
        items.forEach((item, idx2) => {
          htmlChunks.push(_gridCardEditor(idx2, {
            title: item.title,
            body: item.body,
            imageSrc: item.imageSrc,
            imageAlt: item.imageAlt,
            titleInit: item.titleInit,
            titleAlign: item.titleAlign,
            titleClick: item.titleClick,
            imageClick: item.imageClick,
          }, { includeImage: showImageFields }));
        });
        if (showImageFields) {
          htmlChunks.push(_gridAddCardEditor());
        }
        if (isMediaCardCarousel) {
          const autoEnabled = String(best.c.dataset.wbCarouselAuto || '') === '1';
          const delaySec = Math.max(2, parseInt(best.c.dataset.wbCarouselDelaySec || '4', 10) || 4);
          const styleKey = _normalizeMediaCarouselStyle(best.c.dataset.wbCarouselStyle || 'classic');
          const controlPos = _normalizeMediaCarouselControlPos(best.c.dataset.wbCarouselControlPos || 'bottom-center');
          const controlsVisibility = _normalizeMediaCarouselControlsVisibility(
            best.c.dataset.wbCarouselControlsVisibility
              || (String(best.c.dataset.wbCarouselHoverOnly || '') === '1' ? 'hover' : 'always')
          );
          htmlChunks.push(_gridCarouselOptionsField({ enabled: autoEnabled, delaySec, styleKey, controlPos, controlsVisibility }));
        }
      }
    }

    // Image collage editor (order + weight + focus + media library)
    const collageContainer = isImageCollage ? _findImageCollageContainer(el) : null;
    if (collageContainer) {
      const collageOpts = _readImageCollageOptions(collageContainer);
      _applyImageCollageLayout(collageContainer, collageOpts);
      const itemEls = [...collageContainer.children].filter(node => ['FIGURE', 'DIV', 'ARTICLE', 'LI'].includes(node.tagName));
      const items = itemEls.map((itemEl) => {
        const imageEl = itemEl.querySelector('img') || null;
        if (!imageEl) return null;
        const focus = _readImageCollageFocus(imageEl);
        return {
          itemEl,
          imageEl,
          src: imageEl.getAttribute('src') || imageEl.src || '',
          alt: imageEl.alt || imageEl.getAttribute('aria-label') || '',
          weight: _readImageCollageWeight(itemEl),
          focusX: focus.x,
          focusY: focus.y,
        };
      }).filter(Boolean);

      if (items.length) {
        collageMeta = {
          container: collageContainer,
          items,
          fidToItem: new Map(),
          autoFit: collageOpts.autoFit,
          centered: collageOpts.centered,
          styleKey: collageOpts.styleKey,
          breathing: collageOpts.breathing,
          fillStrategy: collageOpts.fillStrategy,
        };
        htmlChunks.push('<div style="border-top:1px dashed var(--border);padding-top:10px;margin-top:6px"><label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:8px">🧩 Photo Mosaic Mix</label></div>');
        htmlChunks.push(_imageCollageOptionsField(collageOpts));
        items.forEach((item, idx2) => {
          const fid = `collage-${idx2}-image`;
          collageMeta.fidToItem.set(fid, item.itemEl);
          htmlChunks.push(_imageCollageItemEditor(idx2, {
            src: item.src,
            alt: item.alt,
            weight: item.weight,
            focusX: item.focusX,
            focusY: item.focusY,
            autoFit: collageOpts.autoFit,
            styleKey: collageOpts.styleKey,
          }));
        });
        htmlChunks.push(_imageCollageAddItemEditor());
      }
    }

    let bgUrl = '';
    let bgUrls = [];
    let bgColorInput = '#ffffff';
    let carouselEnabled = false;
    let carouselIntervalSec = 5;
    let carouselStyle = 'slide-left';
    let carouselSpeedMs = 900;
    let bgMotion = 'none';

    if (!isMediaCardCarousel && !isImageCollage) {
      // ── Background editor (shown for standard sections) ───────────────────
      const bgTarget = _bgTarget(el);
      const computed = iframeView.getComputedStyle(bgTarget);
      const bgImage  = computed.backgroundImage !== 'none' ? computed.backgroundImage : (bgTarget.style.backgroundImage || '');
      const bgColor  = bgTarget.style.backgroundColor || computed.backgroundColor || '';
      const bgUrlMatch = bgImage.match(/url\(["']?([^"')]+)["']?\)/);
      bgUrl = _normalizeStagingAssetUrl(bgUrlMatch ? bgUrlMatch[1] : '');
      const carouselRaw = bgTarget.dataset.wbBgCarouselUrls || '';
      bgUrls = carouselRaw
        ? carouselRaw.split('||').map(s => _normalizeStagingAssetUrl(s.trim())).filter(Boolean)
        : (bgUrl ? [bgUrl] : []);
      bgColorInput = _rgbToHex((bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') ? bgColor : '#ffffff');
      carouselEnabled = bgUrls.length > 1;
      carouselIntervalSec = Math.max(2, Math.round((parseInt(bgTarget.dataset.wbBgIntervalMs || '5000', 10) || 5000) / 1000));
      carouselStyle = bgTarget.dataset.wbBgStyle || 'slide-left';
      carouselSpeedMs = Math.max(250, parseInt(bgTarget.dataset.wbBgSpeedMs || '900', 10) || 900);
      bgMotion = bgTarget.dataset.wbBgMotion || 'none';
      const sectionLabel = activeSectionIndex !== null && stagingSections[activeSectionIndex] ? stagingSections[activeSectionIndex].label : 'Section';
      htmlChunks.push(_bgField(bgUrl, bgColor, bgUrls, carouselEnabled, carouselIntervalSec, carouselStyle, carouselSpeedMs, bgMotion, sectionLabel, activeSectionIndex));
    }

    if (htmlChunks.length === 0) {
      fields.innerHTML = '<p style="font-size:.82rem;color:var(--muted);text-align:center;padding:24px">No editable text or images detected in this section.</p>';
    } else {
      // Single innerHTML write — eliminates O(n²) DOM rebuilds from repeated +=
      fields.innerHTML = htmlChunks.join('');
      if (!isMediaCardCarousel && !isImageCollage) {
        _refreshBgNameList();
        loadExistingBgImages();
      }
    }

    // Stamp metadata on stable DOM nodes (after innerHTML is final)
    if (brandEl) {
      fields._brandEl  = brandEl;
      fields._brandFid = brandFid;
    }
    if (logo) {
      fields._logoEl = logo;
    }
    fields._headingEls   = _headingEls;
    fields._headingStart = _headingStartField;
    fields._paraEls      = _paraEntries.map(entry => entry.el);
    fields._paraEntries  = _paraEntries;
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
    fields._allianceMeta = allianceMeta;
    fields._gridMeta = gridMeta;
    fields._collageMeta = collageMeta;
    fields._heroMeta = heroMeta;
    fields._sectionAnchorMeta = sectionAnchorMeta;
    fields._sectionAnchorInit = {
      anchorName: String(el.dataset?.wbAnchorName || '').trim() || _friendlyAnchorName(el.id || sectionEntry.baseLabel || 'section'),
      anchorId: String(el.id || sectionEntry.anchorId || '').trim(),
      baseLabel: sectionEntry.baseLabel || 'Section',
    };
    fields._sectionBoxMeta = sectionBoxMeta;
    fields._sectionBoxInit = {
      borderStyle,
      borderColor,
      borderWidth: Math.round(borderWidth),
      radius: Math.round(borderRadius),
      widthPct: Math.round(widthPct),
      align,
    };
    fields._bgInit = {
      urls: bgUrls.slice(),
      url: _normalizeStagingAssetUrl(bgUrl || ''),
      color: bgColorInput,
      opacity: 100,
      size: document.getElementById('secBgSize')?.value || 'cover',
      overlay: 0,
      carouselEnabled,
      interval: carouselIntervalSec,
      style: carouselStyle,
      speed: carouselSpeedMs,
      motion: bgMotion,
    };
    fields._imgFidToEl = _imgFidToEl;
    fields._isMediaCardCarousel = isMediaCardCarousel;
    _imgFidToEl.forEach((imgEl, fid) => {
      const div = fields.querySelector(`div[data-fid="${fid}"]`);
      if (div) div._imgEl = imgEl;
    });
    if (collageMeta && Array.isArray(collageMeta.items)) {
      collageMeta.items.forEach((item, idx2) => {
        const fid = `collage-${idx2}-image`;
        const div = fields.querySelector(`[data-fid="${fid}"]`);
        if (div) div._collageItemEl = item.itemEl;
      });
      _renumberImageCollageEditorCards();
      _syncCollageStyleThumbSelection(collageMeta.styleKey || 'professional');
    }

    fields._sectionEl = el;
    editor._sectionEl = el;
  }); // end requestAnimationFrame
}

function addAllianceRowToActiveSection() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const { el } = stagingSections[activeSectionIndex];
  const table = el.querySelector('table');
  if (!table) {
    toast('No table found in this section', false);
    return;
  }

  const brand = (document.getElementById('ar-new-brand')?.value || '').trim();
  const category = (document.getElementById('ar-new-category')?.value || '').trim();
  const support = (document.getElementById('ar-new-support')?.value || '').trim();
  const logo = (document.getElementById('ar-new-logo')?.value || '').trim();

  if (!brand || !category || !support) {
    toast('Please fill Brand, Category, and Support fields', false);
    return;
  }

  _historyPush();
  const doc = frame.contentDocument;
  const body = table.tBodies[0] || table;
  const template = body.querySelector('tr:last-child');
  const newRow = template ? template.cloneNode(true) : doc.createElement('tr');

  if (!template) {
    newRow.innerHTML = '<td></td><td></td><td></td>';
  }

  const cells = [...newRow.querySelectorAll('td')];
  while (cells.length < 3) {
    const td = doc.createElement('td');
    newRow.appendChild(td);
    cells.push(td);
  }

  const c0 = cells[0], c1 = cells[1], c2 = cells[2];
  const existingImg = c0.querySelector('img');
  const existingStrong = c0.querySelector('strong');
  const brandWrap = c0.querySelector('.brand-cell');

  if (brandWrap) {
    if (existingImg) {
      const src = logo || existingImg.getAttribute('src') || existingImg.src;
      existingImg.src = src;
      existingImg.setAttribute('src', src);
      existingImg.alt = `${brand} logo`;
    }
    if (existingStrong) {
      existingStrong.textContent = brand;
    } else {
      const s = doc.createElement('strong');
      s.textContent = brand;
      brandWrap.appendChild(s);
    }
  } else if (existingImg || logo) {
    c0.innerHTML = '';
    const wrap = doc.createElement('div');
    wrap.className = 'brand-cell';
    const lp = doc.createElement('div');
    lp.className = 'brand-logo-placeholder';
    const img = existingImg || doc.createElement('img');
    if (logo) {
      img.src = logo;
      img.setAttribute('src', logo);
    }
    img.alt = `${brand} logo`;
    img.loading = 'lazy';
    lp.appendChild(img);
    const s = doc.createElement('strong');
    s.textContent = brand;
    wrap.appendChild(lp);
    wrap.appendChild(s);
    c0.appendChild(wrap);
  } else {
    c0.textContent = brand;
  }

  _setText(c1, category);
  _setParagraphText(c2, support);

  body.appendChild(newRow);
  openSecEditor(activeSectionIndex);
  toast('Alliance row added — click 💾 Save to persist');
}

function _bgField(bgUrl, bgColor, bgUrls = [], carouselEnabled = false, carouselIntervalSec = 5, carouselStyle = 'slide-left', carouselSpeedMs = 900, bgMotion = 'none', sectionLabel = 'Section', secIdx = 0) {
  const urls = (Array.isArray(bgUrls) ? bgUrls : []).filter(Boolean);
  const resolvedUrls = urls.length ? urls : (bgUrl ? [bgUrl] : []);
  const firstUrl = resolvedUrls[0] || '';
  const firstName = _displayBgImageName(firstUrl);
  const thumb = firstUrl ? `<img src="${_esc(_toPreviewMediaUrl(firstUrl))}" style="width:100%;height:60px;object-fit:cover;border-radius:6px;margin-top:6px;border:1px solid var(--border)" id="bgThumb">` : `<div id="bgThumb"></div>`;
  const urlsText = resolvedUrls.join('\n');
  const namesHtml = resolvedUrls.length
    ? resolvedUrls.map((u, i) => `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 7px;border:1px solid var(--border);border-radius:999px;background:var(--bg);font-size:.68rem;color:var(--text)">${i + 1}. ${_esc(_displayBgImageName(u))}</span>`).join(' ')
    : '<span style="color:var(--muted);font-size:.68rem"><em>No images added</em></span>';
  const safeColor = (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') ? bgColor : '#ffffff';
  // Convert rgb() to hex for color input
  const hexColor = _rgbToHex(safeColor);
  return `<div data-type="bg" style="border-top:1px dashed var(--border);padding-top:12px;margin-top:4px">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:6px">🎨 Section Background</label>
    <div style="background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:10px 12px;margin-bottom:8px;font-size:.69rem;color:var(--text)">
      <div style="margin-bottom:5px;display:flex;justify-content:space-between;align-items:center">
        <strong style="color:#667eea">📍 ${_esc(sectionLabel.split('#')[0].trim()) || 'Section'}</strong>
        ${sectionLabel.includes('#') ? `<span style="background:#e0e7ff;color:#4f46e5;padding:2px 6px;border-radius:3px;font-weight:600;font-size:.65rem">${_esc(sectionLabel.split('#')[1] || '')}</span>` : ''}
      </div>
      <div style="margin-bottom:5px;word-break:break-word;max-height:40px;overflow:auto"><strong>🖼️ Image:</strong> <span style="color:var(--muted);font-size:.68rem">${firstName ? _esc(firstName) : '<em>(None)</em>'}</span></div>
      <div style="margin-bottom:5px"><strong>🔄 Carousel:</strong> <span style="color:var(--muted)">${carouselEnabled ? `Enabled • ${resolvedUrls.length} imgs • ${carouselStyle}` : 'Disabled'}</span></div>
      <div><strong>✨ Motion:</strong> <span style="color:var(--muted)">${bgMotion === 'none' ? 'None' : bgMotion.charAt(0).toUpperCase() + bgMotion.slice(1)}</span></div>
    </div>
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
    <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Background images</label>
    <div id="secBgNamesList" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">${namesHtml}</div>
    <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px">
      <select id="secBgExistingImage" style="display:none">
        <option value="">Select existing image from server…</option>
      </select>
      <button type="button" class="btn btn-secondary btn-sm" onclick="openExistingBgImagePicker()" title="Choose from uploaded media">🗂 Media Library</button>
      <button type="button" class="btn btn-secondary btn-sm" onclick="loadExistingBgImages()" title="Refresh server image list">↻ Refresh</button>
    </div>
    <div id="secBgExistingLabel" style="font-size:.71rem;color:var(--muted);margin:-4px 0 8px 0">No existing image selected</div>
    <textarea id="secBgUrls" style="display:none">${_esc(urlsText)}</textarea>
    <input type="hidden" id="secBgUrl" value="${_esc(firstUrl)}">
    <!-- Visual image strip -->
    <div id="secBgStrip" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;min-height:${resolvedUrls.length ? '0' : '0'}">
      ${resolvedUrls.map((u, i) => `
        <div style="position:relative;width:64px;height:48px;border-radius:5px;overflow:hidden;border:1.5px solid var(--border);flex-shrink:0" title="${_esc(_displayBgImageName(u))}">
          <img src="${_esc(_toPreviewMediaUrl(u))}" style="width:100%;height:100%;object-fit:cover">
          <button type="button" onclick="removeBgImageAt(${i})" title="Remove"
            style="position:absolute;top:1px;right:1px;background:rgba(0,0,0,.6);color:#fff;border:none;border-radius:3px;width:16px;height:16px;font-size:9px;cursor:pointer;line-height:1;display:flex;align-items:center;justify-content:center">✕</button>
          <div style="position:absolute;bottom:1px;left:2px;background:rgba(0,0,0,.55);color:#fff;font-size:8px;padding:0 3px;border-radius:2px">${i+1}</div>
        </div>`).join('')}
    </div>
    <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted);margin:4px 0 6px 0">
      <input type="checkbox" id="secBgCarouselEnabled" ${carouselEnabled ? 'checked' : ''} onchange="toggleBgCarouselOptions();previewBg()">
      Enable carousel slide for background images
    </label>
    <div id="secBgCarouselOpts" style="display:${carouselEnabled ? 'flex' : 'none'};gap:8px;align-items:center;margin-bottom:6px">
      <label style="font-size:.72rem;color:var(--muted)">Slide every</label>
      <input type="number" id="secBgInterval" min="2" max="30" value="${carouselIntervalSec}" oninput="_previewBgDebounced()"
        style="width:84px;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
      <span style="font-size:.72rem;color:var(--muted)">seconds</span>
    </div>
    <div id="secBgTransitionOpts" style="display:${carouselEnabled ? 'grid' : 'none'};grid-template-columns:1fr 1fr;gap:8px;margin-bottom:6px">
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Movement style</label>
        <select id="secBgStyle" onchange="_previewBgDebounced()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
          <option value="slide-left" ${carouselStyle === 'slide-left' ? 'selected' : ''}>Slide Left</option>
          <option value="slide-right" ${carouselStyle === 'slide-right' ? 'selected' : ''}>Slide Right</option>
          <option value="fade" ${carouselStyle === 'fade' ? 'selected' : ''}>Fade</option>
          <option value="zoom" ${carouselStyle === 'zoom' ? 'selected' : ''}>Zoom</option>
          <option value="parallax" ${carouselStyle === 'parallax' ? 'selected' : ''}>Parallax Drift</option>
        </select>
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Transition speed</label>
        <select id="secBgSpeed" onchange="_previewBgDebounced()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
          <option value="500" ${carouselSpeedMs <= 600 ? 'selected' : ''}>Fast</option>
          <option value="900" ${carouselSpeedMs > 600 && carouselSpeedMs <= 1100 ? 'selected' : ''}>Normal</option>
          <option value="1400" ${carouselSpeedMs > 1100 ? 'selected' : ''}>Slow</option>
        </select>
      </div>
    </div>
    <div style="margin-bottom:6px">
      <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Background motion</label>
      <select id="secBgMotion" onchange="_previewBgDebounced()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="none" ${bgMotion === 'none' ? 'selected' : ''}>None</option>
        <option value="drift" ${bgMotion === 'drift' ? 'selected' : ''}>Drift</option>
        <option value="zoom" ${bgMotion === 'zoom' ? 'selected' : ''}>Slow Zoom</option>
        <option value="pulse" ${bgMotion === 'pulse' ? 'selected' : ''}>Breathing Pulse</option>
      </select>
    </div>
    <div style="display:flex;gap:6px;margin-bottom:6px">
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyBgAnimPreset('subtle')">Subtle</button>
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyBgAnimPreset('medium')">Medium</button>
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyBgAnimPreset('bold')">Bold</button>
    </div>
    ${thumb}
    <div style="display:flex;gap:6px;margin-top:6px">
      <select id="secBgSize" onchange="previewBg()" style="padding:5px 7px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.78rem">
        <option value="cover">Cover</option>
        <option value="contain">Contain</option>
        <option value="auto">Auto</option>
        <option value="100% 100%">Stretch</option>
      </select>
      <button class="btn btn-secondary btn-sm" style="color:#ef4444;border-color:rgba(239,68,68,.4)" onclick="clearBg()" title="Remove background">🗑 Clear all</button>
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

function _shadeHex(hex, amount) {
  const norm = (hex || '').replace('#', '');
  if (norm.length !== 6) return '#111827';
  const clamp = v => Math.max(0, Math.min(255, v));
  const r = clamp(parseInt(norm.slice(0, 2), 16) + amount);
  const g = clamp(parseInt(norm.slice(2, 4), 16) + amount);
  const b = clamp(parseInt(norm.slice(4, 6), 16) + amount);
  return '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join('');
}

function _ensureWbLinkId(a) {
  if (!a.dataset.wbLinkId) {
    a.dataset.wbLinkId = 'wblink' + Math.random().toString(36).slice(2, 9);
  }
  return a.dataset.wbLinkId;
}

function _upsertLinkHoverRule(doc, linkId, hoverBg, hoverText) {
  let styleEl = doc.getElementById('__wb_link_hover_overrides');
  if (!styleEl) {
    styleEl = doc.createElement('style');
    styleEl.id = '__wb_link_hover_overrides';
    doc.head.appendChild(styleEl);
  }
  const ruleRe = new RegExp(`a\\[data-wb-link-id=\\"${linkId}\\"\\]:hover\\{[^}]*\\}`, 'g');
  const cleaned = (styleEl.textContent || '').replace(ruleRe, '').trim();
  if (!hoverBg && !hoverText) {
    styleEl.textContent = cleaned;
    return;
  }
  const parts = [];
  if (hoverBg) parts.push(`background-color:${hoverBg} !important`);
  if (hoverText) parts.push(`color:${hoverText} !important`);
  const rule = `a[data-wb-link-id=\"${linkId}\"]:hover{${parts.join(';')}}`;
  styleEl.textContent = (cleaned ? cleaned + '\n' : '') + rule;
}

function toggleLinkStyleInput(fid, key) {
  const enabled = document.querySelector(`[data-fid="${fid}-${key}-enabled"]`)?.checked;
  const colorEl = document.querySelector(`[data-fid="${fid}-${key}"]`);
  if (colorEl) colorEl.disabled = !enabled;
}

function _assetFileName(path) {
  const raw = String(path || '').trim();
  if (!raw) return '';
  const clean = raw.split('?')[0].split('#')[0];
  const parts = clean.split('/').filter(Boolean);
  return parts.length ? parts[parts.length - 1] : clean;
}

function _toTitleWords(input) {
  const text = String(input || '').trim();
  if (!text) return '';
  return text
    .split(' ')
    .map(part => part ? (part.charAt(0).toUpperCase() + part.slice(1)) : part)
    .join(' ')
    .trim();
}

function _looksMachineLikeName(name) {
  const s = String(name || '').trim();
  if (!s) return true;
  if (/[a-f0-9]{18,}/i.test(s)) return true;
  if (/\b\d{10,}\b/.test(s)) return true;
  return /[_-]{2,}|[a-f0-9]{8,}(?:[_-]|$)/i.test(s);
}

function _friendlyImageName(rawName, path = '') {
  const fallback = _assetFileName(path || rawName);
  let name = String(rawName || '').trim() || fallback;
  name = name.replace(/\.[a-z0-9]{2,5}$/i, '');
  if (_looksMachineLikeName(name)) {
    name = name
      .replace(/[a-f0-9]{10,}/ig, ' ')
      .replace(/\b\d{6,}\b/g, ' ')
      .replace(/[_-]+/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim();
  } else {
    name = name.replace(/[_-]+/g, ' ').replace(/\s{2,}/g, ' ').trim();
  }
  if (!name) {
    name = fallback.replace(/\.[a-z0-9]{2,5}$/i, '').replace(/[_-]+/g, ' ').trim();
  }
  return _toTitleWords(name || 'Uploaded Image');
}

function _deriveSocialProvider(url = '') {
  const raw = String(url || '').trim().toLowerCase();
  if (!raw) return '';
  const host = raw.replace(/^https?:\/\//, '').split('/')[0].trim();
  if (!host) return '';
  if (host.includes('instagram.')) return 'instagram';
  if (host.includes('facebook.')) return 'facebook';
  if (host.includes('youtube.') || host.includes('youtu.be')) return 'youtube';
  if (host.includes('linkedin.')) return 'linkedin';
  if (host.includes('x.com') || host.includes('twitter.')) return 'x';
  if (host.includes('tiktok.')) return 'tiktok';
  if (host.includes('pinterest.')) return 'pinterest';
  if (host.includes('snapchat.')) return 'snapchat';
  return host.replace(/^www\./, '').split(':')[0];
}

function _socialProviderGlyph(provider = '') {
  const p = String(provider || '').trim().toLowerCase();
  if (!p) return '🔗';
  if (p === 'youtube') return '▶';
  if (p === 'linkedin') return 'in';
  if (p === 'x' || p === 'twitter') return '𝕏';
  if (p === 'facebook') return 'f';
  if (p === 'instagram') return '◉';
  if (p === 'tiktok') return '♪';
  return '🔗';
}

function _socialProviderPalette(provider = '') {
  const p = String(provider || '').trim().toLowerCase();
  if (p === 'instagram') return { from: '#833ab4', to: '#fd1d1d', chip: 'rgba(255,255,255,.22)' };
  if (p === 'facebook') return { from: '#1877f2', to: '#0a55b8', chip: 'rgba(255,255,255,.24)' };
  if (p === 'youtube') return { from: '#ff0000', to: '#b91c1c', chip: 'rgba(255,255,255,.24)' };
  if (p === 'linkedin') return { from: '#0a66c2', to: '#0b4e93', chip: 'rgba(255,255,255,.24)' };
  if (p === 'x' || p === 'twitter') return { from: '#111827', to: '#374151', chip: 'rgba(255,255,255,.20)' };
  if (p === 'tiktok') return { from: '#111827', to: '#db2777', chip: 'rgba(255,255,255,.22)' };
  if (p === 'pinterest') return { from: '#e60023', to: '#9f1239', chip: 'rgba(255,255,255,.24)' };
  if (p === 'snapchat') return { from: '#facc15', to: '#f59e0b', chip: 'rgba(0,0,0,.16)' };
  return { from: '#1e3a8a', to: '#0369a1', chip: 'rgba(255,255,255,.22)' };
}

function _mediaPickerVideoHover(cardEl) {
  const video = cardEl?.querySelector('video[data-media-preview="video"]');
  if (!video) return;
  try {
    video.currentTime = 0;
    const p = video.play();
    if (p && typeof p.catch === 'function') p.catch(() => {});
  } catch (_) {}
}

function _mediaPickerVideoLeave(cardEl) {
  const video = cardEl?.querySelector('video[data-media-preview="video"]');
  if (!video) return;
  try {
    video.pause();
    video.currentTime = 0;
  } catch (_) {}
}

function _renderImageMediaPreviewHtml(mediaType = 'image', src = '', label = '', provider = '') {
  const type = String(mediaType || 'image').toLowerCase();
  const val = String(src || '').trim();
  const previewSrc = (type === 'social') ? val : _toPreviewMediaUrl(val);
  const safeLabel = _esc(String(label || '').trim() || 'Media');
  if (!val) {
    return `<div style="height:54px;border:1px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.72rem;margin-top:6px">No media selected</div>`;
  }
  if (type === 'image') {
    return `<img src="${_esc(previewSrc)}" style="height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px">`;
  }
  if (type === 'video') {
    return `<video src="${_esc(previewSrc)}" muted playsinline preload="metadata" style="height:54px;width:110px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px;background:#0f172a"></video>`;
  }
  const pr = provider || _deriveSocialProvider(val);
  const pal = _socialProviderPalette(pr);
  return `<div style="height:54px;min-width:110px;max-width:180px;padding:0 10px;border:1px solid var(--border);border-radius:6px;display:flex;align-items:center;gap:8px;margin-top:6px;background:linear-gradient(135deg,${pal.from},${pal.to});color:#fff;font-size:.75rem">
    <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:999px;background:${pal.chip};font-weight:700">${_socialProviderGlyph(pr)}</span>
    <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${safeLabel}</span>
  </div>`;
}

function _friendlyMediaSourceLabel(rawPath = '') {
  const norm = _normalizeStagingAssetUrl(rawPath || '');
  if (!norm) return '';
  const mapped = _siteImageLabelByPath.get(norm);
  if (mapped && String(mapped).trim()) return String(mapped).trim();
  return _assetFileName(norm) || norm;
}

function _truncateMediaLabel(label = '', maxChars = 32) {
  const text = String(label || '').trim();
  if (!text) return '';
  if (text.length <= maxChars) return text;
  return `${text.slice(0, Math.max(0, maxChars - 1)).trimEnd()}…`;
}

function _toPreviewMediaUrl(rawUrl = '') {
  const raw = String(rawUrl || '').trim();
  if (!raw) return '';
  if (/^(https?:)?\/\//i.test(raw) || raw.startsWith('data:') || raw.startsWith('blob:')) return raw;
  const norm = _normalizeStagingAssetUrl(raw);
  if (!norm) return raw;
  if (!/^assets\//i.test(norm)) return norm;
  const m = String(currentStagingUrl || '').match(/\/output\/staging\/([^/]+)/i);
  if (!m) return norm;
  return `/output/staging/${m[1]}/${norm}`;
}

function _setImageSourceFieldValue(fid, rawValue) {
  const srcEl = document.querySelector(`input[data-fid="${fid}-src"]`);
  if (srcEl) srcEl.value = String(rawValue || '').trim();
  const displayEl = document.querySelector(`input[data-fid="${fid}-src-display"]`);
  if (displayEl) {
    const friendly = _friendlyMediaSourceLabel(rawValue);
    displayEl.value = friendly || String(rawValue || '').trim();
    displayEl.title = String(rawValue || '').trim();
  }
}

function _syncImageMediaFieldUI(fid) {
  const typeEl = document.querySelector(`select[data-fid="${fid}-media-type"]`);
  const srcEl = document.querySelector(`input[data-fid="${fid}-src"]`);
  const srcDisplayEl = document.querySelector(`input[data-fid="${fid}-src-display"]`);
  const altEl = document.querySelector(`input[data-fid="${fid}-alt"]`);
  const animEl = document.querySelector(`select[data-fid="${fid}-anim"]`);
  if (!typeEl) return;
  const mediaType = String(typeEl.value || 'image').toLowerCase();
  if (srcEl) {
    srcEl.placeholder = mediaType === 'video' ? 'Video source' : (mediaType === 'social' ? 'Social URL' : 'Image source');
    srcEl.style.display = mediaType === 'social' ? 'block' : 'none';
  }
  if (srcDisplayEl) {
    srcDisplayEl.style.display = mediaType === 'social' ? 'none' : 'block';
    if (mediaType !== 'social') {
      const raw = String(srcEl?.value || '').trim();
      srcDisplayEl.value = _friendlyMediaSourceLabel(raw) || raw;
      srcDisplayEl.title = raw;
    }
  }
  if (altEl) altEl.placeholder = mediaType === 'social' ? 'Link label' : 'Alt text / label';
  if (animEl) {
    const disabled = mediaType !== 'image';
    animEl.disabled = disabled;
    animEl.style.opacity = disabled ? '.55' : '1';
  }
  _updateImageMediaPreview(fid);
}

function _updateImageMediaPreview(fid) {
  const typeEl = document.querySelector(`select[data-fid="${fid}-media-type"]`);
  const srcEl = document.querySelector(`input[data-fid="${fid}-src"]`);
  const altEl = document.querySelector(`input[data-fid="${fid}-alt"]`);
  const preview = document.querySelector(`[data-fid="${fid}-preview"]`);
  if (!preview) return;
  const mediaType = String(typeEl?.value || 'image').toLowerCase();
  const src = String(srcEl?.value || '').trim();
  const label = String(altEl?.value || '').trim();
  preview.innerHTML = _renderImageMediaPreviewHtml(mediaType, src, label, _deriveSocialProvider(src));
}

function _setSelectedExistingBgImage(mediaId = '') {
  const mediaKey = String(mediaId || '').trim();
  _selectedExistingMediaPath = mediaKey;
  const sel = document.getElementById('secBgExistingImage');
  if (sel) sel.value = mediaKey || '';
  const labelEl = document.getElementById('secBgExistingLabel');
  const meta = mediaKey ? _siteMediaById.get(mediaKey) : null;
  if (labelEl) {
    if (!mediaKey) {
      labelEl.textContent = 'No existing image selected';
    } else {
      const mediaName = String(meta?.name || '').trim() || _displayBgImageName(meta?.path || meta?.url || '');
      labelEl.textContent = `Selected: ${mediaName}`;
    }
  }
}

function _selectedMediaMeta() {
  const key = String(_selectedExistingMediaPath || '').trim();
  return key ? (_siteMediaById.get(key) || null) : null;
}

function _displayBgImageName(path) {
  const norm = _normalizeStagingAssetUrl(path || '');
  if (norm && _siteImageLabelByPath.has(norm)) return _siteImageLabelByPath.get(norm) || _friendlyImageName('', norm);
  return _friendlyImageName('', norm || path);
}

function _refreshBgNameList() {
  const box = document.getElementById('secBgNamesList');
  if (!box) return;
  const urls = _parseBgUrls();
  if (!urls.length) {
    box.innerHTML = '<span style="color:var(--muted);font-size:.68rem"><em>No images added</em></span>';
    return;
  }
  box.innerHTML = urls
    .map((u, i) => `<span style="display:inline-flex;align-items:center;gap:4px;padding:3px 7px;border:1px solid var(--border);border-radius:999px;background:var(--bg);font-size:.68rem;color:var(--text)">${i + 1}. ${_esc(_displayBgImageName(u))}</span>`)
    .join(' ');
}

function _currentSiteSlugForFinalize() {
  const site = (websites || []).find(x => x.website_id === stagedWebsiteId);
  const localPath = String(site?.local_path || '').replace(/\\/g, '/').replace(/\/+$/, '');
  if (localPath) {
    const segs = localPath.split('/').filter(Boolean);
    return segs[segs.length - 1] || '';
  }
  const m = String(currentStagingUrl || '').match(/\/output\/staging\/([^/]+)/i);
  return m ? m[1] : '';
}

function _extractUploadedFilename(url) {
  const m = String(url || '').match(/assets\/uploads\/([^/?#]+)/i);
  return m ? m[1] : '';
}

async function _finalizeUploadedAssetUrl(url) {
  const filename = _extractUploadedFilename(url);
  if (!filename || !stagedWebsiteId) return url;
  const siteSlug = _currentSiteSlugForFinalize();
  if (!siteSlug) return url;
  try {
    const r = await fetch(`${API}/media/finalize-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ website_id: stagedWebsiteId, site_slug: siteSlug, filename }),
    });
    if (!r.ok) return url;
    const data = await r.json();
    return _normalizeStagingAssetUrl(data.image_url || url);
  } catch (_) {
    return url;
  }
}

async function _uploadImageBlobToMedia(blob, filename = 'image.png') {
  const fd = new FormData();
  fd.append('file', blob, filename || 'image.png');
  if (stagedWebsiteId) fd.append('website_id', stagedWebsiteId);
  const r = await fetch(`${API}/media/upload-image`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err?.detail || `HTTP ${r.status}`);
  }
  const data = await r.json();
  const uploadedUrl = _normalizeStagingAssetUrl(data.full_url || data.thumb_url || '');
  return await _finalizeUploadedAssetUrl(uploadedUrl);
}

function _refreshMediaPickerHeader() {
  const titleEl = document.getElementById('existingBgPickerTitle');
  const actionBtn = document.getElementById('existingBgPickerActionBtn');
  const typeFilterEl = document.getElementById('existingBgTypeFilter');
  const mode = _mediaPickerContext.mode;
  if (titleEl) {
    titleEl.textContent = mode === 'background'
      ? 'Media Library - Choose Background Image'
      : mode === 'image-field'
        ? 'Media Library - Choose Block Media'
        : mode === 'metadata-image'
          ? 'Media Library - Choose Metadata Preview Image'
        : 'Media Library';
  }
  if (typeFilterEl) {
    if (mode === 'background' || mode === 'metadata-image') {
      typeFilterEl.value = 'image';
      typeFilterEl.disabled = true;
      _mediaLibraryTypeFilter = 'image';
    } else {
      typeFilterEl.disabled = false;
      if (!['all', 'image', 'video', 'social'].includes(typeFilterEl.value)) {
        typeFilterEl.value = _mediaLibraryTypeFilter;
      }
      _mediaLibraryTypeFilter = typeFilterEl.value || 'all';
    }
  }
  if (actionBtn) {
    if (mode === 'manage') {
      actionBtn.style.display = 'none';
    } else {
      actionBtn.style.display = '';
      actionBtn.textContent = mode === 'background'
        ? 'Add To Background'
        : mode === 'metadata-image'
          ? 'Use For Metadata'
          : 'Use In Block';
    }
  }
}

function onMediaTypeFilterChange() {
  const typeFilterEl = document.getElementById('existingBgTypeFilter');
  if (!typeFilterEl) return;
  _mediaLibraryTypeFilter = typeFilterEl.value || 'all';
  loadExistingBgImages();
}

function openStagingMediaLibrary() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  _mediaPickerContext = { mode: 'manage', fid: '' };
  _mediaLibraryTypeFilter = 'all';
  _refreshMediaPickerHeader();
  openModal('existingBgImageModal');
  loadExistingBgImages();
  renderExistingBgImagePicker();
}

function openImageFieldMediaPicker(fid) {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  _mediaPickerContext = { mode: 'image-field', fid: String(fid || '') };
  _mediaLibraryTypeFilter = 'all';
  _refreshMediaPickerHeader();
  openModal('existingBgImageModal');
  loadExistingBgImages();
  renderExistingBgImagePicker();
}

function triggerMediaUploadFromPicker() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  const input = document.getElementById('existingBgUploadInput');
  if (!input) return;
  input.value = '';
  input.click();
}

function triggerMediaVideoUploadFromPicker() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  const input = document.getElementById('existingBgVideoUploadInput');
  if (!input) return;
  input.value = '';
  input.click();
}

async function uploadMediaImageFromPicker(inputEl) {
  const file = inputEl?.files?.[0];
  if (!file) return;
  inputEl.value = '';
  openImageEditor(file, async blob => {
    try {
      await _uploadImageBlobToMedia(blob, file.name || 'image.png');
      await loadExistingBgImages();
      renderExistingBgImagePicker();
      toast('Image uploaded to Media Library ✅');
    } catch (err) {
      toast(`Upload failed: ${err.message || 'unknown error'}`, false);
    }
  });
}

async function uploadMediaVideoFromPicker(inputEl) {
  const file = inputEl?.files?.[0];
  if (!file) return;
  inputEl.value = '';

  const fd = new FormData();
  fd.append('file', file);
  fd.append('website_id', stagedWebsiteId || '');

  try {
    const r = await fetch(`${API}/media/upload-video`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err?.detail || `HTTP ${r.status}`);
    }
    await loadExistingBgImages();
    renderExistingBgImagePicker();
    toast('Video uploaded to Media Library ✅');
  } catch (err) {
    toast(`Video upload failed: ${err.message || 'unknown error'}`, false);
  }
}

async function addSocialLinkFromPicker() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  const url = (window.prompt('Enter social media URL (https://...)') || '').trim();
  if (!url) return;
  const displayName = (window.prompt('Display name (optional)') || '').trim();
  const provider = _deriveSocialProvider(url);
  try {
    const r = await fetch(`${API}/media/site-links`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ website_id: stagedWebsiteId, url, display_name: displayName, provider }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err?.detail || `HTTP ${r.status}`);
    }
    await loadExistingBgImages();
    renderExistingBgImagePicker();
    toast('Social link added to Media Library ✅');
  } catch (err) {
    toast(`Failed to add social link: ${err.message || 'unknown error'}`, false);
  }
}

function _applySelectedMediaToImageField(media, fid) {
  const safeFid = String(fid || '').trim();
  if (!media || !safeFid) return;
  const mediaType = String(media.media_type || 'image').trim().toLowerCase();
  const rawSource = String(media.url || media.path || '').trim();
  if (!rawSource) return;
  const srcVal = mediaType === 'social' ? rawSource : _normalizeStagingAssetUrl(rawSource);
  const srcEl = document.querySelector(`[data-fid="${safeFid}-src"]`);
  const typeEl = document.querySelector(`[data-fid="${safeFid}-media-type"]`);
  const altEl = document.querySelector(`[data-fid="${safeFid}-alt"]`);
  if (!srcEl) {
    toast('Target image field is no longer available', false);
    return;
  }
  if (typeEl) typeEl.value = mediaType;
  _setImageSourceFieldValue(safeFid, srcVal);
  if (altEl && !String(altEl.value || '').trim()) {
    if (mediaType === 'social') {
      altEl.value = String(media.name || media.provider || 'Open Link').trim();
    } else if (mediaType === 'video') {
      altEl.value = String(media.name || 'Video').trim();
    }
  }
  const wrap = srcEl.closest('[data-fid]');
  if (wrap) {
    const existing = wrap.querySelector('img');
    const previewSrc = mediaType === 'image' ? _toPreviewMediaUrl(srcVal) : '';
    if (existing) {
      existing.src = previewSrc;
      existing.style.removeProperty('display');
    } else {
      const img = document.createElement('img');
      img.src = previewSrc;
      img.style.cssText = 'height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px';
      wrap.prepend(img);
    }
  }
  _syncImageMediaFieldUI(safeFid);
  const gridMatch = safeFid.match(/^grid-(\d+)-image$/);
  if (gridMatch) {
    _updateGridImagePreview(safeFid);
    _previewMediaCarouselGridItem(parseInt(gridMatch[1], 10) || 0);
  }
  const collageMatch = safeFid.match(/^collage-(\d+)-image$/);
  if (collageMatch) {
    _updateImageCollageItemPreview(safeFid);
  }
  const displayName = String(media.name || '').trim() || _displayBgImageName(srcVal);
  toast(`Selected ${displayName} ✅`);
}

async function loadExistingBgImages() {
  const sel = document.getElementById('secBgExistingImage');
  if (!stagedWebsiteId) return;
  const typeFilterEl = document.getElementById('existingBgTypeFilter');
  const mode = _mediaPickerContext.mode;
  const reqType = mode === 'background'
    ? 'image'
    : ((typeFilterEl?.value || _mediaLibraryTypeFilter || 'all').toLowerCase());
  try {
    const r = await fetch(`${API}/media/site-media/${stagedWebsiteId}?media_type=${encodeURIComponent(reqType)}`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) return;
    const data = await r.json();
    const items = Array.isArray(data?.items) ? data.items : [];
    const prev = (sel?.value || _selectedExistingMediaPath || '').trim();
    _siteImageLabelByPath = new Map();
    _siteImageMetaByPath = new Map();
    _siteImageItems = [];
    _siteMediaById = new Map();
    if (sel) sel.innerHTML = '<option value="">Select existing image from server…</option>';
    items.forEach(it => {
      const mediaType = String(it?.media_type || 'image').trim().toLowerCase();
      const mediaId = String(it?.media_id || it?.image_id || '').trim();
      const rawUrl = String(it?.url || it?.path || '').trim();
      const path = mediaType === 'social' ? rawUrl : _normalizeStagingAssetUrl(rawUrl);
      if (!mediaId || !path) return;
      const displayName = String(it?.name || '').trim() || _friendlyImageName('', path);
      if (mediaType === 'image') {
        _siteImageLabelByPath.set(path, displayName);
      }
      const meta = {
        media_id: mediaId,
        image_id: String(it?.image_id || mediaId).trim(),
        media_type: mediaType,
        name: displayName,
        raw_name: String(it?.name || '').trim(),
        folder: String(it?.folder || '').trim() || 'uploads',
        provider: String(it?.provider || '').trim() || _deriveSocialProvider(path),
        mime_type: String(it?.mime_type || '').trim(),
        path,
        url: path,
      };
      _siteImageMetaByPath.set(mediaId, meta);
      _siteMediaById.set(mediaId, meta);
      _siteImageItems.push(meta);
      if (sel) sel.innerHTML += `<option value="${_esc(mediaId)}">${_esc(displayName)} (${_esc(mediaType)})</option>`;
    });
    if (prev && _siteMediaById.has(prev)) {
      _setSelectedExistingBgImage(prev);
    } else {
      _setSelectedExistingBgImage('');
    }
    _refreshBgNameList();
    renderExistingBgImagePicker();
  } catch (_) {
    // Keep editor usable even if list endpoint fails.
  }
}

function openExistingBgImagePicker() {
  if (!stagedWebsiteId) {
    toast('Open a staging website first', false);
    return;
  }
  _mediaPickerContext = { mode: 'background', fid: '' };
  _mediaLibraryTypeFilter = 'image';
  _refreshMediaPickerHeader();
  openModal('existingBgImageModal');
  loadExistingBgImages();
  renderExistingBgImagePicker();
}

function renderExistingBgImagePicker() {
  const grid = document.getElementById('existingBgImageGrid');
  const status = document.getElementById('existingBgPickerStatus');
  const typeFilterEl = document.getElementById('existingBgTypeFilter');
  if (!grid || !status) return;
  const chosenId = String(_selectedExistingMediaPath || '').trim();
  const currentFilter = (typeFilterEl?.value || _mediaLibraryTypeFilter || 'all').toLowerCase();
  const items = Array.isArray(_siteImageItems) ? [..._siteImageItems] : [];
  const filtered = currentFilter === 'all'
    ? items
    : items.filter(it => String(it.media_type || 'image') === currentFilter);
  filtered.sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));

  if (!filtered.length) {
    status.textContent = 'No media found for this filter';
    grid.innerHTML = '<div class="existing-bg-empty">No media available for the selected type.</div>';
    return;
  }

  status.textContent = `${filtered.length} item${filtered.length === 1 ? '' : 's'} available`;
  grid.innerHTML = filtered.map(it => {
    const mediaId = String(it.media_id || '').trim();
    const mediaType = String(it.media_type || 'image').trim().toLowerCase();
    const provider = String(it.provider || '').trim() || _deriveSocialProvider(it.url || it.path || '');
    const pal = _socialProviderPalette(provider);
    const selected = mediaId && chosenId === mediaId;
    const fullName = String(it.name || _friendlyImageName('', it.path || it.url || '')).trim() || 'Uploaded image';
    const displayName = _truncateMediaLabel(fullName, 32);
    const tag = mediaType === 'image'
      ? (it.folder === 'images' ? 'image • finalized' : 'image • uploaded')
      : mediaType === 'video'
        ? 'video'
        : `social${provider ? ` • ${provider}` : ''}`;
    const cover = mediaType === 'image'
      ? `<img src="${_esc(_toPreviewMediaUrl(it.path || ''))}" loading="lazy" alt="${_esc(fullName)}" title="${_esc(fullName)}">`
      : mediaType === 'video'
        ? `<video data-media-preview="video" src="${_esc(_toPreviewMediaUrl(it.path || ''))}" muted loop playsinline preload="metadata" style="width:100%;height:96px;object-fit:cover;border-bottom:1px solid var(--border);background:#0f172a"></video>`
        : `<div style="height:96px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,${pal.from},${pal.to});font-size:2rem;color:#fff">${_socialProviderGlyph(provider)}</div>`;
    return `<button type="button" class="existing-bg-card ${selected ? 'selected' : ''}" data-id="${_esc(mediaId)}" onclick="selectExistingBgImageCard(this)" ${mediaType === 'video' ? 'onmouseenter="_mediaPickerVideoHover(this)" onmouseleave="_mediaPickerVideoLeave(this)"' : ''} title="${_esc(fullName)}">
      ${cover}
      <div class="existing-bg-card-body">
        <div class="existing-bg-card-name" title="${_esc(fullName)}">${_esc(displayName)}</div>
        <div class="existing-bg-card-tag">${_esc(tag)}</div>
      </div>
    </button>`;
  }).join('');
}

function addChosenExistingBgImageFromPicker() {
  const selected = _selectedMediaMeta();
  if (!selected) {
    toast('Choose an existing image first', false);
    return;
  }
  if (_mediaPickerContext.mode === 'image-field') {
    _applySelectedMediaToImageField(selected, _mediaPickerContext.fid);
    closeModal('existingBgImageModal');
    return;
  }
  if (_mediaPickerContext.mode === 'metadata-image') {
    _applySelectedMediaToMetadata(selected);
    closeModal('existingBgImageModal');
    return;
  }
  if (_mediaPickerContext.mode === 'background') {
    addSelectedExistingBgImage();
    if (_selectedExistingMediaPath) {
      closeModal('existingBgImageModal');
    }
  }
}

function selectExistingBgImageCard(btnEl) {
  const mediaId = String(btnEl?.dataset?.id || '').trim();
  _setSelectedExistingBgImage(mediaId);
  renderExistingBgImagePicker();
}

async function deleteSelectedExistingBgImageFromPicker() {
  const before = document.getElementById('secBgExistingImage')?.value || '';
  await deleteSelectedExistingBgImage();
  const after = document.getElementById('secBgExistingImage')?.value || '';
  if (before && !after) {
    renderExistingBgImagePicker();
  } else {
    await loadExistingBgImages();
  }
}

function addSelectedExistingBgImage() {
  const selected = _selectedMediaMeta();
  if (!selected) {
    toast('Choose an existing image first', false);
    return;
  }
  if (String(selected.media_type || '').toLowerCase() !== 'image') {
    toast('Background supports images only', false);
    return;
  }
  const path = _normalizeStagingAssetUrl(selected.path || selected.url || '');
  const ta = document.getElementById('secBgUrls');
  const urls = _parseBgUrls();
  if (!urls.includes(path)) urls.push(path);
  if (ta) ta.value = urls.join('\n');
  const single = document.getElementById('secBgUrl');
  if (single && !single.value) single.value = urls[0] || '';
  _syncBgStrip();
  _refreshBgNameList();
  _previewBgDebounced();
  toast(`Added ${_displayBgImageName(path)} ✅`);
}

async function deleteSelectedExistingBgImage() {
  const selected = _selectedMediaMeta();
  if (!stagedWebsiteId || !selected) {
    toast('Choose an existing image first', false);
    return;
  }
  const mediaId = String(selected.media_id || selected.image_id || '').trim();
  const path = String(selected.path || selected.url || '').trim();
  if (!mediaId) {
    toast('Selected image cannot be deleted (missing id)', false);
    return;
  }
  const displayName = selected?.name || _displayBgImageName(path);
  if (!window.confirm(`Delete "${displayName}" from media library?`)) return;

  try {
    const r = await fetch(`${API}/media/site-media/${stagedWebsiteId}/${encodeURIComponent(mediaId)}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err?.detail || `HTTP ${r.status}`);
    }

    const ta = document.getElementById('secBgUrls');
    const urls = _parseBgUrls().filter(u => u !== path);
    if (ta) ta.value = urls.join('\n');
    const single = document.getElementById('secBgUrl');
    if (single) single.value = urls[0] || '';
    _setSelectedExistingBgImage('');

    await loadExistingBgImages();
    _syncBgStrip();
    _previewBgDebounced();
    toast(`Deleted ${displayName} ✅`);
  } catch (err) {
    toast(`Delete failed: ${err.message || 'unknown error'}`, false);
  }
}

function _parseBgUrls() {
  const list = document.getElementById('secBgUrls')?.value || '';
  return list
    .split(/\r?\n|,/)
    .map(s => s.trim())
    .map(s => _normalizeStagingAssetUrl(s))
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i);
}

function _isBgPanelDirty(fieldsEl) {
  const init = fieldsEl?._bgInit;
  if (!init) return false;

  const cur = {
    urls: _parseBgUrls(),
    url: _normalizeStagingAssetUrl(document.getElementById('secBgUrl')?.value?.trim() || ''),
    color: document.getElementById('secBgColor')?.value || '#ffffff',
    opacity: parseInt(document.getElementById('secBgOpacity')?.value || '100', 10) || 100,
    size: document.getElementById('secBgSize')?.value || 'cover',
    overlay: parseInt(document.getElementById('secBgOverlay')?.value || '0', 10) || 0,
    carouselEnabled: !!document.getElementById('secBgCarouselEnabled')?.checked,
    interval: Math.max(2, parseInt(document.getElementById('secBgInterval')?.value || '5', 10) || 5),
    style: document.getElementById('secBgStyle')?.value || 'slide-left',
    speed: Math.max(250, parseInt(document.getElementById('secBgSpeed')?.value || '900', 10) || 900),
    motion: document.getElementById('secBgMotion')?.value || 'none',
  };

  const arrEq = (a, b) => {
    if (!Array.isArray(a) || !Array.isArray(b)) return false;
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
    return true;
  };

  if (!arrEq(cur.urls, init.urls || [])) return true;
  if (cur.url !== (init.url || '')) return true;
  if (cur.color !== (init.color || '#ffffff')) return true;
  if (cur.opacity !== (init.opacity ?? 100)) return true;
  if (cur.size !== (init.size || 'cover')) return true;
  if (cur.overlay !== (init.overlay ?? 0)) return true;
  if (cur.carouselEnabled !== !!init.carouselEnabled) return true;
  if (cur.interval !== (init.interval ?? 5)) return true;
  if (cur.style !== (init.style || 'slide-left')) return true;
  if (cur.speed !== (init.speed ?? 900)) return true;
  if (cur.motion !== (init.motion || 'none')) return true;

  return false;
}

function _isSectionBoxPanelDirty(fieldsEl) {
  const init = fieldsEl?._sectionBoxInit;
  if (!init) return false;

  const cur = {
    borderStyle: fieldsEl.querySelector('#secBoxBorderStyle')?.value || 'none',
    borderColor: fieldsEl.querySelector('#secBoxBorderColor')?.value || '#d1d5db',
    borderWidth: Math.max(0, parseInt(fieldsEl.querySelector('#secBoxBorderWidth')?.value || '0', 10) || 0),
    radius: Math.max(0, parseInt(fieldsEl.querySelector('#secBoxRadius')?.value || '0', 10) || 0),
    widthPct: Math.max(20, Math.min(100, parseInt(fieldsEl.querySelector('#secBoxWidthPct')?.value || '100', 10) || 100)),
    align: fieldsEl.querySelector('#secBoxAlign')?.value || 'center',
  };

  if (cur.borderStyle !== (init.borderStyle || 'none')) return true;
  if (cur.borderColor !== (init.borderColor || '#d1d5db')) return true;
  if (cur.borderWidth !== (init.borderWidth ?? 0)) return true;
  if (cur.radius !== (init.radius ?? 0)) return true;
  if (cur.widthPct !== (init.widthPct ?? 100)) return true;
  if (cur.align !== (init.align || 'center')) return true;

  return false;
}

function syncBgUrlListFromSingle() {
  const single = _normalizeStagingAssetUrl((document.getElementById('secBgUrl')?.value || '').trim());
  if (!single) return;
  const urls = _parseBgUrls();
  if (!urls.length) {
    const ta = document.getElementById('secBgUrls');
    if (ta) ta.value = single;
    return;
  }
  urls[0] = single;
  const ta = document.getElementById('secBgUrls');
  if (ta) ta.value = urls.join('\n');
}

function toggleBgCarouselOptions() {
  const enabled = !!document.getElementById('secBgCarouselEnabled')?.checked;
  const box = document.getElementById('secBgCarouselOpts');
  if (box) box.style.display = enabled ? 'flex' : 'none';
  const trans = document.getElementById('secBgTransitionOpts');
  if (trans) trans.style.display = enabled ? 'grid' : 'none';
  if (enabled) {
    const count = _parseBgUrls().length;
    if (count < 2) {
      toast('Add at least 2 background images for carousel animation', false);
    }
  }
}

function applyBgAnimPreset(level) {
  const motion = document.getElementById('secBgMotion');
  const style = document.getElementById('secBgStyle');
  const speed = document.getElementById('secBgSpeed');
  const interval = document.getElementById('secBgInterval');
  if (!motion || !style || !speed || !interval) return;

  if (level === 'subtle') {
    motion.value = 'drift';
    style.value = 'fade';
    speed.value = '1400';
    interval.value = '7';
  } else if (level === 'bold') {
    motion.value = 'pulse';
    style.value = 'parallax';
    speed.value = '500';
    interval.value = '3';
  } else {
    motion.value = 'zoom';
    style.value = 'slide-left';
    speed.value = '900';
    interval.value = '5';
  }
  _previewBgDebounced();
}

function applyImgAnimPreset(fid, level) {
  const sel = document.querySelector(`select[data-fid="${fid}-anim"]`);
  if (!sel) return;
  if (level === 'subtle') sel.value = 'float';
  else if (level === 'bold') sel.value = 'sway';
  else sel.value = 'zoom';
}

function previewBg() {
  if (activeSectionIndex === null) return;
  const { el } = stagingSections[activeSectionIndex];
  _applyBgToEl(el);
  // Update thumb
  const url = (_parseBgUrls()[0] || document.getElementById('secBgUrl')?.value || '').trim();
  const thumb = document.getElementById('bgThumb');
  if (thumb && url) {
    const previewUrl = _toPreviewMediaUrl(url);
    thumb.tagName === 'IMG'
      ? (thumb.src = previewUrl)
      : (thumb.outerHTML = `<img src="${previewUrl}" style="width:100%;height:60px;object-fit:cover;border-radius:6px;margin-top:6px;border:1px solid var(--border)" id="bgThumb">`);
  }
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
      if (child.classList.contains('__wb_badge') || child.classList.contains('__wb_badge_anchor') || child.classList.contains('__wb_bg_carousel')) continue;
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

function _ensureImageAnimationStyles(doc) {
  if (!doc || !doc.head || doc.getElementById('__wb_img_anim_styles')) return;
  const style = doc.createElement('style');
  style.id = '__wb_img_anim_styles';
  style.textContent = `
    @keyframes wbImgFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }
    @keyframes wbImgZoom { 0%,100%{transform:scale(1)} 50%{transform:scale(1.06)} }
    @keyframes wbImgFadeIn { from{opacity:.2;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
    @keyframes wbImgSway { 0%,100%{transform:rotate(0deg)} 25%{transform:rotate(1.2deg)} 75%{transform:rotate(-1.2deg)} }
    @keyframes wbBgDrift { 0%,100%{background-position:center center} 50%{background-position:center 38%} }
    @keyframes wbBgZoom { 0%,100%{background-size:cover} 50%{background-size:112%} }
    @keyframes wbBgPulse { 0%,100%{filter:brightness(1)} 50%{filter:brightness(1.08)} }
    .__wb_bg_carousel[data-motion='drift'] .__wb_bg_slide{animation:wbBgDrift 16s ease-in-out infinite}
    .__wb_bg_carousel[data-motion='zoom'] .__wb_bg_slide{animation:wbBgZoom 18s ease-in-out infinite}
    .__wb_bg_carousel[data-motion='pulse'] .__wb_bg_slide{animation:wbBgPulse 8s ease-in-out infinite}
  `;
  doc.head.appendChild(style);
}

function _applyImgAnimation(img, mode = 'none') {
  if (!img) return;
  img.dataset.wbImgAnim = mode;
  img.style.removeProperty('animation');
  img.style.removeProperty('transform-origin');
  img.style.removeProperty('display');
  switch (mode) {
    case 'float':
      img.style.setProperty('animation', 'wbImgFloat 5s ease-in-out infinite', 'important');
      break;
    case 'zoom':
      img.style.setProperty('animation', 'wbImgZoom 6.5s ease-in-out infinite', 'important');
      img.style.setProperty('transform-origin', 'center center', 'important');
      break;
    case 'fade-in':
      img.style.setProperty('animation', 'wbImgFadeIn 1.2s ease both', 'important');
      break;
    case 'sway':
      img.style.setProperty('animation', 'wbImgSway 6.2s ease-in-out infinite', 'important');
      img.style.setProperty('transform-origin', 'center top', 'important');
      break;
    default:
      break;
  }
}

function _injectBgCarouselEngine(doc) {
  if (!doc || !doc.head) return;
  _ensureImageAnimationStyles(doc);
  if (!doc.getElementById('__wb_bg_carousel_styles')) {
    const styleEl = doc.createElement('style');
    styleEl.id = '__wb_bg_carousel_styles';
    styleEl.textContent = `
      .__wb_bg_carousel{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:0}
      .__wb_bg_carousel .__wb_bg_slide{position:absolute;inset:0;background-size:cover;background-position:center;background-repeat:no-repeat;transition:transform .9s ease,opacity .9s ease;will-change:transform,opacity}
      .__wb_bg_carousel .__wb_bg_slide.out{transform:translateX(-14%);opacity:0}
      .__wb_bg_carousel .__wb_bg_slide.in{transform:translateX(0);opacity:1}
      .__wb_bg_carousel[data-style='slide-right'] .__wb_bg_slide.out{transform:translateX(14%);opacity:0}
      .__wb_bg_carousel[data-style='fade'] .__wb_bg_slide.out{transform:none;opacity:0}
      .__wb_bg_carousel[data-style='fade'] .__wb_bg_slide.in{transform:none;opacity:1}
      .__wb_bg_carousel[data-style='zoom'] .__wb_bg_slide.out{transform:scale(1.08);opacity:0}
      .__wb_bg_carousel[data-style='zoom'] .__wb_bg_slide.in{transform:scale(1);opacity:1}
      .__wb_bg_carousel[data-style='parallax'] .__wb_bg_slide.out{transform:translateX(-6%) scale(1.06);opacity:0}
      .__wb_bg_carousel[data-style='parallax'] .__wb_bg_slide.in{transform:translateX(0) scale(1);opacity:1}
      [data-wb-bg-carousel='on']{position:relative;overflow:hidden}
      [data-wb-bg-carousel='on'] > *:not(.__wb_bg_carousel):not(.__wb_badge):not(.__wb_badge_anchor){position:relative;z-index:1}
    `;
    doc.head.appendChild(styleEl);
  }

  if (!doc.getElementById('__wb_bg_carousel_script')) {
    const script = doc.createElement('script');
    script.id = '__wb_bg_carousel_script';
    script.textContent = `(function(){
      function ensure(el){
        if (!el || el.dataset.wbBgCarousel !== 'on') return;
        var urls = (el.dataset.wbBgCarouselUrls || '').split('||').map(function(s){ return s.trim(); }).filter(Boolean);
        if (urls.length < 2) return;
        var interval = Math.max(2000, parseInt(el.dataset.wbBgIntervalMs || '5000', 10) || 5000);
        var overlay = Math.max(0, Math.min(0.8, parseFloat(el.dataset.wbBgOverlay || '0') || 0));
        var size = (el.dataset.wbBgSize || 'cover');
        var style = (el.dataset.wbBgStyle || 'slide-left');
        var speed = Math.max(250, parseInt(el.dataset.wbBgSpeedMs || '900', 10) || 900);
        var layer = el.querySelector('.__wb_bg_carousel');
        var motion = (el.dataset.wbBgMotion || 'none');
        if (!layer) {
          layer = document.createElement('div');
          layer.className = '__wb_bg_carousel';
          layer.innerHTML = '<div class="__wb_bg_slide in"></div><div class="__wb_bg_slide out"></div>';
          el.insertBefore(layer, el.firstChild);
        }
        layer.setAttribute('data-style', style);
        layer.setAttribute('data-motion', motion);
        var a = layer.children[0], b = layer.children[1];
        a.style.backgroundSize = size; b.style.backgroundSize = size;
        a.style.transitionDuration = speed + 'ms';
        b.style.transitionDuration = speed + 'ms';
        var idx = parseInt(el.dataset.wbBgIndex || '0', 10) || 0;
        var cur = urls[idx % urls.length];
        var ov = overlay > 0 ? ('linear-gradient(rgba(0,0,0,'+overlay+'),rgba(0,0,0,'+overlay+')),' ) : '';
        a.style.backgroundImage = ov + 'url("'+cur+'")';
        a.classList.add('in'); a.classList.remove('out');
        b.classList.add('out'); b.classList.remove('in');
        if (el.__wbBgTimer) clearInterval(el.__wbBgTimer);
        el.__wbBgTimer = setInterval(function(){
          idx = (idx + 1) % urls.length;
          var next = urls[idx];
          b.style.backgroundImage = ov + 'url("'+next+'")';
          b.classList.remove('out'); b.classList.add('in');
          a.classList.remove('in'); a.classList.add('out');
          var t = a; a = b; b = t;
          el.dataset.wbBgIndex = String(idx);
        }, interval);
      }
      function run(){ document.querySelectorAll('[data-wb-bg-carousel="on"]').forEach(ensure); }
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
      window.__wbRefreshBgCarousel = run;
    })();`;
    doc.body ? doc.body.appendChild(script) : doc.head.appendChild(script);
  }
}

function _applyBgToEl(el) {
  const doc    = el.ownerDocument;
  const target = _bgTarget(el);
  const wbId   = _ensureWbId(target);

  const urls    = _parseBgUrls();
  const fallbackUrl = _normalizeStagingAssetUrl(document.getElementById('secBgUrl')?.value?.trim() || '');
  const finalUrls = urls.length ? urls : (fallbackUrl ? [fallbackUrl] : []);
  const url     = finalUrls[0] || '';
  const color   = document.getElementById('secBgColor')?.value || '#ffffff';
  const opacity = (document.getElementById('secBgOpacity')?.value ?? 100) / 100;
  const size    = document.getElementById('secBgSize')?.value || 'cover';
  const overlay = (document.getElementById('secBgOverlay')?.value ?? 0) / 100;
  const carouselEnabled = !!document.getElementById('secBgCarouselEnabled')?.checked && finalUrls.length > 1;
  const intervalSec = Math.max(2, parseInt(document.getElementById('secBgInterval')?.value || '5', 10) || 5);
  const style = document.getElementById('secBgStyle')?.value || 'slide-left';
  const speedMs = Math.max(250, parseInt(document.getElementById('secBgSpeed')?.value || '900', 10) || 900);
  const bgMotion = document.getElementById('secBgMotion')?.value || 'none';

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

  target.dataset.wbBgMotion = bgMotion;
  target.style.removeProperty('animation');
  target.style.removeProperty('background-size');
  target.style.removeProperty('background-position');
  target.style.removeProperty('filter');
  if (bgMotion === 'drift') {
    target.style.setProperty('animation', 'wbBgDrift 16s ease-in-out infinite', 'important');
  } else if (bgMotion === 'zoom') {
    target.style.setProperty('animation', 'wbBgZoom 18s ease-in-out infinite', 'important');
  } else if (bgMotion === 'pulse') {
    target.style.setProperty('animation', 'wbBgPulse 8s ease-in-out infinite', 'important');
  }

  if (carouselEnabled) {
    target.dataset.wbBgCarousel = 'on';
    target.dataset.wbBgCarouselUrls = finalUrls.join('||');
    target.dataset.wbBgIntervalMs = String(intervalSec * 1000);
    target.dataset.wbBgOverlay = String(overlay);
    target.dataset.wbBgSize = size;
    target.dataset.wbBgStyle = style;
    target.dataset.wbBgSpeedMs = String(speedMs);
    target.dataset.wbBgMotion = bgMotion;
    _injectBgCarouselEngine(doc);
    if (doc.defaultView && typeof doc.defaultView.__wbRefreshBgCarousel === 'function') {
      doc.defaultView.__wbRefreshBgCarousel();
    }
  } else {
    delete target.dataset.wbBgCarousel;
    delete target.dataset.wbBgCarouselUrls;
    delete target.dataset.wbBgIntervalMs;
    delete target.dataset.wbBgOverlay;
    delete target.dataset.wbBgSize;
    delete target.dataset.wbBgStyle;
    delete target.dataset.wbBgSpeedMs;
    delete target.dataset.wbBgMotion;
    const layer = target.querySelector('.__wb_bg_carousel');
    if (layer) layer.remove();
    if (target.__wbBgTimer) { clearInterval(target.__wbBgTimer); target.__wbBgTimer = null; }
  }
}

async function uploadBgImage(inputEl) {
  const files = [...(inputEl.files || [])];
  if (!files.length) return;
  inputEl.value = '';

  const _currentSiteSlugForFinalize = () => {
    const site = (websites || []).find(x => x.website_id === stagedWebsiteId);
    const localPath = String(site?.local_path || '').replace(/\\/g, '/').replace(/\/+$/, '');
    if (localPath) {
      const segs = localPath.split('/').filter(Boolean);
      return segs[segs.length - 1] || '';
    }
    const m = String(currentStagingUrl || '').match(/\/output\/staging\/([^/]+)/i);
    return m ? m[1] : '';
  };

  const _extractUploadedFilename = (url) => {
    const m = String(url || '').match(/assets\/uploads\/([^/?#]+)/i);
    return m ? m[1] : '';
  };

  const _finalizeUploadedAssetUrl = async (url) => {
    const filename = _extractUploadedFilename(url);
    if (!filename || !stagedWebsiteId) return url;
    const siteSlug = _currentSiteSlugForFinalize();
    if (!siteSlug) return url;
    try {
      const r = await fetch(`${API}/media/finalize-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ website_id: stagedWebsiteId, site_slug: siteSlug, filename }),
      });
      if (!r.ok) return url;
      const data = await r.json();
      return _normalizeStagingAssetUrl(data.image_url || url);
    } catch (_) {
      return url;
    }
  };

  const appendUrl = (url) => {
    const ta = document.getElementById('secBgUrls');
    if (ta) {
      const urls = _parseBgUrls();
      if (!urls.includes(url)) urls.push(url);
      ta.value = urls.join('\n');
    }
    const first = _parseBgUrls()[0] || '';
    const inp = document.getElementById('secBgUrl');
    if (inp) inp.value = first;
    _syncBgStrip();
  };

  const uploadBlob = async (blob, name = 'image.png') => {
    const fd = new FormData();
    fd.append('file', blob, name);
    if (stagedWebsiteId) fd.append('website_id', stagedWebsiteId);
    const r = await fetch(`${API}/media/upload-image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (r.ok) {
      const data = await r.json();
      const uploadedUrl = _normalizeStagingAssetUrl(data.full_url || data.thumb_url || '');
      const finalUrl = await _finalizeUploadedAssetUrl(uploadedUrl);
      appendUrl(finalUrl);
      return true;
    } else {
      return false;
    }
  };

  // Always open crop editor per file — user clicks "＋ Add" for each image
  openImageEditor(files[0], async blob => {
    const ok = await uploadBlob(blob, files[0].name || 'image.png');
    if (ok) {
      previewBg();
      toast('Image added to carousel ✅');
    } else {
      toast('Upload failed', false);
    }
  });
}

function _syncBgStrip() {
  const strip = document.getElementById('secBgStrip');
  if (!strip) return;
  const urls = _parseBgUrls();
  // Rebuild thumbnails based on selected media paths.
  const tiles = urls.map((u, i) => {
    const div = document.createElement('div');
    div.style.cssText = 'position:relative;width:64px;height:48px;border-radius:5px;overflow:hidden;border:1.5px solid var(--border);flex-shrink:0';
    div.title = _displayBgImageName(u);
    div.innerHTML = `<img src="${_toPreviewMediaUrl(u)}" style="width:100%;height:100%;object-fit:cover">
      <button type="button" onclick="removeBgImageAt(${i})" title="Remove"
        style="position:absolute;top:1px;right:1px;background:rgba(0,0,0,.6);color:#fff;border:none;border-radius:3px;width:16px;height:16px;font-size:9px;cursor:pointer;line-height:1;display:flex;align-items:center;justify-content:center">✕</button>
      <div style="position:absolute;bottom:1px;left:2px;background:rgba(0,0,0,.55);color:#fff;font-size:8px;padding:0 3px;border-radius:2px">${i+1}</div>`;
    return div;
  });
  strip.innerHTML = '';
  tiles.forEach(t => strip.appendChild(t));
  _refreshBgNameList();
}

function removeBgImageAt(idx) {
  const ta = document.getElementById('secBgUrls');
  if (!ta) return;
  const urls = _parseBgUrls();
  urls.splice(idx, 1);
  ta.value = urls.join('\n');
  const inp = document.getElementById('secBgUrl');
  if (inp) inp.value = urls[0] || '';
  _syncBgStrip();
  _refreshBgNameList();
  _previewBgDebounced();
}

function addBgImageUrl() {
  const inp = document.getElementById('secBgAddUrl');
  if (!inp) return;
  const url = _normalizeStagingAssetUrl(inp.value.trim());
  if (!url) return;
  const ta = document.getElementById('secBgUrls');
  if (ta) {
    const urls = _parseBgUrls();
    if (!urls.includes(url)) {
      urls.push(url);
      ta.value = urls.join('\n');
    }
  }
  const first = _parseBgUrls()[0] || '';
  const singleInp = document.getElementById('secBgUrl');
  if (singleInp) singleInp.value = first;
  inp.value = '';
  _refreshBgNameList();
  _previewBgDebounced();
  toast('Image URL added ✅');
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
  delete target.dataset.wbBgCarousel;
  delete target.dataset.wbBgCarouselUrls;
  delete target.dataset.wbBgIntervalMs;
  delete target.dataset.wbBgOverlay;
  delete target.dataset.wbBgSize;
  const layer = target.querySelector('.__wb_bg_carousel');
  if (layer) layer.remove();
  if (target.__wbBgTimer) { clearInterval(target.__wbBgTimer); target.__wbBgTimer = null; }
  const inp = document.getElementById('secBgUrl');
  if (inp) inp.value = '';
  const ta = document.getElementById('secBgUrls');
  if (ta) ta.value = '';
  const thumb = document.getElementById('bgThumb');
  if (thumb && thumb.tagName === 'IMG') thumb.src = '';
  const c = document.getElementById('secBgColor');
  if (c) c.value = '#ffffff';
  const cb = document.getElementById('secBgCarouselEnabled');
  if (cb) cb.checked = false;
  const styleSel = document.getElementById('secBgStyle');
  if (styleSel) styleSel.value = 'slide-left';
  const speedSel = document.getElementById('secBgSpeed');
  if (speedSel) speedSel.value = '900';
  const motionSel = document.getElementById('secBgMotion');
  if (motionSel) motionSel.value = 'none';
  delete target.dataset.wbBgStyle;
  delete target.dataset.wbBgSpeedMs;
  delete target.dataset.wbBgMotion;
  toggleBgCarouselOptions();
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
  const align = _normalizeTextAlignValue(init.align || 'left');
  const alignOpts = ['left', 'center', 'right', 'justify']
    .map((v) => `<option value="${v}"${align === v ? ' selected' : ''}>${v.charAt(0).toUpperCase() + v.slice(1)}</option>`)
    .join('');
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
    <select data-fid="${fid}-align" title="Text alignment"
      style="padding:3px 5px;background:var(--bg);border:1px solid var(--border);border-radius:5px;color:var(--text);font-size:.72rem;width:86px"
      onchange="previewFieldStyle('${fid}')">${alignOpts}</select>
    <input type="color" data-fid="${fid}-color" value="${initColor}" title="Text colour"
      oninput="_previewFieldStyleDebounced('${fid}')" onchange="previewFieldStyle('${fid}')"
      style="width:30px;height:26px;padding:1px;border:1px solid var(--border);border-radius:5px;cursor:pointer;background:var(--bg)">
    <button data-fid="${fid}-bold" title="Bold" onclick="toggleStyleBtn(this,'${fid}','bold')"
      style="width:26px;height:26px;border:1px solid var(--border);border-radius:5px;background:var(--bg);cursor:pointer;font-weight:700;color:var(--text);font-size:.85rem;${isBold}">B</button>
    <button data-fid="${fid}-italic" title="Italic" onclick="toggleStyleBtn(this,'${fid}','italic')"
      style="width:26px;height:26px;border:1px solid var(--border);border-radius:5px;background:var(--bg);cursor:pointer;font-style:italic;color:var(--text);font-size:.85rem;${isItalic}"><em>I</em></button>
  </div>`;
}

function _textField(idx, tag, val, fid, init = {}, opts = {}) {
  const clickable = !!opts.clickable;
  const clickInit = opts.clickInit || {};
  return `<div data-fid="${fid}" data-type="text" data-tag="${tag}">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <input type="text" value="${_esc(val)}" data-fid="${fid}"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.88rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    ${_styleBar(fid, init)}
    ${clickable ? _clickActionField(fid, clickInit) : ''}
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

function _linkField(idx, tag, text, href, fid, init = {}) {
  const bgEnabled = init.bgEnabled ? 'checked' : '';
  const hoverEnabled = init.hoverEnabled ? 'checked' : '';
  const bgDisabled = init.bgEnabled ? '' : 'disabled';
  const hoverDisabled = init.hoverEnabled ? '' : 'disabled';
  const bgColor = init.bgColor || '#111827';
  const textColor = init.textColor || '#ffffff';
  const hoverBgColor = init.hoverBgColor || '#374151';
  const hoverTextColor = init.hoverTextColor || textColor;
  return `<div data-fid="${fid}" data-type="link" style="position:relative">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <input type="text" value="${_esc(text)}" data-fid="${fid}-text" placeholder="Link label"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.88rem;outline:none;margin-bottom:4px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <input type="text" value="${_esc(href)}" placeholder="href e.g. #section or https://…" data-fid="${fid}-href"
      style="width:100%;padding:8px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.8rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px;padding:8px;border:1px solid var(--border);border-radius:6px;background:rgba(99,102,241,.04)">
      <label style="display:flex;align-items:center;gap:5px;font-size:.72rem;color:var(--muted)">
        <input type="checkbox" data-fid="${fid}-bg-enabled" ${bgEnabled} onchange="toggleLinkStyleInput('${fid}','bg')">
        Background
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted)">
        Color
        <input type="color" data-fid="${fid}-bg" value="${bgColor}" ${bgDisabled} style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:4px;background:var(--bg)">
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted)">
        Text
        <input type="color" data-fid="${fid}-text-color" value="${textColor}" style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:4px;background:var(--bg)">
      </label>
      <label style="display:flex;align-items:center;gap:5px;font-size:.72rem;color:var(--muted)">
        <input type="checkbox" data-fid="${fid}-hover-bg-enabled" ${hoverEnabled} onchange="toggleLinkStyleInput('${fid}','hover-bg')">
        Hover BG
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted)">
        Hover Color
        <input type="color" data-fid="${fid}-hover-bg" value="${hoverBgColor}" ${hoverDisabled} style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:4px;background:var(--bg)">
      </label>
      <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted)">
        Hover Text
        <input type="color" data-fid="${fid}-hover-text-color" value="${hoverTextColor}" ${hoverDisabled} style="width:28px;height:22px;padding:0;border:1px solid var(--border);border-radius:4px;background:var(--bg)">
      </label>
    </div>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-secondary btn-sm" style="flex:1" onclick="addSectionLink(this)">＋ Add Link After</button>
      <button class="btn btn-secondary btn-sm" style="color:#ef4444;border-color:rgba(239,68,68,.4)" onclick="removeSectionLink(this, '${fid}')">🗑 Remove</button>
    </div>
  </div>`;
}

function _clickActionField(fid, init = {}) {
  const enabled = !!init.enabled;
  const mode = ['popup', 'newtab', 'same'].includes(init.mode) ? init.mode : 'popup';
  const url = _normalizeClickActionUrl(init.url || '');
  const pages = _stagingHtmlPages(currentStagingArtifacts, currentStagingEntryPath);
  const selectedInternal = _matchInternalClickActionPath(url, pages);
  const badgeOn = enabled && !!url;
  const disabled = enabled ? '' : 'disabled';
  return `<div style="margin-top:6px;padding:8px;border:1px solid var(--border);border-radius:6px;background:rgba(99,102,241,.04)">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
      <label style="display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--muted)">
        <input type="checkbox" data-fid="${fid}-click-enabled" ${enabled ? 'checked' : ''} onchange="toggleClickActionInputs('${fid}');_previewClickActionFromEditor('${fid}')">
        Enable click action
      </label>
      <span data-fid="${fid}-click-badge" style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;border:1px solid ${badgeOn ? 'rgba(34,197,94,.45)' : 'var(--border)'};background:${badgeOn ? 'rgba(34,197,94,.14)' : 'rgba(255,255,255,.02)'};color:${badgeOn ? 'var(--success)' : 'var(--muted)'};font-size:.66rem;font-weight:700;letter-spacing:.35px;text-transform:uppercase">${badgeOn ? 'Link On' : 'Link Off'}</span>
    </div>
    <div style="margin-top:6px">
      <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Internal page</label>
      <select data-fid="${fid}-click-page" ${disabled} onchange="onClickActionInternalPageChange('${fid}');_previewClickActionFromEditor('${fid}')"
        style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="">Custom / external URL</option>
        ${pages.map((p) => `<option value="${_esc(p)}"${p === selectedInternal ? ' selected' : ''}>${_esc(_pageDisplayNameFromPath(p))}</option>`).join('')}
      </select>
    </div>
    <input type="text" data-fid="${fid}-click-url" value="${_esc(url)}" placeholder="https://example.com/page"
      ${disabled}
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;margin-top:6px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" oninput="syncClickActionInternalPageSelection('${fid}');_refreshClickActionBadge('${fid}');_previewClickActionFromEditor('${fid}')" />
    <div style="margin-top:6px">
      <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Target action</label>
      <select data-fid="${fid}-click-mode" ${disabled} onchange="_previewClickActionFromEditor('${fid}')"
        style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="popup" ${mode === 'popup' ? 'selected' : ''}>Popup (themed)</option>
        <option value="newtab" ${mode === 'newtab' ? 'selected' : ''}>Open in new tab</option>
        <option value="same" ${mode === 'same' ? 'selected' : ''}>Open in same tab</option>
      </select>
    </div>
  </div>`;
}

function _refreshClickActionBadge(fid) {
  const enabled = !!document.querySelector(`[data-fid="${fid}-click-enabled"]`)?.checked;
  const url = String(document.querySelector(`[data-fid="${fid}-click-url"]`)?.value || '').trim();
  const badge = document.querySelector(`[data-fid="${fid}-click-badge"]`);
  if (!badge) return;
  const isOn = enabled && !!url;
  badge.textContent = isOn ? 'Link On' : 'Link Off';
  badge.style.borderColor = isOn ? 'rgba(34,197,94,.45)' : 'var(--border)';
  badge.style.background = isOn ? 'rgba(34,197,94,.14)' : 'rgba(255,255,255,.02)';
  badge.style.color = isOn ? 'var(--success)' : 'var(--muted)';
}

function _relativeHrefBetweenPages(fromEntryPath, toEntryPath) {
  const from = _normalizeStagingPagePath(fromEntryPath || currentStagingEntryPath || 'index.html');
  const to = _normalizeStagingPagePath(toEntryPath || '');
  if (!from || !to) return '';
  if (from === to) return '#';

  const fromParts = from.split('/');
  fromParts.pop();
  const toParts = to.split('/');

  while (fromParts.length && toParts.length && fromParts[0] === toParts[0]) {
    fromParts.shift();
    toParts.shift();
  }
  return `${'../'.repeat(fromParts.length)}${toParts.join('/')}` || '#';
}

function _matchInternalClickActionPath(rawUrl, pages) {
  const clean = String(rawUrl || '').trim().split('#')[0].split('?')[0];
  if (!clean) return '';
  const list = Array.isArray(pages) ? pages : _stagingHtmlPages(currentStagingArtifacts, currentStagingEntryPath);
  for (const p of list) {
    const rel = _relativeHrefBetweenPages(currentStagingEntryPath, p);
    if (clean === rel || clean === p || clean === `/${p}`) return p;
  }
  return '';
}

function onClickActionInternalPageChange(fid) {
  const pageEl = document.querySelector(`[data-fid="${fid}-click-page"]`);
  const urlEl = document.querySelector(`[data-fid="${fid}-click-url"]`);
  if (!pageEl || !urlEl) return;
  const pagePath = String(pageEl.value || '').trim();
  if (!pagePath) return;
  urlEl.value = _relativeHrefBetweenPages(currentStagingEntryPath, pagePath);
  _refreshClickActionBadge(fid);
}

function syncClickActionInternalPageSelection(fid) {
  const pageEl = document.querySelector(`[data-fid="${fid}-click-page"]`);
  const urlEl = document.querySelector(`[data-fid="${fid}-click-url"]`);
  if (!pageEl || !urlEl) return;
  const pages = _stagingHtmlPages(currentStagingArtifacts, currentStagingEntryPath);
  pageEl.value = _matchInternalClickActionPath(urlEl.value, pages) || '';
}

function toggleClickActionInputs(fid) {
  const enabled = !!document.querySelector(`[data-fid="${fid}-click-enabled"]`)?.checked;
  const pageEl = document.querySelector(`[data-fid="${fid}-click-page"]`);
  const urlEl = document.querySelector(`[data-fid="${fid}-click-url"]`);
  const modeEl = document.querySelector(`[data-fid="${fid}-click-mode"]`);
  if (pageEl) pageEl.disabled = !enabled;
  if (urlEl) urlEl.disabled = !enabled;
  if (modeEl) modeEl.disabled = !enabled;
  _refreshClickActionBadge(fid);
}

function _previewClickActionFromEditor(fid) {
  const frame = document.getElementById('stagingIframe');
  if (!frame?.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const { el } = stagingSections[activeSectionIndex];
  const fieldsEl = document.getElementById('secEditorFields');
  if (!fieldsEl) return;
  const targets = _getFidTargets(el, fid);
  if (!targets.length) return;
  targets.forEach((t) => _applyClickActionFromField(fieldsEl, fid, t));
  const status = document.getElementById('stagingStatusBar');
  if (status) status.textContent = 'Preview updated — unsaved. Click 💾 Save Changes.';
}

function _ensureWbClickActionEngine(doc) {
  if (!doc || !doc.head) return;
  if (!doc.getElementById('__wb_click_action_style')) {
    const st = doc.createElement('style');
    st.id = '__wb_click_action_style';
    st.textContent = `
      .__wb_action_overlay{position:fixed;inset:0;background:rgba(10,15,25,.55);display:none;align-items:center;justify-content:center;z-index:999999}
      .__wb_action_overlay.open{display:flex}
      .__wb_action_modal{width:min(92vw,980px);height:min(86vh,760px);background:var(--card,#fff);color:var(--text,#111827);border-radius:14px;box-shadow:0 22px 64px rgba(0,0,0,.35);border:1px solid color-mix(in srgb, var(--primary,#2563eb) 20%, transparent);display:flex;flex-direction:column;overflow:hidden}
      .__wb_action_hd{display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:linear-gradient(90deg, color-mix(in srgb, var(--primary,#2563eb) 14%, white), color-mix(in srgb, var(--secondary,#38bdf8) 10%, white));border-bottom:1px solid color-mix(in srgb, var(--primary,#2563eb) 18%, transparent)}
      .__wb_action_title{font-size:.84rem;font-weight:700;opacity:.9}
      .__wb_action_btns{display:flex;gap:8px}
      .__wb_action_btn{border:1px solid var(--border,#d1d5db);background:var(--bg,#f8fafc);color:var(--text,#111827);border-radius:8px;padding:5px 9px;font-size:.75rem;cursor:pointer}
      .__wb_action_btn.close{font-weight:700}
      .__wb_action_btn.open{display:inline-flex;align-items:center;justify-content:center;width:32px;height:30px;padding:0}
      .__wb_action_btn.open svg{width:15px;height:15px;display:block;fill:currentColor}
      .__wb_action_fallback{display:none;margin:10px 12px;padding:10px 12px;border-radius:10px;border:1px solid color-mix(in srgb, var(--primary,#2563eb) 24%, transparent);background:color-mix(in srgb, var(--primary,#2563eb) 8%, white);font-size:.78rem;line-height:1.35}
      .__wb_action_fallback.open{display:block}
      .__wb_action_frame{width:100%;height:100%;border:0;background:#fff}
      [data-wb-click-enabled="1"]{cursor:pointer}
    `;
    doc.head.appendChild(st);
  }
  if (!doc.getElementById('__wb_click_action_script')) {
    const sc = doc.createElement('script');
    sc.id = '__wb_click_action_script';
    sc.textContent = `(function(){
      function normalizeUrl(raw){
        var u = String(raw || '').trim();
        if (!u) return '';
        if (/^(https?:|mailto:|tel:|#|\\/)/i.test(u)) return u;
        if (/^\\/\\//.test(u)) return 'https:' + u;
        if (/^[a-z0-9.-]+\\.[a-z]{2,}(?:[/:?#].*)?$/i.test(u)) return 'https://' + u;
        return u;
      }
      function ensureOverlay(){
        var o = document.querySelector('.__wb_action_overlay');
        if (o) return o;
        o = document.createElement('div');
        o.className = '__wb_action_overlay';
        o.innerHTML = '<div class="__wb_action_modal"><div class="__wb_action_hd"><span class="__wb_action_title">Quick View</span><div class="__wb_action_btns"><button class="__wb_action_btn open" aria-label="Open in new tab" title="Open in new tab"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3z"></path><path d="M5 5h6V3H3v8h2V5zm0 14h14v-6h2v8H3v-8h2v6z"></path></svg></button><button class="__wb_action_btn close" aria-label="Close">✕</button></div></div><div class="__wb_action_fallback" role="status" aria-live="polite"></div><iframe class="__wb_action_frame" src="about:blank" loading="lazy"></iframe></div>';
        document.body.appendChild(o);
        o.addEventListener('click', function(e){ if (e.target === o) close(); });
        o.querySelector('.close').addEventListener('click', close);
        o.querySelector('.open').addEventListener('click', function(){
          var u = o.dataset.url || '';
          if (u) window.open(u, '_blank', 'noopener');
        });
        return o;
      }
      function setFallback(o, isVisible, text){
        var box = o.querySelector('.__wb_action_fallback');
        if (!box) return;
        if (isVisible) {
          box.textContent = text || 'This page may block embedding in an iframe. Use Open in new tab to continue.';
          box.classList.add('open');
        } else {
          box.textContent = '';
          box.classList.remove('open');
        }
      }
      function monitorEmbed(o, url){
        var frame = o.querySelector('.__wb_action_frame');
        if (!frame) return;
        if (o.__wbEmbedTimer) {
          clearTimeout(o.__wbEmbedTimer);
          o.__wbEmbedTimer = null;
        }
        setFallback(o, false, '');
        frame.onload = function(){
          if (o.__wbEmbedTimer) {
            clearTimeout(o.__wbEmbedTimer);
            o.__wbEmbedTimer = null;
          }
          try {
            var currentHref = String(frame.contentWindow && frame.contentWindow.location && frame.contentWindow.location.href || '');
            var isExternal = /^https?:/i.test(url);
            if (isExternal && currentHref === 'about:blank') {
              setFallback(o, true, 'This site appears to block iframe embedding. Use Open in new tab to view it.');
              return;
            }
          } catch (_e) {
            // Cross-origin frame loaded; not inspectable, which is expected.
          }
          setFallback(o, false, '');
        };
        frame.onerror = function(){
          if (o.__wbEmbedTimer) {
            clearTimeout(o.__wbEmbedTimer);
            o.__wbEmbedTimer = null;
          }
          setFallback(o, true, 'Unable to load this page in the popup. Use Open in new tab to continue.');
        };
        o.__wbEmbedTimer = setTimeout(function(){
          setFallback(o, true, 'Loading is taking longer than expected. This site may block iframe embedding. Use Open in new tab.');
        }, 4500);
      }
      function open(url){
        url = normalizeUrl(url);
        if (!url) return;
        var o = ensureOverlay();
        o.dataset.url = url;
        monitorEmbed(o, url);
        o.querySelector('.__wb_action_frame').src = url;
        o.classList.add('open');
      }
      function close(){
        var o = document.querySelector('.__wb_action_overlay');
        if (!o) return;
        if (o.__wbEmbedTimer) {
          clearTimeout(o.__wbEmbedTimer);
          o.__wbEmbedTimer = null;
        }
        setFallback(o, false, '');
        o.classList.remove('open');
        o.querySelector('.__wb_action_frame').src = 'about:blank';
      }
      function onClick(ev){
        var n = ev.target.closest('[data-wb-click-enabled="1"]');
        if (!n) return;
        var url = normalizeUrl(n.dataset.wbClickUrl || '');
        var mode = (n.dataset.wbClickMode || 'popup').trim();
        if (!url) return;
        ev.preventDefault();
        ev.stopPropagation();
        if (mode === 'newtab') window.open(url, '_blank', 'noopener');
        else if (mode === 'same') window.location.href = url;
        else open(url);
      }
      function onKey(ev){
        if (ev.key !== 'Enter' && ev.key !== ' ') return;
        var n = ev.target.closest('[data-wb-click-enabled="1"]');
        if (!n) return;
        ev.preventDefault();
        n.click();
      }
      function applyBindings(){
        document.querySelectorAll('[data-wb-click-enabled="1"]').forEach(function(n){
          n.setAttribute('tabindex', '0');
          n.setAttribute('role', 'button');
        });
      }
      if (!document.__wbClickBound){
        document.addEventListener('click', onClick, true);
        document.addEventListener('keydown', onKey, true);
        document.__wbClickBound = true;
      }
      window.__wbOpenActionPopup = open;
      window.__wbCloseActionPopup = close;
      window.__wbApplyClickBindings = applyBindings;
      applyBindings();
    })();`;
    (doc.body || doc.head).appendChild(sc);
  }
}

function _applyClickActionFromField(fieldsEl, fid, domEl) {
  if (!domEl) return;
  const enabledEl = fieldsEl.querySelector(`[data-fid="${fid}-click-enabled"]`);
  if (!enabledEl) return;
  const url = _normalizeClickActionUrl((fieldsEl.querySelector(`[data-fid="${fid}-click-url"]`)?.value || '').trim());
  const mode = (fieldsEl.querySelector(`[data-fid="${fid}-click-mode"]`)?.value || 'popup').trim();
  const enabled = !!enabledEl.checked && !!url;
  if (enabled) {
    domEl.dataset.wbClickEnabled = '1';
    domEl.dataset.wbClickUrl = url;
    domEl.dataset.wbClickMode = ['popup','newtab','same'].includes(mode) ? mode : 'popup';
    domEl.style.setProperty('cursor', 'pointer', 'important');
    // Some templates disable image pointer events; force-enable so click actions work on images too.
    if (domEl.tagName === 'IMG') {
      domEl.style.setProperty('pointer-events', 'auto', 'important');
    }
  } else {
    delete domEl.dataset.wbClickEnabled;
    delete domEl.dataset.wbClickUrl;
    delete domEl.dataset.wbClickMode;
    domEl.style.removeProperty('cursor');
    if (domEl.tagName === 'IMG') {
      domEl.style.removeProperty('pointer-events');
    }
    domEl.removeAttribute('tabindex');
    domEl.removeAttribute('role');
  }
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
  newEl.innerHTML = _linkField(newIdx, 'New Link', '', '', fid, {
    bgEnabled: false,
    bgColor: '#111827',
    textColor: '#ffffff',
    hoverEnabled: false,
    hoverBgColor: '#374151',
    hoverTextColor: '#ffffff',
  });
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

function _imgField(idx, tag, src, alt, fid, init = {}) {
  const mode = init.mode || 'none';
  const mediaType = String(init.mediaType || 'image').trim().toLowerCase();
  const isFileMedia = mediaType !== 'social';
  const sourceLabel = mediaType === 'video' ? 'Video source' : (mediaType === 'social' ? 'Social URL' : 'Image source');
  const sourceDisplay = isFileMedia ? _friendlyMediaSourceLabel(src) : src;
  const clickInit = init.click || {};
  const animDisabled = mediaType !== 'image' ? 'disabled style="opacity:.55"' : '';
  const previewHtml = _renderImageMediaPreviewHtml(mediaType, src, alt, _deriveSocialProvider(src));
  return `<div data-fid="${fid}" data-type="img">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);display:block;margin-bottom:4px">${idx}. ${tag}</label>
    <div style="margin:4px 0 6px">
      <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Media type</label>
      <select data-fid="${fid}-media-type" onchange="_syncImageMediaFieldUI('${fid}')" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="image" ${mediaType === 'image' ? 'selected' : ''}>Image</option>
        <option value="video" ${mediaType === 'video' ? 'selected' : ''}>Video</option>
        <option value="social" ${mediaType === 'social' ? 'selected' : ''}>Social Link</option>
      </select>
    </div>
    <div data-fid="${fid}-preview">${previewHtml}</div>
    <input type="text" value="${_esc(src)}" placeholder="${_esc(sourceLabel)}" data-fid="${fid}-src" oninput="_updateImageMediaPreview('${fid}')"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;margin-top:6px;display:${isFileMedia ? 'none' : 'block'}"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <input type="text" value="${_esc(sourceDisplay)}" data-fid="${fid}-src-display" readonly title="${_esc(src)}"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;margin-top:6px;display:${isFileMedia ? 'block' : 'none'}"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <input type="text" value="${_esc(alt)}" placeholder="Alt text / link label" data-fid="${fid}-alt" oninput="_updateImageMediaPreview('${fid}')"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--muted);font-size:.8rem;outline:none;margin-top:4px"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'" />
    <div style="margin-top:6px">
      <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Image animation</label>
      <select data-fid="${fid}-anim" ${animDisabled} style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="none" ${mode === 'none' ? 'selected' : ''}>None</option>
        <option value="float" ${mode === 'float' ? 'selected' : ''}>Float</option>
        <option value="zoom" ${mode === 'zoom' ? 'selected' : ''}>Zoom Pulse</option>
        <option value="fade-in" ${mode === 'fade-in' ? 'selected' : ''}>Fade In</option>
        <option value="sway" ${mode === 'sway' ? 'selected' : ''}>Sway</option>
      </select>
    </div>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyImgAnimPreset('${fid}','subtle')">Subtle</button>
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyImgAnimPreset('${fid}','medium')">Medium</button>
      <button type="button" class="btn btn-secondary btn-sm" style="flex:1" onclick="applyImgAnimPreset('${fid}','bold')">Bold</button>
    </div>
    <div style="display:flex;gap:6px;margin-top:6px">
      <button class="btn btn-secondary btn-sm" onclick="openImageFieldMediaPicker('${fid}')" title="Choose media from uploaded library" style="flex:1">🗂 Choose From Media Library</button>
    </div>
    ${_clickActionField(fid, clickInit)}
  </div>`;
}

function _esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function _getDeepTextTarget(el) {
  let target = el;
  while (target.children.length === 1) {
    const child = target.children[0];
    const tag = child.tagName;
    if (['SPAN','EM','STRONG','B','I','MARK','SMALL'].includes(tag)) {
      target = child;
    } else break;
  }
  return target;
}

function _setParagraphText(el, text) {
  const target = _getDeepTextTarget(el);
  const raw = String(text || '');
  if (raw.includes('\n')) {
    target.innerHTML = _esc(raw).replace(/\r?\n/g, '<br>');
    target.style.setProperty('white-space', 'normal', 'important');
  } else {
    target.textContent = raw;
  }
}

function _splitParagraphText(rawText) {
  const normalized = String(rawText || '').replace(/\r\n/g, '\n').trim();
  if (!normalized) return [];
  return normalized
    .split(/(?:\n\s*){2,}/)
    .map(part => part.replace(/\n+/g, ' ').trim())
    .filter(Boolean);
}

function _getLogicalParagraphText(el) {
  const rawHtml = String(el?.innerHTML || '');
  const rawText = rawHtml
    ? (() => {
        const tmp = el?.ownerDocument?.createElement('div');
        if (!tmp) return String(el?.innerText || el?.textContent || '').replace(/\u00a0/g, ' ').replace(/\r\n/g, '\n');
        tmp.innerHTML = rawHtml.replace(/<br\s*\/?\s*>/gi, '\n');
        return String(tmp.textContent || '').replace(/\u00a0/g, ' ').replace(/\r\n/g, '\n');
      })()
    : String(el?.innerText || el?.textContent || '').replace(/\u00a0/g, ' ').replace(/\r\n/g, '\n');
  return _splitParagraphText(rawText);
}

function _paragraphDisplayText(parts) {
  return parts.join('\n\n');
}

function _normalizeStagingAssetUrl(rawUrl) {
  const raw = String(rawUrl || '').trim();
  if (!raw) return '';

  if (/^assets\//i.test(raw)) return raw;
  if (/^\/assets\//i.test(raw)) return raw.replace(/^\//, '');

  const fromStagingPath = (p) => {
    const m = String(p || '').match(/\/output\/staging\/[^/]+\/(.+)$/i);
    return (m && m[1]) ? m[1] : null;
  };

  if (/^\/output\/staging\//i.test(raw)) {
    return fromStagingPath(raw) || raw;
  }

  try {
    const u = new URL(raw, window.location.origin);
    const rel = fromStagingPath(u.pathname);
    if (rel) return rel;
  } catch (_) {
    // Keep unparseable values as-is
  }

  return raw;
}

function _normalizeClickActionUrl(rawUrl) {
  const raw = String(rawUrl || '').trim();
  if (!raw) return '';
  if (/^(https?:|mailto:|tel:|#|\/)/i.test(raw)) return raw;
  if (/^\/\//.test(raw)) return 'https:' + raw;
  // Bare domains like "www.google.com" or "example.org/path"
  if (/^[a-z0-9.-]+\.[a-z]{2,}(?:[/:?#].*)?$/i.test(raw)) return 'https://' + raw;
  return raw;
}

function _allianceRowEditor(rowIdx, data) {
  const logoFid = `ar-${rowIdx}-logo`;
  const brandFid = `ar-${rowIdx}-brand`;
  const categoryFid = `ar-${rowIdx}-category`;
  const supportFid = `ar-${rowIdx}-support`;
  return `<div style="border:1px solid var(--border);border-radius:8px;padding:10px 10px 8px;margin-bottom:8px;background:var(--bg)">
    <label style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin-bottom:6px">Alliance Row ${rowIdx + 1}</label>
    <div style="display:grid;grid-template-columns:1fr;gap:6px">
      <label style="font-size:.7rem;color:var(--muted)">Logo Image URL</label>
      <input data-fid="${logoFid}" type="text" value="${_esc(data.logo || '')}" placeholder="assets/images/logo.jpg"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">

      <label style="font-size:.7rem;color:var(--muted)">Brand</label>
      <input data-fid="${brandFid}" type="text" value="${_esc(data.brand || '')}" placeholder="Brand name"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">

      <label style="font-size:.7rem;color:var(--muted)">Category</label>
      <input data-fid="${categoryFid}" type="text" value="${_esc(data.category || '')}" placeholder="Category"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">

      <label style="font-size:.7rem;color:var(--muted)">Support Offered</label>
      <textarea data-fid="${supportFid}" rows="2" placeholder="Support details"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;resize:vertical"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">${_esc(data.support || '')}</textarea>
    </div>
  </div>`;
}

function _allianceAddRowEditor() {
  return `<div style="border-top:1px dashed var(--border);padding-top:10px;margin-top:8px">
    <label style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin-bottom:6px">＋ Add Alliance Row</label>
    <div style="display:grid;grid-template-columns:1fr;gap:6px">
      <label style="font-size:.7rem;color:var(--muted)">Logo Image URL</label>
      <input id="ar-new-logo" type="text" placeholder="assets/images/new-logo.jpg"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <label style="font-size:.7rem;color:var(--muted)">Brand</label>
      <input id="ar-new-brand" type="text" placeholder="Brand name"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <label style="font-size:.7rem;color:var(--muted)">Category</label>
      <input id="ar-new-category" type="text" placeholder="Category"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <label style="font-size:.7rem;color:var(--muted)">Support Offered</label>
      <textarea id="ar-new-support" rows="2" placeholder="Support details"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;resize:vertical"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'"></textarea>
    </div>
    <div style="margin-top:8px;display:flex;justify-content:flex-end">
      <button class="btn btn-secondary btn-sm" type="button" onclick="addAllianceRowToActiveSection()">＋ Add Row</button>
    </div>
  </div>`;
}

function _isMediaCardCarouselSection(sectionEl) {
  if (!sectionEl) return false;
  const sid = String(sectionEl.id || '').toLowerCase();
  if (sid.includes('media-card-carousel')) return true;
  if (String(sectionEl.dataset?.wbCarousel || '') === '1') return true;
  if (sectionEl.querySelector('[data-wb-carousel="1"], [data-wb-carousel-controls="1"]')) return true;

  const containers = [...sectionEl.querySelectorAll('div,section,article,ul,ol')];
  const hasCarouselRail = containers.some((c) => {
    const cs = sectionEl.ownerDocument.defaultView.getComputedStyle(c);
    const style = c.style || {};
    const gridAutoFlow = String(style.gridAutoFlow || cs.gridAutoFlow || '').toLowerCase();
    const scrollSnap = String(style.scrollSnapType || cs.scrollSnapType || '').toLowerCase();
    const overflowX = String(style.overflowX || cs.overflowX || '').toLowerCase();
    const isLayout = String(cs.display || '').includes('grid') || String(cs.display || '').includes('flex');
    if (!isLayout) return false;
    const kids = [...c.children].filter(k => ['DIV', 'ARTICLE', 'LI', 'SECTION'].includes(k.tagName));
    if (kids.length < 2) return false;
    const imageCards = kids.filter(k => !!k.querySelector('img')).length;
    const textCards = kids.filter(k => !!k.querySelector('h1,h2,h3,h4,h5,p,small')).length;
    if (imageCards < 2 || textCards < 2) return false;
    return gridAutoFlow.includes('column')
      || scrollSnap.includes('x')
      || ['hidden', 'auto', 'scroll', 'clip'].includes(overflowX);
  });
  if (hasCarouselRail) return true;

  const heading = (sectionEl.querySelector('h1,h2,h3')?.textContent || '').trim().toLowerCase();
  return heading.includes('media showcase') || heading.includes('media carousel');
}

function _isImageCollageSection(sectionEl) {
  if (!sectionEl) return false;
  const sid = String(sectionEl.id || '').toLowerCase();
  if (sid.includes('photo-mosaic-mix') || sid.includes('image-collage')) return true;
  if (String(sectionEl.dataset?.wbCollage || '') === '1') return true;
  return !!sectionEl.querySelector('[data-wb-collage-grid="1"]');
}

function _findImageCollageContainer(sectionEl) {
  if (!sectionEl) return null;
  const tagged = sectionEl.querySelector('[data-wb-collage-grid="1"]');
  if (tagged) return tagged;
  const candidates = [...sectionEl.querySelectorAll('div,section,article,ul,ol')].filter((container) => {
    const kids = [...container.children].filter(k => ['FIGURE', 'DIV', 'ARTICLE', 'LI'].includes(k.tagName));
    if (kids.length < 3) return false;
    const imgCount = kids.filter(k => k.querySelector('img')).length;
    if (imgCount < 3) return false;
    const cs = sectionEl.ownerDocument.defaultView.getComputedStyle(container);
    return cs.display.includes('grid') || cs.display.includes('flex');
  });
  return candidates[0] || null;
}

function _readImageCollageWeight(itemEl) {
  const ds = parseInt(String(itemEl?.dataset?.wbCollageWeight || ''), 10);
  if (Number.isFinite(ds) && ds >= 1 && ds <= 4) return ds;
  const colSpan = parseInt(String(itemEl?.style?.gridColumn || '').match(/span\s*(\d+)/i)?.[1] || '1', 10) || 1;
  const rowSpan = parseInt(String(itemEl?.style?.gridRow || '').match(/span\s*(\d+)/i)?.[1] || '1', 10) || 1;
  if (colSpan >= 2 && rowSpan >= 2) return 4;
  if (rowSpan >= 2) return 3;
  if (colSpan >= 2) return 2;
  return 1;
}

function _applyImageCollageWeight(itemEl, weight) {
  if (!itemEl) return;
  const w = Math.max(1, Math.min(4, parseInt(String(weight || '1'), 10) || 1));
  const map = {
    1: { col: 1, row: 1, minH: '90px' },
    2: { col: 2, row: 1, minH: '100px' },
    3: { col: 1, row: 2, minH: '150px' },
    4: { col: 2, row: 2, minH: '170px' },
  };
  const cfg = map[w];
  itemEl.dataset.wbCollageWeight = String(w);
  itemEl.style.setProperty('grid-column', `span ${cfg.col}`, 'important');
  itemEl.style.setProperty('grid-row', `span ${cfg.row}`, 'important');
  itemEl.style.setProperty('min-height', cfg.minH, 'important');
}

function _readImageCollageFocus(imgEl) {
  const raw = String(imgEl?.style?.objectPosition || '').trim();
  const m = raw.match(/([\d.]+)%\s+([\d.]+)%/);
  const x = m ? Number(m[1]) : 50;
  const y = m ? Number(m[2]) : 50;
  return {
    x: Math.max(0, Math.min(100, Number.isFinite(x) ? x : 50)),
    y: Math.max(0, Math.min(100, Number.isFinite(y) ? y : 50)),
  };
}

function _readImageCollageOptions(containerEl) {
  const autoFitRaw = String(containerEl?.dataset?.wbCollageAutofit || '').trim();
  const centeredRaw = String(containerEl?.dataset?.wbCollageCentered || '').trim();
  const styleRaw = String(containerEl?.dataset?.wbCollageStyle || '').trim().toLowerCase();
  const breathingRaw = String(containerEl?.dataset?.wbCollageBreathing || '').trim().toLowerCase();
  const strategyRaw = String(containerEl?.dataset?.wbCollageFillStrategy || '').trim().toLowerCase();
  const firstImg = containerEl?.querySelector('img');
  const inferredAutoFit = firstImg ? String(firstImg.style.objectFit || '').toLowerCase() === 'contain' : true;
  const styleKey = [
    'professional', 'artistic', 'cinematic', 'banner',
    'boomer', 'playful', 'kidzee', 'editorial', 'minimal', 'retro'
  ].includes(styleRaw) ? styleRaw : 'professional';
  const breathing = ['tight', 'normal', 'airy'].includes(breathingRaw) ? breathingRaw : 'normal';
  const fillStrategy = ['balanced', 'left-heavy', 'right-heavy', 'top-heavy'].includes(strategyRaw)
    ? strategyRaw
    : 'balanced';
  return {
    autoFit: autoFitRaw ? autoFitRaw !== '0' : inferredAutoFit,
    centered: centeredRaw ? centeredRaw !== '0' : true,
    styleKey,
    breathing,
    fillStrategy,
  };
}

function _applyImageCollageLayout(containerEl, opts = {}) {
  if (!containerEl) return;
  const autoFit = opts.autoFit !== false;
  const centered = opts.centered !== false;
  const styleKey = [
    'professional', 'artistic', 'cinematic', 'banner',
    'boomer', 'playful', 'kidzee', 'editorial', 'minimal', 'retro'
  ].includes(String(opts.styleKey || '').toLowerCase())
    ? String(opts.styleKey || '').toLowerCase()
    : 'professional';
  const breathing = ['tight', 'normal', 'airy'].includes(String(opts.breathing || '').toLowerCase())
    ? String(opts.breathing || '').toLowerCase()
    : 'normal';
  const fillStrategy = ['balanced', 'left-heavy', 'right-heavy', 'top-heavy'].includes(String(opts.fillStrategy || '').toLowerCase())
    ? String(opts.fillStrategy || '').toLowerCase()
    : 'balanced';
  const breathingPad = breathing === 'tight' ? '0' : (breathing === 'airy' ? '14px' : '6px');
  const styleCfg = {
    professional: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(72px,8.5vw,108px)',
      gap: '12px',
      maxWidth: '980px',
      radius: '14px',
      shadow: '0 6px 18px rgba(15,23,42,.08)',
      panelBg: autoFit ? '#f8fafc' : '#e5e7eb',
      panelPad: autoFit ? '8px' : '0',
      imgFilter: 'none',
    },
    boomer: {
      columns: 'repeat(5,minmax(0,1fr))',
      rows: 'clamp(84px,9.6vw,128px)',
      gap: '16px',
      maxWidth: '980px',
      radius: '22px',
      shadow: '0 12px 24px rgba(15,23,42,.17)',
      panelBg: autoFit ? '#ffffff' : '#dbeafe',
      panelPad: autoFit ? '12px' : '2px',
      imgFilter: 'contrast(1.06) saturate(1.04)',
    },
    playful: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(76px,9.2vw,122px)',
      gap: '14px',
      maxWidth: '1020px',
      radius: '20px',
      shadow: '0 10px 24px rgba(99,102,241,.18)',
      panelBg: autoFit ? '#eef2ff' : '#dbeafe',
      panelPad: autoFit ? '10px' : '2px',
      imgFilter: 'saturate(1.12) contrast(1.03)',
    },
    kidzee: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(82px,9.8vw,132px)',
      gap: '16px',
      maxWidth: '1000px',
      radius: '26px',
      shadow: '0 12px 26px rgba(244,114,182,.20)',
      panelBg: autoFit ? '#fff7ed' : '#ffedd5',
      panelPad: autoFit ? '12px' : '4px',
      imgFilter: 'saturate(1.16) brightness(1.02)',
    },
    editorial: {
      columns: 'repeat(7,minmax(0,1fr))',
      rows: 'clamp(68px,8vw,104px)',
      gap: '12px',
      maxWidth: '1060px',
      radius: '8px',
      shadow: '0 8px 18px rgba(15,23,42,.13)',
      panelBg: autoFit ? '#f8fafc' : '#e2e8f0',
      panelPad: autoFit ? '7px' : '0',
      imgFilter: 'contrast(1.06)',
    },
    minimal: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(70px,8.4vw,104px)',
      gap: '8px',
      maxWidth: '980px',
      radius: '6px',
      shadow: 'none',
      panelBg: autoFit ? '#f8fafc' : '#e2e8f0',
      panelPad: autoFit ? '5px' : '0',
      imgFilter: 'none',
    },
    retro: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(74px,8.8vw,112px)',
      gap: '13px',
      maxWidth: '1000px',
      radius: '12px',
      shadow: '0 10px 0 rgba(15,23,42,.12)',
      panelBg: autoFit ? '#fff7ed' : '#fde68a',
      panelPad: autoFit ? '8px' : '2px',
      imgFilter: 'sepia(.12) saturate(1.08)',
    },
    artistic: {
      columns: 'repeat(6,minmax(0,1fr))',
      rows: 'clamp(76px,9vw,118px)',
      gap: '14px',
      maxWidth: '1000px',
      radius: '18px',
      shadow: '0 10px 24px rgba(30,41,59,.16)',
      panelBg: autoFit ? '#f8fafc' : '#dbeafe',
      panelPad: autoFit ? '10px' : '2px',
      imgFilter: 'saturate(1.06) contrast(1.04)',
    },
    cinematic: {
      columns: 'repeat(8,minmax(0,1fr))',
      rows: 'clamp(66px,7vw,96px)',
      gap: '10px',
      maxWidth: '1040px',
      radius: '10px',
      shadow: '0 14px 28px rgba(2,6,23,.24)',
      panelBg: autoFit ? '#111827' : '#0f172a',
      panelPad: autoFit ? '8px' : '0',
      imgFilter: 'contrast(1.08) saturate(1.02)',
    },
    banner: {
      columns: 'repeat(12,minmax(0,1fr))',
      rows: 'clamp(54px,5.8vw,78px)',
      gap: '8px',
      maxWidth: '1120px',
      radius: '10px',
      shadow: '0 4px 14px rgba(15,23,42,.09)',
      panelBg: autoFit ? '#f8fafc' : '#e2e8f0',
      panelPad: autoFit ? '6px' : '0',
      imgFilter: 'none',
    },
  }[styleKey];
  containerEl.dataset.wbCollageGrid = '1';
  containerEl.dataset.wbCollageAutofit = autoFit ? '1' : '0';
  containerEl.dataset.wbCollageCentered = centered ? '1' : '0';
  containerEl.dataset.wbCollageStyle = styleKey;
  containerEl.dataset.wbCollageBreathing = breathing;
  containerEl.dataset.wbCollageFillStrategy = fillStrategy;
  containerEl.style.setProperty('display', 'grid', 'important');
  containerEl.style.setProperty('grid-template-columns', styleCfg.columns, 'important');
  containerEl.style.setProperty('grid-auto-rows', styleCfg.rows, 'important');
  containerEl.style.setProperty('gap', styleCfg.gap, 'important');
  containerEl.style.setProperty('grid-auto-flow', 'dense', 'important');
  containerEl.style.setProperty('width', '100%', 'important');
  containerEl.style.setProperty('align-items', 'stretch', 'important');
  containerEl.style.setProperty('justify-items', 'stretch', 'important');
  if (centered) {
    containerEl.style.setProperty('max-width', styleCfg.maxWidth, 'important');
    containerEl.style.setProperty('margin-left', 'auto', 'important');
    containerEl.style.setProperty('margin-right', 'auto', 'important');
    containerEl.style.setProperty('justify-content', 'center', 'important');
    containerEl.style.setProperty('align-content', 'start', 'important');
    containerEl.style.setProperty('padding', breathingPad, 'important');
  } else {
    containerEl.style.setProperty('max-width', '100%', 'important');
    containerEl.style.setProperty('margin-left', '0', 'important');
    containerEl.style.setProperty('margin-right', '0', 'important');
    containerEl.style.setProperty('justify-content', 'stretch', 'important');
    containerEl.style.setProperty('align-content', 'start', 'important');
    containerEl.style.setProperty('padding', breathing === 'tight' ? '0' : '4px', 'important');
  }

  const itemEls = [...containerEl.children].filter(node => ['FIGURE', 'DIV', 'ARTICLE', 'LI'].includes(node.tagName));
  const placementList = itemEls.map((itemEl, idx) => ({
    itemEl,
    idx,
    weight: _readImageCollageWeight(itemEl),
  }));
  if (fillStrategy === 'top-heavy' || fillStrategy === 'left-heavy') {
    placementList.sort((a, b) => (b.weight - a.weight) || (a.idx - b.idx));
  } else if (fillStrategy === 'right-heavy') {
    placementList.sort((a, b) => (a.weight - b.weight) || (a.idx - b.idx));
  }
  const ordered = fillStrategy === 'balanced' ? placementList : placementList;
  ordered.forEach((entry, orderIdx) => {
    entry.itemEl.style.setProperty('order', String(orderIdx), 'important');
  });

  itemEls.forEach((itemEl) => {
    itemEl.style.setProperty('margin', '0', 'important');
    itemEl.style.setProperty('border-radius', styleCfg.radius, 'important');
    itemEl.style.setProperty('overflow', 'hidden', 'important');
    itemEl.style.setProperty('display', 'flex', 'important');
    itemEl.style.setProperty('align-items', 'center', 'important');
    itemEl.style.setProperty('justify-content', 'center', 'important');
    itemEl.style.setProperty('background', styleCfg.panelBg, 'important');
    itemEl.style.setProperty('padding', styleCfg.panelPad, 'important');
    itemEl.style.setProperty('box-shadow', styleCfg.shadow, 'important');
    if (styleKey === 'artistic' || styleKey === 'playful' || styleKey === 'kidzee') {
      const n = [...containerEl.children].indexOf(itemEl);
      const rot = styleKey === 'kidzee'
        ? ((n % 4 === 0) ? '-1.8deg' : (n % 4 === 1 ? '1.4deg' : (n % 4 === 2 ? '-0.8deg' : '0.6deg')))
        : ((n % 3 === 0) ? '-1.2deg' : (n % 3 === 1 ? '0.8deg' : '0deg'));
      itemEl.style.setProperty('transform', `rotate(${rot})`, 'important');
    } else {
      itemEl.style.removeProperty('transform');
    }
    const imgEl = itemEl.querySelector('img');
    if (!imgEl) return;
    imgEl.style.setProperty('width', '100%', 'important');
    imgEl.style.setProperty('height', '100%', 'important');
    imgEl.style.setProperty('display', 'block', 'important');
    imgEl.style.setProperty('object-fit', autoFit ? 'contain' : 'cover', 'important');
    imgEl.style.setProperty('filter', styleCfg.imgFilter, 'important');
    if (autoFit) {
      imgEl.style.setProperty('object-position', '50% 50%', 'important');
    }
  });
}

function _imageCollageOptionsField(init = {}) {
  const autoFit = init.autoFit !== false;
  const centered = init.centered !== false;
  const styleKey = [
    'professional', 'artistic', 'cinematic', 'banner',
    'boomer', 'playful', 'kidzee', 'editorial', 'minimal', 'retro'
  ].includes(String(init.styleKey || '').toLowerCase())
    ? String(init.styleKey || '').toLowerCase()
    : 'professional';
  const breathing = ['tight', 'normal', 'airy'].includes(String(init.breathing || '').toLowerCase())
    ? String(init.breathing || '').toLowerCase()
    : 'normal';
  const fillStrategy = ['balanced', 'left-heavy', 'right-heavy', 'top-heavy'].includes(String(init.fillStrategy || '').toLowerCase())
    ? String(init.fillStrategy || '').toLowerCase()
    : 'balanced';
  const thumb = (key, label, bg, accent) => `<button type="button" data-collage-style-thumb="${key}" onclick="_selectCollageStyleThumb('${key}')" title="${label}" style="padding:0;border:1.5px solid var(--border);border-radius:8px;background:${bg};cursor:pointer;overflow:hidden">
    <div style="height:42px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:3px;padding:6px;background:${bg}">
      <span style="display:block;border-radius:3px;background:${accent};opacity:.95;grid-column:span 2"></span>
      <span style="display:block;border-radius:3px;background:${accent};opacity:.78"></span>
      <span style="display:block;border-radius:3px;background:${accent};opacity:.62"></span>
      <span style="display:block;border-radius:3px;background:${accent};opacity:.7"></span>
      <span style="display:block;border-radius:3px;background:${accent};opacity:.9;grid-column:span 2"></span>
      <span style="display:block;border-radius:3px;background:${accent};opacity:.55"></span>
    </div>
    <div style="padding:4px 6px;font-size:.65rem;color:var(--text);text-align:center;border-top:1px solid var(--border)">${label}</div>
  </button>`;
  const thumbs = [
    ['professional', 'Professional', '#f8fafc', '#64748b'],
    ['artistic', 'Artistic', '#eef2ff', '#6366f1'],
    ['cinematic', 'Cinematic', '#0f172a', '#94a3b8'],
    ['banner', 'Banner', '#ecfeff', '#0ea5e9'],
    ['boomer', 'Boomer', '#eff6ff', '#2563eb'],
    ['playful', 'Playful', '#f5f3ff', '#8b5cf6'],
    ['kidzee', 'Kidzee', '#fff7ed', '#f97316'],
    ['editorial', 'Editorial', '#f8fafc', '#334155'],
    ['minimal', 'Minimal', '#f8fafc', '#9ca3af'],
    ['retro', 'Retro', '#fff7ed', '#d97706'],
  ].map(([k, l, bg, ac]) => thumb(k, l, bg, ac)).join('');
  return `<div data-type="collage-options" style="border:1px solid var(--border);border-radius:8px;padding:10px;margin:0 0 8px;background:var(--bg)">
    <label style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin-bottom:6px">Layout Options</label>
    <div style="margin-bottom:6px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Collage style</label>
      <select id="collageStyleKey" onchange="_previewImageCollageLayout()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="professional" ${styleKey === 'professional' ? 'selected' : ''}>Professional</option>
        <option value="artistic" ${styleKey === 'artistic' ? 'selected' : ''}>Artistic</option>
        <option value="cinematic" ${styleKey === 'cinematic' ? 'selected' : ''}>Cinematic</option>
        <option value="banner" ${styleKey === 'banner' ? 'selected' : ''}>Banner</option>
        <option value="boomer" ${styleKey === 'boomer' ? 'selected' : ''}>Boomer</option>
        <option value="playful" ${styleKey === 'playful' ? 'selected' : ''}>Playful</option>
        <option value="kidzee" ${styleKey === 'kidzee' ? 'selected' : ''}>Kidzee</option>
        <option value="editorial" ${styleKey === 'editorial' ? 'selected' : ''}>Editorial</option>
        <option value="minimal" ${styleKey === 'minimal' ? 'selected' : ''}>Minimal</option>
        <option value="retro" ${styleKey === 'retro' ? 'selected' : ''}>Retro</option>
      </select>
    </div>
    <div style="margin-bottom:8px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Style thumbnails</label>
      <div id="collageStyleThumbGrid" style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px">${thumbs}</div>
    </div>
    <div style="margin-bottom:6px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Corner breathing</label>
      <select id="collageBreathing" onchange="_previewImageCollageLayout()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="tight" ${breathing === 'tight' ? 'selected' : ''}>Tight (edge-to-edge)</option>
        <option value="normal" ${breathing === 'normal' ? 'selected' : ''}>Normal</option>
        <option value="airy" ${breathing === 'airy' ? 'selected' : ''}>Airy</option>
      </select>
    </div>
    <div style="margin-bottom:6px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Fill strategy</label>
      <select id="collageFillStrategy" onchange="_previewImageCollageLayout()" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
        <option value="balanced" ${fillStrategy === 'balanced' ? 'selected' : ''}>Balanced</option>
        <option value="left-heavy" ${fillStrategy === 'left-heavy' ? 'selected' : ''}>Left-heavy</option>
        <option value="right-heavy" ${fillStrategy === 'right-heavy' ? 'selected' : ''}>Right-heavy</option>
        <option value="top-heavy" ${fillStrategy === 'top-heavy' ? 'selected' : ''}>Top-heavy</option>
      </select>
    </div>
    <label style="display:flex;align-items:center;gap:7px;font-size:.78rem;color:var(--text);margin-bottom:6px">
      <input type="checkbox" id="collageAutoFit" ${autoFit ? 'checked' : ''} onchange="_previewImageCollageLayout()">
      Auto-fit (no crop / no distortion)
    </label>
    <label style="display:flex;align-items:center;gap:7px;font-size:.78rem;color:var(--text)">
      <input type="checkbox" id="collageCenterSection" ${centered ? 'checked' : ''} onchange="_previewImageCollageLayout()">
      Center collage within section
    </label>
  </div>`;
}

function _syncCollageStyleThumbSelection(styleKey) {
  const key = String(styleKey || '').toLowerCase();
  const thumbs = [...document.querySelectorAll('[data-collage-style-thumb]')];
  thumbs.forEach((btn) => {
    const active = String(btn.getAttribute('data-collage-style-thumb') || '') === key;
    btn.style.borderColor = active ? 'var(--accent)' : 'var(--border)';
    btn.style.boxShadow = active ? '0 0 0 2px color-mix(in srgb, var(--accent) 20%, transparent)' : 'none';
    btn.style.transform = active ? 'translateY(-1px)' : 'none';
  });
}

function _selectCollageStyleThumb(styleKey) {
  const sel = document.getElementById('collageStyleKey');
  if (!sel) return;
  sel.value = String(styleKey || 'professional').toLowerCase();
  _previewImageCollageLayout();
}

function _imageCollageItemEditor(itemIdx, data) {
  const fid = `collage-${itemIdx}-image`;
  const src = _normalizeStagingAssetUrl(data.src || '');
  const srcDisplay = _friendlyMediaSourceLabel(src) || src;
  const alt = String(data.alt || '').trim();
  const weight = Math.max(1, Math.min(4, parseInt(String(data.weight || '1'), 10) || 1));
  const focusX = Math.max(0, Math.min(100, Number(data.focusX ?? 50) || 50));
  const focusY = Math.max(0, Math.min(100, Number(data.focusY ?? 50) || 50));
  const autoFit = data.autoFit === true;
  const previewFit = autoFit ? 'contain' : 'cover';
  const preview = src
    ? `<img src="${_esc(_toPreviewMediaUrl(src))}" style="height:54px;width:80px;object-fit:${previewFit};border-radius:5px;border:1px solid var(--border);margin-top:6px;object-position:${focusX}% ${focusY}%">`
    : `<div style="height:54px;border:1px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.72rem;margin-top:6px">No image selected</div>`;
  return `<div data-type="collage-item" data-fid="${fid}" draggable="true" ondragstart="_onImageCollageDragStart(event)" ondragover="_onImageCollageDragOver(event)" ondrop="_onImageCollageDrop(event)" ondragend="_onImageCollageDragEnd(event)" style="border:1px solid var(--border);border-radius:8px;padding:10px 10px 8px;margin-bottom:8px;background:var(--bg)">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px">
      <div style="display:flex;align-items:center;gap:8px">
        <span title="Drag to reorder" style="cursor:grab;font-size:.95rem;line-height:1;color:var(--muted)">⋮⋮</span>
        <label data-collage-label="1" style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin:0">Collage Image ${itemIdx + 1}</label>
      </div>
      <div style="display:flex;gap:4px">
        <button class="btn btn-secondary btn-sm" type="button" onclick="moveImageCollageItemInEditor(${itemIdx}, -1)" title="Move up">↑</button>
        <button class="btn btn-secondary btn-sm" type="button" onclick="moveImageCollageItemInEditor(${itemIdx}, 1)" title="Move down">↓</button>
        <button class="btn btn-secondary btn-sm" type="button" onclick="removeCollageImageFromActiveSection(${itemIdx})" title="Delete this image">🗑</button>
      </div>
    </div>
    <input data-fid="${fid}-src" type="hidden" value="${_esc(src)}" oninput="_updateImageCollageItemPreview('${fid}')">
    <input data-fid="${fid}-src-display" type="text" value="${_esc(srcDisplay)}" placeholder="No image selected" readonly title="${_esc(src)}"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
    <label style="font-size:.7rem;color:var(--muted);display:block;margin-top:4px">Alt text</label>
    <input data-fid="${fid}-alt" type="text" value="${_esc(alt)}" placeholder="Image description" oninput="_updateImageCollageItemPreview('${fid}')"
      style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
      onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:6px">
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Weight (size)</label>
        <select data-fid="${fid}-weight" onchange="_updateImageCollageItemPreview('${fid}')" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
          <option value="1" ${weight === 1 ? 'selected' : ''}>Small</option>
          <option value="2" ${weight === 2 ? 'selected' : ''}>Wide</option>
          <option value="3" ${weight === 3 ? 'selected' : ''}>Tall</option>
          <option value="4" ${weight === 4 ? 'selected' : ''}>Hero</option>
        </select>
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Focus point</label>
        <div style="display:flex;gap:6px">
          <input data-fid="${fid}-focus-x" type="number" min="0" max="100" value="${Math.round(focusX)}" oninput="_updateImageCollageItemPreview('${fid}')"
            style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem" title="Horizontal focus %">
          <input data-fid="${fid}-focus-y" type="number" min="0" max="100" value="${Math.round(focusY)}" oninput="_updateImageCollageItemPreview('${fid}')"
            style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem" title="Vertical focus %">
        </div>
      </div>
    </div>
    <div data-fid="${fid}-preview">${preview}</div>
    <button class="btn btn-secondary btn-sm" type="button" onclick="openImageFieldMediaPicker('${fid}')" style="margin-top:6px">🗂 Choose From Media Library</button>
  </div>`;
}

function _imageCollageAddItemEditor() {
  return `<div style="display:flex;justify-content:flex-end;margin:8px 0 10px">
    <button class="btn btn-secondary btn-sm" type="button" onclick="addCollageImageToActiveSection()">＋ Add Collage Image</button>
  </div>`;
}

function _renumberImageCollageEditorCards() {
  const fieldsEl = document.getElementById('secEditorFields');
  if (!fieldsEl) return;
  const cards = [...fieldsEl.querySelectorAll('[data-type="collage-item"]')];
  cards.forEach((card, idx) => {
    card.dataset.orderIndex = String(idx);
    const labelEl = card.querySelector('[data-collage-label="1"]');
    if (labelEl) labelEl.textContent = `Collage Image ${idx + 1}`;
    const upBtn = card.querySelector('button[title="Move up"]');
    const downBtn = card.querySelector('button[title="Move down"]');
    const delBtn = card.querySelector('button[title="Delete this image"]');
    if (upBtn) upBtn.setAttribute('onclick', `moveImageCollageItemInEditor(${idx}, -1)`);
    if (downBtn) downBtn.setAttribute('onclick', `moveImageCollageItemInEditor(${idx}, 1)`);
    if (delBtn) delBtn.setAttribute('onclick', `removeCollageImageFromActiveSection(${idx})`);
  });
}

function _imageCollageCards() {
  const fieldsEl = document.getElementById('secEditorFields');
  if (!fieldsEl) return [];
  return [...fieldsEl.querySelectorAll('[data-type="collage-item"]')];
}

function _clearImageCollageDropMarkers() {
  _imageCollageCards().forEach((card) => {
    card.style.removeProperty('border-top-color');
    card.style.removeProperty('border-bottom-color');
    card.style.removeProperty('border-top-width');
    card.style.removeProperty('border-bottom-width');
    card.style.removeProperty('opacity');
  });
}

function _onImageCollageDragStart(event) {
  const card = event?.currentTarget;
  if (!card) return;
  card.dataset.dragging = '1';
  card.style.setProperty('opacity', '.55');
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', card.getAttribute('data-fid') || '');
  }
}

function _onImageCollageDragOver(event) {
  event.preventDefault();
  const card = event?.currentTarget;
  if (!card || card.dataset.dragging === '1') return;
  _clearImageCollageDropMarkers();
  const rect = card.getBoundingClientRect();
  const before = (event.clientY - rect.top) < (rect.height / 2);
  if (before) {
    card.style.setProperty('border-top-color', 'var(--accent)', 'important');
    card.style.setProperty('border-top-width', '2px', 'important');
  } else {
    card.style.setProperty('border-bottom-color', 'var(--accent)', 'important');
    card.style.setProperty('border-bottom-width', '2px', 'important');
  }
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
}

function _onImageCollageDrop(event) {
  event.preventDefault();
  const target = event?.currentTarget;
  const fieldsEl = document.getElementById('secEditorFields');
  if (!target || !fieldsEl) return;
  const dragging = fieldsEl.querySelector('[data-type="collage-item"][data-dragging="1"]');
  if (!dragging || dragging === target) {
    _clearImageCollageDropMarkers();
    return;
  }
  const rect = target.getBoundingClientRect();
  const before = (event.clientY - rect.top) < (rect.height / 2);
  if (before) {
    target.parentNode.insertBefore(dragging, target);
  } else {
    target.parentNode.insertBefore(dragging, target.nextSibling);
  }
  delete dragging.dataset.dragging;
  _clearImageCollageDropMarkers();
  _renumberImageCollageEditorCards();
}

function _onImageCollageDragEnd(event) {
  const card = event?.currentTarget;
  if (card) delete card.dataset.dragging;
  _clearImageCollageDropMarkers();
}

function _previewImageCollageLayout() {
  const fieldsEl = document.getElementById('secEditorFields');
  const collageMeta = fieldsEl?._collageMeta;
  if (!collageMeta?.container) return;
  const autoFit = !!document.getElementById('collageAutoFit')?.checked;
  const centered = !!document.getElementById('collageCenterSection')?.checked;
  const styleKey = document.getElementById('collageStyleKey')?.value || 'professional';
  const breathing = document.getElementById('collageBreathing')?.value || 'normal';
  const fillStrategy = document.getElementById('collageFillStrategy')?.value || 'balanced';
  _syncCollageStyleThumbSelection(styleKey);
  _applyImageCollageLayout(collageMeta.container, { autoFit, centered, styleKey, breathing, fillStrategy });
  const cards = [...fieldsEl.querySelectorAll('[data-type="collage-item"]')];
  cards.forEach((card, idx2) => {
    const fid = String(card.getAttribute('data-fid') || `collage-${idx2}-image`);
    _updateImageCollageItemPreview(fid);
  });
}

function moveImageCollageItemInEditor(idx, direction) {
  const fieldsEl = document.getElementById('secEditorFields');
  if (!fieldsEl) return;
  const cards = [...fieldsEl.querySelectorAll('[data-type="collage-item"]')];
  const at = Number(idx) || 0;
  const target = cards[at];
  if (!target) return;
  if (direction < 0 && target.previousElementSibling && target.previousElementSibling.getAttribute('data-type') === 'collage-item') {
    target.parentNode.insertBefore(target, target.previousElementSibling);
  } else if (direction > 0 && target.nextElementSibling && target.nextElementSibling.getAttribute('data-type') === 'collage-item') {
    target.parentNode.insertBefore(target.nextElementSibling, target);
  }
  _renumberImageCollageEditorCards();
}

function _updateImageCollageItemPreview(fid) {
  const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
  const srcDisplayEl = document.querySelector(`[data-fid="${fid}-src-display"]`);
  const altEl = document.querySelector(`[data-fid="${fid}-alt"]`);
  const focusXEl = document.querySelector(`[data-fid="${fid}-focus-x"]`);
  const focusYEl = document.querySelector(`[data-fid="${fid}-focus-y"]`);
  const weightEl = document.querySelector(`[data-fid="${fid}-weight"]`);
  const wrap = document.querySelector(`[data-fid="${fid}-preview"]`);
  if (!srcEl || !wrap) return;
  const autoFit = !!document.getElementById('collageAutoFit')?.checked;
  const src = _normalizeStagingAssetUrl(srcEl.value || '');
  const focusX = Math.max(0, Math.min(100, parseInt(focusXEl?.value || '50', 10) || 50));
  const focusY = Math.max(0, Math.min(100, parseInt(focusYEl?.value || '50', 10) || 50));
  if (srcDisplayEl) {
    srcDisplayEl.value = _friendlyMediaSourceLabel(src) || src;
    srcDisplayEl.title = src;
  }
  if (!src) {
    wrap.innerHTML = '<div style="height:54px;border:1px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.72rem;margin-top:6px">No image selected</div>';
    return;
  }
  const fit = autoFit ? 'contain' : 'cover';
  const pos = autoFit ? '50% 50%' : `${focusX}% ${focusY}%`;
  wrap.innerHTML = `<img src="${_esc(_toPreviewMediaUrl(src))}" style="height:54px;width:80px;object-fit:${fit};border-radius:5px;border:1px solid var(--border);margin-top:6px;object-position:${pos}">`;

  const fieldsEl = document.getElementById('secEditorFields');
  const itemEl = fieldsEl?._collageMeta?.fidToItem?.get(fid);
  if (!itemEl) return;
  const imgEl = itemEl.querySelector('img') || itemEl;
  const alt = String(altEl?.value || '').trim();
  const weight = Math.max(1, Math.min(4, parseInt(weightEl?.value || '1', 10) || 1));
  _applyImageCollageWeight(itemEl, weight);
  if (imgEl && imgEl.tagName === 'IMG') {
    if (src) {
      imgEl.src = src;
      imgEl.setAttribute('src', src);
    }
    imgEl.style.setProperty('object-fit', autoFit ? 'contain' : 'cover', 'important');
    imgEl.style.setProperty('object-position', autoFit ? '50% 50%' : `${focusX}% ${focusY}%`, 'important');
    if (alt) imgEl.alt = alt;
  }
}

function addCollageImageToActiveSection() {
  const frame = document.getElementById('stagingIframe');
  if (!frame?.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const fieldsEl = document.getElementById('secEditorFields');
  const collageMeta = fieldsEl?._collageMeta;
  if (!collageMeta?.container) {
    toast('No collage found in this section', false);
    return;
  }

  _historyPush();
  const doc = frame.contentDocument;
  const figure = doc.createElement('figure');
  figure.setAttribute('data-wb-collage-item', '1');
  figure.style.cssText = 'margin:0;border-radius:14px;overflow:hidden;background:#e2e8f0';
  _applyImageCollageWeight(figure, 1);

  const img = doc.createElement('img');
  img.setAttribute('src', `https://picsum.photos/seed/collage-${Date.now()}/920/740`);
  img.alt = 'Collage image';
  img.style.cssText = 'width:100%;height:100%;object-fit:cover;object-position:50% 50%;display:block';
  figure.appendChild(img);
  collageMeta.container.appendChild(figure);
  const autoFit = !!document.getElementById('collageAutoFit')?.checked;
  const centered = !!document.getElementById('collageCenterSection')?.checked;
  const styleKey = document.getElementById('collageStyleKey')?.value || 'professional';
  const breathing = document.getElementById('collageBreathing')?.value || 'normal';
  const fillStrategy = document.getElementById('collageFillStrategy')?.value || 'balanced';
  _applyImageCollageLayout(collageMeta.container, { autoFit, centered, styleKey, breathing, fillStrategy });
  openSecEditor(activeSectionIndex);
  toast('Collage image added — choose media from library and save changes', true);
}

function removeCollageImageFromActiveSection(idx) {
  const fieldsEl = document.getElementById('secEditorFields');
  const collageMeta = fieldsEl?._collageMeta;
  if (!collageMeta?.container || !Array.isArray(collageMeta.items)) {
    toast('No collage found in this section', false);
    return;
  }
  if (collageMeta.items.length <= 1) {
    toast('At least one collage image is required', false);
    return;
  }
  const item = collageMeta.items[Number(idx) || 0];
  if (!item?.itemEl) return;
  _historyPush();
  item.itemEl.remove();
  openSecEditor(activeSectionIndex);
  toast('Collage image removed — click Save to persist', true);
}

function _findMediaCardCarouselContainer(sectionEl) {
  if (!sectionEl) return null;
  const containers = [...sectionEl.querySelectorAll('div,section,article,ul,ol')];
  const scored = containers.map((c) => {
    const cs = sectionEl.ownerDocument.defaultView.getComputedStyle(c);
    const hasHorizontal = cs.overflowX === 'auto' || cs.overflowX === 'scroll' || /(auto|scroll)/.test(String(c.style.overflowX || '').toLowerCase());
    const isLayout = cs.display.includes('grid') || cs.display.includes('flex');
    const kids = [...c.children].filter(k => ['DIV', 'ARTICLE', 'LI', 'SECTION'].includes(k.tagName));
    return { c, score: (hasHorizontal ? 100 : 0) + (isLayout ? 10 : 0) + kids.length, hasHorizontal, kids };
  }).filter(x => x.kids.length >= 2).sort((a, b) => b.score - a.score);
  return scored.length ? scored[0].c : null;
}

function _gridCardEditor(cardIdx, data, opts = {}) {
  const includeImage = !!opts.includeImage;
  const tFid = `grid-${cardIdx}-title`;
  const bFid = `grid-${cardIdx}-body`;
  const iFid = `grid-${cardIdx}-image`;
  const aFid = `${iFid}-alt`;
  const titleAlign = _normalizeTextAlignValue(data.titleAlign || 'left');
  const titleAlignOpts = ['left', 'center', 'right', 'justify']
    .map((v) => `<option value="${v}"${titleAlign === v ? ' selected' : ''}>${v.charAt(0).toUpperCase() + v.slice(1)}</option>`)
    .join('');
  const imgSrc = _normalizeStagingAssetUrl(data.imageSrc || '');
  const imgDisplay = _friendlyMediaSourceLabel(imgSrc) || imgSrc;
  const imgPreview = imgSrc
    ? `<img src="${_esc(_toPreviewMediaUrl(imgSrc))}" style="height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px">`
    : `<div style="height:54px;border:1px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.72rem;margin-top:6px">No image selected</div>`;
  return `<div style="border:1px solid var(--border);border-radius:8px;padding:10px 10px 8px;margin-bottom:8px;background:var(--bg)">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px">
      <label style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin:0">Grid Item ${cardIdx + 1}</label>
      <button class="btn btn-secondary btn-sm" type="button" onclick="removeGridCardFromActiveSection(${cardIdx})" title="Delete this grid card">🗑 Delete</button>
    </div>
    <div style="display:grid;grid-template-columns:1fr;gap:6px">
      <label style="font-size:.7rem;color:var(--muted)">Title / Label</label>
      <input data-fid="${tFid}" type="text" value="${_esc(data.title || '')}" placeholder="Card title"
        oninput="_previewMediaCarouselGridItem(${cardIdx})"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      ${includeImage ? _styleBar(tFid, data.titleInit || {}) : ''}
      ${includeImage ? `<div style="margin-top:6px">
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:3px">Title alignment</label>
        <select data-fid="${tFid}-align" onchange="_previewMediaCarouselGridItem(${cardIdx})" style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">${titleAlignOpts}</select>
      </div>` : ''}
      ${includeImage ? _clickActionField(tFid, data.titleClick || {}) : ''}

      <label style="font-size:.7rem;color:var(--muted)">Body</label>
      <textarea data-fid="${bFid}" rows="2" placeholder="Card text"
        oninput="_previewMediaCarouselGridItem(${cardIdx})"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none;resize:vertical"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">${_esc(data.body || '')}</textarea>
      ${includeImage ? `
      <label style="font-size:.7rem;color:var(--muted)">Card Image</label>
      <div data-fid="${iFid}">
      <input data-fid="${iFid}-src" type="hidden" value="${_esc(imgSrc)}"
        oninput="_updateGridImagePreview('${iFid}');_previewMediaCarouselGridItem(${cardIdx})"
        >
      <input data-fid="${iFid}-src-display" type="text" value="${_esc(imgDisplay)}" placeholder="No image selected" readonly title="${_esc(imgSrc)}"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <input type="hidden" data-fid="${iFid}-media-type" value="image">
      <label style="font-size:.7rem;color:var(--muted)">Image Alt Text</label>
      <input data-fid="${aFid}" type="text" value="${_esc(data.imageAlt || '')}" placeholder="Image description"
        oninput="_previewMediaCarouselGridItem(${cardIdx})"
        style="width:100%;padding:7px 10px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem;outline:none"
        onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'">
      <div data-fid="${iFid}-preview">${imgPreview}</div>
      <button class="btn btn-secondary btn-sm" type="button" onclick="openImageFieldMediaPicker('${iFid}')" style="margin-top:2px">🗂 Choose From Media Library</button>
      ${_clickActionField(iFid, data.imageClick || {})}
      </div>
      ` : ''}
    </div>
  </div>`;
}

function _gridAddCardEditor() {
  return `<div style="display:flex;justify-content:flex-end;margin:8px 0 10px">
    <button class="btn btn-secondary btn-sm" type="button" onclick="addGridCardToActiveSection()">＋ Add Grid Card</button>
  </div>`;
}

function _gridCarouselOptionsField(init = {}) {
  const enabled = !!init.enabled;
  const delaySec = Math.max(2, Math.min(60, Number(init.delaySec || 4) || 4));
  const styleKey = _normalizeMediaCarouselStyle(init.styleKey || 'classic');
  const controlPos = _normalizeMediaCarouselControlPos(init.controlPos || 'bottom-center');
  const controlsVisibility = _normalizeMediaCarouselControlsVisibility(
    init.controlsVisibility || (init.showOnHover ? 'hover' : 'always')
  );
  const styleOpts = [
    ['classic', 'Classic'],
    ['glass', 'Glass'],
    ['elevated', 'Elevated'],
    ['contrast', 'High Contrast'],
    ['minimal', 'Minimal'],
  ].map(([k, l]) => `<option value="${k}"${styleKey === k ? ' selected' : ''}>${l}</option>`).join('');
  const posOpts = [
    ['bottom-center', 'Bottom Center'],
    ['top-center', 'Top Center'],
    ['side-overlay', 'Side Overlay'],
  ].map(([k, l]) => `<option value="${k}"${controlPos === k ? ' selected' : ''}>${l}</option>`).join('');
  const visibilityOpts = [
    ['always', 'Always show controls'],
    ['hover', 'Show controls on hover'],
    ['hidden', 'Hide controls'],
  ].map(([k, l]) => `<option value="${k}"${controlsVisibility === k ? ' selected' : ''}>${l}</option>`).join('');
  return `<div style="border:1px solid var(--border);border-radius:8px;padding:10px;margin:0 0 8px;background:var(--bg)">
    <label style="font-size:.72rem;font-weight:700;color:var(--accent);display:block;margin-bottom:6px">↔ Carousel Behavior</label>
    <label style="display:flex;align-items:center;gap:7px;font-size:.78rem;color:var(--text);margin-bottom:8px">
      <input type="checkbox" data-fid="grid-carousel-auto" ${enabled ? 'checked' : ''} onchange="_previewMediaCarouselBehavior()">
      Enable auto-carousel (infinite loop)
    </label>
    <div style="display:flex;align-items:center;gap:8px">
      <label style="font-size:.72rem;color:var(--muted)">Delay</label>
      <input type="number" min="2" max="60" step="1" data-fid="grid-carousel-delay" value="${delaySec}"
        oninput="_previewMediaCarouselBehavior()"
        style="width:92px;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">
      <span style="font-size:.72rem;color:var(--muted)">seconds</span>
    </div>
    <div style="margin-top:8px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Carousel style</label>
      <select data-fid="grid-carousel-style" onchange="_previewMediaCarouselBehavior()"
        style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">${styleOpts}</select>
    </div>
    <div style="margin-top:8px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Control position</label>
      <select data-fid="grid-carousel-control-pos" onchange="_previewMediaCarouselBehavior()"
        style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">${posOpts}</select>
    </div>
    <div style="margin-top:8px">
      <label style="font-size:.72rem;color:var(--muted);display:block;margin-bottom:4px">Controls visibility</label>
      <select data-fid="grid-carousel-controls-visibility" onchange="_previewMediaCarouselBehavior()"
        style="width:100%;padding:6px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem">${visibilityOpts}</select>
    </div>
  </div>`;
}

function _normalizeMediaCarouselControlPos(value) {
  const v = String(value || '').trim().toLowerCase();
  if (['bottom-center', 'top-center', 'side-overlay'].includes(v)) return v;
  return 'bottom-center';
}

function _normalizeMediaCarouselStyle(value) {
  const v = String(value || '').trim().toLowerCase();
  if (['classic', 'glass', 'elevated', 'contrast', 'minimal'].includes(v)) return v;
  return 'classic';
}

function _normalizeMediaCarouselControlsVisibility(value) {
  const v = String(value || '').trim().toLowerCase();
  if (['always', 'hover', 'hidden'].includes(v)) return v;
  return 'always';
}

function _mediaCarouselStyleTokens(styleKey) {
  const style = _normalizeMediaCarouselStyle(styleKey);
  const table = {
    classic: {
      cardBg: 'var(--panel,#f8fafc)', cardBorder: 'var(--border,#e2e8f0)', cardShadow: 'none', cardRadius: '14px',
      btnBg: 'var(--panel,#ffffff)', btnBorder: 'var(--border,#cbd5e1)', btnColor: 'var(--text,#0f172a)',
      dotActive: 'var(--accent,#2563eb)', dotInactive: 'var(--muted,#94a3b8)', controlsGap: '10px',
    },
    glass: {
      cardBg: 'color-mix(in srgb, var(--panel,#ffffff) 74%, transparent)', cardBorder: 'color-mix(in srgb, var(--border,#94a3b8) 55%, transparent)', cardShadow: '0 12px 24px rgba(15,23,42,.1)', cardRadius: '16px',
      btnBg: 'color-mix(in srgb, var(--panel,#ffffff) 86%, transparent)', btnBorder: 'color-mix(in srgb, var(--border,#94a3b8) 60%, transparent)', btnColor: 'var(--text,#0f172a)',
      dotActive: 'var(--accent,#0ea5e9)', dotInactive: 'color-mix(in srgb, var(--muted,#a3b8cc) 75%, transparent)', controlsGap: '12px',
      cardBackdrop: 'blur(8px)',
    },
    elevated: {
      cardBg: 'var(--panel,#ffffff)', cardBorder: 'color-mix(in srgb, var(--border,#dbe6f2) 85%, transparent)', cardShadow: '0 14px 28px rgba(15,23,42,.14)', cardRadius: '16px',
      btnBg: 'var(--panel,#ffffff)', btnBorder: 'color-mix(in srgb, var(--border,#c9d7e8) 85%, transparent)', btnColor: 'var(--text,#0f172a)',
      dotActive: 'var(--accent,#1d4ed8)', dotInactive: 'color-mix(in srgb, var(--muted,#9fb0c6) 80%, transparent)', controlsGap: '12px',
    },
    contrast: {
      cardBg: 'var(--text,#0f172a)', cardBorder: 'color-mix(in srgb, var(--text,#334155) 65%, var(--bg,#fff))', cardShadow: '0 10px 22px rgba(2,6,23,.35)', cardRadius: '12px',
      btnBg: 'var(--text,#0f172a)', btnBorder: 'color-mix(in srgb, var(--text,#475569) 60%, var(--bg,#fff))', btnColor: 'var(--bg,#e2e8f0)',
      dotActive: 'var(--accent,#22d3ee)', dotInactive: 'color-mix(in srgb, var(--muted,#64748b) 80%, transparent)', controlsGap: '10px',
    },
    minimal: {
      cardBg: 'var(--panel,#ffffff)', cardBorder: 'var(--border,#e5e7eb)', cardShadow: 'none', cardRadius: '10px',
      btnBg: 'transparent', btnBorder: 'var(--border,#cbd5e1)', btnColor: 'var(--text,#334155)',
      dotActive: 'var(--text,#334155)', dotInactive: 'var(--border,#cbd5e1)', controlsGap: '8px',
    },
  };
  return table[style];
}

function _applyMediaCarouselStyle(containerEl, controlsEl, styleKey) {
  if (!containerEl) return;
  const key = _normalizeMediaCarouselStyle(styleKey);
  const cfg = _mediaCarouselStyleTokens(key);
  containerEl.dataset.wbCarouselStyle = key;
  containerEl.dataset.wbCarouselDotActive = cfg.dotActive;
  containerEl.dataset.wbCarouselDotInactive = cfg.dotInactive;

  const cards = [...containerEl.children].filter(el => ['ARTICLE', 'DIV', 'LI', 'SECTION'].includes(el.tagName));
  cards.forEach((card) => {
    card.style.setProperty('background', cfg.cardBg, 'important');
    card.style.setProperty('border', `1px solid ${cfg.cardBorder}`, 'important');
    card.style.setProperty('box-shadow', cfg.cardShadow, 'important');
    card.style.setProperty('border-radius', cfg.cardRadius, 'important');
    card.style.setProperty('display', 'flex', 'important');
    card.style.setProperty('flex-direction', 'column', 'important');
    card.style.setProperty('align-items', 'stretch', 'important');
    card.style.setProperty('justify-content', 'flex-start', 'important');
    card.style.setProperty('overflow', 'hidden', 'important');
    if (cfg.cardBackdrop) {
      card.style.setProperty('backdrop-filter', cfg.cardBackdrop, 'important');
      card.style.setProperty('-webkit-backdrop-filter', cfg.cardBackdrop, 'important');
    } else {
      card.style.removeProperty('backdrop-filter');
      card.style.removeProperty('-webkit-backdrop-filter');
    }
  });

  if (controlsEl) {
    controlsEl.style.setProperty('gap', cfg.controlsGap, 'important');
    controlsEl.querySelectorAll('button').forEach((btn) => {
      btn.style.setProperty('background', cfg.btnBg, 'important');
      btn.style.setProperty('border-color', cfg.btnBorder, 'important');
      btn.style.setProperty('color', cfg.btnColor, 'important');
    });
    const dots = controlsEl.querySelectorAll('[data-wb-carousel-dots="1"] button');
    dots.forEach((dot, i) => {
      dot.style.setProperty('background', i === 0 ? cfg.dotActive : cfg.dotInactive, 'important');
    });
  }
}

function _wireMediaCarouselInteractions(containerEl, controlsEl) {
  if (!containerEl || !controlsEl) return;
  const win = containerEl.ownerDocument?.defaultView;
  const runtimeManaged = !!(win && typeof win.wbMediaCardCarouselInitAll === 'function');

  // When runtime exists in iframe, let it own click/dot/autoplay wiring to avoid duplicate timers.
  if (runtimeManaged) {
    if (controlsEl.__wbClickHandler) {
      controlsEl.removeEventListener('click', controlsEl.__wbClickHandler);
      controlsEl.__wbClickHandler = null;
    }
    if (containerEl.__wbDotSync) {
      containerEl.removeEventListener('scroll', containerEl.__wbDotSync);
      containerEl.__wbDotSync = null;
    }
    if (containerEl.__wbAutoTimer) {
      clearInterval(containerEl.__wbAutoTimer);
      containerEl.__wbAutoTimer = null;
    }
    return;
  }

  const dotActive = containerEl.dataset.wbCarouselDotActive || '#2563eb';
  const dotInactive = containerEl.dataset.wbCarouselDotInactive || '#94a3b8';

  const getCards = () => [...containerEl.children].filter(el => ['ARTICLE', 'DIV', 'LI', 'SECTION'].includes(el.tagName));
  const ensureCardOrigins = () => {
    getCards().forEach((card, idx) => {
      if (!card.dataset.wbCardOrigin) card.dataset.wbCardOrigin = String(idx);
    });
  };
  ensureCardOrigins();

  const syncDots = () => {
    const dots = [...controlsEl.querySelectorAll('[data-wb-carousel-dots="1"] button[data-wb-go]')];
    if (!dots.length) return;
    const cards = getCards();
    if (!cards.length) return;
    const active = Math.max(0, parseInt(cards[0].dataset.wbCardOrigin || '0', 10) || 0);
    dots.forEach((dot, idx) => {
      dot.style.setProperty('background', idx === active ? dotActive : dotInactive, 'important');
    });
    containerEl.dataset.wbCarouselIndex = String(active);
  };

  const rotateBy = (dir, times = 1) => {
    let cards = getCards();
    if (cards.length < 2) return;
    const count = Math.max(1, Math.abs(Number(times) || 1));
    for (let step = 0; step < count; step++) {
      cards = getCards();
      if (!cards.length) break;
      if (Number(dir) >= 0) containerEl.appendChild(cards[0]);
      else containerEl.insertBefore(cards[cards.length - 1], cards[0]);
    }
    containerEl.scrollLeft = 0;
    syncDots();
  };

  const goTo = (idx) => {
    const cards = getCards();
    if (!cards.length) return;
    const nextIdx = Math.max(0, Math.min(cards.length - 1, Number(idx) || 0));
    const pos = cards.findIndex(card => Number(card.dataset.wbCardOrigin || '-1') === nextIdx);
    if (pos < 0) return;
    if (pos === 0) {
      syncDots();
      return;
    }
    rotateBy(1, pos);
  };

  const shiftBy = (dir) => {
    rotateBy(Number(dir) >= 0 ? 1 : -1, 1);
  };

  if (controlsEl.__wbClickHandler) controlsEl.removeEventListener('click', controlsEl.__wbClickHandler);
  controlsEl.__wbClickHandler = (ev) => {
    const btn = ev.target.closest('button');
    if (!btn) return;
    const dir = btn.getAttribute('data-wb-dir');
    const go = btn.getAttribute('data-wb-go');
    if (dir !== null) {
      ev.preventDefault();
      shiftBy(Number(dir));
      return;
    }
    if (go !== null) {
      ev.preventDefault();
      goTo(Number(go));
    }
  };
  controlsEl.addEventListener('click', controlsEl.__wbClickHandler);

  if (containerEl.__wbDotSync) containerEl.removeEventListener('scroll', containerEl.__wbDotSync);
  containerEl.__wbDotSync = () => syncDots();
  containerEl.addEventListener('scroll', containerEl.__wbDotSync, { passive: true });

  if (containerEl.__wbAutoTimer) {
    clearInterval(containerEl.__wbAutoTimer);
    containerEl.__wbAutoTimer = null;
  }
  const auto = containerEl.dataset.wbCarouselAuto === '1';
  const delaySec = Math.max(2, parseInt(containerEl.dataset.wbCarouselDelaySec || '4', 10) || 4);
  if (auto && getCards().length > 1) {
    containerEl.__wbAutoTimer = setInterval(() => rotateBy(1, 1), delaySec * 1000);
  }

  syncDots();
}

function _updateGridImagePreview(fid) {
  const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
  const srcDisplayEl = document.querySelector(`[data-fid="${fid}-src-display"]`);
  const wrap = document.querySelector(`[data-fid="${fid}-preview"]`);
  if (!srcEl || !wrap) return;
  const raw = String(srcEl.value || '').trim();
  const src = _normalizeStagingAssetUrl(raw);
  if (srcDisplayEl) {
    srcDisplayEl.value = _friendlyMediaSourceLabel(src) || src;
    srcDisplayEl.title = src;
  }
  if (!src) {
    wrap.innerHTML = '<div style="height:54px;border:1px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:.72rem;margin-top:6px">No image selected</div>';
    return;
  }
  wrap.innerHTML = `<img src="${_esc(_toPreviewMediaUrl(src))}" style="height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px">`;
}

function _previewMediaCarouselGridItem(cardIdx) {
  const frame = document.getElementById('stagingIframe');
  if (!frame?.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const fieldsEl = document.getElementById('secEditorFields');
  const gridMeta = fieldsEl?._gridMeta;
  if (!gridMeta || !Array.isArray(gridMeta.items)) return;
  const item = gridMeta.items[Number(cardIdx) || 0];
  if (!item) return;

  const titleVal = fieldsEl.querySelector(`[data-fid="grid-${cardIdx}-title"]`)?.value ?? '';
  const bodyVal = fieldsEl.querySelector(`[data-fid="grid-${cardIdx}-body"]`)?.value ?? '';
  const imageVal = _normalizeStagingAssetUrl(fieldsEl.querySelector(`[data-fid="grid-${cardIdx}-image-src"]`)?.value?.trim() || '');
  const imageAlt = fieldsEl.querySelector(`[data-fid="grid-${cardIdx}-image-alt"]`)?.value?.trim() || '';
  const titleAlign = fieldsEl.querySelector(`[data-fid="grid-${cardIdx}-title-align"]`)?.value || 'left';

  if (item.titleEl) {
    _setText(item.titleEl, titleVal);
    _applyStyleBarToEl(fieldsEl, `grid-${cardIdx}-title`, item.titleEl);
    item.titleEl.style.setProperty('text-align', titleAlign, 'important');
    _applyClickActionFromField(fieldsEl, `grid-${cardIdx}-title`, item.titleEl);
  } else if (item.cardEl) {
    const tgt = item.cardEl.querySelector('h1,h2,h3,h4,h5,strong,b,.title,[class*="title"],[class*="label"]') || item.cardEl;
    _setText(tgt, titleVal);
  }
  if (item.bodyEl) {
    _setParagraphText(item.bodyEl, bodyVal);
  } else if (item.cardEl) {
    const p = item.cardEl.querySelector('p,small,span,div') || item.cardEl;
    _setParagraphText(p, bodyVal);
  }
  if (item.imageEl) {
    if (imageVal) {
      item.imageEl.src = imageVal;
      item.imageEl.setAttribute('src', imageVal);
      item.imageEl.style.removeProperty('display');
      delete item.imageEl.dataset.wbEditorHidden;
    } else {
      item.imageEl.removeAttribute('src');
      item.imageEl.style.setProperty('display', 'none', 'important');
      item.imageEl.dataset.wbEditorHidden = '1';
    }
    item.imageEl.alt = imageAlt || '';
    _applyClickActionFromField(fieldsEl, `grid-${cardIdx}-image`, item.imageEl);
  }

  const status = document.getElementById('stagingStatusBar');
  if (status) status.textContent = 'Preview updated — unsaved. Click 💾 Save Changes.';
}

function _previewMediaCarouselBehavior() {
  const frame = document.getElementById('stagingIframe');
  if (!frame?.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const fieldsEl = document.getElementById('secEditorFields');
  const gridMeta = fieldsEl?._gridMeta;
  if (!gridMeta?.isMediaCarousel || !gridMeta.container) return;

  const autoEnabled = !!fieldsEl.querySelector('[data-fid="grid-carousel-auto"]')?.checked;
  const delaySec = Math.max(2, Math.min(60,
    parseInt(fieldsEl.querySelector('[data-fid="grid-carousel-delay"]')?.value || '4', 10) || 4
  ));
  const styleKey = _normalizeMediaCarouselStyle(fieldsEl.querySelector('[data-fid="grid-carousel-style"]')?.value || 'classic');
  const controlPos = _normalizeMediaCarouselControlPos(fieldsEl.querySelector('[data-fid="grid-carousel-control-pos"]')?.value || 'bottom-center');
  const controlsVisibility = _normalizeMediaCarouselControlsVisibility(
    fieldsEl.querySelector('[data-fid="grid-carousel-controls-visibility"]')?.value || 'always'
  );
  const hoverOnly = controlsVisibility === 'hover';

  gridMeta.container.dataset.wbCarousel = '1';
  gridMeta.container.dataset.wbCarouselAuto = autoEnabled ? '1' : '0';
  gridMeta.container.dataset.wbCarouselDelaySec = String(delaySec);
  gridMeta.container.dataset.wbCarouselStyle = styleKey;
  gridMeta.container.dataset.wbCarouselControlPos = controlPos;
  gridMeta.container.dataset.wbCarouselControlsVisibility = controlsVisibility;
  gridMeta.container.dataset.wbCarouselHoverOnly = hoverOnly ? '1' : '0';
  _syncMediaCarouselControls(stagingSections[activeSectionIndex].el, gridMeta.container);
  frame.contentDocument.defaultView?.wbMediaCardCarouselInitAll?.(frame.contentDocument);

  const status = document.getElementById('stagingStatusBar');
  if (status) status.textContent = 'Preview updated — unsaved. Click 💾 Save Changes.';
}

function _ensureMediaCardCarouselRuntime(doc) {
  if (!doc) return;
  const prev = doc.getElementById('__wb_media_card_carousel_runtime');
  if (prev) prev.remove();
  try {
    if (doc.defaultView) {
      doc.defaultView.__wbMediaCardCarouselRuntime = false;
      delete doc.defaultView.__wbMediaCardCarouselRuntime;
      delete doc.defaultView.__wbMediaCardCarouselRuntimeVersion;
    }
  } catch (_) {}

  const script = doc.createElement('script');
  script.id = '__wb_media_card_carousel_runtime';
  script.textContent = `(function(){
      if (window.__wbMediaCardCarouselRuntimeVersion === 'v2') return;
      window.__wbMediaCardCarouselRuntime = true;
      window.__wbMediaCardCarouselRuntimeVersion = 'v2';
      function getCards(c){
        return Array.from(c.children).filter(function(el){ return ['ARTICLE','DIV','LI','SECTION'].includes(el.tagName); });
      }
      function ensureId(c){
        if (!c.id) c.id = 'wb-media-carousel-' + Math.random().toString(36).slice(2,8);
        return c.id;
      }
      function ensureCardOrigins(c){
        getCards(c).forEach(function(card, idx){
          if (!card.dataset.wbCardOrigin) card.dataset.wbCardOrigin = String(idx);
        });
      }
      function rotateBy(c, dir, times){
        var steps = Math.max(1, Math.abs(Number(times) || 1));
        for (var i = 0; i < steps; i++) {
          var cards = getCards(c);
          if (cards.length < 2) return;
          if (Number(dir) >= 0) c.appendChild(cards[0]);
          else c.insertBefore(cards[cards.length - 1], cards[0]);
        }
        c.scrollLeft = 0;
        syncDots(c);
      }
      function syncDots(c){
        var controls = c.parentElement && c.parentElement.querySelector('[data-wb-carousel-controls="1"][data-target="'+c.id+'"]');
        if (!controls) return;
        var dots = controls.querySelector('[data-wb-carousel-dots="1"]');
        if (!dots) return;
        var cards = getCards(c);
        if (!cards.length) return;
        var active = Math.max(0, parseInt(cards[0].dataset.wbCardOrigin || '0', 10) || 0);
        var dotActive = c.dataset.wbCarouselDotActive || '#2563eb';
        var dotInactive = c.dataset.wbCarouselDotInactive || '#94a3b8';
        Array.from(dots.querySelectorAll('button')).forEach(function(btn, idx){
          btn.style.background = idx === active ? dotActive : dotInactive;
        });
        c.dataset.wbCarouselIndex = String(active);
      }
      window.wbMediaCarouselGo = function(id, idx){
        var c = document.getElementById(id);
        if (!c) return;
        var cards = getCards(c);
        if (!cards.length) return;
        var nextIdx = Math.max(0, Math.min(cards.length - 1, Number(idx) || 0));
        var pos = cards.findIndex(function(card){ return Number(card.dataset.wbCardOrigin || '-1') === nextIdx; });
        if (pos < 0) return;
        if (pos === 0) {
          syncDots(c);
          return;
        }
        rotateBy(c, 1, pos);
      };
      window.wbMediaCarouselShift = function(id, dir){
        var c = document.getElementById(id);
        if (!c) return;
        var cards = getCards(c);
        if (!cards.length) return;
        rotateBy(c, Number(dir) >= 0 ? 1 : -1, 1);
      };
      function bindControls(c){
        var controls = c.parentElement && c.parentElement.querySelector('[data-wb-carousel-controls="1"][data-target="'+c.id+'"]');
        if (!controls) return;
        var layout = String(controls.getAttribute('data-wb-layout') || 'flex').toLowerCase() === 'grid' ? 'grid' : 'flex';

        if (controls.__wbClickHandler) controls.removeEventListener('click', controls.__wbClickHandler);
        controls.__wbClickHandler = function(ev){
          var btn = ev.target && ev.target.closest ? ev.target.closest('button') : null;
          if (!btn) return;
          var dir = btn.getAttribute('data-wb-dir');
          var go = btn.getAttribute('data-wb-go');
          if (dir !== null) {
            ev.preventDefault();
            window.wbMediaCarouselShift(c.id, Number(dir));
            return;
          }
          if (go !== null) {
            ev.preventDefault();
            window.wbMediaCarouselGo(c.id, Number(go));
          }
        };
        controls.addEventListener('click', controls.__wbClickHandler);

        var visibility = String(c.dataset.wbCarouselControlsVisibility || '').toLowerCase();
        if (visibility !== 'always' && visibility !== 'hover' && visibility !== 'hidden') {
          visibility = c.dataset.wbCarouselHoverOnly === '1' ? 'hover' : 'always';
        }
        var hoverOnly = visibility === 'hover';
        var hidden = visibility === 'hidden';
        if (hidden) {
          controls.style.display = 'none';
          controls.style.opacity = '0';
          if (c.__wbHoverIn) c.removeEventListener('mouseenter', c.__wbHoverIn);
          if (c.__wbHoverOut) c.removeEventListener('mouseleave', c.__wbHoverOut);
          c.__wbHoverIn = null;
          c.__wbHoverOut = null;
        } else if (hoverOnly) {
          controls.style.display = layout;
          controls.style.opacity = '0';
          controls.style.transition = 'opacity .2s ease';
          if (c.__wbHoverIn) c.removeEventListener('mouseenter', c.__wbHoverIn);
          if (c.__wbHoverOut) c.removeEventListener('mouseleave', c.__wbHoverOut);
          c.__wbHoverIn = function(){ controls.style.opacity = '1'; };
          c.__wbHoverOut = function(){ controls.style.opacity = '0'; };
          c.addEventListener('mouseenter', c.__wbHoverIn);
          c.addEventListener('mouseleave', c.__wbHoverOut);
        } else {
          controls.style.display = layout;
          controls.style.opacity = '1';
          if (c.__wbHoverIn) c.removeEventListener('mouseenter', c.__wbHoverIn);
          if (c.__wbHoverOut) c.removeEventListener('mouseleave', c.__wbHoverOut);
          c.__wbHoverIn = null;
          c.__wbHoverOut = null;
        }
      }
      function startAuto(c){
        if (c.__wbAutoTimer) { clearInterval(c.__wbAutoTimer); c.__wbAutoTimer = null; }
        var auto = c.dataset.wbCarouselAuto === '1';
        var cards = getCards(c);
        if (!auto || cards.length < 2) return;
        var delaySec = Math.max(2, parseInt(c.dataset.wbCarouselDelaySec || '4', 10) || 4);
        c.__wbAutoTimer = setInterval(function(){ rotateBy(c, 1, 1); }, delaySec * 1000);
      }
      window.wbMediaCardCarouselInitAll = function(root){
        var scope = root || document;
        var list = scope.querySelectorAll('[data-wb-carousel="1"]');
        list.forEach(function(c){
          ensureId(c);
          ensureCardOrigins(c);
          bindControls(c);
          c.removeEventListener('scroll', c.__wbDotSync || function(){});
          c.__wbDotSync = function(){ syncDots(c); };
          c.addEventListener('scroll', c.__wbDotSync, { passive: true });
          syncDots(c);
          startAuto(c);
        });
      };
      document.addEventListener('DOMContentLoaded', function(){ window.wbMediaCardCarouselInitAll(document); });
      window.wbMediaCardCarouselInitAll(document);
    })();`;
  doc.body.appendChild(script);
}

function _syncMediaCarouselControls(sectionEl, containerEl) {
  if (!sectionEl || !containerEl) return;
  containerEl.dataset.wbCarousel = '1';
  const styleKey = _normalizeMediaCarouselStyle(containerEl.dataset.wbCarouselStyle || 'classic');
  const controlPos = _normalizeMediaCarouselControlPos(containerEl.dataset.wbCarouselControlPos || 'bottom-center');
  const controlsVisibility = _normalizeMediaCarouselControlsVisibility(
    containerEl.dataset.wbCarouselControlsVisibility
      || (String(containerEl.dataset.wbCarouselHoverOnly || '') === '1' ? 'hover' : 'always')
  );
  const hoverOnly = controlsVisibility === 'hover';
  const controlsHidden = controlsVisibility === 'hidden';
  const cfg = _mediaCarouselStyleTokens(styleKey);
  if (!containerEl.id) containerEl.id = `media-carousel-${Math.random().toString(36).slice(2, 8)}`;
  containerEl.style.setProperty('overflow-x', 'hidden', 'important');
  containerEl.style.setProperty('scrollbar-width', 'none', 'important');
  const cards = [...containerEl.children].filter(el => ['ARTICLE', 'DIV', 'LI', 'SECTION'].includes(el.tagName));
  cards.forEach((card, idx) => {
    card.dataset.wbCardOrigin = String(idx);
  });
  // Remove legacy static controls that come from the original template markup.
  const legacySibling = containerEl.nextElementSibling;
  if (legacySibling
    && String(legacySibling.getAttribute('data-wb-carousel-controls') || '') !== '1'
    && legacySibling.querySelector('[aria-label="Scroll left"], [aria-label="Scroll right"]')
    && legacySibling.querySelector('a[aria-label^="Slide"], button[aria-label^="Slide"]')) {
    legacySibling.remove();
  }

  const allControls = [...sectionEl.querySelectorAll(`[data-wb-carousel-controls="1"][data-target="${containerEl.id}"]`)];
  let controls = allControls[0] || null;
  if (allControls.length > 1) {
    allControls.slice(1).forEach(el => el.remove());
  }
  if (!controls) {
    controls = sectionEl.ownerDocument.createElement('div');
    containerEl.insertAdjacentElement('afterend', controls);
  }
  controls.setAttribute('data-wb-carousel-controls', '1');
  controls.setAttribute('data-target', containerEl.id);
  controls.style.cssText = 'display:flex;align-items:center;justify-content:center;gap:10px;margin-top:14px;width:100%';
  if (controlPos === 'top-center') {
    controls.setAttribute('data-wb-layout', 'flex');
    controls.style.setProperty('margin-top', '0', 'important');
    controls.style.setProperty('margin-bottom', '10px', 'important');
    containerEl.insertAdjacentElement('beforebegin', controls);
  } else if (controlPos === 'side-overlay') {
    controls.setAttribute('data-wb-layout', 'grid');
    controls.style.setProperty('display', 'grid', 'important');
    controls.style.setProperty('grid-template-columns', '1fr auto 1fr', 'important');
    controls.style.setProperty('align-items', 'center', 'important');
    controls.style.setProperty('width', '100%', 'important');
    controls.style.setProperty('margin-top', '10px', 'important');
    controls.style.setProperty('margin-bottom', '0', 'important');
    containerEl.insertAdjacentElement('afterend', controls);
  } else {
    controls.setAttribute('data-wb-layout', 'flex');
    controls.style.removeProperty('position');
    controls.style.removeProperty('inset');
    controls.style.removeProperty('grid-template-columns');
    controls.style.removeProperty('padding');
    controls.style.removeProperty('z-index');
    controls.style.removeProperty('pointer-events');
    controls.style.removeProperty('margin-bottom');
    controls.style.setProperty('margin-top', '14px', 'important');
    containerEl.insertAdjacentElement('afterend', controls);
  }
  controls.innerHTML = `<button type="button" data-wb-dir="-1" aria-label="Scroll left" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid ${cfg.btnBorder};border-radius:999px;background:${cfg.btnBg};text-decoration:none;color:${cfg.btnColor};cursor:pointer">◀</button>
    <div data-wb-carousel-dots="1" style="display:flex;align-items:center;gap:8px">${cards.map((_, idx) => `<button type="button" data-wb-go="${idx}" aria-label="Slide ${idx + 1}" style="width:9px;height:9px;background:${idx===0?cfg.dotActive:cfg.dotInactive};border-radius:999px;border:none;cursor:pointer;padding:0"></button>`).join('')}</div>
    <button type="button" data-wb-dir="1" aria-label="Scroll right" style="display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border:1px solid ${cfg.btnBorder};border-radius:999px;background:${cfg.btnBg};text-decoration:none;color:${cfg.btnColor};cursor:pointer">▶</button>`;

  if (controlPos === 'side-overlay') {
    const leftBtn = controls.querySelector('button[data-wb-dir="-1"]');
    const rightBtn = controls.querySelector('button[data-wb-dir="1"]');
    const dots = controls.querySelector('[data-wb-carousel-dots="1"]');
    if (leftBtn) leftBtn.style.setProperty('justify-self', 'start', 'important');
    if (rightBtn) rightBtn.style.setProperty('justify-self', 'end', 'important');
    if (dots) dots.style.setProperty('justify-self', 'center', 'important');
  }

  if (controlsHidden) {
    controls.style.setProperty('display', 'none', 'important');
    controls.style.setProperty('opacity', '0', 'important');
    if (containerEl.__wbHoverIn) containerEl.removeEventListener('mouseenter', containerEl.__wbHoverIn);
    if (containerEl.__wbHoverOut) containerEl.removeEventListener('mouseleave', containerEl.__wbHoverOut);
    containerEl.__wbHoverIn = null;
    containerEl.__wbHoverOut = null;
  } else if (hoverOnly) {
    controls.style.setProperty('display', controls.getAttribute('data-wb-layout') === 'grid' ? 'grid' : 'flex', 'important');
    controls.style.setProperty('opacity', '0', 'important');
    controls.style.setProperty('transition', 'opacity .2s ease', 'important');
    if (containerEl.__wbHoverIn) containerEl.removeEventListener('mouseenter', containerEl.__wbHoverIn);
    if (containerEl.__wbHoverOut) containerEl.removeEventListener('mouseleave', containerEl.__wbHoverOut);
    containerEl.__wbHoverIn = () => controls.style.setProperty('opacity', '1', 'important');
    containerEl.__wbHoverOut = () => controls.style.setProperty('opacity', '0', 'important');
    containerEl.addEventListener('mouseenter', containerEl.__wbHoverIn);
    containerEl.addEventListener('mouseleave', containerEl.__wbHoverOut);
  } else {
    controls.style.setProperty('display', controls.getAttribute('data-wb-layout') === 'grid' ? 'grid' : 'flex', 'important');
    controls.style.setProperty('opacity', '1', 'important');
    if (containerEl.__wbHoverIn) containerEl.removeEventListener('mouseenter', containerEl.__wbHoverIn);
    if (containerEl.__wbHoverOut) containerEl.removeEventListener('mouseleave', containerEl.__wbHoverOut);
    containerEl.__wbHoverIn = null;
    containerEl.__wbHoverOut = null;
  }

  _applyMediaCarouselStyle(containerEl, controls, styleKey);
  _wireMediaCarouselInteractions(containerEl, controls);
}

function addGridCardToActiveSection() {
  const frame = document.getElementById('stagingIframe');
  if (!frame.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const fieldsEl = document.getElementById('secEditorFields');
  const gridMeta = fieldsEl?._gridMeta;
  if (!gridMeta || !gridMeta.container) {
    toast('No editable grid found in this section', false);
    return;
  }

  const container = gridMeta.container;
  const cards = [...container.children].filter(el => ['ARTICLE', 'DIV', 'LI', 'SECTION'].includes(el.tagName));
  const template = cards[cards.length - 1] || cards[0];
  if (!template) {
    toast('Unable to add card: no template card found', false);
    return;
  }

  _historyPush();
  const newCard = template.cloneNode(true);
  const nextNum = cards.length + 1;
  const titleEl = newCard.querySelector('h1,h2,h3,h4,h5,strong,b,.title,[class*="title"],[class*="label"]');
  const bodyEl = newCard.querySelector('p,small,span,div');
  const imageEl = newCard.querySelector('img');
  if (titleEl) _setText(titleEl, `Card ${nextNum}`);
  if (bodyEl && bodyEl !== titleEl) _setParagraphText(bodyEl, 'Add description here.');
  if (imageEl) {
    const seed = `media-card-${Date.now()}-${nextNum}`;
    imageEl.src = `https://picsum.photos/seed/${seed}/640/420`;
    imageEl.setAttribute('src', imageEl.src);
    imageEl.alt = `Media item ${nextNum}`;
  }

  if (newCard.id) {
    const sectionId = stagingSections[activeSectionIndex].el.id || `section-${activeSectionIndex + 1}`;
    newCard.id = `${sectionId}-item-${nextNum}`;
  }

  container.appendChild(newCard);
  if (gridMeta.isMediaCarousel) {
    const styleKey = _normalizeMediaCarouselStyle(container.dataset.wbCarouselStyle || 'classic');
    _applyMediaCarouselStyle(container, null, styleKey);
  }
  if (gridMeta.isMediaCarousel) _syncMediaCarouselControls(stagingSections[activeSectionIndex].el, container);
  openSecEditor(activeSectionIndex);
  toast('Grid card added — click Save to persist', true);
}

async function removeGridCardFromActiveSection(cardIdx) {
  const frame = document.getElementById('stagingIframe');
  if (!frame?.contentDocument || activeSectionIndex === null || !stagingSections[activeSectionIndex]) return;
  const fieldsEl = document.getElementById('secEditorFields');
  const gridMeta = fieldsEl?._gridMeta;
  if (!gridMeta || !Array.isArray(gridMeta.items) || !gridMeta.container) {
    toast('No editable grid found in this section', false);
    return;
  }

  const idx = Number(cardIdx) || 0;
  if (gridMeta.items.length <= 1) {
    toast('At least one grid card is required', false);
    return;
  }
  const item = gridMeta.items[idx];
  if (!item?.cardEl) {
    toast('Unable to delete this grid card', false);
    return;
  }

  const ok = await styledConfirm(
    `Delete Grid Item ${idx + 1}? This action can be undone only with Undo.`,
    {
      title: 'Delete Grid Card',
      okLabel: 'Delete',
      okClass: 'btn-danger',
      icon: '🗑',
    }
  );
  if (!ok) return;

  _historyPush();
  item.cardEl.remove();

  if (gridMeta.isMediaCarousel) {
    _syncMediaCarouselControls(stagingSections[activeSectionIndex].el, gridMeta.container);
    frame.contentDocument.defaultView?.wbMediaCardCarouselInitAll?.(frame.contentDocument);
  }

  openSecEditor(activeSectionIndex);
  toast('Grid card deleted — click Save to persist', true);
}

function _normalizeTextAlignValue(v) {
  const raw = String(v || '').toLowerCase();
  if (raw === 'start') return 'left';
  if (raw === 'end') return 'right';
  if (raw.includes('center')) return 'center';
  if (raw.includes('right')) return 'right';
  if (raw.includes('justify')) return 'justify';
  return 'left';
}

function _findHeroTextTarget(sectionEl) {
  if (!sectionEl) return null;
  const preferred = sectionEl.querySelector('.hero-copy, .hero-content, .hero-text, .intro-copy, .intro-content, .banner-copy, .banner-content');
  if (preferred) return preferred;
  const firstText = sectionEl.querySelector('h1, h2, h3, p');
  if (!firstText) return null;
  return firstText.closest('div, section, article, header, main') || sectionEl;
}

function _findHeroImageTarget(sectionEl) {
  if (!sectionEl) return null;
  const imgs = [...sectionEl.querySelectorAll('img')].filter(img => {
    const cls = String(img.className || '').toLowerCase();
    if (/logo|brand|icon|avatar/.test(cls)) return false;
    if (img.closest('.logo, .brand, .brand-cell, .brand-logo-placeholder, nav')) return false;
    return true;
  });
  if (!imgs.length) return null;

  let best = imgs[0];
  let bestArea = 0;
  imgs.forEach(img => {
    const r = img.getBoundingClientRect();
    const area = Math.max(0, r.width * r.height);
    if (area > bestArea) {
      best = img;
      bestArea = area;
    }
  });
  return best;
}

function _findSectionLogoTarget(sectionEl) {
  if (!sectionEl) return null;

  const markedLogo = sectionEl.querySelector('img[data-wb-role="brand-logo"]');
  if (markedLogo) return markedLogo;

  const scopedLogo = sectionEl.querySelector('.brand-cell img, .brand img, .logo img, .site-title img, nav .brand img, nav .logo img, header .brand img, header .logo img');
  if (scopedLogo) return scopedLogo;

  const candidates = [...sectionEl.querySelectorAll('img')];
  if (!candidates.length) return null;

  let best = null;
  let bestScore = -999;
  candidates.forEach((img) => {
    const cls = String(img.className || '').toLowerCase();
    const alt = String(img.alt || '').toLowerCase();
    const inBrandArea = !!img.closest('nav,header,.brand,.logo,.site-title,.brand-cell,[class*="brand"],[class*="logo"]');
    const inContentCard = !!img.closest('article,.card,[class*="card"],.gallery,.mosaic,[data-type="grid-item"]');

    let score = 0;
    if (/logo|brand/.test(cls) || /logo|brand/.test(alt)) score += 10;
    if (inBrandArea) score += 8;
    if (inContentCard) score -= 8;

    const r = img.getBoundingClientRect();
    const w = Math.max(0, r.width || 0);
    const h = Math.max(0, r.height || 0);
    const area = w * h;
    if (area > 0 && area <= 28000) score += 3;
    if (h > 0 && h <= 90) score += 2;
    if (w > 0 && w <= 280) score += 1;

    if (score > bestScore) {
      best = img;
      bestScore = score;
    }
  });

  return bestScore >= 3 ? best : null;
}

function _heroLayoutField(init = {}) {
  const showImage = init.showImage !== false;
  const hasImage = !!init.hasImage;
  const textAlign = _normalizeTextAlignValue(init.textAlign || 'left');
  const vAlign = ['top', 'center', 'bottom'].includes(init.vAlign) ? init.vAlign : 'top';
  const layoutMode = ['preserve','flex','grid'].includes(init.layoutMode) ? init.layoutMode : 'preserve';
  const disabled = hasImage ? '' : 'disabled';
  return `<div data-type="hero-layout" style="border-top:1px dashed var(--border);padding-top:12px;margin-top:6px">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:8px">🧭 Hero / Intro Layout</label>
    <label style="display:flex;align-items:center;gap:7px;font-size:.78rem;color:var(--text);margin-bottom:8px">
      <input type="checkbox" id="heroImageEnabled" ${showImage ? 'checked' : ''} ${disabled}>
      Show intro/hero image
    </label>
    ${hasImage ? '' : '<div style="font-size:.72rem;color:var(--muted);margin:-4px 0 8px 0">No image detected in this section</div>'}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Text align</label>
        <select id="heroTextAlign" style="width:100%;padding:7px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem">
          <option value="left" ${textAlign === 'left' ? 'selected' : ''}>Left</option>
          <option value="center" ${textAlign === 'center' ? 'selected' : ''}>Center</option>
          <option value="right" ${textAlign === 'right' ? 'selected' : ''}>Right</option>
          <option value="justify" ${textAlign === 'justify' ? 'selected' : ''}>Justify</option>
        </select>
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Vertical align</label>
        <select id="heroTextVAlign" style="width:100%;padding:7px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem">
          <option value="top" ${vAlign === 'top' ? 'selected' : ''}>Top</option>
          <option value="center" ${vAlign === 'center' ? 'selected' : ''}>Center</option>
          <option value="bottom" ${vAlign === 'bottom' ? 'selected' : ''}>Bottom</option>
        </select>
      </div>
      <div style="grid-column:1 / span 2">
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Layout mode for vertical align</label>
        <select id="heroLayoutMode" style="width:100%;padding:7px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem">
          <option value="preserve" ${layoutMode === 'preserve' ? 'selected' : ''}>Preserve current layout (safe)</option>
          <option value="flex" ${layoutMode === 'flex' ? 'selected' : ''}>Use flex column</option>
          <option value="grid" ${layoutMode === 'grid' ? 'selected' : ''}>Use grid</option>
        </select>
      </div>
    </div>
  </div>`;
}

function _sectionBoxField(init = {}) {
  const bw = Math.max(0, Math.min(20, Number(init.borderWidth ?? 0) || 0));
  const br = Math.max(0, Math.min(80, Number(init.borderRadius ?? 0) || 0));
  const widthPct = Math.max(20, Math.min(100, Number(init.widthPct ?? 100) || 100));
  const borderStyle = ['none','solid','dashed','dotted','double'].includes(init.borderStyle) ? init.borderStyle : 'none';
  const borderColor = init.borderColor || '#d1d5db';
  const align = ['left','center','right'].includes(init.align) ? init.align : 'center';

  return `<div data-type="section-box" style="border-top:1px dashed var(--border);padding-top:12px;margin-top:6px">
    <label style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:var(--accent);display:block;margin-bottom:8px">📦 Section Box Layout</label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:end">
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Border style</label>
        <select id="secBoxBorderStyle" style="width:100%;padding:7px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem">
          <option value="none" ${borderStyle === 'none' ? 'selected' : ''}>None</option>
          <option value="solid" ${borderStyle === 'solid' ? 'selected' : ''}>Solid</option>
          <option value="dashed" ${borderStyle === 'dashed' ? 'selected' : ''}>Dashed</option>
          <option value="dotted" ${borderStyle === 'dotted' ? 'selected' : ''}>Dotted</option>
          <option value="double" ${borderStyle === 'double' ? 'selected' : ''}>Double</option>
        </select>
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Border color</label>
        <input id="secBoxBorderColor" type="color" value="${borderColor}" style="width:100%;height:34px;padding:2px;border:1.5px solid var(--border);border-radius:6px;background:var(--bg)">
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Border width: <span id="secBoxBorderWidthVal">${Math.round(bw)}px</span></label>
        <input id="secBoxBorderWidth" type="range" min="0" max="20" step="1" value="${Math.round(bw)}" oninput="document.getElementById('secBoxBorderWidthVal').textContent=this.value+'px'" style="width:100%">
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Corner radius: <span id="secBoxRadiusVal">${Math.round(br)}px</span></label>
        <input id="secBoxRadius" type="range" min="0" max="80" step="1" value="${Math.round(br)}" oninput="document.getElementById('secBoxRadiusVal').textContent=this.value+'px'" style="width:100%">
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Width: <span id="secBoxWidthVal">${Math.round(widthPct)}%</span></label>
        <input id="secBoxWidthPct" type="range" min="20" max="100" step="1" value="${Math.round(widthPct)}" oninput="document.getElementById('secBoxWidthVal').textContent=this.value+'%'" style="width:100%">
      </div>
      <div>
        <label style="font-size:.7rem;color:var(--muted);display:block;margin-bottom:4px">Alignment</label>
        <select id="secBoxAlign" style="width:100%;padding:7px 8px;background:var(--bg);border:1.5px solid var(--border);border-radius:6px;color:var(--text);font-size:.8rem">
          <option value="left" ${align === 'left' ? 'selected' : ''}>Left</option>
          <option value="center" ${align === 'center' ? 'selected' : ''}>Center</option>
          <option value="right" ${align === 'right' ? 'selected' : ''}>Right</option>
        </select>
      </div>
    </div>
  </div>`;
}

function _slugifyAnchorName(value = '') {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function _friendlyAnchorName(value = '') {
  return _toTitleWords(String(value || '')
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim());
}

function _sanitizeAnchorFriendlyName(value = '') {
  return String(value || '')
    .replace(/[^A-Za-z0-9\s-]/g, '')
    .replace(/\s+/g, ' ')
    .replace(/-+/g, '-')
    .trim()
    .slice(0, 60);
}

function _sectionEntryLabel(index, baseLabel, anchorId) {
  const slug = _slugifyAnchorName(anchorId || '');
  return `${index + 1}. ${baseLabel}${slug ? ` #${slug}` : ''}`;
}

function _applySectionAnchorRename(fieldsEl, doc, el, index) {
  if (!fieldsEl || !doc || !el) return false;
  const init = fieldsEl._sectionAnchorInit || {};
  const inputEl = document.getElementById('secEditorAnchorName');
  const rawName = String(inputEl?.value || '').trim();
  const nextName = rawName || '';
  const nextId = _slugifyAnchorName(nextName || init.anchorId || el.id || `section-${index + 1}`) || `section-${index + 1}`;
  const prevId = String(init.anchorId || el.id || '').trim();

  if (prevId === nextId && nextName === String(init.anchorName || '').trim()) return false;

  if (prevId && prevId !== nextId) {
    [...doc.querySelectorAll('a')].forEach((a) => {
      if (String(a.getAttribute('href') || '').trim() === `#${prevId}`) {
        a.setAttribute('href', `#${nextId}`);
      }
    });
  }

  el.id = nextId;
  if (nextName) el.dataset.wbAnchorName = nextName;
  else delete el.dataset.wbAnchorName;

  const sectionEntry = stagingSections[index];
  if (sectionEntry) {
    sectionEntry.baseLabel = sectionEntry.baseLabel || init.baseLabel || 'Section';
    sectionEntry.anchorId = nextId;
    sectionEntry.label = _sectionEntryLabel(index, sectionEntry.baseLabel, nextId);
  }

  const editorTitle = document.getElementById('secEditorTitle');
  if (editorTitle && sectionEntry) editorTitle.textContent = sectionEntry.label;
  const anchorPreviewEl = document.getElementById('secEditorAnchorPreview');
  if (anchorPreviewEl) anchorPreviewEl.textContent = `#${nextId}`;

  const badge = el.querySelector('.__wb_badge');
  if (badge) {
    const base = sectionEntry?.baseLabel || 'Section';
    badge.title = `Edit: ${base}${nextId ? ` #${nextId}` : ''}`;
  }
  const anchorChip = el.querySelector('.__wb_badge_anchor');
  if (anchorChip) {
    anchorChip.textContent = `#${nextId}`;
    anchorChip.title = `Anchor target: #${nextId}`;
  }

  fieldsEl._sectionAnchorInit = {
    anchorName: nextName,
    anchorId: nextId,
    baseLabel: sectionEntry?.baseLabel || init.baseLabel || 'Section',
  };
  return true;
}

/* Set text on an element without destroying inner styling spans/em/strong.
   Walks down to the deepest single-child inline element that holds the text,
   so font classes on wrappers like <span class="fancy"> are preserved. */
function _setText(el, text) {
  // Walk into sole child inline elements (span, em, strong, b, i, a without href change)
  const target = _getDeepTextTarget(el);
  // Only set textContent on the deepest target; preserves all ancestor element classes/styles
  target.textContent = text;
}

/* Apply style bar values from the editor panel onto a live DOM element */
function _applyStyleBarToEl(fieldsEl, fid, domEl) {
  const font   = fieldsEl.querySelector(`[data-fid="${fid}-font"]`)?.value   || '';
  const size   = fieldsEl.querySelector(`[data-fid="${fid}-size"]`)?.value   || '';
  const weight = fieldsEl.querySelector(`[data-fid="${fid}-weight"]`)?.value || '';
  const align  = fieldsEl.querySelector(`[data-fid="${fid}-align"]`)?.value  || '';
  const color  = fieldsEl.querySelector(`[data-fid="${fid}-color"]`)?.value  || '';
  const boldActive   = fieldsEl.querySelector(`[data-fid="${fid}-bold"]`)?.dataset.active === '1';
  const italicActive = fieldsEl.querySelector(`[data-fid="${fid}-italic"]`)?.dataset.active === '1';
  // Use setProperty with 'important' so styles override template !important CSS rules
  if (font)   domEl.style.setProperty('font-family',  font,               'important');
  if (size)   domEl.style.setProperty('font-size',    size,               'important');
  if (align)  domEl.style.setProperty('text-align',   align,              'important');
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
  const isMediaCardCarousel = _isMediaCardCarouselSection(el);

  // Rebuild editable element lists from the section.
  // Prefer the exact targets captured when opening the editor so field order stays stable.
  const headings  = fieldsEl._headingEls || [...el.querySelectorAll('h1,h2,h3,h4')].filter(h => h.innerText.trim());
  const paras     = fieldsEl._paraEls || [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3);
  const links     = [...el.querySelectorAll('a')].filter(a => {
    if (String(a?.dataset?.wbMediaType || '').toLowerCase() === 'social') return false;
    const text = (a.textContent || '').trim();
    return text.length > 0 && text.length <= 60;
  });
  let imgs        = [...el.querySelectorAll('img')];

  let hIdx = 0, pIdx = 0, lIdx = 0, iIdx = 0;
  let fieldNum = 0;
  _ensureImageAnimationStyles(doc);
  _ensureWbClickActionEngine(doc);

  // Logo + Brand Name — only for first section
  if (activeSectionIndex === 0) {
    const LOGO_FIXED_HEIGHT_PX = 32;

    fieldNum++;
    const logoFid = `img-${fieldNum}`;
    const logoSrcEl = fieldsEl.querySelector(`input[data-fid="${logoFid}-src"]`);
    const logoAltEl = fieldsEl.querySelector(`input[data-fid="${logoFid}-alt"]`);
    if (logoSrcEl && logoSrcEl.value.trim()) {
      let logoImg = fieldsEl._logoEl || _findSectionLogoTarget(el);
      if (!logoImg) {
        logoImg = el.ownerDocument.createElement('img');
        logoImg.style.cssText = `height:${LOGO_FIXED_HEIGHT_PX}px;max-height:${LOGO_FIXED_HEIGHT_PX}px;width:auto;object-fit:contain;vertical-align:middle;margin:0 8px 0 0`;
        const insertWrap = el.querySelector('.brand-cell, .brand, .logo, .site-title, [class*="brand"], [class*="logo"], nav, header') || el;
        insertWrap.prepend(logoImg);
        imgs = [logoImg, ...imgs]; iIdx = 0;
      }
      logoImg.setAttribute('data-wb-role', 'brand-logo');
      logoImg.src = logoSrcEl.value;
      logoImg.setAttribute('src', logoSrcEl.value);
      if (logoAltEl) logoImg.alt = logoAltEl.value;

      // Keep logo grouped with brand text when a brand container exists.
      const brandWrapEl = el.querySelector('.brand, .logo, .site-title, [class*="brand"], [class*="logo"]');
      if (brandWrapEl && logoImg.parentElement !== brandWrapEl) {
        brandWrapEl.prepend(logoImg);
      }

      // Keep nav/header layout stable after logo replacement.
      logoImg.style.setProperty('height', `${LOGO_FIXED_HEIGHT_PX}px`, 'important');
      logoImg.style.setProperty('width', 'auto', 'important');
      logoImg.style.setProperty('max-height', `${LOGO_FIXED_HEIGHT_PX}px`, 'important');
      logoImg.style.setProperty('max-width', '220px', 'important');
      logoImg.style.setProperty('object-fit', 'contain', 'important');
      logoImg.style.setProperty('display', 'inline-block', 'important');
      logoImg.style.setProperty('vertical-align', 'middle', 'important');
      logoImg.style.setProperty('margin', '0 8px 0 0', 'important');
      logoImg.style.setProperty('flex-shrink', '0', 'important');

      const logoWrap = logoImg.parentElement;
      if (logoWrap) {
        const wrapStyle = logoWrap.style;
        if (wrapStyle.getPropertyValue('display') === 'inline-flex') wrapStyle.removeProperty('display');
        if (wrapStyle.getPropertyValue('align-items') === 'center') wrapStyle.removeProperty('align-items');
        const wrapGap = wrapStyle.getPropertyValue('gap');
        if (wrapGap === '6px' || wrapGap === '10px') wrapStyle.removeProperty('gap');
      }
      fieldsEl._logoEl = logoImg;
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
        _applyClickActionFromField(fieldsEl, brandFid, brandEl);
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
    _applyClickActionFromField(fieldsEl, fid, h);
  });

  // Paragraphs — apply text + styles
  const paraEntries = fieldsEl._paraEntries || paras.map((p, idx) => ({ el: p, fid: `para-${fieldNum + idx + 1}`, parts: [p.innerText || ''], partIndex: 0, isSplit: false }));
  const paraGroups = new Map();
  paraEntries.forEach((entry, idx) => {
    const fid = entry.fid || `para-${fieldNum + idx + 1}`;
    const ta = fieldsEl.querySelector(`textarea[data-fid="${fid}"]`);
    const groupKey = entry.el;
    if (!paraGroups.has(groupKey)) paraGroups.set(groupKey, { el: entry.el, entries: [] });
    paraGroups.get(groupKey).entries.push({ ...entry, fid, ta });
    _applyStyleBarToEl(fieldsEl, fid, entry.el);
  });
  paraGroups.forEach(({ el: paraEl, entries: groupEntries }) => {
    const ordered = groupEntries.sort((a, b) => a.partIndex - b.partIndex);
    const merged = ordered.map(item => String(item.ta ? item.ta.value : '')).join('\n\n');
    _setParagraphText(paraEl, merged);
  });
  fieldNum += paraEntries.length;

  // Links — iterate by current field order (supports add/remove/reorder)
  if (!isMediaCardCarousel) {
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
    const textColor = div.querySelector(`input[data-fid="${fid}-text-color"]`)?.value || '';
    const bgEnabled = !!div.querySelector(`input[data-fid="${fid}-bg-enabled"]`)?.checked;
    const bgColor = bgEnabled ? (div.querySelector(`input[data-fid="${fid}-bg"]`)?.value || '') : '';
    const hoverEnabled = !!div.querySelector(`input[data-fid="${fid}-hover-bg-enabled"]`)?.checked;
    const hoverBgColor = hoverEnabled ? (div.querySelector(`input[data-fid="${fid}-hover-bg"]`)?.value || '') : '';
    const hoverTextColor = hoverEnabled ? (div.querySelector(`input[data-fid="${fid}-hover-text-color"]`)?.value || '') : '';
    if (anchor) {
      _setText(anchor, newText);
      anchor.setAttribute('href', newHref || '#');
      // Preserve the exact case entered in the editor, even when template CSS forces uppercase.
      anchor.style.setProperty('text-transform', 'none', 'important');
      if (bgColor) {
        anchor.style.setProperty('background-color', bgColor, 'important');
        if (!anchor.style.padding) anchor.style.setProperty('padding', '6px 12px', 'important');
        if (!anchor.style.borderRadius) anchor.style.setProperty('border-radius', '999px', 'important');
        anchor.style.setProperty('display', 'inline-block', 'important');
      } else {
        anchor.style.removeProperty('background-color');
      }
      if (textColor) anchor.style.setProperty('color', textColor, 'important');
      const linkId = _ensureWbLinkId(anchor);
      _upsertLinkHoverRule(el.ownerDocument, linkId, hoverBgColor, hoverTextColor);
      orderedAnchors.push(anchor);
    } else if (newText) {
      // Newly added field (no _anchorEl) — create fresh anchor
      const a = el.ownerDocument.createElement('a');
      a.textContent = newText;
      a.setAttribute('href', newHref || '#');
      a.style.cssText = 'display:inline-block;margin:4px 8px;color:var(--accent,#6366f1);text-transform:none';
      if (bgColor) {
        a.style.setProperty('background-color', bgColor, 'important');
        a.style.setProperty('padding', '6px 12px', 'important');
        a.style.setProperty('border-radius', '999px', 'important');
      }
      if (textColor) a.style.setProperty('color', textColor, 'important');
      const linkId = _ensureWbLinkId(a);
      _upsertLinkHoverRule(el.ownerDocument, linkId, hoverBgColor, hoverTextColor);
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
  }

  const _replaceMediaNodeType = (node, targetType) => {
    if (!node || !node.ownerDocument) return node;
    const doc2 = node.ownerDocument;
    const currentType = String(node.dataset?.wbMediaType || (node.tagName === 'VIDEO' ? 'video' : (node.tagName === 'A' ? 'social' : 'image'))).toLowerCase();
    if (currentType === targetType) return node;

    const replacement = targetType === 'video'
      ? doc2.createElement('video')
      : targetType === 'social'
        ? doc2.createElement('a')
        : doc2.createElement('img');

    replacement.style.cssText = node.style.cssText || '';
    replacement.className = node.className || '';
    replacement.setAttribute('data-wb-media-type', targetType);

    if (targetType === 'video') {
      replacement.setAttribute('controls', 'controls');
      replacement.setAttribute('playsinline', 'playsinline');
      replacement.setAttribute('preload', 'metadata');
    }
    if (targetType === 'social') {
      replacement.setAttribute('target', '_blank');
      replacement.setAttribute('rel', 'noopener noreferrer');
      replacement.style.setProperty('display', 'inline-block', 'important');
      replacement.style.setProperty('text-decoration', 'underline', 'important');
    }

    node.replaceWith(replacement);
    return replacement;
  };

  const mediaDivs = [...fieldsEl.querySelectorAll('[data-type="img"]')];
  const skipLogoField = activeSectionIndex === 0 ? 1 : 0;
  mediaDivs.slice(skipLogoField).forEach((div) => {
    fieldNum++;
    const fid = String(div.getAttribute('data-fid') || `img-${fieldNum}`);
    const srcEl = fieldsEl.querySelector(`input[data-fid="${fid}-src"]`);
    const altEl = fieldsEl.querySelector(`input[data-fid="${fid}-alt"]`);
    const animEl = fieldsEl.querySelector(`select[data-fid="${fid}-anim"]`);
    const typeEl = fieldsEl.querySelector(`select[data-fid="${fid}-media-type"]`);
    const mediaType = String(typeEl?.value || 'image').toLowerCase();

    let node = div._imgEl || fieldsEl._imgFidToEl?.get(fid);
    if (!node) {
      const fallback = mediaType === 'video'
        ? el.ownerDocument.createElement('video')
        : mediaType === 'social'
          ? el.ownerDocument.createElement('a')
          : el.ownerDocument.createElement('img');
      fallback.setAttribute('data-wb-media-type', mediaType);
      el.appendChild(fallback);
      node = fallback;
    }
    node = _replaceMediaNodeType(node, mediaType);
    node.dataset.wbMediaType = mediaType;

    const rawSrc = String(srcEl?.value || '').trim();
    const newSrc = mediaType === 'social' ? _normalizeClickActionUrl(rawSrc) : _normalizeStagingAssetUrl(rawSrc);
    const newAlt = String(altEl?.value || '').trim();

    if (mediaType === 'image') {
      if (newSrc) {
        node.src = newSrc;
        node.setAttribute('src', newSrc);
        node.style.removeProperty('display');
        delete node.dataset.wbEditorHidden;
      } else {
        node.removeAttribute('src');
        node.style.setProperty('display', 'none', 'important');
        node.dataset.wbEditorHidden = '1';
      }
      node.alt = newAlt;
      _applyImgAnimation(node, animEl?.value || 'none');
      _applyClickActionFromField(fieldsEl, fid, node);
    } else if (mediaType === 'video') {
      node.removeAttribute('href');
      node.textContent = '';
      if (newSrc) {
        node.setAttribute('src', newSrc);
        node.src = newSrc;
        node.style.removeProperty('display');
      } else {
        node.removeAttribute('src');
        node.style.setProperty('display', 'none', 'important');
      }
      if (newAlt) node.setAttribute('aria-label', newAlt);
      _applyClickActionFromField(fieldsEl, fid, node);
    } else {
      node.removeAttribute('src');
      node.setAttribute('href', newSrc || '#');
      node.textContent = newAlt || 'Open Social Link';
      node.style.removeProperty('display');
      node.removeAttribute('alt');
      _applyClickActionFromField(fieldsEl, fid, node);
    }

    div._imgEl = node;
    if (fieldsEl._imgFidToEl && typeof fieldsEl._imgFidToEl.set === 'function') {
      fieldsEl._imgFidToEl.set(fid, node);
    }
  });

  // Alliance table rows (if present in this section)
  const allianceMeta = fieldsEl._allianceMeta;
  if (allianceMeta && Array.isArray(allianceMeta.rows)) {
    allianceMeta.rows.forEach((rowEl, rowIdx) => {
      if (!rowEl || !rowEl.isConnected) return;
      const logo = fieldsEl.querySelector(`[data-fid="ar-${rowIdx}-logo"]`)?.value?.trim() || '';
      const brand = fieldsEl.querySelector(`[data-fid="ar-${rowIdx}-brand"]`)?.value?.trim() || '';
      const category = fieldsEl.querySelector(`[data-fid="ar-${rowIdx}-category"]`)?.value?.trim() || '';
      const support = fieldsEl.querySelector(`[data-fid="ar-${rowIdx}-support"]`)?.value?.trim() || '';

      const cells = [...rowEl.querySelectorAll('td')];
      const c0 = cells[0];
      const c1 = cells[1];
      const c2 = cells[2];
      if (!c0) return;

      const img = c0.querySelector('img');
      const strong = c0.querySelector('strong');
      if (img && logo) {
        img.src = logo;
        img.setAttribute('src', logo);
      }
      if (img && brand) img.alt = `${brand} logo`;
      if (strong && brand) {
        _setText(strong, brand);
      } else if (!img && brand) {
        _setText(c0, brand);
      }
      if (c1 && category) _setText(c1, category);
      if (c2 && support) _setParagraphText(c2, support);
    });
  }

  // Generic grid/card item edits
  const gridMeta = fieldsEl._gridMeta;
  if (gridMeta && Array.isArray(gridMeta.items)) {
    gridMeta.items.forEach((item, idx2) => {
      const titleVal = fieldsEl.querySelector(`[data-fid="grid-${idx2}-title"]`)?.value?.trim() || '';
      const bodyVal = fieldsEl.querySelector(`[data-fid="grid-${idx2}-body"]`)?.value || '';
      const imageValRaw = fieldsEl.querySelector(`[data-fid="grid-${idx2}-image-src"]`)?.value?.trim() || '';
      const imageVal = _normalizeStagingAssetUrl(imageValRaw);
      const imageAlt = fieldsEl.querySelector(`[data-fid="grid-${idx2}-image-alt"]`)?.value?.trim() || "";
      const titleAlign = fieldsEl.querySelector(`[data-fid="grid-${idx2}-title-align"]`)?.value || 'left';
      if (item.titleEl) _setText(item.titleEl, titleVal);
      if (item.bodyEl) _setParagraphText(item.bodyEl, bodyVal);
      if (item.imageEl) {
        if (imageVal) {
          item.imageEl.src = imageVal;
          item.imageEl.setAttribute('src', imageVal);
          item.imageEl.style.removeProperty('display');
          delete item.imageEl.dataset.wbEditorHidden;
        } else {
          item.imageEl.removeAttribute('src');
          item.imageEl.style.setProperty('display', 'none', 'important');
          item.imageEl.dataset.wbEditorHidden = '1';
        }
        item.imageEl.alt = imageAlt || '';
      }
      if (item.titleEl) {
        _applyStyleBarToEl(fieldsEl, `grid-${idx2}-title`, item.titleEl);
        item.titleEl.style.setProperty('text-align', titleAlign, 'important');
        _applyClickActionFromField(fieldsEl, `grid-${idx2}-title`, item.titleEl);
      }
      if (item.imageEl) {
        _applyClickActionFromField(fieldsEl, `grid-${idx2}-image`, item.imageEl);
      }
      if (!item.titleEl) {
        const tgt = item.cardEl.querySelector('h1,h2,h3,h4,h5,strong,b') || item.cardEl;
        _setText(tgt, titleVal);
      }
      if (!item.bodyEl && bodyVal.trim()) {
        const p = [...item.cardEl.querySelectorAll('p,small,span,div')].find(n => n !== item.titleEl) || null;
        if (p) {
          _setParagraphText(p, bodyVal);
        } else {
          let fallback = item.cardEl.querySelector('[data-wb-grid-body="1"]');
          if (!fallback) {
            fallback = item.cardEl.ownerDocument.createElement('div');
            fallback.setAttribute('data-wb-grid-body', '1');
            item.cardEl.appendChild(fallback);
          }
          _setParagraphText(fallback, bodyVal);
        }
      }
    });

    if (gridMeta.isMediaCarousel) {
      const autoEnabled = !!fieldsEl.querySelector('[data-fid="grid-carousel-auto"]')?.checked;
      const delaySec = Math.max(2, Math.min(60,
        parseInt(fieldsEl.querySelector('[data-fid="grid-carousel-delay"]')?.value || '4', 10) || 4
      ));
      const styleKey = _normalizeMediaCarouselStyle(fieldsEl.querySelector('[data-fid="grid-carousel-style"]')?.value || 'classic');
      const controlPos = _normalizeMediaCarouselControlPos(fieldsEl.querySelector('[data-fid="grid-carousel-control-pos"]')?.value || 'bottom-center');
      const controlsVisibility = _normalizeMediaCarouselControlsVisibility(
        fieldsEl.querySelector('[data-fid="grid-carousel-controls-visibility"]')?.value || 'always'
      );
      const hoverOnly = controlsVisibility === 'hover';
      gridMeta.container.dataset.wbCarousel = '1';
      gridMeta.container.dataset.wbCarouselAuto = autoEnabled ? '1' : '0';
      gridMeta.container.dataset.wbCarouselDelaySec = String(delaySec);
      gridMeta.container.dataset.wbCarouselStyle = styleKey;
      gridMeta.container.dataset.wbCarouselControlPos = controlPos;
      gridMeta.container.dataset.wbCarouselControlsVisibility = controlsVisibility;
      gridMeta.container.dataset.wbCarouselHoverOnly = hoverOnly ? '1' : '0';
      _syncMediaCarouselControls(el, gridMeta.container);
      _ensureMediaCardCarouselRuntime(doc);
      doc.defaultView?.wbMediaCardCarouselInitAll?.(doc);
    }
  }

  // Image collage edits (order + weight + focus)
  const collageMeta = fieldsEl._collageMeta;
  if (collageMeta && collageMeta.container) {
    const autoFit = !!fieldsEl.querySelector('#collageAutoFit')?.checked;
    const centered = !!fieldsEl.querySelector('#collageCenterSection')?.checked;
    const styleKey = fieldsEl.querySelector('#collageStyleKey')?.value || 'professional';
    const breathing = fieldsEl.querySelector('#collageBreathing')?.value || 'normal';
    const fillStrategy = fieldsEl.querySelector('#collageFillStrategy')?.value || 'balanced';
    _applyImageCollageLayout(collageMeta.container, { autoFit, centered, styleKey, breathing, fillStrategy });
    const collageCards = [...fieldsEl.querySelectorAll('[data-type="collage-item"]')];
    const nextOrder = [];

    collageCards.forEach((card, idx2) => {
      const fid = String(card.getAttribute('data-fid') || `collage-${idx2}-image`);
      const srcRaw = fieldsEl.querySelector(`[data-fid="${fid}-src"]`)?.value || '';
      const src = _normalizeStagingAssetUrl(String(srcRaw).trim());
      const alt = String(fieldsEl.querySelector(`[data-fid="${fid}-alt"]`)?.value || '').trim();
      const weight = Math.max(1, Math.min(4, parseInt(fieldsEl.querySelector(`[data-fid="${fid}-weight"]`)?.value || '1', 10) || 1));
      const focusX = Math.max(0, Math.min(100, parseInt(fieldsEl.querySelector(`[data-fid="${fid}-focus-x"]`)?.value || '50', 10) || 50));
      const focusY = Math.max(0, Math.min(100, parseInt(fieldsEl.querySelector(`[data-fid="${fid}-focus-y"]`)?.value || '50', 10) || 50));

      let itemEl = card._collageItemEl || collageMeta.fidToItem?.get(fid) || null;
      if (!itemEl) {
        itemEl = el.ownerDocument.createElement('figure');
        itemEl.setAttribute('data-wb-collage-item', '1');
        itemEl.style.cssText = 'margin:0;border-radius:14px;overflow:hidden;background:#e2e8f0';
        collageMeta.container.appendChild(itemEl);
      }

      let imgEl = itemEl.querySelector('img');
      if (!imgEl) {
        imgEl = el.ownerDocument.createElement('img');
        imgEl.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block';
        itemEl.appendChild(imgEl);
      }

      imgEl.style.setProperty('flex', '0 0 auto', 'important');
      if (src) {
        imgEl.src = src;
        imgEl.setAttribute('src', src);
      }
      imgEl.alt = alt || imgEl.alt || 'Collage image';
      imgEl.style.setProperty('object-fit', autoFit ? 'contain' : 'cover', 'important');
      imgEl.style.setProperty('object-position', autoFit ? '50% 50%' : `${focusX}% ${focusY}%`, 'important');
      imgEl.dataset.wbFocusX = String(focusX);
      imgEl.dataset.wbFocusY = String(focusY);
      _applyImageCollageWeight(itemEl, weight);

      card._collageItemEl = itemEl;
      if (collageMeta.fidToItem && typeof collageMeta.fidToItem.set === 'function') {
        collageMeta.fidToItem.set(fid, itemEl);
      }
      nextOrder.push(itemEl);
    });

    const existingItems = [...collageMeta.container.children].filter(node => ['FIGURE', 'DIV', 'ARTICLE', 'LI'].includes(node.tagName));
    existingItems.forEach((node) => {
      if (!nextOrder.includes(node)) node.remove();
    });
    nextOrder.forEach((node) => collageMeta.container.appendChild(node));
    collageMeta.items = nextOrder.map((node) => ({ itemEl: node, imageEl: node.querySelector('img') || null }));
  }

  // Hero/Intro layout controls
  const heroMeta = fieldsEl._heroMeta;
  if (heroMeta) {
    const textTarget = heroMeta.textTarget || heroMeta.sectionEl || el;
    const layoutTarget = heroMeta.sectionEl || textTarget;
    const imageTarget = heroMeta.imageTarget;
    const showImage = !!fieldsEl.querySelector('#heroImageEnabled')?.checked;
    const textAlign = fieldsEl.querySelector('#heroTextAlign')?.value || 'left';
    const vAlign = fieldsEl.querySelector('#heroTextVAlign')?.value || 'top';
    const layoutMode = fieldsEl.querySelector('#heroLayoutMode')?.value || 'preserve';

    if (imageTarget) {
      if (showImage) {
        const prev = imageTarget.dataset.wbPrevDisplay || '';
        if (prev && prev !== 'none') imageTarget.style.setProperty('display', prev, 'important');
        else imageTarget.style.removeProperty('display');
        delete imageTarget.dataset.wbEditorHidden;
      } else {
        if (!imageTarget.dataset.wbPrevDisplay) {
          const prev = imageTarget.style.display || imageTarget.ownerDocument.defaultView.getComputedStyle(imageTarget).display || '';
          imageTarget.dataset.wbPrevDisplay = prev;
        }
        imageTarget.style.setProperty('display', 'none', 'important');
        imageTarget.dataset.wbEditorHidden = '1';
      }
    }

    if (textTarget) {
      textTarget.style.setProperty('text-align', textAlign, 'important');
      const v = (vAlign === 'center') ? 'center' : (vAlign === 'bottom' ? 'flex-end' : 'flex-start');
      const gridV = (vAlign === 'center') ? 'center' : (vAlign === 'bottom' ? 'end' : 'start');
      const tag = layoutTarget ? layoutTarget.tagName : textTarget.tagName;
      const canLayout = ['DIV', 'SECTION', 'ARTICLE', 'HEADER', 'MAIN'].includes(tag);
      if (canLayout) {
        const currentDisplay = (layoutTarget.style.display || layoutTarget.ownerDocument.defaultView.getComputedStyle(layoutTarget).display || '').toLowerCase();
        if (layoutMode === 'grid') {
          layoutTarget.style.setProperty('display', 'grid', 'important');
          layoutTarget.style.setProperty('align-content', gridV, 'important');
          layoutTarget.style.removeProperty('justify-content');
          layoutTarget.style.removeProperty('flex-direction');
        } else if (layoutMode === 'flex') {
          layoutTarget.style.setProperty('display', 'flex', 'important');
          layoutTarget.style.setProperty('flex-direction', 'column', 'important');
          layoutTarget.style.setProperty('justify-content', v, 'important');
          if (!layoutTarget.style.minHeight) layoutTarget.style.setProperty('min-height', '100%', 'important');
          layoutTarget.style.removeProperty('align-content');
        } else {
          // Preserve section's existing layout mode and only apply compatible property.
          if (currentDisplay === 'grid') {
            layoutTarget.style.setProperty('align-content', gridV, 'important');
          } else if (currentDisplay.includes('flex')) {
            layoutTarget.style.setProperty('justify-content', v, 'important');
          }
        }
      }
      textTarget.dataset.wbValign = v;
      textTarget.dataset.wbLayoutMode = layoutMode;
    }
  }

  // Section box controls
  const sectionAnchorMeta = fieldsEl._sectionAnchorMeta;
  if (sectionAnchorMeta && sectionAnchorMeta.target) {
    _applySectionAnchorRename(fieldsEl, doc, sectionAnchorMeta.target, activeSectionIndex);
  }

  const sectionBoxMeta = fieldsEl._sectionBoxMeta;
  if (sectionBoxMeta && sectionBoxMeta.target) {
    if (_isSectionBoxPanelDirty(fieldsEl)) {
      const target = sectionBoxMeta.target;
      const init = fieldsEl._sectionBoxInit || {};
      const borderStyle = fieldsEl.querySelector('#secBoxBorderStyle')?.value || 'none';
      const borderColor = fieldsEl.querySelector('#secBoxBorderColor')?.value || '#d1d5db';
      const borderWidth = Math.max(0, parseInt(fieldsEl.querySelector('#secBoxBorderWidth')?.value || '0', 10) || 0);
      const radius = Math.max(0, parseInt(fieldsEl.querySelector('#secBoxRadius')?.value || '0', 10) || 0);
      const widthPct = Math.max(20, Math.min(100, parseInt(fieldsEl.querySelector('#secBoxWidthPct')?.value || '100', 10) || 100));
      const align = fieldsEl.querySelector('#secBoxAlign')?.value || 'center';

      const sizeChanged = widthPct !== (init.widthPct ?? 100) || align !== (init.align || 'center');
      const borderChanged = borderStyle !== (init.borderStyle || 'none') ||
        borderColor !== (init.borderColor || '#d1d5db') ||
        borderWidth !== (init.borderWidth ?? 0);
      const radiusChanged = radius !== (init.radius ?? 0);

      target.style.setProperty('box-sizing', 'border-box', 'important');

      if (sizeChanged) {
        target.style.setProperty('width', `${widthPct}%`, 'important');
        if (align === 'left') {
          target.style.setProperty('margin-left', '0', 'important');
          target.style.setProperty('margin-right', 'auto', 'important');
        } else if (align === 'right') {
          target.style.setProperty('margin-left', 'auto', 'important');
          target.style.setProperty('margin-right', '0', 'important');
        } else {
          target.style.setProperty('margin-left', 'auto', 'important');
          target.style.setProperty('margin-right', 'auto', 'important');
        }
      }

      if (borderChanged) {
        target.style.setProperty('border-style', borderStyle, 'important');
        target.style.setProperty('border-width', `${borderWidth}px`, 'important');
        target.style.setProperty('border-color', borderColor, 'important');
        if (borderStyle === 'none' || borderWidth === 0) {
          target.style.setProperty('border-width', '0px', 'important');
        }
      }

      if (radiusChanged) {
        target.style.setProperty('border-radius', `${radius}px`, 'important');
      }
    }
  }

  // Apply background (colour + image) if the bg panel fields exist
  if (document.getElementById('secBgColor') || document.getElementById('secBgUrl')) {
    if (_isBgPanelDirty(fieldsEl)) {
      _applyBgToEl(el);
    }
  }

  try { if (doc.defaultView && typeof doc.defaultView.__wbApplyClickBindings === 'function') doc.defaultView.__wbApplyClickBindings(); } catch(_) {}
  _renderSecList();

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
    fd.append('file', blob, file.name || 'image.png');
    if (stagedWebsiteId) fd.append('website_id', stagedWebsiteId);
    const r = await fetch(`${API}/media/upload-image`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (r.ok) {
      const data = await r.json();
      const uploadedUrl = _normalizeStagingAssetUrl(data.full_url || data.thumb_url || '');
      let url = uploadedUrl;
      try {
        const site = (websites || []).find(x => x.website_id === stagedWebsiteId);
        const localPath = String(site?.local_path || '').replace(/\\/g, '/').replace(/\/+$/, '');
        const siteSlug = localPath ? localPath.split('/').filter(Boolean).pop() : (String(currentStagingUrl || '').match(/\/output\/staging\/([^/]+)/i)?.[1] || '');
        const fileMatch = String(uploadedUrl || '').match(/assets\/uploads\/([^/?#]+)/i);
        const filename = fileMatch ? fileMatch[1] : '';
        if (siteSlug && filename && stagedWebsiteId) {
          const fr = await fetch(`${API}/media/finalize-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ website_id: stagedWebsiteId, site_slug: siteSlug, filename }),
          });
          if (fr.ok) {
            const fdata = await fr.json();
            url = _normalizeStagingAssetUrl(fdata.image_url || uploadedUrl);
          }
        }
      } catch (_) {}
      const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
      _setImageSourceFieldValue(fid, url);
      // Show thumbnail preview
      const wrap = srcEl?.closest('[data-fid]');
      if (wrap) {
        const existing = wrap.querySelector('img');
        const previewSrc = _toPreviewMediaUrl(url);
        if (existing) existing.src = previewSrc;
        else { const img = document.createElement('img'); img.src = previewSrc; img.style.cssText='height:54px;width:80px;object-fit:cover;border-radius:5px;border:1px solid var(--border);margin-top:6px'; wrap.prepend(img); }
      }
      toast('Image uploaded ✅');
    } else {
      toast('Image upload failed', false);
    }
  });
}

function clearSectionImage(fid) {
  const srcEl = document.querySelector(`[data-fid="${fid}-src"]`);
  _setImageSourceFieldValue(fid, '');
  const wrap = srcEl?.closest('[data-fid]');
  if (wrap) {
    const img = wrap.querySelector('img');
    if (img) {
      img.removeAttribute('src');
      img.style.setProperty('display', 'none', 'important');
    }
  }
  const fieldsEl = document.getElementById('secEditorFields');
  const liveImg = (wrap && wrap._imgEl) || fieldsEl?._imgFidToEl?.get(fid);
  if (liveImg) {
    liveImg.removeAttribute('src');
    liveImg.style.setProperty('display', 'none', 'important');
    liveImg.dataset.wbEditorHidden = '1';
    const status = document.getElementById('stagingStatusBar');
    if (status) status.textContent = 'Preview updated — unsaved. Click 💾 Save Changes.';
  }
}

function closeSecEditor() {
  activeSectionIndex = null;
  document.getElementById('secEditor').style.display = 'none';
  const modeNoteEl = document.getElementById('secEditorModeNote');
  if (modeNoteEl) modeNoteEl.style.display = 'none';
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
      font-size: 1.6rem; cursor: pointer; color: #fff; padding: 4px 8px; z-index: 1001; position: relative;
      min-width: 44px !important; min-height: 44px !important; }

    /* ── Fluid media ── */
    img, video, iframe, embed, object { max-width: 100% !important; height: auto !important; }
    #product article img,
    section[data-wb-anchor-name="product"] article img,
    #biochemistry article img,
    section[data-wb-anchor-name="biochemistry"] article img,
    #electrolyte article img,
    section[data-wb-anchor-name="electrolyte"] article img,
    #haematology article img,
    section[data-wb-anchor-name="haematology"] article img,
    #immunoassay article img,
    section[data-wb-anchor-name="immunoassay"] article img,
    #others article img,
    section[data-wb-anchor-name="others"] article img {
      width: 100% !important;
      height: clamp(170px, 22vw, 260px) !important;
      object-fit: cover !important;
      object-position: 50% 50% !important;
      display: block !important;
    }

    /* ── Add-Section templates: explicit responsive behavior ── */
    section[data-wb-sec-template="image-text"] > div[style*="grid-template-columns"] {
      grid-template-columns: 1fr !important;
      gap: 24px !important;
    }
    section[data-wb-sec-template="cards-grid"] div[style*="grid-template-columns"],
    section[data-wb-sec-template="testimonials"] div[style*="grid-template-columns"],
    section[data-wb-sec-template="gallery"] div[style*="grid-template-columns"] {
      grid-template-columns: 1fr !important;
    }
    section[data-wb-sec-template="media-card-carousel"] div[style*="grid-auto-flow"] {
      display: grid !important;
      grid-auto-flow: row !important;
      grid-auto-columns: unset !important;
      grid-template-columns: 1fr !important;
      overflow-x: visible !important;
      scroll-snap-type: none !important;
    }
    section[data-wb-sec-template="media-card-carousel"] article {
      height: 100% !important;
      display: flex !important;
      flex-direction: column !important;
      align-items: stretch !important;
    }
    section[data-wb-sec-template="media-card-carousel"] article img {
      width: 100% !important;
      height: clamp(170px, 22vw, 260px) !important;
      object-fit: cover !important;
      object-position: 50% 50% !important;
      display: block !important;
    }
    section[data-wb-sec-template="cta"] h2,
    section[data-wb-sec-template="text-content"] h2,
    section[data-wb-sec-template="cards-grid"] h2,
    section[data-wb-sec-template="testimonials"] h2,
    section[data-wb-sec-template="faq"] h2,
    section[data-wb-sec-template="gallery"] h2,
    section[data-wb-sec-template="photo-mosaic-mix"] h2 {
      font-size: clamp(1.45rem, 4.8vw, 2.2rem) !important;
      line-height: 1.25 !important;
    }
    @media (min-width: 768px) {
      section[data-wb-sec-template="image-text"] > div[style*="grid-template-columns"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        gap: 36px !important;
      }
      section[data-wb-sec-template="cards-grid"] div[style*="grid-template-columns"],
      section[data-wb-sec-template="testimonials"] div[style*="grid-template-columns"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      }
      section[data-wb-sec-template="gallery"] div[style*="grid-template-columns"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      }
      section[data-wb-sec-template="media-card-carousel"] div[style*="grid-auto-flow"] {
        grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
      }
    }
    @media (min-width: 1200px) {
      section[data-wb-sec-template="cards-grid"] div[style*="grid-template-columns"],
      section[data-wb-sec-template="testimonials"] div[style*="grid-template-columns"],
      section[data-wb-sec-template="gallery"] div[style*="grid-template-columns"] {
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
      }
      section[data-wb-sec-template="media-card-carousel"] div[style*="grid-auto-flow"] {
        grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
      }
    }

    /* ── Overflow guard (emails / long URLs / phone numbers) ── */
    .grid, .contact-grid { min-width: 0 !important; }
    .grid > *, .contact-grid > *, .card { min-width: 0 !important; }
    a, p, li, td, th { overflow-wrap: anywhere !important; word-break: break-word !important; }
    .card a, .contact-grid a { max-width: 100% !important; display: inline-block !important; }

    /* ── Touch-safe targets (carousel controls excluded) ── */
    a:not([data-wb-go]):not([data-wb-dir]),
    button:not([data-wb-go]):not([data-wb-dir]),
    [role="button"]:not([data-wb-go]):not([data-wb-dir]),
    input[type="submit"], input[type="button"], select {
      min-height: 44px !important;
    }
    /* ── Carousel controls — explicit sizes, not stretched ── */
    [data-wb-go] {
      min-height: unset !important; min-width: unset !important;
      width: 9px !important; height: 9px !important;
      padding: 0 !important; border-radius: 999px !important;
    }
    [data-wb-dir] {
      min-height: unset !important; min-width: unset !important;
      width: 32px !important; height: 32px !important;
    }

    /* ── Tablet (≤ 900px) ── */
    @media (max-width: 900px) {
      .about-strip, .contact-grid {
        grid-template-columns: 1fr !important; gap: 32px !important;
      }
      .about-strip img { height: 240px !important; }
      .footer-grid { grid-template-columns: 1fr 1fr !important; }
      .section { padding: 64px 5% !important; }
      .hero { padding: 80px 5% !important; }
      .hero h1 { font-size: clamp(1.8rem, 5vw, 3rem) !important; }
      .cat-grid, .testi-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important; }
      .hero-carousel, .hero-art-placeholder { min-height: 200px; }
      .hero-carousel__control { opacity: 1; pointer-events: auto; }
    }

    /* ── Large phone (≤ 767px) ── */
    @media (max-width: 767px) {
      .section { padding: 56px 4% !important; }
      .hero { padding: 64px 4% !important; }
      .hero h1 { font-size: clamp(1.7rem, 6vw, 2.6rem) !important; }
      .cat-grid, .testi-grid { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)) !important; }
      table { display: block !important; overflow-x: auto !important; white-space: nowrap !important; }
    }

    /* ── Mobile (≤ 640px) ── */
    @media (max-width: 640px) {
      nav { position: relative !important; }
      .nav-links { display: none !important; }
      .hamburger { display: block !important; }
      .section { padding: 48px 16px !important; }
      .hero { padding: 60px 16px !important; min-height: 60vh !important; }
      .hero h1 { font-size: clamp(1.5rem, 7vw, 2.2rem) !important; }
      .hero p  { font-size: .95rem !important; }
      .hero-btns { flex-direction: column !important; align-items: center !important; gap: 10px !important; }
      .hero-btns .btn, .hero-btns a {
        width: 100% !important; max-width: 320px !important;
        text-align: center !important; box-sizing: border-box !important;
      }
      .cat-grid, .testi-grid { grid-template-columns: 1fr !important; }
      .contact-grid, .about-strip { grid-template-columns: 1fr !important; }
      .footer-grid { grid-template-columns: 1fr !important; }
      .footer-bottom { flex-direction: column !important; gap: 12px !important; text-align: center !important; }
      .form-row { grid-template-columns: 1fr !important; }
      .section-header h2 { font-size: 1.5rem !important; }
      .booking-form { padding: 24px 16px !important; }
      nav, .navbar { padding: 8px 12px !important; }
      .hero-carousel, .hero-art-placeholder { min-height: 170px; }
      .hero-carousel__control { width: 38px; height: 38px; font-size: 1rem; }
      [data-wb-go] { width: 7px !important; height: 7px !important; }
      [data-wb-dir] { width: 26px !important; height: 26px !important; font-size: .8rem !important; }
      [data-wb-carousel-controls="1"] { gap: 5px !important; }
      [data-wb-carousel-dots="1"] { gap: 4px !important; }
    }

    /* ── Small phone (≤ 479px) ── */
    @media (max-width: 479px) {
      [data-wb-carousel-enabled="0"] { grid-template-columns: 1fr !important; gap: 16px !important; }
      .__wb_bg_carousel:not([data-wb-carousel-enabled="1"]) { grid-template-columns: 1fr !important; gap: 16px !important; }
      .section { padding: 40px 12px !important; }
      .hero { padding: 48px 12px !important; min-height: 50vh !important; }
      .hero h1 { font-size: clamp(1.3rem, 8vw, 1.9rem) !important; }
      .card { padding: 18px 14px !important; }
      .btn { padding: 12px 20px !important; font-size: .9rem !important; }
      .product-grid, .card-grid { grid-template-columns: 1fr !important; }
      footer { padding: 40px 16px 20px !important; }
      .hero-carousel, .hero-art-placeholder { min-height: 140px; }
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
    try {
      if (frame.contentDocument) {
        _injectResponsiveEnhancements(frame.contentDocument);
        _ensureMediaCardCarouselRuntime(frame.contentDocument);
        frame.contentDocument.defaultView?.wbMediaCardCarouselInitAll?.(frame.contentDocument);
        loadStagingMetadataFromPreview();
      }
    } catch(_) {}
  };
  frame.src = _cacheBustUrl(currentStagingUrl);
}

function stagingPopout() {
  if (currentStagingUrl) window.open(_cacheBustUrl(currentStagingUrl), '_blank');
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
  const align  = fieldsEl.querySelector(`[data-fid="${fid}-align"]`)?.value  || '';
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
    if (align)  t.style.setProperty('text-align',   align,           'important');
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
  const paras    = fieldsEl._paraEntries ? fieldsEl._paraEntries.map(entry => entry.el) : (fieldsEl._paraEls || [...el.querySelectorAll('p')].filter(p => p.innerText.trim().length >= 3));
  const headStart = fieldsEl._headingStart || 1;
  const paraStart = fieldsEl._paraStart   || (headStart + headings.length);

  const gridMatch = fid.match(/^grid-(\d+)-(title|image)$/);
  if (gridMatch) {
    const idx = parseInt(gridMatch[1], 10);
    const kind = gridMatch[2];
    const gridMeta = fieldsEl?._gridMeta;
    const item = gridMeta?.items?.[idx];
    if (!item) return [];
    if (kind === 'title' && item.titleEl) return [item.titleEl];
    if (kind === 'image' && item.imageEl) return [item.imageEl];
    return [];
  }

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
  // Persist any pending field edits into the live preview before serializing HTML.
  if (activeSectionIndex !== null) {
    applySecEdits();
  }
  const doc = frame.contentDocument;
  // Remove injected overlay badges and highlights
  doc.querySelectorAll('.__wb_badge').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_badge_anchor').forEach(n => n.remove());
  doc.querySelectorAll('.__wb_hi').forEach(n => { n.style.outline = ''; n.classList.remove('__wb_hi'); });
  // Remove browser extension injected elements (Grammarly, etc.)
  doc.querySelectorAll('grammarly-desktop-integration, #PING_IFRAME_FORM_DETECTION, [id^="PING_"], [data-grammarly-shadow-root]').forEach(n => n.remove());
  const html = doc.documentElement.outerHTML;
  if (!html.trim()) { toast('Nothing in preview to save', false); return; }

  const btn = document.getElementById('stagingSaveBtn');
  btn.disabled = true; btn.textContent = '💾 Saving…';

  const r = await apiFetch(`/websites/${stagedWebsiteId}/staged-html`, {
    method: 'PUT',
    body: JSON.stringify({
      html,
      entry_path: currentStagingEntryPath,
      expected_hash: currentStagingHtmlHash || undefined,
    }),
  });
  btn.disabled = false; btn.textContent = '💾 Save Changes';

  if (r && r.saved) {
    toast('Changes saved ✅');
    currentStagingHtmlHash = String(r?.html_hash || '').trim();
    currentStagingManifestEtag = String(r?.staging?.manifest_etag || '').trim();
    // Force iframe reload to reflect saved changes
    const frame = document.getElementById('stagingIframe');
    const url = currentStagingUrl;
    frame.src = '';
    setTimeout(() => { frame.src = _cacheBustUrl(url); }, 100);
    currentStagingEntryPath = (r && r.staging && r.staging.entry_html) || currentStagingEntryPath;
    currentStagingHomeEntryPath = currentStagingEntryPath;
    currentStagingArtifactCount = Number(r && r.staging && r.staging.artifact_count) || currentStagingArtifactCount;
    currentStagingArtifacts = Array.isArray(r && r.staging && r.staging.artifacts) ? r.staging.artifacts : currentStagingArtifacts;
    _renderStagingPagePicker(currentStagingEntryPath);
    _renderStagingSummary((websites || []).find(x => x.website_id === stagedWebsiteId), r && r.staging ? r.staging : null, url);
    // Update status badge
    const w = (websites || []).find(x => x.website_id === stagedWebsiteId);
    if (w) { w.build_status = 'staged'; }
    const badge = document.getElementById('stagingStatusBadge');
    if (badge) badge.innerHTML = `<span class="tag draft" style="background:rgba(245,158,11,.15);color:var(--warn)">🔧 Staged</span>`;
  } else {
    const err = String(apiFetch._lastError || '');
    if (err.toLowerCase().includes('changed since last load')) {
      toast('This page was updated elsewhere. Refresh staging and try again.', false);
    } else {
      toast('Failed to save changes', false);
    }
  }
}

async function goLive() {
  if (!stagedWebsiteId) return;
  const btn = document.getElementById('stagingGoLiveBtn');
  btn.disabled = true; btn.textContent = '🚀 Deploying…';

  const r = await apiFetch(`/websites/${stagedWebsiteId}/deploy`, { method: 'POST' });
  btn.disabled = false; btn.textContent = '🚀 Go Live';

  if (r && r.url) {
    const targetMap = {
      s3: 'S3 Website',
      gdrive: 'Google Drive (files)',
      onedrive: 'OneDrive (files)',
      ftp: 'FTP Hosted',
      local: 'local output',
    };
    const targetLabel = targetMap[r.target] || 'local output';
    let details = `Live on <b>${targetLabel}</b><br>URL: <a href="${r.url}" target="_blank">${r.url}</a>`;
    let shortMsg = 'Deployment Success';
    if (r.target === 'gdrive') {
      const parts = [];
      if (Number.isFinite(Number(r.files_uploaded))) parts.push(`${Number(r.files_uploaded)} file(s)`);
      if (Number.isFinite(Number(r.all_asset_files)) && Number(r.all_asset_files) > 0) {
        parts.push(`${Number(r.all_asset_files)} total asset file(s)`);
      }
      if (r.folder_name) parts.push(`folder: ${r.folder_name}`);
      if (parts.length) details += `<br>${parts.join(', ')}`;
    }
    styledAlert(details, { icon: '🚀', title: 'Deployment Complete', okLabel: 'OK', okClass: 'btn-success' });
    toast(shortMsg);
    const badge = document.getElementById('stagingStatusBadge');
    if (badge) {
      const note = (r.target === 'gdrive' || r.target === 'onedrive')
        ? '<span style="margin-left:6px;font-size:.72rem;color:var(--muted)">files link</span>'
        : '';
      badge.innerHTML = statusBadge('live') + note;
    }
    document.getElementById('stagingStatusBar').textContent = `Live URL: ${r.url}`;

    // Update in-memory site record
    const idx = (websites || []).findIndex(x => x.website_id === stagedWebsiteId);
    if (idx !== -1) {
      websites[idx].status = 'live';
      if (r.target === 's3') websites[idx].s3_url = r.url;
      else websites[idx].live_url = r.url;  // staging path untouched; live_url = published path
    }
    // Keep iframe on local preview for files-link targets that cannot be embedded.
    // Google Drive / OneDrive URLs usually return 403 in iframe due X-Frame-Options.
    const filesLinkTarget = (r.target === 'gdrive' || r.target === 'onedrive');
    if (!filesLinkTarget) {
      currentStagingUrl = r.url;
      const frame = document.getElementById('stagingIframe');
      frame.src = r.url;
    }
    const extra = (r.target === 'gdrive' && Number.isFinite(Number(r.files_uploaded)))
      ? ` • uploaded ${Number(r.files_uploaded)} file(s)`
      : '';
    document.getElementById('stagingStatusBar').textContent = `Live at: ${r.url} (${targetLabel})${extra}`;
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
    fallback:{ msg: '✅ Rebuild complete (fallback mode).',   pct: 100 },
    error:   { msg: '❌ Rebuild failed.',                     pct: 100 },
    timeout: { msg: '⚠️ Taking longer than expected. Check My Websites for status.', pct: 100 },
  };

  await new Promise(resolve => {
    const es = new EventSource(
      `${API}/websites/${id}/build-stream?token=${encodeURIComponent(token)}`
    );
    es.onmessage = async (e) => {
      try {
        const data = JSON.parse(e.data);
        const status = data.build_status || 'queued';
        const s = stageLabels[status] || stageLabels.queued;
        msgEl.textContent = data.error ? `❌ ${data.error}` : s.msg;
        barEl.style.width = s.pct + '%';
        if (['built', 'fallback', 'error', 'timeout', 'not_found'].includes(status)) {
          es.close();
          spinnerEl.style.display = 'none';
          if (status === 'built' || status === 'fallback') {
            toast('Rebuild complete! Opening Staging Area…');
            await loadAllSites();
            await loadStagingWebsites();
            setTimeout(() => { showPage('staging'); loadStagedSite(id); }, 1500);
          } else if (status === 'error') {
            toast(data.error || 'Rebuild failed. Please try again.', false);
          } else if (status === 'timeout') {
            spinnerEl.style.display = 'inline-block';
            msgEl.textContent = '⏳ Rebuild is still running in background. Continuing to check…';
            toast('Rebuild is still running. Continuing to check automatically…');

            const finalState = await _pollBuildStatusUntilTerminal(id, {
              onUpdate: (s2, err2) => {
                const st = stageLabels[s2] || stageLabels.queued;
                msgEl.textContent = err2 ? `❌ ${err2}` : st.msg;
                barEl.style.width = st.pct + '%';
              },
              maxAttempts: 180,
              intervalMs: 5000,
            });

            spinnerEl.style.display = 'none';

            if (finalState.status === 'built' || finalState.status === 'fallback') {
              toast('Rebuild complete! Opening Staging Area…');
              await loadAllSites();
              await loadStagingWebsites();
              setTimeout(() => { showPage('staging'); loadStagedSite(id); }, 1500);
            } else if (finalState.status === 'error') {
              toast(finalState.error || 'Rebuild failed. Please try again.', false);
            } else {
              msgEl.textContent = stageLabels.timeout.msg;
              barEl.style.width = '100%';
              toast('Rebuild is still running. Check My Websites for final status.', false);
            }
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

  // Deliver the processed image blob to the caller's upload handler.
  const cb = _imgCallback;
  _imgCallback = null;
  if (cb) {
    cb(finalBlob || _imgOrigBlob);
  }
}
