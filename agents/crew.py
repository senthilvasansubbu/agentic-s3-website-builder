from crewai import Crew, Process, Task
from agents.designer_agent import designer_agent
from agents.developer_agent import developer_agent
from config.settings import settings


def _generate_static_fallback(user_requirements: str) -> str:
    """Generate a classy, content-rich static HTML website when no API key is available."""
    import re, urllib.parse

    # ── Extract hints from the prompt ─────────────────────────────────────────
    lines = user_requirements.splitlines()
    title = " ".join(user_requirements.split()[:6]).title()

    # Business name
    biz_name = title

    # Categories
    cats_raw = re.findall(r'- (.+?)(?:\n|$)', user_requirements)
    cats = [c.strip() for c in cats_raw if len(c.strip()) < 60][:8]
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

    # Hero keyword
    niche_kw = cats[0].lower().replace(' ', ',') if cats else 'business'

    # Description
    desc_match = re.search(r'Business Description:\s*(.+?)(?:\n\n|\Z)', user_requirements, re.S)
    description = desc_match.group(1).strip() if desc_match else user_requirements[:200]

    # ── Category cards HTML ───────────────────────────────────────────────────
    cat_cards = ""
    for cat in cats:
        kw = cat.lower().replace(' ', ',')
        cat_cards += f"""
        <div class="cat-card">
          <img src="https://source.unsplash.com/featured/400x300/?{kw}" alt="{cat}" loading="lazy">
          <div class="cat-info">
            <h3>{cat}</h3>
            <p>Explore our curated selection of {cat.lower()} — crafted with care and quality.</p>
            <a href="#booking" class="cat-btn">Order Now</a>
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{biz_name}</title>
  <meta name="description" content="{description[:160]}"/>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Lato:wght@300;400;700&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --primary: #2c3e50; --accent: #c0973f; --bg: #fdfcfa;
      --text: #2d2d2d; --muted: #6b7280; --radius: 10px;
      --card-shadow: 0 4px 20px rgba(0,0,0,.08);
    }}
    html {{ scroll-behavior: smooth; }}
    body {{ font-family: 'Lato', sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; }}

    /* ── Navbar ── */
    nav {{
      position: sticky; top: 0; z-index: 1000; background: rgba(253,252,250,.96);
      backdrop-filter: blur(10px); border-bottom: 1px solid #e5e0d8;
      display: flex; align-items: center; justify-content: space-between; padding: 0 5%; height: 72px;
    }}
    .logo {{ font-family: 'Playfair Display', serif; font-size: 1.5rem; color: var(--primary); }}
    .nav-links {{ display: flex; gap: 32px; list-style: none; }}
    .nav-links a {{ color: var(--text); font-size: .9rem; letter-spacing: .5px; font-weight: 700;
      text-transform: uppercase; text-decoration: none; transition: color .2s; }}
    .nav-links a:hover {{ color: var(--accent); }}
    .nav-cta {{ background: var(--accent); color: #fff !important; padding: 10px 22px; border-radius: 6px; }}
    .nav-cta:hover {{ opacity:.85; }}
    .hamburger {{ display:none; background:none; border:none; font-size:1.6rem; cursor:pointer; }}

    /* ── Hero ── */
    .hero {{
      min-height: 90vh; display: flex; align-items: center; justify-content: center; text-align: center;
      background: linear-gradient(rgba(0,0,0,.48),rgba(0,0,0,.48)),
                  url('https://source.unsplash.com/featured/1400x900/?{niche_kw}') center/cover no-repeat;
      color: #fff; padding: 80px 20px;
    }}
    .hero-inner {{ max-width: 720px; animation: fadeUp .8s ease; }}
    .hero h1 {{ font-family: 'Playfair Display', serif; font-size: clamp(2.2rem, 6vw, 4.5rem);
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
    .section-header h2 {{ font-family: 'Playfair Display', serif; font-size: 2.4rem; color: var(--primary); margin-bottom: 12px; }}
    .section-header p {{ color: var(--muted); font-size: 1.05rem; max-width: 600px; margin: 0 auto; }}
    .section-divider {{ width: 60px; height: 3px; background: var(--accent); margin: 14px auto 0; border-radius: 2px; }}

    /* ── Categories ── */
    .cat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 28px; }}
    .cat-card {{ background: #fff; border-radius: var(--radius); box-shadow: var(--card-shadow);
      overflow: hidden; transition: transform .2s; }}
    .cat-card:hover {{ transform: translateY(-5px); }}
    .cat-card img {{ width: 100%; height: 200px; object-fit: cover; }}
    .cat-info {{ padding: 22px; }}
    .cat-info h3 {{ font-family: 'Playfair Display', serif; font-size: 1.25rem; color: var(--primary); margin-bottom: 8px; }}
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
    .about-text h2 {{ font-family: 'Playfair Display', serif; font-size: 2rem; margin-bottom: 20px; }}
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
      font-family: 'Lato', sans-serif; background: var(--bg); transition: border-color .2s; width: 100%; }}
    .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
      outline: none; border-color: var(--accent); }}
    .submit-btn {{ width: 100%; padding: 16px; background: var(--primary); color: #fff; border: none;
      border-radius: 8px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: background .2s;
      font-family: 'Lato', sans-serif; }}
    .submit-btn:hover {{ background: var(--accent); }}
    #booking-confirm {{ display: none; background: #d4edda; border: 1px solid #c3e6cb;
      color: #155724; padding: 18px 24px; border-radius: 8px; margin-top: 20px; font-weight: 700; }}

    /* ── Contact & Map ── */
    .contact-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: start; }}
    .contact-details h3 {{ font-family: 'Playfair Display', serif; font-size: 1.5rem; color: var(--primary); margin-bottom: 24px; }}
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
    .footer-brand h3 {{ font-family: 'Playfair Display', serif; color: #fff; font-size: 1.4rem; margin-bottom: 12px; }}
    .footer-brand p {{ font-size: .88rem; line-height: 1.7; }}
    .footer-col h4 {{ color: #fff; font-size: .9rem; text-transform: uppercase;
      letter-spacing: 1px; margin-bottom: 16px; }}
    .footer-col ul {{ list-style: none; }}
    .footer-col li {{ margin-bottom: 8px; font-size: .88rem; }}
    .footer-col a {{ color: #a0a0b8; text-decoration: none; transition: color .2s; }}
    .footer-col a:hover {{ color: #fff; }}
    .footer-newsletter {{ display: flex; gap: 8px; margin-top: 16px; }}
    .footer-newsletter input {{ flex: 1; padding: 10px 14px; border-radius: 6px; border: none;
      background: rgba(255,255,255,.1); color: #fff; font-family: 'Lato', sans-serif; font-size: .88rem; }}
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

    /* ── Responsive ── */
    @media (max-width: 900px) {{
      .about-strip, .contact-grid, .footer-grid {{ grid-template-columns: 1fr; }}
      .about-strip img {{ height: 240px; }}
    }}
    @media (max-width: 640px) {{
      .nav-links {{ display: none; }}
      .hamburger {{ display: block; }}
      .form-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

<!-- ── Navbar ── -->
<nav>
  <div class="logo">✦ {biz_name}</div>
  <ul class="nav-links">
    <li><a href="#categories">Menu</a></li>
    <li><a href="#about">About</a></li>
    <li><a href="#testimonials">Reviews</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#booking" class="nav-cta">Book Now</a></li>
  </ul>
  <button class="hamburger" onclick="document.querySelector('.nav-links').style.display = document.querySelector('.nav-links').style.display === 'flex' ? 'none' : 'flex'; document.querySelector('.nav-links').style.flexDirection='column'; document.querySelector('.nav-links').style.position='absolute'; document.querySelector('.nav-links').style.top='72px'; document.querySelector('.nav-links').style.left='0'; document.querySelector('.nav-links').style.right='0'; document.querySelector('.nav-links').style.background='#fff'; document.querySelector('.nav-links').style.padding='20px 5%';">☰</button>
</nav>

<!-- ── Hero ── -->
<section class="hero">
  <div class="hero-inner">
    <h1>{biz_name}</h1>
    <p>{description[:220]}</p>
    <div class="hero-btns">
      <a href="#booking" class="btn btn-accent">Book an Order</a>
      <a href="#categories" class="btn btn-outline">View Our Range</a>
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


def create_website_crew():
    """Create and configure the website builder crew"""
    
    # Task 1: Design specifications
    design_task = Task(
        description="""Based on the user's requirements, create a DETAILED, LUXURY-GRADE design specification including:
        1. Layout structure for every page (Home, Categories, About, Contact/Book, Gallery)
        2. Color scheme (primary, secondary, accent, background, text — with exact hex codes)
        3. Typography hierarchy (font families and sizes for H1/H2/H3/body/caption)
        4. Component styles: hero, category cards, product grid, testimonials, booking form, contact section
        5. Responsive breakpoints strategy (mobile, tablet, desktop)
        6. IMAGE PLAN — for every category and section, specify the exact Unsplash query keyword to use
           (e.g. 'https://source.unsplash.com/featured/800x500/?bakery,pastry' for a bakery hero)
        7. CONTENT PLAN — outline real business content for each section:
           - Business description and tagline
           - List of product/service categories with 1-line descriptions
           - Contact block: full address structure, email format, phone format, opening hours
           - Booking/Order form fields and flow
           - 3 realistic customer testimonials for this niche
        8. Animations and microinteractions (hover states, scroll reveals, CTA pulses)

        Output a structured specification that enables the developer to build a complete, content-rich site.""",
        agent=designer_agent,
        expected_output="Detailed design spec with color palette, typography, image plan, content plan, and component guidelines"
    )

    # Task 2: Code generation
    code_task = Task(
        description="""Based on the design specification AND the original user requirements, generate a COMPLETE, 
        production-ready, content-rich HTML/CSS/JavaScript website as a SINGLE FILE.

        MANDATORY requirements — every one of these must be present in the output:

        1. HERO SECTION: Full-width background image from Unsplash matching the business niche.
           Format: style="background-image:url('https://source.unsplash.com/featured/1400x700/?{keyword}')"
           Include business name as H1, a compelling tagline as subtitle, and two CTAs (Book Now / View Menu/Catalogue).

        2. CATEGORIES SECTION: A visually rich card grid showing each product/service category.
           Each card MUST include:
           - An <img> with src="https://source.unsplash.com/featured/400x300/?{category_keyword}" and loading="lazy"
           - Category name as H3
           - 2-sentence description enriched from the user's business description
           - A styled link/button

        3. CONTACT & LOCATION SECTION: Must include ALL of these:
           - Full business address (Street, City, State/Province, Country, Postal Code)
           - Phone number in international format (e.g. +1-555-xxx-xxxx or as provided)
           - Email address (support@{businessname}.com if not provided)
           - Opening hours table (Mon–Fri, Sat, Sun)
           - Google Maps embed: <iframe src="https://maps.google.com/maps?q={URL-encoded address}&output=embed" ...>

        4. BOOKING / ORDER FORM: A styled form with:
           - Fields: Full Name, Email, Phone, Service/Product selection (dropdown from categories), 
             Preferred Date (date picker), Time Slot (dropdown), Special Instructions (textarea)
           - On submit: generate a booking reference 'BK-' + Date.now() and show a confirmation banner
           - Form action is handled by JS (no page reload)

        5. TESTIMONIALS: 3 realistic customer reviews in a card or slider layout.
           Each review must have: star rating (★★★★★), customer name + city, review text specific to the niche.

        6. FOOTER: Includes address, phone, email, social media icons linking to #, copyright year (auto JS), 
           newsletter email input, and a "Back to top" link.

        7. NAVBAR: Logo (business name + emoji matching niche), navigation links, and a prominent CTA button.

        8. All images use loading="lazy" and meaningful alt attributes.
        9. Smooth scroll, CSS animations on card hover, and a scroll-reveal effect on sections (IntersectionObserver).
        10. Mobile responsive with hamburger menu for small screens.

        Output the COMPLETE, valid HTML file with all CSS in a <style> block and all JS in a <script> block.
        Do NOT use placeholder comments like '<!-- add content here -->'. Every section must have real content.""",
        agent=developer_agent,
        expected_output="Complete, single-file HTML website with all sections populated, Unsplash images, booking form, location/contact details, and real content"
    )
    
    crew = Crew(
        agents=[designer_agent, developer_agent],
        tasks=[design_task, code_task],
        process=Process.sequential,
        verbose=settings.VERBOSE_MODE
    )
    
    return crew

def build_website(user_requirements: str, project_name: str = "") -> dict:
    """
    Build a website based on user requirements.
    Falls back to a static template when OPENAI_API_KEY is not configured.
    The generated files are saved to output/<project-slug>/ automatically.
    """
    from tools.html_generator import generate_html, get_website_dir

    # Derive project name from requirements if not provided
    if not project_name:
        project_name = " ".join(user_requirements.split()[:5]).title()

    if not settings.OPENAI_API_KEY:
        print("⚠️  No OPENAI_API_KEY found — generating static template website instead.")
        html_code = _generate_static_fallback(user_requirements)
        filepath = generate_html({}, html_code, project_name, page_name="index")
        site_dir = get_website_dir(project_name)
        print(f"✅ Website saved to: {site_dir}")
        return {
            "status": "success",
            "result": html_code,
            "output_dir": site_dir,
            "index": filepath,
            "requirements": user_requirements,
            "fallback": True,
        }

    crew = create_website_crew()

    result = crew.kickoff(
        inputs={
            "user_requirements": user_requirements,
            "project_name": project_name,
        }
    )

    # Save AI-generated HTML
    html_code = str(result)
    filepath = generate_html({}, html_code, project_name, page_name="index")
    site_dir = get_website_dir(project_name)
    print(f"✅ Website saved to: {site_dir}")

    return {
        "status": "success",
        "result": result,
        "output_dir": site_dir,
        "index": filepath,
        "requirements": user_requirements,
    }

