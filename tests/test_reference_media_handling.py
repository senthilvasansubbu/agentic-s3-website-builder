from agents.crew import _enforce_generated_html_spec, _extract_expected_spec


def _prompt_with_media() -> str:
    return """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Demo Site

=== EXTRACTED FROM EXISTING WEBSITE ===
Source URL: https://example.com

Detected Video Assets (re-use these where relevant):
  1. https://cdn.example.com/media/intro.mp4

Detected Audio Assets (re-use these where relevant):
  1. https://cdn.example.com/media/theme.mp3

Detected Embedded Media URLs (YouTube/Vimeo/SoundCloud):
  1. https://www.youtube.com/embed/abc123
"""


def _prompt_with_multiple_media() -> str:
    return """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Demo Site Multi

=== EXTRACTED FROM EXISTING WEBSITE ===
Source URL: https://example.com

Detected Video Assets (re-use these where relevant):
  1. https://cdn.example.com/media/intro.mp4
  2. https://cdn.example.com/media/overview.mp4

Detected Audio Assets (re-use these where relevant):
  1. https://cdn.example.com/media/theme.mp3
  2. https://cdn.example.com/media/voiceover.mp3

Detected Embedded Media URLs (YouTube/Vimeo/SoundCloud):
  1. https://www.youtube.com/embed/abc123
  2. https://player.vimeo.com/video/456789
"""


def test_extract_expected_spec_parses_reference_media_urls():
    spec = _extract_expected_spec(_prompt_with_media())

    assert spec["media_videos"] == ["https://cdn.example.com/media/intro.mp4"]
    assert spec["media_audios"] == ["https://cdn.example.com/media/theme.mp3"]
    assert spec["media_embeds"] == ["https://www.youtube.com/embed/abc123"]


def test_enforce_generated_html_spec_injects_media_section_when_missing():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"hero\"><h1>Welcome</h1></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert 'id="media"' in out
    assert '<video controls preload="metadata"' in out
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out
    assert 'https://cdn.example.com/media/intro.mp4' in out
    assert 'https://cdn.example.com/media/theme.mp3' in out


def test_enforce_generated_html_spec_injects_only_missing_media_types():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"hero\"><h1>Welcome</h1></section>
  <section id=\"existing\"><video controls src=\"https://cdn.example.com/has-video.mp4\"></video></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    assert out.count('<video controls') == 1
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out


def test_enforce_generated_html_spec_enriches_existing_media_section():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"media\"><h2>Media Highlights</h2></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    assert '<video controls preload="metadata"' in out
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out


def test_enforce_generated_html_spec_keeps_video_and_audio_in_single_media_section():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"media\">
    <h2>Media Highlights</h2>
    <video controls preload=\"metadata\">
      <source src=\"https://cdn.example.com/media/intro.mp4\" />
    </video>
  </section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    media_start = out.index('<section id="media"')
    media_end = out.index('</section>', media_start)
    media_block = out[media_start:media_end]

    assert '<video controls preload="metadata"' in media_block
    assert '<audio controls preload="metadata"' in media_block
    assert 'https://cdn.example.com/media/intro.mp4' in media_block
    assert 'https://cdn.example.com/media/theme.mp3' in media_block


def test_enforce_generated_html_spec_injects_multiple_media_items_with_selector_and_scroll():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id="hero"><h1>Welcome</h1></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_multiple_media())

    assert out.count('<video controls preload="metadata"') == 2
    assert out.count('<audio controls preload="metadata"') == 2
    assert out.count('<iframe src="') >= 2
    assert 'https://cdn.example.com/media/intro.mp4' in out
    assert 'https://cdn.example.com/media/overview.mp4' in out
    assert 'https://cdn.example.com/media/theme.mp3' in out
    assert 'https://cdn.example.com/media/voiceover.mp3' in out
    assert 'https://www.youtube.com/embed/abc123' in out
    assert 'https://player.vimeo.com/video/456789' in out
    assert 'class="media-scroll"' in out
    assert 'aria-label="Choose a video"' in out
    assert 'aria-label="Choose an audio track"' in out


def test_enforce_generated_html_spec_realigns_brand_and_medical_context():
    prompt = """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Aba Aba Clinic
Business Email: hello@abaaba.example.com
Business Phone: +91 98765 43210
Business Location: Chennai, India
Profession: Doctor
NAVIGATION (use exactly these items in this order): Home | Services | About | Contact | Book Appointment
Product/Service Categories (create a visual card for EACH):
- General Consultation
- Preventive Care
- Diagnostics Guidance
- Follow-up Visits
"""
    html = """<!doctype html>
<html>
<head>
  <title>Horizon Connect | Reliable Connectivity Solutions for Individuals and Businesses</title>
  <meta name="description" content="Discover trusted, easy-to-use service solutions from Horizon Connect." />
</head>
<body>
  <header>
    <nav class="navbar container" aria-label="Primary navigation">
      <a href="#home" class="navbar-logo" aria-label="Horizon Connect Home">Horizon Connect</a>
      <div class="navbar-nav" role="menubar" id="nav-menu">
        <a href="#home" role="menuitem" tabindex="0">Home</a>
        <a href="#resources" role="menuitem" tabindex="0">Resources</a>
        <a href="#testimonials" role="menuitem" tabindex="0">Testimonials</a>
        <a href="#contact" role="menuitem" tabindex="0">Contact</a>
        <a href="#booknow" role="menuitem" tabindex="0">Book Now</a>
      </div>
      <div class="navbar-cta"><a href="#booknow"><button type="button">Book Now</button></a></div>
    </nav>
    <div class="navbar-mobile-menu" id="mobileMenu"><a href="#resources">Resources</a></div>
  </header>
  <main id="home">
    <section class="hero"><div class="hero-content"><h1>Simplify Your Everyday Connections</h1><p>Reliable services tailored to fit your lifestyle and business needs. Experience seamless support from start to finish.</p><div class="hero-buttons"><button type="button">Get Started</button><button type="button">Learn More</button></div></div></section>
    <section id="about-us"><h2 class="section-heading">Who We Are</h2><h3 class="subheading">Dedicated to Connecting You Better</h3><p class="section-desc">Horizon Connect is committed to providing dependable and easy-to-use solutions for individuals and businesses alike.</p></section>
    <section id="services"><h2 class="section-heading">What We Offer</h2><h3 class="subheading">Comprehensive Solutions for Your Needs</h3><p class="section-desc">Explore a range of services designed to streamline your life and business.</p><article class="card"><div class="card-content"><h3>Personal Support</h3><p>Tailored assistance that adapts to your unique circumstances.</p><button type="button">Get Personal Support</button></div></article><article class="card"><div class="card-content"><h3>Business Solutions</h3><p>Innovative tools and expert advice.</p><button type="button">Explore Business Solutions</button></div></article></section>
    <section id="resources"><h2 class="section-heading">Learn and Grow</h2><h3 class="subheading">Valuable Information at Your Fingertips</h3><p class="section-desc">Our resource center is created to help you maximize the benefits of our offerings.</p></section>
    <section id="contact"><h2 class="section-heading">Get in Touch</h2><h3 class="subheading">We’re Here to Help You</h3><p class="section-desc">Reach our team for support or consultation.</p><p>support@horizonconnect.com</p><a href="tel:+12175550147">+1 (217) 555-0147</a><iframe src="https://www.google.com/maps?q=Springfield,+IL&output=embed"></iframe></section>
    <section id="booknow"><h2 class="section-heading">Book Now</h2><h3 class="subheading">Schedule today</h3><p class="section-desc">Schedule your personalized support or consultation with Horizon Connect.</p></section>
  </main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, prompt)

    assert "Aba Aba Clinic" in out
    assert "Horizon Connect" not in out
    assert "hello@abaaba.example.com" in out
    assert "+91 98765 43210" in out
    assert "Clinical Services" in out
    assert "General Consultation" in out
    assert "Preventive Care" in out
    assert "Book Appointment" not in out
    assert 'id="booknow"' not in out
    assert "maps?q=Chennai" in out


def test_enforce_generated_html_spec_removes_booking_order_form_when_prefix_missing():
    prompt = """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Acme Studio
BOOKING/ORDER FORM MODE: DISABLED
NAVIGATION (use exactly these items in this order): Home | Services | Contact
"""

    html = """<!doctype html>
<html>
<head><title>Acme Studio</title></head>
<body>
  <header>
    <nav>
      <a href="#home">Home</a>
      <a href="#services">Services</a>
      <a href="#booknow">Book Now</a>
      <a href="#order-form">Order</a>
    </nav>
  </header>
  <main>
    <section id="home"><h1>Acme Studio</h1></section>
    <section id="booknow"><h2>Book Appointment</h2><form id="booking-form"><input name="name"/></form></section>
    <section id="order-form"><h2>Place Order</h2><form class="order-form"><input name="qty"/></form></section>
  </main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, prompt)

    assert 'id="booknow"' not in out
    assert 'id="order-form"' not in out
    assert 'id="booking-form"' not in out
    assert 'href="#booknow"' not in out
    assert 'href="#order-form"' not in out
