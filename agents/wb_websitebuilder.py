"""
Website builder feature logic module.
Contains extracted orchestrator helpers from crew_main_legacy.py.
"""

import re
from typing import List, Dict

def extract_expected_spec(user_requirements: str) -> dict:
    """Extract hard requirements (name/contact/nav/categories/flags) from assembled prompt text."""
    text = user_requirements or ""

    def _pick(pattern: str) -> str:
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else ""

    website_name = _pick(r"WEBSITE NAME:\s*(.+)") or _pick(r"Business Name:\s*(.+)")
    email = _pick(r"Business Email:\s*([^\s]+)")
    phone = _pick(r"Business Phone:\s*([^\n]+)")
    location = _pick(r"Business Location:\s*([^\n]+)")
    logo_url = _pick(r"Business Logo URL:\s*([^\s]+)")

    categories: List[str] = []
    cat_block = re.search(
        r"Product/Service Categories \(create a visual card for EACH\):\s*(.+?)(?:\n\n|\n===|$)",
        text,
        re.S | re.I,
    )
    if cat_block:
        for line in cat_block.group(1).splitlines():
            s = line.strip().lstrip("-*").strip()
            if not s:
                continue
            low = s.lower()
            if low in {".", "our solutions", "what's new", "what’s new"}:
                continue
            categories.append(s)
    categories = list(dict.fromkeys(categories))[:8]

    nav_links: List[str] = []
    nav_match = re.search(
        r"NAVIGATION \(use exactly these items in this order\):\s*(.+)",
        text,
        re.I,
    )
    if nav_match:
        nav_links = [n.strip() for n in nav_match.group(1).split("|") if n.strip()]

    enable_blog = "=== Blog Section ===" in text
    enable_livestream = "=== Live Stream Section ===" in text
    enable_chatbot = "=== Chatbot Widget ===" in text
    non_cart_mode = (
        "=== NON-CART CATALOG DIRECTIVE ===" in text
        or bool(re.search(r"shopping cart is disabled|do\s+not\s+include\s+add\s+to\s+cart", text, re.I))
    )
    enable_shopping_cart = (
        "=== Required E-commerce Features ===" in text
        or "shopping cart/storefront must include" in text.lower()
    )
    if non_cart_mode:
        enable_shopping_cart = False

    booking_prefix = _pick(r"Order/Booking Reference Prefix:\s*([^\n]+)") or _pick(r"Reference Prefix:\s*([^\n]+)")
    booking_prefix = booking_prefix.strip()
    booking_form_disabled = bool(re.search(r"BOOKING/ORDER FORM MODE:\s*DISABLED|Booking/Order Form:\s*DISABLED", text, re.I))
    enable_booking_form = bool(booking_prefix) and not booking_form_disabled

    def _extract_numbered_urls(section_title: str) -> List[str]:
        block = re.search(
            rf"{re.escape(section_title)}\s*:\s*(.+?)(?:\n\n|\n===|$)",
            text,
            re.I | re.S,
        )
        urls: List[str] = []
        if not block:
            return urls
        for line in block.group(1).splitlines():
            m = re.search(r"\b\d+\.\s+(https?://\S+)", line.strip(), re.I)
            if not m:
                continue
            u = (m.group(1) or "").strip().rstrip(",.;)")
            if u and u not in urls:
                urls.append(u)
        return urls

    media_videos = _extract_numbered_urls("Detected Video Assets (re-use these where relevant)")
    media_audios = _extract_numbered_urls("Detected Audio Assets (re-use these where relevant)")
    media_embeds = _extract_numbered_urls("Detected Embedded Media URLs (YouTube/Vimeo/SoundCloud)")

    return {
        "website_name": website_name,
        "email": email,
        "phone": phone,
        "location": location,
        "logo_url": logo_url,
        "categories": categories,
        "nav_links": nav_links,
        "enable_blog": enable_blog,
        "enable_livestream": enable_livestream,
        "enable_chatbot": enable_chatbot,
        "enable_shopping_cart": enable_shopping_cart,
        "booking_prefix": booking_prefix,
        "enable_booking_form": enable_booking_form,
        "media_videos": media_videos,
        "media_audios": media_audios,
        "media_embeds": media_embeds,
    }

def enforce_generated_html_spec(html_code: str, user_requirements: str, website_id: str = "") -> str:
    """Force critical fields to match explicit build spec when LLM output drifts."""
    import re
    from .wb_sections import inject_products_section
    spec = extract_expected_spec(user_requirements)
    name = spec["website_name"]
    email = spec["email"]
    phone = spec["phone"]
    location = spec["location"]
    logo_url = spec.get("logo_url") or ""
    categories = spec["categories"]
    nav_links = spec.get("nav_links") or []
    enable_blog = bool(spec.get("enable_blog"))
    enable_livestream = bool(spec.get("enable_livestream"))
    enable_shopping_cart = bool(spec.get("enable_shopping_cart"))
    enable_chatbot = bool(spec.get("enable_chatbot"))
    enable_booking_form = bool(spec.get("enable_booking_form"))

    fixed = html_code
    # --- Chatbot widget injection ---
# Chatbot widget injection
    if enable_chatbot and 'id="chatbot-widget"' not in fixed:
        chatbot_widget = '''
        <!-- Chatbot Widget -->
<style>
#chatbot-widget { position: fixed; bottom: 28px; right: 28px; z-index: 400; }
#chat-toggle {
    width: 56px; height: 56px; border-radius: 50%;
    background: linear-gradient(135deg, var(--primary), var(--accent));
    border: none; color: #fff; font-size: 1.5rem; cursor: pointer;
    box-shadow: 0 4px 20px rgba(99,102,241,.5);
}
#chat-box {
    position: absolute; bottom: 70px; right: 0; width: 340px;
    background: var(--card, #fff); border: 1px solid var(--border, #e5e7eb); border-radius: 16px;
    box-shadow: 0 8px 40px rgba(0,0,0,.35);
    display: none; flex-direction: column; overflow: hidden;
}
#chat-box.open { display: flex; }
.chat-head {
    background: linear-gradient(135deg, var(--primary), var(--accent));
    color: #fff; padding: 16px 20px; font-weight: 700;
}
.chat-messages { flex: 1; height: 300px; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
.chat-msg { max-width: 80%; padding: 10px 14px; border-radius: 12px; font-size: .88rem; line-height: 1.5; }
.chat-msg.bot  { background: #f0f2f5; align-self: flex-start; border-bottom-left-radius: 4px; }
.chat-msg.user { background: #e0e7ff; align-self: flex-end; border-bottom-right-radius: 4px; }
.chat-footer { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border, #e5e7eb); }
#chatInput { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid var(--border, #e5e7eb); font-size: .95rem; }
#chatInput:focus { outline: none; border-color: var(--accent); }
</style>
<div id="chatbot-widget">
    <div id="chat-box">
        <div class="chat-head">🤖 AI Assistant</div>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-msg bot">Hi! 👋 I'm your AI assistant. Ask me anything about this website or our services.</div>
        </div>
        <div class="chat-footer">
            <input type="text" id="chatInput" placeholder="Ask anything…" onkeydown="if(event.key==='Enter')sendChat()" />
            <button onclick="sendChat()">➤</button>
        </div>
    </div>
    <button id="chat-toggle" onclick="toggleChat()">🤖</button>
</div>
<script>
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
    const res = await fetch('/chatbot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg, context: 'visitor' })
    }).then(r => r.json()).catch(() => ({}));
    document.getElementById('chat-typing')?.remove();
    appendChatMsg(res.reply || 'Sorry, I could not process that.', 'bot');
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
</script>
'''


        if '</body>' in fixed:
            fixed = fixed.replace('</body>', chatbot_widget + '\n</body>', 1)
        else:
            fixed += chatbot_widget


    media_videos = list(spec.get("media_videos") or [])
    media_audios = list(spec.get("media_audios") or [])
    media_embeds = list(spec.get("media_embeds") or [])

    # --- Media section injection/enrichment ---
    # Deduplicate at orchestrator level: only inject missing types
    video_exists = bool(re.search(r'<video[\s>]', fixed))
    audio_exists = bool(re.search(r'<audio[\s>]', fixed))
    # For embeds, check for known platforms in iframes
    embed_exists = bool(re.search(r'<iframe[^>]+src=["\']?[^"\'>]*(youtube|youtu\\.be|vimeo|soundcloud)[^"\'>]*["\']?', fixed, re.I))

    inject_videos = [] if video_exists else media_videos  # Inject all if missing
    inject_audios = [] if audio_exists else media_audios  # Inject all if missing
    inject_embeds = [] if embed_exists else media_embeds  # Inject all if missing

    from agents.wb_media import inject_or_enrich_media_section
    fixed = inject_or_enrich_media_section(fixed, inject_videos, inject_audios, inject_embeds)

    is_medical_domain = bool(re.search(
        r"\b(doctor|clinic|patient|medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\s*equipment|reagent|reseller|distributor)\b",
        user_requirements or "",
        re.I,
    ))

    def _slug(label: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", (label or "").lower()).strip("-") or "section"

    def _nav_anchor(label: str, id_set: set[str]) -> str:
        low = (label or "").strip().lower()
        norm = re.sub(r"[^a-z0-9]+", "", low)
        if "home" in low:
            return "#home"
        if "about" in low:
            return "#about-us" if "about-us" in id_set else "#about"
        if "service" in low:
            return "#services" if "services" in id_set else "#products"
        if "contact" in low:
            return "#contact"
        if "book" in low or "appoint" in low:
            if "booknow" in id_set:
                return "#booknow"
            if "booking" in id_set:
                return "#booking"
            return "#contact"
        if "testimonial" in low or "review" in low:
            return "#testimonials"
        if "blog" in low:
            return "/blog"
        if "shop" in low:
            return "/shop"
        if "live" in low:
            return "#livestream"
        candidate = _slug(label)
        return f"#{candidate}" if candidate in id_set else f"#{candidate}"

    def _replace_section_copy(
        markup: str,
        section_id: str,
        heading: str | None = None,
        subheading: str | None = None,
        description: str | None = None,
    ) -> str:
        pattern = re.compile(
            rf'(<section[^>]*id=["\']{re.escape(section_id)}["\'][^>]*>)(.*?)(</section>)',
            re.I | re.S,
        )
        match = pattern.search(markup)
        if not match:
            return markup
        inner = match.group(2)
        if heading and re.search(r'<h2[^>]*>', inner, re.I):
            inner = re.sub(r'(<h2[^>]*>)(.*?)(</h2>)', rf'\1{heading}\3', inner, count=1, flags=re.I | re.S)
        if subheading and re.search(r'<h3[^>]*class=["\'][^"\']*subheading[^"\']*["\'][^>]*>', inner, re.I):
            inner = re.sub(r'(<h3[^>]*class=["\'][^"\']*subheading[^"\']*["\'][^>]*>)(.*?)(</h3>)', rf'\1{subheading}\3', inner, count=1, flags=re.I | re.S)
        if description and re.search(r'<p[^>]*class=["\'][^"\']*section-desc[^"\']*["\'][^>]*>', inner, re.I):
            inner = re.sub(r'(<p[^>]*class=["\'][^"\']*section-desc[^"\']*["\'][^>]*>)(.*?)(</p>)', rf'\1{description}\3', inner, count=1, flags=re.I | re.S)
        return markup[:match.start(2)] + inner + markup[match.end(2):]

    # --- Brand and content normalization ---
    if name:
        brand_containers = re.findall(
            r'(<(?:a|span|div|p|h[1-6])[^>]*(?:logo|brand|site-?name|navbar-?brand|footer-?brand|company)[^>]*>)(.*?)(</(?:a|span|div|p|h[1-6])>)',
            fixed, re.I | re.S,
        )
        brand_candidates: List[str] = []
        for open_tag, content, close_tag in brand_containers:
            stripped = re.sub(r"<[^>]+>", "", content).strip()
            if stripped and stripped.lower() != name.lower():
                brand_candidates.append(stripped)
                fixed = fixed.replace(open_tag + content + close_tag, open_tag + content.replace(stripped, name) + close_tag, 1)

        wrong_names: List[str] = []
        for pat in [
            r"<title>(.*?)</title>",
            r"<h1[^>]*>(.*?)</h1>",
            r'class=["\'][^"\']*logo[^"\']*["\'][^>]*>(.*?)</',
            r'class=["\'][^"\']*brand[^"\']*["\'][^>]*>(.*?)</',
        ]:
            match = re.search(pat, fixed, re.I | re.S)
            if not match:
                continue
            candidate = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if candidate and candidate.lower() != name.lower() and len(candidate) > 2:
                wrong_names.append(candidate)
        for wrong in wrong_names:
            fixed = re.sub(re.escape(wrong), name, fixed, flags=re.I)
        for wrong in brand_candidates:
            fixed = re.sub(re.escape(wrong), name, fixed, flags=re.I)

        for pat in [
            r"Your Business Name",
            r"Your Company Name",
            r"Company Name",
            r"Site Name",
            r"Business Name",
            r"Organization Name",
        ]:
            fixed = re.sub(pat, name, fixed, flags=re.I)

        if re.search(r"<title>.*?</title>", fixed, re.I | re.S):
            fixed = re.sub(r"<title>.*?</title>", f"<title>{name}</title>", fixed, count=1, flags=re.I | re.S)
        if re.search(r"<h1[^>]*>.*?</h1>", fixed, re.I | re.S):
            fixed = re.sub(r"<h1[^>]*>.*?</h1>", f"<h1>{name}</h1>", fixed, count=1, flags=re.I | re.S)

    if email:
        fixed = re.sub(r"mailto:[^\"'\s]+", f"mailto:{email}", fixed, flags=re.I)
        fixed = re.sub(r">[^<]*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^<]*<", f">{email}<", fixed)

    if phone:
        tel_value = re.sub(r"[^+\d]", "", phone)
        if tel_value:
            fixed = re.sub(r"tel:[^\"'\s]+", f"tel:{tel_value}", fixed, flags=re.I)
            fixed = re.sub(
                r'(<a[^>]*href=["\']tel:[^"\']+["\'][^>]*>)(.*?)(</a>)',
                lambda m: f"{m.group(1)}{phone}{m.group(3)}",
                fixed,
                flags=re.I | re.S,
            )
        fixed = re.sub(r'(?<![\w@])(?:\+?\d[\d\s().-]{7,}\d)', phone, fixed, count=1)

    if nav_links:
        id_set = {m.group(1).lower() for m in re.finditer(r'id=["\']([^"\']+)["\']', fixed, re.I)}
        nav_items_html = "".join(
            f'<a href="{_nav_anchor(item, id_set)}" role="menuitem" tabindex="0">{item}</a>'
            for item in nav_links
        )
        mobile_nav_html = "".join(f'<a href="{_nav_anchor(item, id_set)}">{item}</a>' for item in nav_links)
        fixed = re.sub(
            r'(<div[^>]*class=["\'][^"\']*navbar-nav[^"\']*["\'][^>]*role=["\']menubar["\'][^>]*>)(.*?)(</div>)',
            rf'\1{nav_items_html}\3',
            fixed,
            count=1,
            flags=re.I | re.S,
        )
        fixed = re.sub(
            r'(<div[^>]*class=["\'][^"\']*navbar-mobile-menu[^"\']*["\'][^>]*>)(.*?)(</div>)',
            rf'\1{mobile_nav_html}\3',
            fixed,
            count=1,
            flags=re.I | re.S,
        )
        cta_label = nav_links[-1]
        cta_href = _nav_anchor(cta_label, id_set)
        fixed = re.sub(
            r'(<div[^>]*class=["\'][^"\']*navbar-cta[^"\']*["\'][^>]*>)(.*?)(</div>)',
            rf'\1<a href="{cta_href}"><button type="button">{cta_label}</button></a>\3',
            fixed,
            count=1,
            flags=re.I | re.S,
        )

    if location:
        location_clean = re.sub(r"\s+", " ", location).strip(" ,;")
        map_query = location_clean.replace(" ", "+")
        fixed = re.sub(
            r'(<iframe[^>]*src=["\'])https?://www\.google\.com/maps\?q=[^"\']*(&output=embed)?(["\'][^>]*>)',
            rf'\1https://www.google.com/maps?q={map_query}&output=embed\3',
            fixed,
            flags=re.I,
        )
        fixed = re.sub(
            r'(<(?:p|div)[^>]*class=["\'][^"\']*(?:address|location)[^"\']*["\'][^>]*>)(.*?)(</(?:p|div)>)',
            rf'\1{location_clean}\3',
            fixed,
            count=1,
            flags=re.I | re.S,
        )

    if is_medical_domain:
        category_list = categories[:4]
        services_summary = ", ".join(category_list[:-1]) + (f", and {category_list[-1]}" if len(category_list) > 1 else (category_list[0] if category_list else "patient care"))
        hero_copy = (
            f"Trusted doctor-led clinic providing {services_summary} for patients and families."
            if services_summary else
            "Trusted doctor-led clinic providing consultations, diagnostics guidance, and compassionate patient care."
        )
        meta_copy = (
            f"{name} is a doctor-led clinic offering {services_summary} with patient-first medical care."
            if services_summary else
            f"{name} is a doctor-led clinic offering consultations, diagnostics guidance, and patient-first care."
        )
        fixed = re.sub(
            r'(<meta\s+name=["\']description["\']\s+content=["\'])([^"\']*)(["\'])',
            rf'\1{meta_copy}\3',
            fixed,
            count=1,
            flags=re.I,
        )
        fixed = re.sub(
            r'(<section[^>]*class=["\'][^"\']*hero[^"\']*["\'][^>]*>.*?<p>)(.*?)(</p>)',
            rf'\1{hero_copy}\3',
            fixed,
            count=1,
            flags=re.I | re.S,
        )
        fixed = _replace_section_copy(
            fixed,
            "about-us",
            heading="About Our Clinic",
            subheading="Compassionate, patient-first care",
            description=f"{name} delivers evidence-based consultations, preventive care, and follow-up support tailored to each patient.",
        )
        fixed = _replace_section_copy(
            fixed,
            "services",
            heading="Clinical Services",
            subheading="Care aligned with your health needs",
            description=hero_copy,
        )
        fixed = _replace_section_copy(
            fixed,
            "resources",
            heading="Patient Information",
            subheading="Guidance before and after your visit",
            description="Find clear next steps, appointment guidance, and patient education that support ongoing clinical care.",
        )
        fixed = _replace_section_copy(
            fixed,
            "contact",
            heading="Contact Our Clinic",
            subheading="Book care or ask a clinical question",
            description=f"Reach {name} for appointments, follow-up visits, and general clinical enquiries.",
        )
        fixed = _replace_section_copy(
            fixed,
            "booknow",
            heading="Book an Appointment",
            subheading="Request your visit with our clinic",
            description=f"Schedule a consultation with {name} and receive a booking reference right away.",
        )

        generic_replacements = [
            (r"Simplify Your Everyday Connections", name or "Our Clinic"),
            (r"Reliable services tailored to fit your lifestyle and business needs\. Experience seamless support from start to finish\.", hero_copy),
            (r"Personal Support", category_list[0] if len(category_list) > 0 else "General Consultation"),
            (r"Business Solutions", category_list[1] if len(category_list) > 1 else "Preventive Care"),
            (r"Educational Resources", category_list[2] if len(category_list) > 2 else "Patient Education"),
            (r"Get Personal Support", "Book Consultation"),
            (r"Explore Business Solutions", "Learn About Treatment"),
            (r"Browse Resources", "Patient Information"),
            (r"Book Now", "Book Appointment"),
            (r"Get Started", "Book Appointment"),
            (r"Learn More", "View Services"),
            (r"connectivity", "clinical"),
            (r"business needs", "health needs"),
            (r"business tools", "medical support"),
            (r"support or consultation", "consultation or follow-up care"),
        ]
        for pattern, replacement in generic_replacements:
            fixed = re.sub(pattern, replacement, fixed, flags=re.I)

        services_match = re.search(
            r'(<section[^>]*id=["\']services["\'][^>]*>)(.*?)(</section>)',
            fixed,
            re.I | re.S,
        )
        if services_match and category_list:
            inner = services_match.group(2)
            card_pattern = re.compile(
                r'(<div class="card-content">\s*<h3>)(.*?)(</h3>\s*<p>)(.*?)(</p>\s*<button[^>]*>)(.*?)(</button>)',
                re.S,
            )
            counter = {"value": 0}

            def _rewrite_service_card(match: re.Match) -> str:
                idx = counter["value"]
                counter["value"] += 1
                if idx >= len(category_list):
                    return match.group(0)
                category = category_list[idx]
                description = f"Consult with our clinicians about {category.lower()} and receive clear diagnosis, treatment, and follow-up guidance."
                button = "Book Appointment"
                return f"{match.group(1)}{category}{match.group(3)}{description}{match.group(5)}{button}{match.group(7)}"

            inner = card_pattern.sub(_rewrite_service_card, inner)
            fixed = fixed[:services_match.start(2)] + inner + fixed[services_match.end(2):]

    if not enable_booking_form:
        # Remove booking/order form sections and booking/order-focused navigation when prefix is not provided.
        fixed = re.sub(
            r'<section[^>]*id=["\'](?:booknow|booking|book-appointment|book-appointment-form|order-form|booking-form)["\'][^>]*>.*?</section>',
            '',
            fixed,
            flags=re.I | re.S,
        )
        fixed = re.sub(
            r'<a[^>]*href=["\']#[^"\']*(?:book|booking|order)[^"\']*["\'][^>]*>.*?</a>',
            '',
            fixed,
            flags=re.I | re.S,
        )
        fixed = re.sub(
            r'<a[^>]*>\s*<button[^>]*>\s*[^<]*(?:book|booking|order)[^<]*</button>\s*</a>',
            '',
            fixed,
            flags=re.I | re.S,
        )
        fixed = re.sub(
            r'<button[^>]*>\s*[^<]*(?:book|booking|order now)[^<]*</button>',
            '',
            fixed,
            flags=re.I | re.S,
        )
        fixed = re.sub(
            r'<form[^>]*(?:id|class|name|action)=["\'][^"\']*(?:book|booking|order)[^"\']*["\'][^>]*>.*?</form>',
            '',
            fixed,
            flags=re.I | re.S,
        )
        fixed = re.sub(r'\n{3,}', '\n\n', fixed)

    # Ensure product list exists when categories are present in spec.
    fixed = inject_products_section(fixed, categories)
    return fixed

def generate_static_fallback(user_requirements: str, theme_key: str = "modern") -> str:
    """Generate a content-rich static HTML website when no API key is available."""
    import re
    import urllib.parse
    from agents.crew import THEMES  # If THEMES is not yet modularized, keep this import
    t = THEMES.get(theme_key, THEMES["modern"])
    # ── Extract hints from the prompt ─────────────────────────────────────────
    biz_name_match = re.search(r'WEBSITE NAME:\s*(.+)', user_requirements)
    if biz_name_match:
        biz_name = biz_name_match.group(1).strip()
    else:
        biz_name_match2 = re.search(r'Business Name:\s*(.+)', user_requirements)
        biz_name = biz_name_match2.group(1).strip() if biz_name_match2 else "Business Name"
    is_informational = bool(re.search(r'SITE TYPE:\s*Informational', user_requirements, re.I))
    if "=== NON-CART CATALOG DIRECTIVE ===" in user_requirements:
        is_informational = True
    if re.search(r"Do NOT include Add to Cart|no 'Buy Now'|NO 'Buy Now'", user_requirements, re.I):
        is_informational = True
    nav_links = []
    nav_header_match = re.search(r'NAVIGATION \(use exactly these items.*?\):\s*(.+)', user_requirements)
    if nav_header_match:
        nav_links = [n.strip() for n in nav_header_match.group(1).split('|') if n.strip()]
    logo_match = re.search(r'Brand Logo URL:\s*(https?://\S+)', user_requirements)
    logo_url = logo_match.group(1) if logo_match else ""
    site_images = [m.group(1) for m in re.finditer(r'(?m)^\s+\d+\. (https?://\S+)', user_requirements)]
    cats_raw = re.findall(r'^\s*- (.+?)(?:\n|$)', user_requirements, re.M)
    cats = []
    for c in cats_raw:
        val = c.strip()
        low = val.lower()
        if not val or len(val) >= 60 or val.startswith('='):
            continue
        if low.startswith('classification key:') or low.startswith('classification label:'):
            continue
        cats.append(val)
    cats = cats[:8]
    if not cats:
        cats = ["Products", "Services", "Gallery", "Special Offers"]
    loc_match = re.search(r'Business Location:\s*(.+)', user_requirements)
    location = loc_match.group(1).strip() if loc_match else "123 Main Street, New York, NY 10001, USA"
    location = re.sub(r"\s+", " ", location).strip(" ,;")
    location_lines = [line.strip() for line in re.split(r"[\n;]", location) if line.strip()]
    location = location_lines[0] if location_lines else location
    map_query = urllib.parse.quote_plus(location)
    email_match = re.search(r'Business Email:\s*(\S+)', user_requirements)
    email = email_match.group(1) if email_match else f"info@{biz_name.lower().replace(' ','')}.com"
    phone_match = re.search(r'Business Phone:\s*(\S+)', user_requirements)
    phone = phone_match.group(1) if phone_match else "+1-555-000-0000"
    prefix_match = re.search(r'Reference Prefix:\s*([A-Z\-]+)', user_requirements)
    prefix = prefix_match.group(1) if prefix_match else "ORD"
    niche_kw = cats[0].lower().replace(' ', ',') if cats else 'business'
    hero_bg = site_images[0] if site_images else f"https://source.unsplash.com/featured/1400x900/?{niche_kw}"
    desc_match = re.search(r'Business Description:\s*(.+?)(?:\n\n|\Z)', user_requirements, re.S)
    description = desc_match.group(1).strip() if desc_match else user_requirements[:200]
    # --- Classic single-block HTML generation (pre-modular) ---
    html = f"""
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <title>{biz_name}</title>
        <style>
        .join-community-section {{
            background: #728cf7;
            padding: 64px 0 60px 0;
            text-align: center;
            position: relative;
        }}
        .join-community-section h2 {{
            color: #fff;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .join-community-section p {{
            color: #fff;
            font-size: 1rem;
            margin-bottom: 32px;
            opacity: 0.95;
        }}
        .join-community-form {{
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            display: inline-block;
            padding: 36px 32px 32px 32px;
            max-width: 400px;
            width: 100%;
        }}
        .join-community-form input[type="email"] {{
            border: none;
            border-radius: 6px;
            padding: 12px 16px;
            font-size: 1rem;
            width: 70%;
            margin-bottom: 18px;
            outline: none;
            background: #f5f7fa;
            color: #333;
        }}
        .join-community-form button {{
            background: #f7b2fa;
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 12px 32px;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .join-community-form button:hover {{
            background: #e48be6;
        }}
        @media (max-width: 600px) {{
            .join-community-form {{
                padding: 24px 10px;
                max-width: 98vw;
            }}
            .join-community-section {{
                padding: 40px 0 40px 0;
            }}
        }}
        </style>
    </head>
    <body style='margin:0;padding:0;'>
        <div style='text-align:center;margin:32px 0 0 0;'>" + (f"<img src='{logo_url}' alt='Logo' style='height:64px;margin-bottom:8px;'/>" if logo_url else "") + "</div>
        <h1 style='text-align:center;font-size:2.2rem;margin:8px 0 0 0;font-family:sans-serif;'>{biz_name}</h1>
        " + ("<nav style='text-align:center;margin:24px 0 32px 0;'><ul style='display:inline-flex;gap:32px;list-style:none;padding:0;margin:0;'>" + ''.join([f"<li><a href='#{n.lower().replace(' ','-')}' style='text-decoration:none;color:#728cf7;font-weight:600;font-size:1.1rem;'>{n}</a></li>" for n in nav_links]) + "</ul></nav>" if nav_links else "") + "
        <section style='background:linear-gradient(90deg,#728cf7 60%,#f7b2fa 100%);color:#fff;padding:64px 0 48px 0;text-align:center;'>
            <h2 style='font-size:2rem;font-weight:700;margin-bottom:18px;'>{description}</h2>
            <img src='{hero_bg}' alt='Hero Image' style='max-width:90vw;width:600px;border-radius:18px;box-shadow:0 4px 32px rgba(0,0,0,0.10);margin:32px auto 0 auto;display:block;'>
        </section>
        " + ''.join([f"<section id='{cat.lower().replace(' ','-')}' style='padding:56px 0 40px 0;text-align:center;'><h3 style='font-size:1.5rem;font-weight:600;color:#728cf7;margin-bottom:12px;'>{cat}</h3><p style='max-width:600px;margin:0 auto 0 auto;color:#444;font-size:1.08rem;'>Explore our {cat.lower()} and discover more.</p></section>" for cat in cats]) + "
        <section class='join-community-section'>
            <h2>Join Our Community</h2>
            <p>Join our community and receive writing tips, updates on workshops, and exclusive content straight to your inbox.</p>
            <form class='join-community-form'>
                <input type='email' placeholder='Your email address' required>
                <button type='submit'>Subscribe</button>
            </form>
        </section>
        <footer style='background:#222;color:#fff;text-align:center;padding:32px 0 16px 0;margin-top:0;'>
            <div style='margin-bottom:18px;'>
                <span style='margin:0 18px;font-size:1.3rem;'>📱</span>
                <span style='margin:0 18px;font-size:1.3rem;'>🦜</span>
                <span style='margin:0 18px;font-size:1.3rem;'>📷</span>
                <span style='margin:0 18px;font-size:1.3rem;'>🔗</span>
            </div>
            <div style='font-size:.95rem;opacity:.85;'>© 2026 {biz_name}. All rights reserved.</div>
        </footer>
    </body>
    </html>
    """
    return html

def sync_legacy_entrypoint(site_dir: str, html_code: str) -> None:
    """Legacy entrypoint sync is no longer needed with root-level legacy output."""
    return

def write_output_target_scaffold(site_dir: str, output_target: str, html_code: str) -> None:
    """Create target-specific project scaffolds alongside generated HTML."""
    import os
    target = (output_target or "legacy").strip().lower()
    if target == "legacy":
        return
    artifacts_dir = os.path.join(site_dir, "artifacts", target)
    os.makedirs(artifacts_dir, exist_ok=True)
    staging_note = (
        "The generated site is organized under the staging folder alongside "
        "separate assets/css, assets/js, assets/images, assets/audio, and "
        "assets/video directories."
    )
    if target == "php":
        php_index = os.path.join(artifacts_dir, "index.php")
        with open(php_index, "w", encoding="utf-8") as f:
            f.write("<?php\n// Generated by Agentic Builder\n?>\n")
            f.write(html_code)
        return
    if target == "react":
        files = {
            "package.json": """{\n  \"name\": \"agentic-site-react\",\n  \"private\": true,\n  \"version\": \"0.1.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"react\": \"^18.3.1\",\n    \"react-dom\": \"^18.3.1\"\n  },\n  \"devDependencies\": {\n    \"vite\": \"^5.4.8\"\n  }\n}\n""",
            "index.html": """<!doctype html>\n<html lang=\"en\">\n  <head>\n    <meta charset=\"UTF-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>Agentic React Output</title>\n  </head>\n  <body>\n    <div id=\"root\"></div>\n    <script type=\"module\" src=\"/src/main.jsx\"></script>\n  </body>\n</html>\n""",
            "src/main.jsx": """import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App.jsx';\n\nReactDOM.createRoot(document.getElementById('root')).render(<App />);\n""",
            "src/App.jsx": """export default function App() {\n  return (\n    <main style={{padding: '24px', fontFamily: 'Arial, sans-serif'}}>\n      <h1>Agentic Build Output (React)</h1>\n      <p>""" + staging_note + """ Edit the staged index.html for page-level customization.</p>\n    </main>\n  );\n}\n""",
        }
    elif target == "vue":
        files = {
            "package.json": """{\n  \"name\": \"agentic-site-vue\",\n  \"private\": true,\n  \"version\": \"0.1.0\",\n  \"type\": \"module\",\n  \"scripts\": {\n    \"dev\": \"vite\",\n    \"build\": \"vite build\",\n    \"preview\": \"vite preview\"\n  },\n  \"dependencies\": {\n    \"vue\": \"^3.5.11\"\n  },\n  \"devDependencies\": {\n    \"@vitejs/plugin-vue\": \"^5.1.4\",\n    \"vite\": \"^5.4.8\"\n  }\n}\n""",
            "index.html": """<!doctype html>\n<html lang=\"en\">\n  <head>\n    <meta charset=\"UTF-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>Agentic Vue Output</title>\n  </head>\n  <body>\n    <div id=\"app\"></div>\n    <script type=\"module\" src=\"/src/main.js\"></script>\n  </body>\n</html>\n""",
            "vite.config.js": """import { defineConfig } from 'vite';\nimport vue from '@vitejs/plugin-vue';\n\nexport default defineConfig({ plugins: [vue()] });\n""",
            "src/main.js": """import { createApp } from 'vue';\nimport App from './App.vue';\n\ncreateApp(App).mount('#app');\n""",
            "src/App.vue": """<template>\n  <main style=\"padding:24px;font-family:Arial,sans-serif\">\n    <h1>Agentic Build Output (Vue)</h1>\n    <p>""" + staging_note + """ Edit the staged index.html for page-level customization.</p>\n  </main>\n</template>\n""",
        }
    else:
        readme = os.path.join(artifacts_dir, "README.txt")
        with open(readme, "w", encoding="utf-8") as f:
            f.write(
                "Target scaffold is not defined yet. Use index.html in this staging folder as the generated output, "
                "with linked assets kept under the organized assets subfolders.\n"
            )
        return
    for rel, content in files.items():
        abs_path = os.path.join(artifacts_dir, rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

def create_website_crew(
    theme_key: str = "modern",
    classification: str = "generic",
    classification_label: str = "Generic",
    classification_group: str = "general",
    build_mode: str = "agentic_only",
    output_target: str = "legacy",
):
    """Create and configure the website builder crew with a 3-task pipeline."""
    from agents.crew import THEMES, designer_agent, theme_agent, Task, Crew, Process, settings
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
    fact_lock_block = """
=== SOURCE OF TRUTH (NON-NEGOTIABLE) ===
1. The WEBSITE BUILD SPECIFICATION and explicit user-provided business facts are the highest-priority source of truth.
2. Reference sites, scraped content, and web research are secondary and may only inform structure, terminology, and visual style.
3. If any lower-priority source conflicts with the WEBSITE BUILD SPECIFICATION, ignore the lower-priority source.

Locked facts that must be preserved exactly when present in the input:
- website/business name
- industry/profession/niche
- email, phone, and location
- navigation labels and order
- category, service, product, and model names
- CTA mode (informational vs ecommerce)

Forbidden behavior:
- Do NOT invent or substitute another brand or company name.
- Do NOT switch to a different industry, audience, or business type.
- Do NOT replace exact services/categories with generic unrelated alternatives.
- Do NOT let reference-site branding, cities, contacts, or offers leak into the final output.
=========================================
"""
    classification_note = (
        f"AUDIENCE/CLASSIFICATION KEY: {classification.upper()}\n"
        f"AUDIENCE/CLASSIFICATION LABEL: {classification_label.upper()}\n"
        f"AUDIENCE/CLASSIFICATION GROUP: {classification_group.upper()}\n"
        "Tailor all content, CTA labels, navigation, section types, trust signals, and information architecture to this profile.\n\n"
        f"BUILD MODE: {build_mode.upper()}\n"
        f"OUTPUT TARGET: {output_target.upper()}\n\n"
    )
    design_task = Task(
        description=classification_note + fact_lock_block + """Based on the user's requirements, produce a STRUCTURED CONTENT PLAN for the website.

        First, silently extract the locked business facts from the WEBSITE BUILD SPECIFICATION and keep them consistent through the entire plan.
        If any reference content conflicts with those locked facts, ignore the conflicting reference content.

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
                6. BOOKING/ORDER FORM (CONDITIONAL):
                     - ONLY include this section if the WEBSITE BUILD SPECIFICATION contains
                         an explicit "Order/Booking Reference Prefix".
                     - If enabled, provide form fields with types/placeholders and describe
                         booking reference prefix usage (e.g. BK-, ORD-, RES-).
                     - If disabled, omit booking/order form content entirely.
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
    theme_task = Task(
        description=f"""{classification_note}{fact_lock_block}You will receive a structured CONTENT PLAN from the previous task.

        Before writing HTML, preserve the locked facts exactly as provided in the WEBSITE BUILD SPECIFICATION.
        The final HTML must match the requested business identity and domain even if the CONTENT PLAN or any reference material drifted.

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
          7. Booking/Order form (CONDITIONAL):
              Include this section ONLY if an explicit "Order/Booking Reference Prefix"
              exists in the WEBSITE BUILD SPECIFICATION. If absent, omit booking/order
              sections, booking/order nav links, and booking/order CTAs.
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

def build_website(
    user_requirements: str,
    project_name: str = "",
    theme_key: str = "modern",
    classification: str = "generic",
    classification_label: str = "Generic",
    classification_group: str = "general",
    build_mode: str = "agentic_only",
    output_target: str = "legacy",
    reference_images: list = None,
    website_id: str = "",
) -> dict:
    """
    Build a website based on user requirements.
    Falls back to a static template when OPENAI_API_KEY is not configured.
    The generated files are saved to output/<project-slug>/ automatically.
    """
    import os, re, time, hashlib
    import requests
    from urllib.parse import urlparse
    from agents.crew import logger, settings, _with_retry, _MAX_RETRIES
    from tools.html_generator import generate_html
    from .wb_websitebuilder import (
        enforce_generated_html_spec,
        generate_static_fallback,
        write_output_target_scaffold,
        sync_legacy_entrypoint,
        create_website_crew,
    )
    trace_id = str(os.urandom(8).hex())[:8]
    t0 = time.time()
    logger.info("[%s] ▶ build_website START  project=%r  ai=%s  mode=%s  target=%s",
                trace_id, project_name or "(auto)",
                "enabled" if settings.OPENAI_API_KEY else "disabled (fallback)",
                build_mode, output_target)
    logger.debug("[%s] Theme selection: theme_key=%r", trace_id, theme_key)
    if not project_name:
        project_name = " ".join(user_requirements.split()[:5]).title()
    if not settings.OPENAI_API_KEY:
        logger.warning("[%s] ⚠  No OPENAI_API_KEY — generating static fallback", trace_id)
        t1 = time.time()
        html_code = generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index", output_target=output_target)
        # Reuse the exact directory chosen by generate_html during this run.
        site_dir = os.path.dirname(filepath)
        write_output_target_scaffold(site_dir, output_target, html_code)
        sync_legacy_entrypoint(site_dir, html_code)
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
    logger.info("[%s] 🧠 Kicking off CrewAI pipeline… theme=%s classification=%s group=%s target=%s", trace_id, theme_key, classification_label, classification_group, output_target)
    crew = create_website_crew(
        theme_key=theme_key,
        classification=classification,
        classification_label=classification_label,
        classification_group=classification_group,
        build_mode=build_mode,
        output_target=output_target,
    )
    logger.debug("[%s] Crew created with theme: %r", trace_id, theme_key)
    t1 = time.time()
    try:
        result = _with_retry(
            crew.kickoff,
            inputs={
              "user_requirements": user_requirements,
              "project_name": project_name,
              "classification": classification,
              "classification_label": classification_label,
              "classification_group": classification_group,
              "build_mode": build_mode,
              "output_target": output_target,
            },
            trace_id=trace_id,
        )
    except Exception as exc:
        logger.error("[%s] ❌ CrewAI failed after %d retries: %s — falling back to static", trace_id, _MAX_RETRIES, exc)
        html_code = generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index", output_target=output_target)
        # Reuse the exact directory chosen by generate_html during this run.
        site_dir = os.path.dirname(filepath)
        write_output_target_scaffold(site_dir, output_target, html_code)
        sync_legacy_entrypoint(site_dir, html_code)
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
    html_code = str(result)
    html_code = html_code.strip()
    if html_code.startswith("```"):
        html_code = re.sub(r'^```[a-zA-Z]*\n?', '', html_code)
        html_code = re.sub(r'\n?```\s*$', '', html_code)
        html_code = html_code.strip()
    html_code = enforce_generated_html_spec(html_code, user_requirements, website_id=website_id)
    design_spec = {'css': {}, 'js': {}, 'images': {}, 'audio': {}, 'video': {}}
    css_matches = list(re.finditer(r'<style[^>]*>(.*?)</style>', html_code, re.DOTALL | re.IGNORECASE))
    logger.info(f"Found {len(css_matches)} <style> blocks in HTML.")
    for i, m in enumerate(css_matches):
        css_content = m.group(1).strip()
        if css_content:
            fname = f"main{i+1}.css" if i > 0 else "main.css"
            design_spec['css'][fname] = css_content
            logger.info(f"Extracted CSS: {fname} ({len(css_content)} bytes)")
        html_code = html_code.replace(m.group(0), f'<link rel="stylesheet" href="assets/css/{fname}">')
    js_matches = list(re.finditer(r'<script[^>]*>(.*?)</script>', html_code, re.DOTALL | re.IGNORECASE))
    logger.info(f"Found {len(js_matches)} <script> blocks in HTML.")
    for i, m in enumerate(js_matches):
        js_content = m.group(1).strip()
        if js_content:
            fname = f"main{i+1}.js" if i > 0 else "main.js"
            design_spec['js'][fname] = js_content
            logger.info(f"Extracted JS: {fname} ({len(js_content)} bytes)")
        html_code = html_code.replace(m.group(0), f'<script src="assets/js/{fname}"></script>')
    image_matches = list(re.finditer(r'<img[^>]+src=["\']([^"\'>]+)["\']', html_code, re.IGNORECASE))
    logger.info(f"Found {len(image_matches)} <img> tags in HTML.")
    _ref_imgs = list(reference_images) if reference_images else []
    _ref_img_idx = 0
    _medical_mode = bool(re.search(
      r"\\b(medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\\s*equipment|reagent|reseller|distributor)\\b",
      user_requirements or "",
      re.I,
    ))
    _medical_seeds = [
      "medical-equipment",
      "laboratory-devices",
      "diagnostic-kits",
      "hospital-instruments",
      "clinical-lab",
    ]
    _medical_seed_idx = 0
    def _next_ref_image() -> str | None:
        nonlocal _ref_img_idx
        if not _ref_imgs:
            return None
        img = _ref_imgs[_ref_img_idx % len(_ref_imgs)]
        _ref_img_idx += 1
        return img
    url_to_fname = {}
    for m in image_matches:
        img_url = m.group(1)
        original_url = img_url
        logger.info(f"Processing image URL: {img_url}")
        if img_url.startswith('http://') or img_url.startswith('https://'):
            if img_url in url_to_fname:
                html_code = html_code.replace(img_url, f"assets/images/{url_to_fname[img_url]}")
                continue
            _is_placeholder = "picsum.photos" in img_url or "unsplash.com" in img_url or "placeholder" in img_url
            if _is_placeholder and _ref_imgs:
                real_url = _next_ref_image()
                logger.info(f"Replacing placeholder {img_url} with reference image {real_url}")
                img_url = real_url
                if img_url in url_to_fname:
                    html_code = html_code.replace(original_url, f"assets/images/{url_to_fname[img_url]}")
                    continue
            elif _is_placeholder and _medical_mode and "picsum.photos/seed/" in img_url:
                seed = _medical_seeds[_medical_seed_idx % len(_medical_seeds)]
                _medical_seed_idx += 1
                img_url = re.sub(r"/seed/[^/]+/", f"/seed/{seed}/", img_url, count=1)
            parsed = urlparse(img_url)
            base = os.path.basename(parsed.path).strip()
            ext = os.path.splitext(base)[1].lower() if base else ""
            if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
                ext = ".jpg"
            digest = hashlib.sha1(img_url.encode("utf-8")).hexdigest()[:12]
            safe_base = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.splitext(base)[0]).strip("-")
            if not safe_base or safe_base.isdigit() or len(safe_base) < 3:
                safe_base = "img"
            fname = f"{safe_base}-{digest}{ext}"
            try:
                resp = requests.get(img_url, timeout=5, stream=True)
                logger.info(f"Download status for {img_url}: {resp.status_code}")
                if resp.status_code == 200:
                    content = resp.content
                    design_spec['images'][fname] = content
                    url_to_fname[img_url] = fname
                    logger.info(f"Downloaded image: {fname} ({len(content)} bytes)")
                    html_code = html_code.replace(original_url, f'assets/images/{fname}')
                else:
                    logger.warning(f"Skipping image {img_url}: HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to download image {img_url}: {e}")
    media_matches = list(re.finditer(
      r'<(audio|video|source)\b[^>]*\bsrc=["\']([^"\'>]+)["\']',
      html_code,
      re.IGNORECASE,
    ))
    logger.info(f"Found {len(media_matches)} media tags in HTML.")
    media_url_to_local = {}
    audio_exts = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
    video_exts = {".mp4", ".webm", ".mov", ".m4v", ".m3u8", ".ogv"}
    for m in media_matches:
        media_tag = (m.group(1) or "").lower().strip()
        media_url = (m.group(2) or "").strip()
        original_url = media_url
        if not (media_url.startswith('http://') or media_url.startswith('https://')):
            continue
        if media_url in media_url_to_local:
            html_code = html_code.replace(original_url, media_url_to_local[media_url])
            continue
        parsed = urlparse(media_url)
        base = os.path.basename(parsed.path).strip()
        ext = os.path.splitext(base)[1].lower() if base else ""
        if ext in audio_exts or media_tag == "audio":
            bucket = "audio"
            if ext not in audio_exts:
                ext = ".mp3"
        else:
            bucket = "video"
            if ext not in video_exts:
                ext = ".mp4"
        digest = hashlib.sha1(media_url.encode("utf-8")).hexdigest()[:12]
        safe_base = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.splitext(base)[0]).strip("-")
        if not safe_base or safe_base.isdigit() or len(safe_base) < 3:
            safe_base = media_tag or bucket
        fname = f"{safe_base}-{digest}{ext}"
        try:
            resp = requests.get(media_url, timeout=8, stream=True)
            logger.info(f"Download status for media {media_url}: {resp.status_code}")
            if resp.status_code == 200:
                content = resp.content
                design_spec[bucket][fname] = content
                local_rel = f"assets/{bucket}/{fname}"
                media_url_to_local[media_url] = local_rel
                logger.info(f"Downloaded {bucket}: {fname} ({len(content)} bytes)")
                html_code = html_code.replace(original_url, local_rel)
            else:
                logger.warning(f"Skipping media {media_url}: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Failed to download media {media_url}: {e}")
    filepath = generate_html(design_spec, html_code, project_name, page_name="index", output_target=output_target)
    # Reuse the exact directory chosen by generate_html during this run.
    site_dir = os.path.dirname(filepath)
    write_output_target_scaffold(site_dir, output_target, html_code)
    sync_legacy_entrypoint(site_dir, html_code)
    logger.info("[%s] ✅ AI website saved to %s  (total %.1fs)", trace_id, site_dir, time.time()-t0)
    return {
        "status": "success",
        "result": result,
        "output_dir": site_dir,
        "index": filepath,
        "requirements": user_requirements,
        "trace_id": trace_id,
    }
