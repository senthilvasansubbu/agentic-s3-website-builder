import logging
import time
import uuid as _uuid
from crewai import Crew, Process, Task
from agents.designer_agent import designer_agent
from agents.developer_agent import developer_agent
from agents.theme_agent import theme_agent
from tools.theme_builder import THEMES
from config.settings import settings

logger = logging.getLogger("website_builder.crew")

# ── Retry helper ──────────────────────────────────────────────────────────────
_MAX_RETRIES    = 3
_RETRY_BASE_SEC = 2   # backoff: 2s, 4s, 8s


def _with_retry(fn, *args, trace_id: str = "", **kwargs):
    """Call *fn* up to _MAX_RETRIES times with exponential backoff on failure."""
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            wait = _RETRY_BASE_SEC ** attempt
            logger.warning(
                "[%s] attempt %d/%d failed: %s — retrying in %ds",
                trace_id, attempt, _MAX_RETRIES, exc, wait,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)
    raise last_exc


def _generate_static_fallback(user_requirements: str, theme_key: str = "modern") -> str:
    """Generate a content-rich static HTML website when no API key is available."""
    t = THEMES.get(theme_key, THEMES["modern"])
    import re, urllib.parse

    # ── Extract hints from the prompt ─────────────────────────────────────────

    # Business name — prefer the new priority header format first
    biz_name_match = re.search(r'WEBSITE NAME:\s*(.+)', user_requirements)
    if biz_name_match:
        biz_name = biz_name_match.group(1).strip()
    else:
        biz_name_match2 = re.search(r'Business Name:\s*(.+)', user_requirements)
        biz_name = biz_name_match2.group(1).strip() if biz_name_match2 else \
            " ".join(user_requirements.replace("===", "").split()[:5]).title()

    # Is this an informational (non-retail) site?
    is_informational = bool(re.search(r'SITE TYPE:\s*Informational', user_requirements, re.I))

    # Nav links — prefer the new priority header format
    nav_links: list[str] = []
    nav_header_match = re.search(r'NAVIGATION \(use exactly these items.*?\):\s*(.+)', user_requirements)
    if nav_header_match:
        nav_links = [n.strip() for n in nav_header_match.group(1).split('|') if n.strip()]

    # Logo URL
    logo_match = re.search(r'Brand Logo URL:\s*(https?://\S+)', user_requirements)
    logo_url = logo_match.group(1) if logo_match else ""

    # Real site images
    site_images: list[str] = []
    for m in re.finditer(r'(?m)^\s+\d+\. (https?://\S+)', user_requirements):
        site_images.append(m.group(1))

    # Categories
    cats_raw = re.findall(r'^\s*- (.+?)(?:\n|$)', user_requirements, re.M)
    cats = [c.strip() for c in cats_raw if len(c.strip()) < 60 and not c.strip().startswith('=')][:8]
    if not cats:
        cats = ["Products", "Services", "Gallery", "Special Offers"]

    # Location
    loc_match = re.search(r'Business Location:\s*(.+)', user_requirements)
    location = loc_match.group(1).strip() if loc_match else "123 Main Street, New York, NY 10001, USA"
    map_query = urllib.parse.quote(location)

    # Email
    email_match = re.search(r'Business Email:\s*(\S+)', user_requirements)
    email = email_match.group(1) if email_match else f"info@{biz_name.lower().replace(' ','')}.com"

    # Phone
    phone_match = re.search(r'Business Phone:\s*(\S+)', user_requirements)
    phone = phone_match.group(1) if phone_match else "+1-555-000-0000"

    # Booking prefix
    prefix_match = re.search(r'Reference Prefix:\s*([A-Z\-]+)', user_requirements)
    prefix = prefix_match.group(1) if prefix_match else "ORD"

    # Hero background — use first real site image if available, else Unsplash
    niche_kw = cats[0].lower().replace(' ', ',') if cats else 'business'
    hero_bg = site_images[0] if site_images else f"https://source.unsplash.com/featured/1400x900/?{niche_kw}"

    # Description
    desc_match = re.search(r'Business Description:\s*(.+?)(?:\n\n|\Z)', user_requirements, re.S)
    description = desc_match.group(1).strip() if desc_match else user_requirements[:200]

    # ── Category cards HTML ───────────────────────────────────────────────────
    cat_cta = "Learn More" if is_informational else "Order Now"
    cat_cards = ""
    for i, cat in enumerate(cats):
        kw = cat.lower().replace(' ', ',')
        img_src = site_images[i + 1] if (i + 1) < len(site_images) else \
                  (site_images[0] if site_images else f"https://source.unsplash.com/featured/400x300/?{kw}")
        cat_cards += f"""
        <div class="cat-card">
          <img src="{img_src}" alt="{cat}" loading="lazy">
          <div class="cat-info">
            <h3>{cat}</h3>
            <p>Explore our {cat.lower()} — crafted with care and quality.</p>
            <a href="{'#contact' if is_informational else '#booking'}" class="cat-btn">{cat_cta}</a>
          </div>
        </div>"""

    # ── Category dropdown options ─────────────────────────────────────────────
    cat_options = "".join(f'<option value="{c}">{c}</option>' for c in cats)

    # ── Testimonials ─────────────────────────────────────────────────────────
    testimonials_data = [
        ("Sarah M.", "New York", "★★★★★",
         f"Absolutely love everything from {biz_name}! The quality is exceptional and delivery was super fast."),
        ("James T.", "Los Angeles", "★★★★★",
         f"I've been a loyal customer for years. {biz_name} never disappoints — always fresh and beautifully presented."),
        ("Priya K.", "Chicago", "★★★★☆",
         f"Great experience from start to finish. The booking process was seamless and the products exceeded my expectations."),
    ]
    testimonial_cards = ""
    for name, city, stars, text in testimonials_data:
        testimonial_cards += f"""
        <div class="testi-card">
          <div class="stars">{stars}</div>
          <p class="testi-text">"{text}"</p>
          <div class="testi-author">— {name}, {city}</div>
        </div>"""

    # ── Navbar logo ───────────────────────────────────────────────────────────
    # Strip CSS fallback stack at source: 'Poppins', sans-serif → Poppins
    fh = t["font_heading"].split(',')[0].strip().strip("'").strip('"')
    fb = t["font_body"].split(',')[0].strip().strip("'").strip('"')
    t["font_heading"] = fh
    t["font_body"]    = fb
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="{biz_name}" style="height:48px;object-fit:contain;vertical-align:middle"> <span style="font-family:{fh},serif;font-size:1.1rem;color:#fff;font-weight:700">{biz_name}</span>'
    else:
        logo_html = f'<span style="font-family:{fh},serif;font-size:1.5rem;color:#fff;font-weight:700">✦ {biz_name}</span>'

    # ── Nav items ─────────────────────────────────────────────────────────────
    # Map nav labels to built-in section IDs where possible; extras get their own stub section
    SECTION_KEYWORDS = {
        "categories": ["categor", "product", "service", "offer", "menu", "shop", "collection", "range"],
        "about":      ["about", "story", "who", "history", "mission", "vision"],
        "testimonials": ["testimonial", "review", "feedback", "customer", "client"],
        "booking":    ["book", "order", "reserv", "appoint", "contact", "enquir", "inquiry", "schedule"],
        "contact":    ["contact", "find us", "location", "address", "reach"],
    }
    def _map_nav_to_section(label: str) -> str:
        slug = label.lower()
        for section_id, keywords in SECTION_KEYWORDS.items():
            if any(kw in slug for kw in keywords):
                return f"#{section_id}"
        # No match — return a slugified anchor for a custom section
        return "#" + re.sub(r"[^a-z0-9]+", "-", slug).strip("-")

    extra_sections_html = ""
    if nav_links:
        last_link = nav_links[-1]
        nav_items_html = ""
        extra_section_ids = set()
        for link in nav_links[:-1]:
            anchor = _map_nav_to_section(link)
            nav_items_html += f'<li><a href="{anchor}">{link}</a></li>\n    '
            if not anchor.lstrip("#") in ("categories", "about", "testimonials", "booking", "contact"):
                extra_section_ids.add((anchor.lstrip("#"), link))
        last_anchor = _map_nav_to_section(last_link)
        if last_anchor in ("#contact", "#booking"):
            nav_items_html += f'<li><a href="{last_anchor}" class="nav-cta">{last_link}</a></li>'
        else:
            nav_items_html += f'<li><a href="{last_anchor}" class="nav-cta">{last_link}</a></li>'
            if last_anchor.lstrip("#") not in ("categories", "about", "testimonials", "booking", "contact"):
                extra_section_ids.add((last_anchor.lstrip("#"), last_link))
        # Build stub sections for unrecognised nav items — extract relevant text from scraped prompt
        for sec_id, sec_label in extra_section_ids:
            kw = sec_label.lower().replace(" ", ",")
            # Try to find any scraped paragraph mentioning this section label
            label_lc = sec_label.lower()
            excerpt_match = re.search(
                r'(?i)' + re.escape(label_lc) + r'[^\n]{0,300}',
                user_requirements
            )
            excerpt = excerpt_match.group(0).strip()[:250] if excerpt_match else ""
            section_desc = excerpt if len(excerpt) > 40 else f"Explore our {sec_label} — dedicated to sharing knowledge, community, and inspiration."
            extra_sections_html += f"""
<!-- ── {sec_label} ── -->
<section id="{sec_id}">
  <div class="section reveal">
    <div class="section-header">
      <h2>{sec_label}</h2>
      <p>{section_desc}</p>
      <div class="section-divider"></div>
    </div>
    <div class="cat-grid">
      <div class="cat-card">
        <img src="https://source.unsplash.com/featured/800x500/?{kw}" alt="{sec_label}" loading="lazy">
        <div class="cat-info">
          <h3>{sec_label}</h3>
          <p>{section_desc}</p>
          <a href="#contact" class="cat-btn">Learn More</a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
    else:
        default_cta = "Contact Us" if is_informational else "Book Now"
        default_href = "#contact" if is_informational else "#booking"
        nav_items_html = f"""<li><a href="#categories">Sections</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="{default_href}" class="nav-cta">{default_cta}</a></li>"""

    # ── Hero CTAs ─────────────────────────────────────────────────────────────
    if is_informational:
        hero_cta_html = '<a href="#about" class="btn btn-accent">Learn More</a>\n      <a href="#contact" class="btn btn-outline">Contact Us</a>'
    else:
        hero_cta_html = '<a href="#booking" class="btn btn-accent">Book an Order</a>\n      <a href="#categories" class="btn btn-outline">View Our Range</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{biz_name}</title>
  <meta name="description" content="{description[:160]}"/>
  <link href="https://fonts.googleapis.com/css2?family={fh.replace(' ', '+')}:wght@600;700&family={fb.replace(' ', '+')}:wght@300;400;700&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --primary: {t['primary']}; --secondary: {t['secondary']}; --accent: {t['accent']};
      --bg: {t['bg']}; --text: {t['text']}; --muted: #6b7280;
      --radius: {t['radius']}; --card-shadow: {t['shadow']};
      --gradient: {t['gradient']};
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ font-family: {t['font_body']}, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; }}

    /* ── Navbar ── */
    nav {{
      position: sticky; top: 0; z-index: 1000; background: var(--primary);
      backdrop-filter: blur(10px); border-bottom: 1px solid rgba(255,255,255,.12);
      display: flex; align-items: center; justify-content: space-between; padding: 0 5%; height: 72px;
    }}
    .logo {{ font-family: {t['font_heading']}, serif; font-size: 1.5rem; color: #fff; }}
    .nav-links {{ display: flex; gap: 32px; list-style: none; }}
    .nav-links a {{ color: rgba(255,255,255,.85); font-size: .9rem; letter-spacing: .5px; font-weight: 700;
      text-transform: uppercase; text-decoration: none; transition: color .2s; }}
    .nav-links a:hover {{ color: var(--accent); }}
    .nav-cta {{ background: var(--accent); color: #fff !important; padding: 10px 22px; border-radius: var(--radius); }}
    .nav-cta:hover {{ opacity:.85; }}
    .hamburger {{ display:none; background:none; border:none; font-size:1.6rem; cursor:pointer; color:#fff; }}

    /* ── Hero ── */
    .hero {{
      min-height: 90vh; display: flex; align-items: center; justify-content: center; text-align: center;
      background: linear-gradient(rgba(0,0,0,.48),rgba(0,0,0,.48)),
                  url('{hero_bg}') center/cover no-repeat;
      color: #fff; padding: 80px 20px;
    }}
    .hero-inner {{ max-width: 720px; animation: fadeUp .8s ease; }}
    .hero h1 {{ font-family: {fh}, serif; font-size: clamp(2.2rem, 6vw, 4.5rem);
      line-height: 1.15; margin-bottom: 20px; }}
    .hero p {{ font-size: 1.2rem; opacity: .9; margin-bottom: 36px; font-weight: 300; }}
    .hero-btns {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }}
    .btn {{
      padding: 14px 36px; border-radius: 6px; font-weight: 700; font-size: .95rem;
      text-decoration: none; transition: transform .2s, box-shadow .2s; display: inline-block;
    }}
    .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.2); }}
    .btn-light {{ background: #fff; color: var(--primary); }}
    .btn-accent {{ background: var(--accent); color: #fff; }}
    .btn-outline {{ border: 2px solid #fff; color: #fff; background: transparent; }}

    /* ── Sections ── */
    .section {{ padding: 88px 5%; max-width: 1280px; margin: 0 auto; }}
    .section-header {{ text-align: center; margin-bottom: 56px; }}
    .section-header h2 {{ font-family: {fh}, serif; font-size: 2.4rem; color: var(--secondary); margin-bottom: 12px; }}
    .section-header p {{ color: var(--muted); font-size: 1.05rem; max-width: 600px; margin: 0 auto; }}
    .section-divider {{ width: 60px; height: 3px; background: var(--accent); margin: 14px auto 0; border-radius: 2px; }}

    /* ── Categories ── */
    .cat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 28px; }}
    .cat-card {{ background: #fff; border-radius: var(--radius); box-shadow: var(--card-shadow);
      overflow: hidden; transition: transform .2s; }}
    .cat-card:hover {{ transform: translateY(-5px); }}
    .cat-card img {{ width: 100%; height: 200px; object-fit: cover; }}
    .cat-info {{ padding: 22px; }}
    .cat-info h3 {{ font-family: {fh}, serif; font-size: 1.25rem; color: var(--primary); margin-bottom: 8px; }}
    .cat-info p {{ color: var(--muted); font-size: .9rem; margin-bottom: 14px; }}
    .cat-btn {{ display: inline-block; padding: 8px 20px; background: var(--primary); color: #fff;
      border-radius: 5px; font-size: .85rem; font-weight: 700; text-decoration: none; transition: background .2s; }}
    .cat-btn:hover {{ background: var(--accent); }}

    /* ── About strip ── */
    .about-strip {{
      background: var(--primary); color: #fff; padding: 80px 5%;
      display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: center;
    }}
    .about-strip img {{ width: 100%; border-radius: 12px; height: 380px; object-fit: cover; }}
    .about-text h2 {{ font-family: {fh}, serif; font-size: 2rem; margin-bottom: 20px; }}
    .about-text p {{ opacity: .85; font-size: 1rem; line-height: 1.8; }}

    /* ── Testimonials ── */
    .testi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }}
    .testi-card {{ background: #fff; border-radius: var(--radius); padding: 32px; box-shadow: var(--card-shadow);
      border-top: 4px solid var(--accent); }}
    .stars {{ font-size: 1.1rem; color: var(--accent); margin-bottom: 12px; }}
    .testi-text {{ font-style: italic; color: var(--muted); font-size: .95rem; line-height: 1.7; margin-bottom: 16px; }}
    .testi-author {{ font-weight: 700; font-size: .85rem; color: var(--primary); }}

    /* ── Booking Form ── */
    #booking {{ background: #f5f2ee; }}
    #booking .section {{ max-width: 760px; }}
    .booking-form {{ background: #fff; padding: 40px; border-radius: 14px; box-shadow: var(--card-shadow); }}
    .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .form-group {{ display: flex; flex-direction: column; gap: 6px; margin-bottom: 20px; }}
    .form-group label {{ font-size: .82rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: .5px; color: var(--primary); }}
    .form-group input, .form-group select, .form-group textarea {{
      padding: 12px 14px; border: 1.5px solid #e0dbd4; border-radius: 7px; font-size: .95rem;
      font-family: {fb}, sans-serif; background: var(--bg); transition: border-color .2s; width: 100%; }}
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
      outline: none; border-color: var(--accent); }}
    .submit-btn {{ width: 100%; padding: 16px; background: var(--primary); color: #fff; border: none;
      border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: background .2s;
      font-family: {fb}, sans-serif; }}
    .submit-btn:hover {{ background: var(--accent); }}
    #booking-confirm {{ display: none; background: #d4edda; border: 1px solid #c3e6cb;
      color: #155724; padding: 18px 24px; border-radius: 8px; margin-top: 20px; font-weight: 700; }}

    /* ── Contact & Map ── */
    .contact-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: start; }}
    .contact-details h3 {{ font-family: {fh}, serif; font-size: 1.5rem; color: var(--primary); margin-bottom: 24px; }}
    .contact-item {{ display: flex; gap: 14px; align-items: flex-start; margin-bottom: 18px; }}
    .contact-item .icon {{ font-size: 1.3rem; margin-top: 2px; }}
    .contact-item p {{ color: var(--muted); font-size: .95rem; margin: 0; }}
    .contact-item strong {{ color: var(--text); display: block; font-size: .85rem; font-weight: 700; text-transform: uppercase; letter-spacing: .4px; }}
    .hours-table {{ width: 100%; border-collapse: collapse; font-size: .9rem; margin-top: 20px; }}
    .hours-table td {{ padding: 8px 0; border-bottom: 1px solid #eee; color: var(--muted); }}
    .hours-table td:first-child {{ font-weight: 700; color: var(--text); width: 120px; }}
    .map-container iframe {{ width: 100%; height: 360px; border-radius: 12px; border: 0;
      box-shadow: var(--card-shadow); }}

    /* ── Footer ── */
    footer {{ background: #1a1a2e; color: #a0a0b8; padding: 60px 5% 30px; }}
    .footer-grid {{ display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 40px; margin-bottom: 40px; }}
    .footer-brand h3 {{ font-family: {fh}, serif; color: #fff; font-size: 1.4rem; margin-bottom: 12px; }}
    .footer-brand p {{ font-size: .88rem; line-height: 1.7; }}
    .footer-col h4 {{ color: #fff; font-size: .9rem; text-transform: uppercase;
      letter-spacing: 1px; margin-bottom: 16px; }}
    .footer-col ul {{ list-style: none; }}
    .footer-col li {{ margin-bottom: 8px; font-size: .88rem; }}
    .footer-col a {{ color: #a0a0b8; text-decoration: none; transition: color .2s; }}
    .footer-col a:hover {{ color: #fff; }}
    .footer-newsletter {{ display: flex; gap: 8px; margin-top: 16px; }}
    .footer-newsletter input {{ flex: 1; padding: 10px 14px; border-radius: 6px; border: none;
      background: rgba(255,255,255,.1); color: #fff; font-family: {fb}, sans-serif; font-size: .88rem; }}
    .footer-newsletter button {{ padding: 10px 18px; background: var(--accent); color: #fff;
      border: none; border-radius: 6px; cursor: pointer; font-weight: 700; font-size: .88rem; }}
    .footer-bottom {{ border-top: 1px solid rgba(255,255,255,.08); padding-top: 24px;
      display: flex; justify-content: space-between; align-items: center; font-size: .82rem; }}
    .social-links {{ display: flex; gap: 16px; }}
    .social-links a {{ color: #a0a0b8; font-size: 1.1rem; text-decoration: none; transition: color .2s; }}
    .social-links a:hover {{ color: #fff; }}

    /* ── Animations ── */
    @keyframes fadeUp {{ from {{ opacity:0; transform: translateY(24px); }} to {{ opacity:1; transform: translateY(0); }} }}
    .reveal {{ opacity: 0; transform: translateY(30px); transition: opacity .6s ease, transform .6s ease; }}
    .reveal.visible {{ opacity: 1; transform: translateY(0); }}

    /* ── Responsive: tablet ── */
    @media (max-width: 900px) {{
      .about-strip, .contact-grid {{
        grid-template-columns: 1fr !important; gap: 32px;
      }}
      .about-strip img {{ height: 240px; }}
      .footer-grid {{ grid-template-columns: 1fr 1fr !important; }}
      .section {{ padding: 64px 5%; }}
      .hero h1 {{ font-size: clamp(1.8rem, 5vw, 3rem); }}
      .cat-grid, .testi-grid {{ grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }}
    }}
    @media (max-width: 640px) {{
      nav {{ padding: 0 16px; }}
      .nav-links {{ display: none; flex-direction: column; position: absolute; top: 72px;
        left: 0; right: 0; background: rgba(20,20,30,.97); padding: 20px 16px;
        gap: 12px; z-index: 999; box-shadow: 0 8px 24px rgba(0,0,0,.3); list-style: none; }}
      .nav-links.open {{ display: flex; }}
      .hamburger {{ display: block; }}
      .section {{ padding: 48px 16px; }}
      .hero {{ padding: 60px 16px; min-height: 70vh; }}
      .hero h1 {{ font-size: clamp(1.6rem, 7vw, 2.4rem); }}
      .hero p  {{ font-size: .95rem; }}
      .hero-btns {{ flex-direction: column; align-items: center; }}
      .hero-btns .btn, .hero-btns a {{ width: 100% !important; max-width: 320px; text-align: center; box-sizing: border-box; }}
      .cat-grid, .testi-grid {{ grid-template-columns: 1fr; }}
      .footer-grid {{ grid-template-columns: 1fr !important; }}
      .footer-bottom {{ flex-direction: column; gap: 12px; text-align: center; }}
      .form-row {{ grid-template-columns: 1fr; }}
      .section-header h2 {{ font-size: 1.6rem; }}
      .booking-form {{ padding: 24px 16px; }}
    }}
  </style>
</head>
<body>

<!-- ── Navbar ── -->
<nav>
  <div class="logo">{logo_html}
  </div>
  <ul class="nav-links">
    {nav_items_html}
  </ul>
  <button class="hamburger" onclick="document.querySelector('.nav-links').classList.toggle('open');this.textContent=document.querySelector('.nav-links').classList.contains('open')?'✕':'☰'">☰</button>
</nav>

<!-- ── Hero ── -->
<section class="hero">
  <div class="hero-inner">
    <h1>{biz_name}</h1>
    <p>{description[:220]}</p>
    <div class="hero-btns">
      {hero_cta_html}
    </div>
  </div>
</section>

<!-- ── Categories ── -->
<section id="categories">
  <div class="section reveal">
    <div class="section-header">
      <h2>What We Offer</h2>
      <p>Discover our handcrafted selection — every item made with passion and the finest ingredients.</p>
      <div class="section-divider"></div>
    </div>
    <div class="cat-grid">
      {cat_cards}
    </div>
  </div>
</section>

<!-- ── About ── -->
<section id="about">
  <div class="about-strip reveal">
    <img src="https://source.unsplash.com/featured/700x500/?{niche_kw},interior" alt="About {biz_name}" loading="lazy">
    <div class="about-text">
      <h2>Our Story</h2>
      <p>{description}</p>
      <br>
      <p>We are passionate about quality, craftsmanship, and the community we serve. Every product is made fresh using the finest ingredients sourced locally and internationally.</p>
      <br>
      <a href="#booking" class="btn btn-light" style="background:var(--accent);color:#fff;margin-top:8px">Order Today</a>
    </div>
  </div>
</section>

<!-- ── Testimonials ── -->
<section id="testimonials">
  <div class="section reveal">
    <div class="section-header">
      <h2>What Our Customers Say</h2>
      <p>Real experiences from people who love what we do.</p>
      <div class="section-divider"></div>
    </div>
    <div class="testi-grid">
      {testimonial_cards}
    </div>
  </div>
</section>

<!-- ── Booking ── -->
<section id="booking">
  <div class="section reveal">
    <div class="section-header">
      <h2>Place Your Order</h2>
      <p>Fill in your details below and we'll confirm your booking right away.</p>
      <div class="section-divider"></div>
    </div>
    <div class="booking-form">
      <div class="form-row">
        <div class="form-group"><label>Full Name</label><input id="f-name" type="text" placeholder="Jane Smith" required></div>
        <div class="form-group"><label>Email Address</label><input id="f-email" type="email" placeholder="jane@example.com" required></div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Phone Number</label><input id="f-phone" type="tel" placeholder="+1 555 000 0000"></div>
        <div class="form-group"><label>Select Category</label>
          <select id="f-service"><option value="">— Choose —</option>{cat_options}</select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-group"><label>Preferred Date</label><input id="f-date" type="date"></div>
        <div class="form-group"><label>Time Slot</label>
          <select id="f-time">
            <option>09:00 AM – 10:00 AM</option><option>10:00 AM – 11:00 AM</option>
            <option>11:00 AM – 12:00 PM</option><option>02:00 PM – 03:00 PM</option>
            <option>03:00 PM – 04:00 PM</option><option>04:00 PM – 05:00 PM</option>
          </select>
        </div>
      </div>
      <div class="form-group"><label>Special Instructions</label>
        <textarea id="f-notes" rows="3" placeholder="Any dietary requirements, customisations, or special requests…"></textarea>
      </div>
      <button class="submit-btn" onclick="submitBooking()">Confirm Order</button>
      <div id="booking-confirm"></div>
    </div>
  </div>
</section>

{extra_sections_html}
<!-- ── Contact ── -->
<section id="contact">
  <div class="section reveal">
    <div class="section-header">
      <h2>Find Us</h2>
      <p>We'd love to hear from you — visit us, call us, or drop an email.</p>
      <div class="section-divider"></div>
    </div>
    <div class="contact-grid">
      <div class="contact-details">
        <h3>Get in Touch</h3>
        <div class="contact-item"><span class="icon">📍</span><div><strong>Address</strong><p>{location}</p></div></div>
        <div class="contact-item"><span class="icon">📞</span><div><strong>Phone</strong><p>{phone}</p></div></div>
        <div class="contact-item"><span class="icon">✉️</span><div><strong>Email</strong><p><a href="mailto:{email}" style="color:var(--accent)">{email}</a></p></div></div>
        <table class="hours-table">
          <tr><td>Mon – Fri</td><td>9:00 AM – 6:00 PM</td></tr>
          <tr><td>Saturday</td><td>9:00 AM – 4:00 PM</td></tr>
          <tr><td>Sunday</td><td>10:00 AM – 2:00 PM</td></tr>
        </table>
      </div>
      <div class="map-container">
        <iframe src="https://maps.google.com/maps?q={map_query}&output=embed" allowfullscreen loading="lazy" title="Our Location"></iframe>
      </div>
    </div>
  </div>
</section>

<!-- ── Footer ── -->
<footer>
  <div class="footer-grid">
    <div class="footer-brand">
      <h3>✦ {biz_name}</h3>
      <p>{description[:160]}</p>
      <div class="footer-newsletter">
        <input type="email" placeholder="Your email for updates…">
        <button>Subscribe</button>
      </div>
    </div>
    <div class="footer-col">
      <h4>Quick Links</h4>
      <ul>
        <li><a href="#categories">Our Range</a></li>
        <li><a href="#about">About Us</a></li>
        <li><a href="#booking">Book an Order</a></li>
        <li><a href="#contact">Contact</a></li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>Contact</h4>
      <ul>
        <li>{location}</li>
        <li><a href="tel:{phone}">{phone}</a></li>
        <li><a href="mailto:{email}">{email}</a></li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <span>© <span id="yr"></span> {biz_name}. All rights reserved.</span>
    <div class="social-links">
      <a href="#" title="Facebook">📘</a>
      <a href="#" title="Instagram">📷</a>
      <a href="#" title="Twitter">🐦</a>
      <a href="#" title="WhatsApp">💬</a>
    </div>
    <a href="#" style="color:#a0a0b8">↑ Back to top</a>
  </div>
</footer>

<script>
  // Year
  document.getElementById('yr').textContent = new Date().getFullYear();

  // Booking form
  function submitBooking() {{
    const name = document.getElementById('f-name').value.trim();
    const email = document.getElementById('f-email').value.trim();
    if (!name || !email) {{ alert('Please fill in your name and email.'); return; }}
    const ref = '{prefix}-' + Date.now();
    const conf = document.getElementById('booking-confirm');
    conf.style.display = 'block';
    conf.innerHTML = `✅ Thank you, ${{name}}! Your order has been confirmed.<br>
      <strong>Booking Reference: ${{ref}}</strong><br>
      A confirmation will be sent to ${{email}}.`;
    document.querySelector('.booking-form').querySelectorAll('input, select, textarea').forEach(el => el.value = '');
  }}

  // Scroll reveal
  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(e => {{ if (e.isIntersecting) e.target.classList.add('visible'); }});
  }}, {{ threshold: 0.12 }});
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
</script>
</body>
</html>"""


def create_website_crew(theme_key: str = "modern", classification: str = "generic"):
    """Create and configure the website builder crew with a 3-task pipeline.

    Pipeline:
      Task 1 (designer_agent)  → structured content plan (NO style/CSS decisions)
      Task 2 (theme_agent)     → complete HTML using locked theme tokens
    """
    t = THEMES.get(theme_key, THEMES["modern"])
    theme_spec_block = f"""
=== THEME_SPEC (LOCKED — do not deviate) ===
Theme Name:       {t['label']}
Primary Colour:   {t['primary']}
Secondary Colour: {t['secondary']}
Accent Colour:    {t['accent']}
Background:       {t['bg']}
Text Colour:      {t['text']}
Heading Font:     {t['font_heading']}
Body Font:        {t['font_body']}
Border Radius:    {t['radius']}
Shadow:           {t['shadow']}
Hero Gradient:    {t['gradient']}

Mapping:
  --primary   → {t['primary']}   (navbar bg, section headings, key UI)
  --secondary → {t['secondary']}  (hover states, sub-headings)
  --accent    → {t['accent']}   (all buttons and CTAs)
  --bg        → {t['bg']}     (page background)
  --text      → {t['text']}     (all body text)
  font-heading → {t['font_heading']} (every h1/h2/h3)
  font-body    → {t['font_body']} (paragraphs, labels, nav)
  border-radius → {t['radius']} (cards, buttons, inputs)
  box-shadow   → {t['shadow']} (cards, sections)
  hero/gradient → {t['gradient']}
==========================================
"""

    # Classification profile hint injected into tasks
    classification_note = f"AUDIENCE/CLASSIFICATION: {classification.upper()} — tailor all content, CTA labels, navigation, and section types to suit this profile.\n\n"

    # Task 1 — Content planning (no style decisions)
    design_task = Task(
        description=classification_note + """Based on the user's requirements, produce a STRUCTURED CONTENT PLAN for the website.

        Include ALL of the following — with NO colour, font, or CSS decisions:

        1. SITE IDENTITY: Business name, tagline, brand voice (1–2 sentences)
        2. NAVIGATION: Ordered list of nav items
        3. HERO: Headline, sub-headline, primary CTA label, secondary CTA label,
           Unsplash keyword for hero background image
        4. SECTIONS (for each section provide):
           - Section ID and heading
           - Sub-heading
           - Body copy (2–4 sentences)
           - Content items (cards/list entries) with: title, description (2 sentences),
             Unsplash image keyword
        5. CONTACT DETAILS: Full address, phone, email, opening hours
        6. BOOKING FORM: List of form fields with types and placeholder text,
           booking reference prefix (e.g. BK-, ORD-, RES-)
        7. TESTIMONIALS: 3 reviews — each with star rating, customer name, city, review text
        8. FOOTER: Column headings, quick links, social platforms, newsletter sign-up copy
        9. SEO: Page title tag, meta description

        CRITICAL: Do NOT write any HTML, CSS, hex codes, font names, or style descriptions.
        Output clean structured text only.""",
        agent=designer_agent,
        expected_output=(
            "Structured content plan: site identity, nav, hero, sections with copy and Unsplash keywords, "
            "contact details, booking form fields, testimonials, footer content, SEO meta. No HTML or CSS."
        ),
    )

    # Task 2 — Theme implementation (HTML output using locked theme tokens)
    theme_task = Task(
        description=f"""{classification_note}You will receive a structured CONTENT PLAN from the previous task.

        Apply it to produce a COMPLETE, single-file HTML/CSS/JS website using ONLY the tokens
        in the THEME_SPEC block below. Every visual decision must come from THEME_SPEC.

{theme_spec_block}

        MANDATORY sections (all must appear with real content — no placeholder comments):
        1. Sticky navbar: logo (business name), nav links, accent-coloured CTA button
        2. Hero: full-width gradient background (use gradient from THEME_SPEC), H1, tagline, two CTAs
        3. Services/Categories: card grid — each card has Unsplash image, heading, description, button
        4. About / Brand Story section
        5. Testimonials: 3 cards with ★★★★★, customer name + city, review text
        6. Contact & Location: address, phone, email, opening hours, Google Maps embed iframe
        7. Booking/Order form: all fields from content plan, JS booking reference on submit
        8. Footer: address, social icons, newsletter input, auto copyright year
        9. Mobile responsive with hamburger menu, smooth scroll, IntersectionObserver scroll-reveal

        CSS rules:
        - Declare :root variables matching THEME_SPEC tokens
        - Import required Google Fonts for both heading and body fonts
        - Use var(--primary), var(--accent) etc. throughout — never hardcode hex values
        - Buttons always use accent colour background and match the border-radius token

        Output the COMPLETE valid HTML file. All CSS in <style>, all JS in <script>.""",
        agent=theme_agent,
        expected_output=(
            "Complete single-file HTML website using only the THEME_SPEC colours and fonts, "
            "all sections populated with real content, Unsplash images, booking form, contact section."
        ),
        context=[design_task],
    )

    crew = Crew(
        agents=[designer_agent, theme_agent],
        tasks=[design_task, theme_task],
        process=Process.sequential,
        verbose=settings.VERBOSE_MODE,
    )

    return crew

def build_website(user_requirements: str, project_name: str = "", theme_key: str = "modern", classification: str = "generic") -> dict:
    """
    Build a website based on user requirements.
    Falls back to a static template when OPENAI_API_KEY is not configured.
    The generated files are saved to output/<project-slug>/ automatically.

    Parameters
    ----------
    user_requirements : str
        The full assembled prompt from requirements_analyst.build_prompt()
    project_name : str
        Slugified project/site name used for the output directory
    theme_key : str
        One of the keys from tools.theme_builder.THEMES (default: 'modern')
    """
    from tools.html_generator import generate_html, get_website_dir

    trace_id = str(_uuid.uuid4())[:8]
    t0 = time.time()
    logger.info("[%s] ▶ build_website START  project=%r  ai=%s",
                trace_id, project_name or "(auto)",
                "enabled" if settings.OPENAI_API_KEY else "disabled (fallback)")

    # Derive project name from requirements if not provided
    if not project_name:
        project_name = " ".join(user_requirements.split()[:5]).title()

    if not settings.OPENAI_API_KEY:
        logger.warning("[%s] ⚠  No OPENAI_API_KEY — generating static fallback", trace_id)
        t1 = time.time()
        html_code = _generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index")
        site_dir = get_website_dir(project_name)
        logger.info("[%s] ✅ static fallback saved to %s  (%.1fs)", trace_id, site_dir, time.time()-t0)
        return {
            "status": "success",
            "result": html_code,
            "output_dir": site_dir,
            "index": filepath,
            "requirements": user_requirements,
            "fallback": True,
            "trace_id": trace_id,
        }

    logger.info("[%s] 🧠 Kicking off CrewAI pipeline… theme=%s", trace_id, theme_key)
    crew = create_website_crew(theme_key=theme_key, classification=classification)
    t1 = time.time()
    try:
        result = _with_retry(
            crew.kickoff,
            inputs={"user_requirements": user_requirements, "project_name": project_name},
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.error("[%s] ❌ CrewAI failed after %d retries: %s — falling back to static", trace_id, _MAX_RETRIES, exc)
        html_code = _generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index")
        site_dir = get_website_dir(project_name)
        return {
            "status": "fallback",
            "result": html_code,
            "output_dir": site_dir,
            "index": filepath,
            "requirements": user_requirements,
            "fallback": True,
            "error": str(exc),
            "trace_id": trace_id,
        }
    logger.info("[%s] 🎨 CrewAI finished in %.1fs — saving output", trace_id, time.time()-t1)

    # Save AI-generated HTML
    html_code = str(result)

    # --- Asset extraction logic ---
    import re
    design_spec = {'css': {}, 'js': {}, 'images': {}}

    # Extract <style> blocks
    css_matches = list(re.finditer(r'<style[^>]*>(.*?)</style>', html_code, re.DOTALL | re.IGNORECASE))
    logger.info(f"Found {len(css_matches)} <style> blocks in HTML.")
    for i, m in enumerate(css_matches):
        css_content = m.group(1).strip()
        if css_content:
            fname = f"main{i+1}.css" if i > 0 else "main.css"
            design_spec['css'][fname] = css_content
            logger.info(f"Extracted CSS: {fname} ({len(css_content)} bytes)")
        html_code = html_code.replace(m.group(0), f'<link rel="stylesheet" href="assets/css/{fname}">')

    # Extract <script> blocks
    js_matches = list(re.finditer(r'<script[^>]*>(.*?)</script>', html_code, re.DOTALL | re.IGNORECASE))
    logger.info(f"Found {len(js_matches)} <script> blocks in HTML.")
    for i, m in enumerate(js_matches):
        js_content = m.group(1).strip()
        if js_content:
            fname = f"main{i+1}.js" if i > 0 else "main.js"
            design_spec['js'][fname] = js_content
            logger.info(f"Extracted JS: {fname} ({len(js_content)} bytes)")
        html_code = html_code.replace(m.group(0), f'<script src="assets/js/{fname}"></script>')

    # Extract image URLs, download, and update HTML to use local paths
    import requests
    from urllib.parse import urlparse
    image_matches = list(re.finditer(r'<img[^>]+src=["\']([^"\'>]+)["\']', html_code, re.IGNORECASE))
    logger.info(f"Found {len(image_matches)} <img> tags in HTML.")
    for m in image_matches:
        img_url = m.group(1)
        logger.info(f"Processing image URL: {img_url}")
        if img_url.startswith('http://') or img_url.startswith('https://'):
            parsed = urlparse(img_url)
            fname = os.path.basename(parsed.path)
            if not fname:
                fname = f"img_{abs(hash(img_url))}.jpg"
            try:
                resp = requests.get(img_url, timeout=10)
                logger.info(f"Download status for {img_url}: {resp.status_code}")
                if resp.status_code == 200:
                    design_spec['images'][fname] = resp.content
                    logger.info(f"Downloaded image: {fname} ({len(resp.content)} bytes)")
                    html_code = html_code.replace(img_url, f'assets/images/{fname}')
                else:
                    logger.warning(f"Failed to download image {img_url}: status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to download image {img_url}: {e}")

    filepath = generate_html(design_spec, html_code, project_name, page_name="index")
    site_dir = get_website_dir(project_name)
    logger.info("[%s] ✅ AI website saved to %s  (total %.1fs)", trace_id, site_dir, time.time()-t0)

    return {
        "status": "success",
        "result": result,
        "output_dir": site_dir,
        "index": filepath,
        "requirements": user_requirements,
        "trace_id": trace_id,
    }

