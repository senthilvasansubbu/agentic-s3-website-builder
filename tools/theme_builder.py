"""
Theme engine — defines all built-in themes and renders multi-page websites.
Each theme supplies a CSS token set and a base HTML shell.
"""
from typing import Dict, Any, List, Optional

# ── Theme registry ─────────────────────────────────────────────────────────────

THEMES: Dict[str, Dict[str, Any]] = {
    "modern": {
        "label": "Modern",
        "primary": "#667eea",
        "secondary": "#764ba2",
        "accent": "#f093fb",
        "bg": "#f5f7fa",
        "text": "#2d3748",
        "font_body": "'Inter', sans-serif",
        "font_heading": "'Poppins', sans-serif",
        "radius": "12px",
        "shadow": "0 4px 20px rgba(0,0,0,.08)",
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    },
    "classic": {
        "label": "Classic",
        "primary": "#1a365d",
        "secondary": "#2b6cb0",
        "accent": "#e53e3e",
        "bg": "#ffffff",
        "text": "#2d3748",
        "font_body": "'Georgia', serif",
        "font_heading": "'Playfair Display', serif",
        "radius": "4px",
        "shadow": "0 2px 8px rgba(0,0,0,.12)",
        "gradient": "linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%)",
    },
    "minimal": {
        "label": "Minimal",
        "primary": "#1a1a1a",
        "secondary": "#555",
        "accent": "#f6c90e",
        "bg": "#fafafa",
        "text": "#222",
        "font_body": "'DM Sans', sans-serif",
        "font_heading": "'Space Grotesk', sans-serif",
        "radius": "6px",
        "shadow": "0 1px 4px rgba(0,0,0,.06)",
        "gradient": "linear-gradient(135deg, #1a1a1a 0%, #444 100%)",
    },
    "dark": {
        "label": "Dark",
        "primary": "#7c3aed",
        "secondary": "#4f46e5",
        "accent": "#06b6d4",
        "bg": "#0f172a",
        "text": "#e2e8f0",
        "font_body": "'Roboto', sans-serif",
        "font_heading": "'Montserrat', sans-serif",
        "radius": "10px",
        "shadow": "0 4px 24px rgba(0,0,0,.4)",
        "gradient": "linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)",
    },
    "nature": {
        "label": "Nature",
        "primary": "#276749",
        "secondary": "#38a169",
        "accent": "#f6ad55",
        "bg": "#f0fff4",
        "text": "#1a202c",
        "font_body": "'Lato', sans-serif",
        "font_heading": "'Merriweather', serif",
        "radius": "8px",
        "shadow": "0 2px 12px rgba(0,0,0,.07)",
        "gradient": "linear-gradient(135deg, #276749 0%, #38a169 100%)",
    },
    "ecommerce": {
        "label": "E-Commerce",
        "primary": "#dd6b20",
        "secondary": "#c05621",
        "accent": "#3182ce",
        "bg": "#fff",
        "text": "#2d3748",
        "font_body": "'Open Sans', sans-serif",
        "font_heading": "'Nunito', sans-serif",
        "radius": "8px",
        "shadow": "0 2px 10px rgba(0,0,0,.08)",
        "gradient": "linear-gradient(135deg, #dd6b20 0%, #c05621 100%)",
    },
}


# ── CSS generator ──────────────────────────────────────────────────────────────

def build_theme_css(theme_key: str, custom_overrides: Optional[str] = None) -> str:
    t = THEMES.get(theme_key, THEMES["modern"])
    css = f"""
/* ── Theme: {t['label']} ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Poppins:wght@600;700&family=Montserrat:wght@600;700&family=Nunito:wght@400;600&family=Open+Sans:wght@400;600&display=swap');

:root {{
  --primary:   {t['primary']};
  --secondary: {t['secondary']};
  --accent:    {t['accent']};
  --bg:        {t['bg']};
  --text:      {t['text']};
  --radius:    {t['radius']};
  --shadow:    {t['shadow']};
  --gradient:  {t['gradient']};
  --font-body: {t['font_body']};
  --font-heading: {t['font_heading']};
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; }}
body {{ font-family: var(--font-body); background: var(--bg); color: var(--text); line-height: 1.7; }}

/* Typography */
h1,h2,h3,h4,h5,h6 {{ font-family: var(--font-heading); color: var(--text); line-height: 1.2; }}
a {{ color: var(--primary); text-decoration: none; }}
a:hover {{ opacity: .8; }}

/* Navbar */
.navbar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 40px; background: var(--bg);
  box-shadow: var(--shadow); position: sticky; top: 0; z-index: 1000;
}}
.navbar .logo {{ font-family: var(--font-heading); font-size: 1.4rem; font-weight: 700; color: var(--primary); }}
.navbar .logo img {{ height: 40px; vertical-align: middle; margin-right: 8px; }}
.nav-links {{ display: flex; gap: 28px; list-style: none; }}
.nav-links a {{ font-weight: 600; color: var(--text); transition: color .2s; }}
.nav-links a:hover {{ color: var(--primary); }}
.nav-cta {{ padding: 10px 22px; background: var(--gradient); color: #fff !important; border-radius: var(--radius); font-weight: 700 !important; }}

/* Hero */
.hero {{
  background: var(--gradient); color: #fff; text-align: center;
  padding: 100px 20px; position: relative; overflow: hidden;
}}
.hero h1 {{ font-size: clamp(2rem, 5vw, 3.5rem); margin-bottom: 20px; }}
.hero p  {{ font-size: 1.2rem; opacity: .9; max-width: 640px; margin: 0 auto 32px; }}
.btn {{
  display: inline-block; padding: 14px 36px; border-radius: var(--radius);
  background: #fff; color: var(--primary); font-weight: 700;
  transition: transform .2s, box-shadow .2s;
}}
.btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.15); }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-outline {{ border: 2px solid var(--primary); background: transparent; color: var(--primary); }}

/* Sections */
.section {{ padding: 72px 40px; max-width: 1200px; margin: 0 auto; }}
.section-title {{ font-size: 2rem; font-weight: 700; margin-bottom: 12px; }}
.section-sub {{ color: #888; margin-bottom: 48px; font-size: 1.05rem; }}

/* Cards */
.card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr)); gap: 24px; }}
.card {{ background: #fff; border-radius: var(--radius); padding: 28px; box-shadow: var(--shadow); transition: transform .2s; }}
.card:hover {{ transform: translateY(-4px); }}
.card h3 {{ color: var(--primary); margin-bottom: 10px; }}

/* Product grid */
.product-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 20px; }}
.product-card {{ background: #fff; border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; transition: transform .2s; }}
.product-card:hover {{ transform: translateY(-3px); }}
.product-card img {{ width: 100%; height: 200px; object-fit: cover; }}
.product-card .info {{ padding: 16px; }}
.product-card .price {{ font-size: 1.25rem; font-weight: 700; color: var(--primary); }}
.add-to-cart {{ width: 100%; margin-top: 10px; padding: 10px; background: var(--primary); color: #fff; border: none; border-radius: var(--radius); cursor: pointer; font-weight: 600; }}

/* Cart sidebar */
#cart-sidebar {{
  position: fixed; right: 0; top: 0; height: 100vh; width: 360px; max-width: 95vw;
  background: #fff; box-shadow: -4px 0 30px rgba(0,0,0,.12);
  transform: translateX(100%); transition: transform .3s; z-index: 2000; display: flex; flex-direction: column;
}}
#cart-sidebar.open {{ transform: translateX(0); }}
.cart-header {{ padding: 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
.cart-items {{ flex: 1; overflow-y: auto; padding: 20px; }}
.cart-footer {{ padding: 20px; border-top: 1px solid #eee; }}
.cart-total {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 12px; }}
#cart-btn {{ position: fixed; bottom: 28px; right: 28px; background: var(--primary); color: #fff; border: none; border-radius: 50px; padding: 14px 22px; cursor: pointer; font-size: 1rem; font-weight: 700; box-shadow: 0 4px 20px rgba(0,0,0,.2); z-index: 1500; }}

/* Forms */
.form-group {{ margin-bottom: 20px; }}
.form-group label {{ display: block; margin-bottom: 6px; font-weight: 600; font-size: .9rem; }}
.form-group input, .form-group select, .form-group textarea {{
  width: 100%; padding: 12px 16px; border: 1px solid #ddd; border-radius: var(--radius);
  font-size: 1rem; font-family: var(--font-body);
  transition: border-color .2s;
}}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
  outline: none; border-color: var(--primary);
}}

/* Footer */
footer {{ background: #1a202c; color: #a0aec0; padding: 60px 40px 30px; }}
.footer-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); gap: 40px; margin-bottom: 40px; }}
.footer-col h4 {{ color: #fff; margin-bottom: 16px; }}
.footer-col ul {{ list-style: none; }}
.footer-col li {{ margin-bottom: 8px; }}
.footer-col a {{ color: #a0aec0; transition: color .2s; }}
.footer-col a:hover {{ color: #fff; }}
.footer-bottom {{ border-top: 1px solid #2d3748; padding-top: 24px; text-align: center; font-size: .85rem; }}

/* ── Hamburger button (hidden on desktop) ── */
.hamburger {{ display: none; background: none; border: none; font-size: 1.6rem; cursor: pointer; color: #fff; padding: 4px 8px; }}

/* ── Responsive: tablet ── */
@media (max-width: 900px) {{
  .grid-2, .grid-3, .grid-4,
  .about-strip, .contact-grid, .footer-grid,
  [class*="two-col"], [class*="three-col"] {{
    grid-template-columns: 1fr !important;
  }}
  .section {{ padding: 64px 5%; }}
  .hero h1 {{ font-size: clamp(1.8rem, 5vw, 3rem); }}
  .card-grid, .cat-grid, .testi-grid, .product-grid {{
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  }}
  .footer-grid {{ grid-template-columns: 1fr 1fr !important; }}
}}

/* ── Responsive: mobile ── */
@media (max-width: 640px) {{
  .navbar {{ padding: 10px 16px; }}
  .nav-links {{ display: none; flex-direction: column; position: absolute; top: 64px; left: 0; right: 0;
    background: rgba(30,30,40,.97); padding: 20px 16px; gap: 12px; z-index: 999; box-shadow: 0 8px 24px rgba(0,0,0,.3); }}
  .nav-links.open {{ display: flex; }}
  .hamburger {{ display: block; }}
  .section {{ padding: 48px 16px; }}
  .hero {{ padding: 60px 16px; min-height: 70vh; }}
  .hero h1 {{ font-size: clamp(1.6rem, 7vw, 2.4rem); }}
  .hero p  {{ font-size: .95rem; }}
  .hero-btns {{ flex-direction: column; align-items: center; }}
  .hero-btns .btn {{ width: 100%; max-width: 320px; text-align: center; }}
  .card-grid, .cat-grid, .testi-grid, .product-grid {{
    grid-template-columns: 1fr;
  }}
  .about-strip, .contact-grid {{ gap: 32px; }}
  .footer-grid {{ grid-template-columns: 1fr !important; }}
  .footer-bottom {{ flex-direction: column; gap: 12px; text-align: center; }}
  .form-row {{ grid-template-columns: 1fr; }}
  #cart-sidebar {{ width: 100vw; }}
  .section-header h2 {{ font-size: 1.6rem; }}
  table {{ font-size: .82rem; }}
  .booking-form {{ padding: 24px 16px; }}
}}
"""
    if custom_overrides:
        css += f"\n/* Custom overrides */\n{custom_overrides}\n"
    return css


# ── Full page renderer ─────────────────────────────────────────────────────────

def render_page(
    page_title: str,
    site_title: str,
    logo_url: Optional[str],
    nav_pages: List[Dict[str, str]],
    body_html: str,
    theme_key: str = "modern",
    custom_css: Optional[str] = None,
    include_cart: bool = False,
    include_analytics_snippet: bool = True,
    currency_symbol: str = "$",
    stripe_publishable_key: Optional[str] = None,
) -> str:
    css = build_theme_css(theme_key, custom_css)
    logo_tag = (
        f'<img src="{logo_url}" alt="{site_title} logo">'
        if logo_url
        else ""
    )
    nav_items = "".join(
        f'<li><a href="{p["url"]}">{p["label"]}</a></li>' for p in nav_pages
    )
    cart_html = ""
    cart_js   = ""
    stripe_js = ""

    if include_cart:
        cart_html = """
<button id="cart-btn" onclick="toggleCart()">🛒 Cart (<span id="cart-count">0</span>)</button>
<div id="cart-sidebar">
  <div class="cart-header">
    <h3>Your Cart</h3>
    <button onclick="toggleCart()" style="background:none;border:none;font-size:1.4rem;cursor:pointer;">✕</button>
  </div>
  <div class="cart-items" id="cart-items-list"></div>
  <div class="cart-footer">
    <div class="cart-total">Total: <span id="currency-symbol">""" + currency_symbol + """</span><span id="cart-total-amt">0.00</span></div>
    <button class="btn btn-primary" onclick="proceedToCheckout()" style="width:100%">Checkout</button>
  </div>
</div>
<div id="cart-overlay" onclick="toggleCart()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1999;"></div>
"""
        cart_js = """
<script>
let cart = JSON.parse(localStorage.getItem('wb_cart') || '[]');

function saveCart(){ localStorage.setItem('wb_cart', JSON.stringify(cart)); }
function updateCartUI(){
  document.getElementById('cart-count').textContent = cart.reduce((s,i)=>s+i.qty,0);
  const list = document.getElementById('cart-items-list');
  if(!list) return;
  if(!cart.length){ list.innerHTML='<p style="color:#888">Your cart is empty.</p>'; return; }
  list.innerHTML = cart.map(i=>`
    <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px">
      <img src="${i.img||'/placeholder.png'}" style="width:60px;height:60px;object-fit:cover;border-radius:6px">
      <div style="flex:1">
        <strong>${i.name}</strong><br>
        <small>${i.qty} × """ + currency_symbol + """${parseFloat(i.price).toFixed(2)}</small>
      </div>
      <button onclick="removeFromCart('${i.id}')" style="background:none;border:none;font-size:1.2rem;cursor:pointer;">🗑</button>
    </div>
  `).join('');
  const total = cart.reduce((s,i)=>s+(i.price*i.qty),0);
  const el = document.getElementById('cart-total-amt');
  if(el) el.textContent = total.toFixed(2);
}
function addToCart(id, name, price, img){
  const existing = cart.find(i=>i.id===id);
  if(existing) existing.qty++;
  else cart.push({id, name, price:parseFloat(price), img, qty:1});
  saveCart(); updateCartUI();
  document.getElementById('cart-sidebar').classList.add('open');
  document.getElementById('cart-overlay').style.display='block';
}
function removeFromCart(id){
  cart = cart.filter(i=>i.id!==id);
  saveCart(); updateCartUI();
}
function toggleCart(){
  const s = document.getElementById('cart-sidebar');
  const o = document.getElementById('cart-overlay');
  s.classList.toggle('open');
  o.style.display = s.classList.contains('open') ? 'block' : 'none';
  updateCartUI();
}
function proceedToCheckout(){
  window.location.href='/checkout?cart='+encodeURIComponent(JSON.stringify(cart));
}
document.addEventListener('DOMContentLoaded', updateCartUI);
</script>
"""
    if stripe_publishable_key:
        stripe_js = f'<script src="https://js.stripe.com/v3/"></script>\n<script>const stripe=Stripe("{stripe_publishable_key}");</script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page_title} | {site_title}</title>
  <style>{css}</style>
  {stripe_js}
</head>
<body>
  <nav class="navbar">
    <div class="logo">{logo_tag}{site_title}</div>
    <ul class="nav-links">{nav_items}<li><a href="/login" class="nav-cta">My Account</a></li></ul>
  </nav>

  {body_html}

  {cart_html}

  <footer>
    <div class="footer-grid">
      <div class="footer-col"><h4>{site_title}</h4><p>Built with Agentic AI Website Builder.</p></div>
      <div class="footer-col"><h4>Links</h4><ul>{nav_items}</ul></div>
      <div class="footer-col"><h4>Legal</h4><ul>
        <li><a href="/privacy">Privacy Policy</a></li>
        <li><a href="/terms">Terms of Service</a></li>
      </ul></div>
    </div>
    <div class="footer-bottom">&copy; 2026 {site_title}. All rights reserved.</div>
  </footer>
  {cart_js}
</body>
</html>
"""
