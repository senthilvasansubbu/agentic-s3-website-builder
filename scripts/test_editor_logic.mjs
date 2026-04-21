import { JSDOM } from 'jsdom';

const pass = (label, cond) => console.log((cond ? '  ✅ PASS' : '  ❌ FAIL') + ': ' + label);

// ── Helpers (mirrors dashboard.html logic) ──
function _wrapperOf(a) {
  const li = a.parentElement;
  return (li && li.tagName === 'LI') ? li : a;
}
function getListParent(anchors) {
  if (!anchors.length) return null;
  const p = _wrapperOf(anchors[0]).parentNode;
  if (!p || (p.tagName !== 'UL' && p.tagName !== 'OL')) return null;
  if (anchors.every(a => _wrapperOf(a).parentNode === p)) return p;
  return null;
}
function getSharedParent(anchors, listParent) {
  if (listParent || !anchors.length) return null;
  const p = anchors[0].parentNode;
  if (p && anchors.every(a => a.parentNode === p)) return p;
  return null;
}

// ════════════════════════════════════════
console.log('\n─── Test 1: Nav <ul><li><a> (MMGK / Sayeesaran nav) ───');
{
  const dom = new JSDOM(`<nav><ul class="nav-links">
    <li><a href="#nepali">NEPALI</a></li>
    <li><a href="#tutorial">TUTORIAL</a></li>
    <li><a href="#newsletter">NEWSLETTER</a></li>
    <li><a href="#classes">CLASSES</a></li>
  </ul></nav>`);
  const doc = dom.window.document;
  const anchors = [...doc.querySelectorAll('a')];
  const listParent = getListParent(anchors);
  pass('listParent detected', listParent !== null);
  pass('listParent is UL', listParent?.tagName === 'UL');

  // Reorder: swap NEPALI and TUTORIAL
  const orderedAnchors = [anchors[1], anchors[0], anchors[2], anchors[3]];
  const lastOrigWrapper = _wrapperOf(anchors[anchors.length - 1]);
  const afterRef1 = lastOrigWrapper.nextSibling;
  orderedAnchors.forEach(a => listParent.insertBefore(_wrapperOf(a), afterRef1));
  const result = [...doc.querySelectorAll('.nav-links a')].map(a => a.textContent.trim());
  pass('TUTORIAL moved before NEPALI', result[0] === 'TUTORIAL' && result[1] === 'NEPALI');
  pass('Remaining items preserved', result[2] === 'NEWSLETTER' && result[3] === 'CLASSES');
}

// ════════════════════════════════════════
console.log('\n─── Test 2: Cards section (scattered anchors - Sayeesaran #categories) ───');
{
  const dom = new JSDOM(`<section id="categories">
    <div class="cat-card"><a href="#booking">Order Now</a></div>
    <div class="cat-card"><a href="#booking">Order Now</a></div>
    <div class="cat-card"><a href="#booking">Order Now</a></div>
    <div class="cat-card"><a href="#booking">Contact</a></div>
  </section>`);
  const doc = dom.window.document;
  const anchors = [...doc.querySelectorAll('a')];
  const listParent = getListParent(anchors);
  const sharedParent = getSharedParent(anchors, listParent);
  pass('listParent is null (no shared list)', listParent === null);
  pass('sharedParent is null (scattered parents)', sharedParent === null);
  // Only text/href update — no DOM reorder
  anchors[0].textContent = 'Buy Now';
  anchors[0].setAttribute('href', '#buy');
  pass('Text update in-place works', doc.querySelectorAll('a')[0].textContent === 'Buy Now');
  pass('All 4 cards intact after text update', doc.querySelectorAll('.cat-card').length === 4);
  pass('Other anchors untouched', doc.querySelectorAll('a')[1].textContent === 'Order Now');
}

// ════════════════════════════════════════
console.log('\n─── Test 3: Hero buttons (shared container, bare <a>) ───');
{
  const dom = new JSDOM(`<div class="hero-btns">
    <a href="#booking" class="btn-accent">Book an Order</a>
    <a href="#categories" class="btn-outline">View Range</a>
  </div>`);
  const doc = dom.window.document;
  const anchors = [...doc.querySelectorAll('a')];
  const listParent = getListParent(anchors);
  const sharedParent = getSharedParent(anchors, listParent);
  pass('listParent is null', listParent === null);
  pass('sharedParent detected', sharedParent !== null);
  // Reorder
  const orderedAnchors3 = [anchors[1], anchors[0]];
  const lastOrig3 = anchors[anchors.length - 1];
  const afterRef3 = lastOrig3.nextSibling;
  orderedAnchors3.forEach(a => sharedParent.insertBefore(a, afterRef3));
  const result = [...doc.querySelectorAll('.hero-btns a')].map(a => a.textContent.trim());
  pass('View Range moved first', result[0] === 'View Range');
  pass('Book an Order moved second', result[1] === 'Book an Order');
}

// ════════════════════════════════════════
console.log('\n─── Test 4: Footer <ul><li><a> ───');
{
  const dom = new JSDOM(`<footer><ul>
    <li><a href="#categories">Our Range</a></li>
    <li><a href="#about">About Us</a></li>
    <li><a href="#booking">Book an Order</a></li>
    <li><a href="#contact">Contact</a></li>
  </ul></footer>`);
  const doc = dom.window.document;
  const anchors = [...doc.querySelectorAll('a')];
  const listParent = getListParent(anchors);
  pass('Footer listParent detected', listParent !== null);
  const orderedAnchors2 = [anchors[1], anchors[0], anchors[2], anchors[3]];
  const lastOrigWrapper2 = _wrapperOf(anchors[anchors.length - 1]);
  const afterRef4 = lastOrigWrapper2.nextSibling;
  orderedAnchors2.forEach(a => listParent.insertBefore(_wrapperOf(a), afterRef4));
  const result = [...doc.querySelectorAll('footer a')].map(a => a.textContent.trim());
  pass('About Us moved to top', result[0] === 'About Us');
  pass('Our Range second', result[1] === 'Our Range');
}

// ════════════════════════════════════════
console.log('\n─── Test 5: Section sidebar order matches DOM (footer before post-footer section) ───');
{
  const dom = new JSDOM(`<body>
    <nav id="nav"></nav>
    <section id="hero"></section>
    <section id="about"></section>
    <footer id="footer"></footer>
    <section id="join-us"></section>
  </body>`);
  const doc = dom.window.document;
  const found = [...doc.querySelectorAll('nav, header, section, footer')].filter(el => {
    return el.closest('nav, header, section, footer') === el;
  });
  const ids = found.map(el => el.id || el.tagName.toLowerCase());
  pass('nav is first', ids[0] === 'nav');
  pass('footer before join-us', ids.indexOf('footer') < ids.indexOf('join-us'));
  pass('Total 5 elements found in DOM order', found.length === 5);
}

// ════════════════════════════════════════
console.log('\n─── Test 6: Undo stack (5 limit) ───');
{
  const HISTORY_LIMIT = 5;
  let stack = [];
  function push(html) {
    stack.push(html);
    if (stack.length > HISTORY_LIMIT) stack.shift();
  }
  for (let i = 1; i <= 7; i++) push(`<html>state${i}</html>`);
  pass('Stack capped at 5', stack.length === 5);
  pass('Oldest (state1, state2) evicted', !stack.includes('<html>state1</html>') && !stack.includes('<html>state2</html>'));
  pass('Latest state7 present', stack[stack.length - 1] === '<html>state7</html>');
  const restored = stack.pop();
  pass('Undo pops latest', restored === '<html>state7</html>');
  pass('Stack has 4 after undo', stack.length === 4);
}

// ════════════════════════════════════════
console.log('\n─── Test 7: Hamburger menu toggle ───');
{
  const dom = new JSDOM(`<html><head></head><body>
    <nav style="position:relative">
      <div class="logo">Logo</div>
      <ul class="nav-links"><li><a href="#a">HOME</a></li><li><a href="#b">ABOUT</a></li></ul>
      <button class="hamburger" onclick="document.querySelector('.nav-links').style.background='#fff'">☰</button>
    </nav>
  </body></html>`);
  const doc = dom.window.document;
  const hamburger = doc.querySelector('.hamburger');
  const navLinks  = doc.querySelector('.nav-links');

  // Simulate _injectResponsiveEnhancements onclick replacement
  navLinks._wbOpen = false;
  hamburger.onclick = (e) => {
    navLinks._wbOpen = !navLinks._wbOpen;
    if (navLinks._wbOpen) {
      navLinks.style.setProperty('display',        'flex',               'important');
      navLinks.style.setProperty('flex-direction', 'column',             'important');
      navLinks.style.setProperty('position',       'absolute',           'important');
      navLinks.style.setProperty('top',            '72px',               'important');
      navLinks.style.setProperty('background',     'rgba(20,20,34,.97)', 'important');
      hamburger.textContent = '✕';
    } else {
      navLinks.style.removeProperty('display');
      navLinks.style.removeProperty('flex-direction');
      navLinks.style.removeProperty('position');
      navLinks.style.removeProperty('top');
      navLinks.style.removeProperty('background');
      hamburger.textContent = '☰';
    }
  };

  hamburger.click();
  pass('menu opens on click', navLinks.style.display === 'flex');
  pass('menu is column flex', navLinks.style.flexDirection === 'column');
  pass('menu is absolute positioned', navLinks.style.position === 'absolute');
  pass('menu has dark background (not white)', !navLinks.style.background.includes('255, 255, 255') && navLinks.style.background !== '' && navLinks.style.background !== '#fff');
  pass('hamburger shows ✕', hamburger.textContent === '✕');

  hamburger.click();
  pass('menu closes on second click', !navLinks.style.display);
  pass('hamburger shows ☰', hamburger.textContent === '☰');
  pass('no leftover position', !navLinks.style.position);
}

// ════════════════════════════════════════
console.log('\n─── Test 7b: ResizeObserver — mobile/desktop show-hide ───');
{
  const dom = new JSDOM(`<html><head></head><body>
    <nav style="position:relative">
      <ul class="nav-links"></ul>
      <button class="hamburger" style="display:none">☰</button>
    </nav>
  </body></html>`, { pretendToBeVisual: true });
  const doc = dom.window.document;
  const hamburger = doc.querySelector('.hamburger');
  const navLinks  = doc.querySelector('.nav-links');
  navLinks._wbOpen = false;

  function closeMenu() {
    navLinks._wbOpen = false;
    navLinks.style.removeProperty('display');
    hamburger.textContent = '☰';
  }

  // Simulate applyMobileMode from _injectResponsiveEnhancements
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

  // Mobile width ≤ 640
  applyMobileMode(true);
  pass('hamburger visible on mobile', hamburger.style.display === 'block');
  pass('nav hidden on mobile (closed)', navLinks.style.display === 'none');

  // Open menu then go to desktop width
  navLinks._wbOpen = true;
  navLinks.style.setProperty('display', 'flex', 'important');
  hamburger.textContent = '✕';
  applyMobileMode(false);
  pass('hamburger hidden on desktop', !hamburger.style.display);
  pass('nav display cleared on desktop', !navLinks.style.display);
  pass('open menu closed when switching to desktop', !navLinks._wbOpen);

  // Back to mobile with menu already closed
  applyMobileMode(true);
  pass('hamburger re-shown when back to mobile', hamburger.style.display === 'block');
  pass('nav stays hidden while menu is closed', navLinks.style.display === 'none');
}

// ════════════════════════════════════════
console.log('\n─── Test 8: JS syntax check on dashboard.html ───');
{
  import('child_process').then(async ({ execSync }) => {
    const { readFileSync } = await import('fs');
    try {
      const html = readFileSync('frontend/dashboard.html', 'utf8');
      const scripts = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
      execSync('node --check', { input: scripts.join('\n'), encoding: 'utf8' });
      pass('dashboard.html JS syntax clean', true);
    } catch(e) {
      pass('dashboard.html JS syntax clean', false);
      console.log('  Error:', e.stderr || e.message);
    }
  });
}

console.log('');
