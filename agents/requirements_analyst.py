"""
RequirementsAnalystAgent
────────────────────────
Assembles the final LLM prompt from the raw build request, the website
DB record, and any external research (web search, social search, URL scrape).

This logic was previously inline inside the build route handler
(api/routes/website_builder.py). Extracting it here means:

  • Adding a new feature (e.g. TikTok links) = one change in this file,
    nowhere else.
  • The route handler stays clean — it only orchestrates, not assembles.
  • The prompt can be unit-tested independently of the HTTP layer.

Usage
─────
    from agents.requirements_analyst import build_prompt

    full_prompt = build_prompt(body, site, extra_context)
"""

import re
import json
import urllib.parse
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from tools.theme_builder import THEMES

logger = logging.getLogger("website_builder.requirements_analyst")

# ── Feature → plain-English instruction mapping ───────────────────────────────
CART_FEATURE_PROMPTS: Dict[str, str] = {
    "categories":      "Product listing with category navigation and breadcrumbs.",
    "price_filter":    "Price range filter slider on product/shop pages.",
    "images":          "Product image gallery with zoom and multiple images per product.",
    "discounts":       "Display original price, sale price, and discount percentage badge.",
    "coupons":         "Coupon code input field at checkout with validation feedback.",
    "flash_offers":    "Flash sale section with countdown timer and highlighted deal cards.",
    "ads":             "Advertisement banner placeholders (hero, sidebar, and footer positions).",
    "email_notify":    "Email subscription opt-in form for promotions and newsletters.",
    "sms_notify":      "SMS/WhatsApp opt-in checkbox at checkout for order updates.",
    "whatsapp_notify": "WhatsApp contact button and order notification opt-in.",
    "reviews":         "Product review and star-rating section on product detail pages.",
    "wishlist":        "Add-to-wishlist button on product cards.",
    "search":          "Search bar with autocomplete for products.",
}


@dataclass
class BuildRequest:
    """
    Mirrors the relevant fields from BuildWebsiteRequest (api/routes/website_builder.py).
    Kept as a plain dataclass so this module has zero dependency on FastAPI/Pydantic.
    """
    requirements: str
    use_web_search: bool = False
    use_social_search: bool = False
    existing_website_url: Optional[str] = None
    existing_website_urls: Optional[List[str]] = None
    build_mode: str = "agentic_only"
    output_target: str = "legacy"
    categories: Optional[List[str]] = None
    catalog_items: Optional[List[str]] = None   # exact product/model names — no AI hallucination
    location: Optional[str] = None
    niche: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_prefix: Optional[str] = None
    social_links: Optional[Dict[str, Any]] = None
    classification: str = "generic"
    classification_label: Optional[str] = None
    classification_group: Optional[str] = None
    website_id: Optional[str] = None
    include_shopping_cart: bool = False
    scraped_title: Optional[str] = None  # New: scraped business/site title
    nav_links: Optional[list] = None     # New: scraped nav links (list of str)
    content_depth: Optional[str] = 'standard'  # minimal | standard | detailed | enterprise


def _parse_cart_features(site: Dict[str, Any]) -> List[str]:
    """Safely parse cart_features JSON from the websites DB row."""
    try:
        cf = site.get("cart_features") or "[]"
        return json.loads(cf) if isinstance(cf, str) else list(cf)
    except Exception:
        return []


def _auto_extract_categories(requirements: str) -> List[str]:
    """
    Fall-back category extraction: pulls comma-separated tokens that follow
    keywords like 'categories:', 'types:' etc. in the requirements string.
    """
    raw = re.findall(
        r'(?:categor(?:y|ies)[:\s]+|types?[:\s]+)([A-Za-z ,&]+)',
        requirements,
    )
    if not raw:
        return []
    cats = [c.strip() for item in raw for c in item.split(",") if c.strip()]
    return cats


def _detect_medical_domain(requirements: str) -> bool:
    """Check if this is a medical/diagnostic/pharmaceutical domain."""
    medical_keywords = r"\b(medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\s*equipment|reagent|reseller|distributor|hospital|clinic|healthcare|health\s*care|device|analyzer|analyzer)\b"
    return bool(re.search(medical_keywords, requirements or "", re.I))


# Canonical grouped taxonomy used by the build UI.
CLASSIFICATION_SERVICES = {
    'b2b': ['Product Demo', 'Pricing & Quote', 'Partnership Inquiry', 'Bulk Order', 'Technical Support', 'Account Consultation'],
    'b2c': ['Product Inquiry', 'Order Support', 'Shipping Information', 'Returns & Exchanges', 'Customer Support', 'Product Recommendations'],
    'ecommerce_store': ['Browse Catalog', 'Bulk Purchase Inquiry', 'Order Tracking', 'Returns & Replacement', 'Product Availability', 'Checkout Support'],
    'medical_practice': ['Schedule Appointment', 'Patient Consultation', 'Follow-up Visit', 'Prescription Refill', 'Teleconsultation', 'Patient Support'],
    'diagnostics_lab': ['Book a Test', 'Health Package Inquiry', 'Sample Collection', 'Report Assistance', 'Corporate Screening', 'Lab Support'],
    'medical_equipment': ['Equipment Consultation', 'Product Demonstration', 'Request a Quote', 'Installation & Training', 'Maintenance & Support', 'Reagent Supply'],
    'pharmacy_wellness': ['Medicine Availability', 'Wellness Consultation', 'Refill Support', 'Home Delivery Inquiry', 'Product Guidance', 'Customer Support'],
    'tutor': ['Book a Session', 'Course Inquiry', 'Learning Plan Discussion', 'Exam Preparation', 'Parent Consultation', 'Study Materials'],
    'school': ['Admissions Inquiry', 'Campus Visit', 'Program Information', 'Fee Structure', 'Faculty Interaction', 'Parent Support'],
    'training_institute': ['Enroll in Program', 'Certification Inquiry', 'Placement Support', 'Batch Schedule', 'Demo Class', 'Course Counseling'],
    'research_lab': ['Research Collaboration', 'Publication Inquiry', 'Lab Partnership', 'Grant Discussion', 'Data Access Request', 'Scientific Consulting'],
    'law_firm': ['Free Consultation', 'Case Review', 'Document Review', 'Legal Notice Support', 'Contract Advisory', 'Client Meeting'],
    'engineering_services': ['Project Consultation', 'Technical Assessment', 'Design Review', 'Implementation Support', 'Maintenance Contract', 'Proposal Request'],
    'real_estate_agency': ['Schedule Property Visit', 'Property Inquiry', 'Rental Consultation', 'Valuation Request', 'Buyer Assistance', 'Seller Consultation'],
    'startup_saas': ['Schedule Demo', 'Pricing Inquiry', 'Trial Access', 'Implementation Call', 'Enterprise Plan', 'Customer Success'],
    'manufacturer_distributor': ['Request Catalog', 'Dealer Inquiry', 'Bulk Pricing', 'Industry Consultation', 'After-Sales Support', 'Supply Partnership'],
    'restaurant': ['Reserve a Table', 'Private Dining', 'Catering Inquiry', 'Event Booking', 'Delivery Support', 'Special Request'],
    'salon_spa': ['Book Appointment', 'Service Pricing', 'Bridal Package Inquiry', 'Membership Details', 'Gift Voucher', 'Consultation'],
    'fitness_wellness': ['Join Membership', 'Trial Session', 'Personal Training', 'Nutrition Consultation', 'Class Schedule', 'Wellness Program'],
    'artist_portfolio': ['Commission Inquiry', 'Artwork Purchase', 'Exhibition Invitation', 'Collaboration Request', 'Portfolio Review', 'Custom Project'],
    'photographer': ['Book a Session', 'Print Order', 'Event Coverage Inquiry', 'Studio Visit', 'Portfolio Review', 'Licensing Request'],
    'musician_band': ['Booking Inquiry', 'Merchandise Order', 'Event/Show Inquiry', 'Press Inquiry', 'Fan Message', 'Collaboration Request'],
    'freelancer': ['Hire Me', 'Project Inquiry', 'Rate Consultation', 'Proposal Request', 'Availability Check', 'Portfolio Discussion'],
    'writer_blogger': ['Newsletter Signup', 'Book Purchase Inquiry', 'Content Collaboration', 'Speaking Inquiry', 'Guest Post Proposal', 'Fan Message'],
    'student_portfolio': ['Project Discussion', 'Mentorship Request', 'Internship Inquiry', 'Resume Review', 'Collaboration Request', 'Portfolio Feedback'],
    'ngo': ['Donate Now', 'Volunteer Signup', 'Program Partnership', 'Grant Inquiry', 'Event Participation', 'Support Request'],
    'religious_org': ['Join a Service', 'Event Registration', 'Donation', 'Volunteer Signup', 'Prayer Request', 'Community Inquiry'],
    'cultural_org': ['Event Registration', 'Membership Inquiry', 'Program Information', 'Heritage Showcase', 'Sponsorship Inquiry', 'Volunteer'],
    'charity_foundation': ['Donate to a Cause', 'Campaign Participation', 'Volunteer Signup', 'Partnership Proposal', 'Grant Inquiry', 'Impact Report'],
    'community_club': ['Join as Member', 'Event Registration', 'Match/Event Schedule', 'Sponsorship Inquiry', 'Volunteer', 'Club Inquiry'],
    'generic': ['General Inquiry', 'Product Information', 'Service Request', 'Quote Request', 'Support Request', 'Schedule Callback'],
}

CLASSIFICATION_ALIASES = {
    'doctor': 'medical_practice',
    'teacher': 'tutor',
    'lawyer': 'law_firm',
    'engineer': 'engineering_services',
    'startup': 'startup_saas',
    'artist': 'artist_portfolio',
    'student': 'student_portfolio',
    'salon': 'salon_spa',
    'realestate': 'real_estate_agency',
    'fitness': 'fitness_wellness',
    'scientist': 'research_lab',
    'photo': 'photographer',
    'band': 'musician_band',
    'musician': 'musician_band',
    'freelance': 'freelancer',
    'blogger': 'writer_blogger',
    'writer': 'writer_blogger',
    'temple': 'religious_org',
    'church': 'religious_org',
    'mosque': 'religious_org',
    'charity': 'charity_foundation',
    'foundation': 'charity_foundation',
    'club': 'community_club',
    'sports_club': 'community_club',
    'cultural': 'cultural_org',
}

def _get_medical_services() -> List[str]:
    """Return medical-specific services for booking/inquiry forms."""
    return [
        "Equipment Consultation",
        "Product Demonstration",
        "Installation & Training",
        "Maintenance & Support",
        "Replacement Parts",
        "Reagent Supply",
        "Warranty & Service",
    ]


def _get_services_for_classification(class_key: str) -> List[str]:
    """Get booking services based on classification key."""
    normalized = CLASSIFICATION_ALIASES.get(class_key, class_key)
    return CLASSIFICATION_SERVICES.get(normalized, CLASSIFICATION_SERVICES['generic'])


def _get_domain_services_directive(class_key: str, class_label: str, class_group: str = "general") -> str:
    """Inject domain-specific booking form guidance into prompt based on classification."""
    normalized = CLASSIFICATION_ALIASES.get(class_key, class_key)
    services = _get_services_for_classification(normalized)
    return (
        f"\n\n=== DOMAIN-SPECIFIC BOOKING/INQUIRY SERVICES ===\n"
        f"Classification Group: {class_group}\n"
        f"Classification: {class_label}\n"
        f"The booking/inquiry form service dropdown MUST use ONLY these {class_label.lower()}-relevant options:\n"
        + "\n".join(f"- {svc}" for svc in services) + "\n"
        f"Do NOT use generic or unrelated services. Keep all form copy, CTAs, and booking options strictly relevant to {class_label.lower()} services.\n"
    )


def _get_medical_services_directive() -> str:
    """Inject medical-specific booking form guidance into prompt."""
    return _get_domain_services_directive('medical_equipment', 'Medical Equipment', 'Healthcare & Life Sciences')


def _build_cart_section(cart_features: List[str]) -> str:
    if not cart_features:
        return ""
    feat_text = "\n".join(
        f"- {CART_FEATURE_PROMPTS.get(f, f)}"
        for f in cart_features
        if f in CART_FEATURE_PROMPTS
    )
    if not feat_text:
        return ""
    return (
        "\n\n=== Required E-commerce Features ===\n"
        "The shopping cart/storefront must include:\n"
        + feat_text
    )


def _build_shop_nav_section(website_id: str) -> str:
    """
    Injects instructions so the AI generates a live Shop page that fetches
    products dynamically from the platform API using the website_id.
    """
    return f"""

=== Shop / Product Catalogue Navigation ===
This website has a live product catalogue managed via the platform API.

You MUST:
1. Add a "Shop" link in the main navigation bar (before the CTA button) that
    links to  /shop  as a dedicated page entry point.
2. Do NOT render the Shop catalogue inline inside index.html.
    The homepage should only expose the navigation link to /shop.
3. The separate Shop experience should provide:
   - A search bar (input type="text" id="shopSearch") that filters the product
     grid in real time.
   - A product grid (CSS grid, 3-4 columns on desktop, 2 on tablet, 1 on mobile).
   - Each product card must show: product image, name, price (formatted with
     currency symbol), a short description snippet, category badge, and an
     "Add to Cart" button styled with the site accent colour.
4. Load products dynamically with this JavaScript (place before </body>):

<script>
(function () {{
  const WEBSITE_ID = "{website_id}";
  const API_BASE   = window.location.origin + "/api/v1";

  async function loadProducts() {{
    const grid = document.getElementById("shopGrid");
    if (!grid) return;
    try {{
      const res  = await fetch(`${{API_BASE}}/shop/cart-items/${{WEBSITE_ID}}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || []);
      if (!items.length) {{ grid.innerHTML = "<p style='grid-column:1/-1;text-align:center;color:#888'>No products yet.</p>"; return; }}
      grid.innerHTML = items.map(p => `
        <div class="product-card" data-name="${{(p.name||'').toLowerCase()}}">
          <div class="product-img-wrap">
            <img src="${{p.image_url || p.thumb_url || 'https://source.unsplash.com/featured/400x400/?product'}}"
                 alt="${{p.name}}" loading="lazy" style="width:100%;height:220px;object-fit:cover;border-radius:8px 8px 0 0">
            ${{p.category_name ? `<span class="cat-badge">${{p.category_name}}</span>` : ''}}
          </div>
          <div class="product-info" style="padding:14px">
            <h3 style="margin:0 0 6px;font-size:1rem">${{p.name}}</h3>
            <p style="color:#888;font-size:.85rem;margin:0 0 10px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${{p.description||''}}</p>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:700;font-size:1.05rem">${{p.currency||'$'}}${{Number(p.price||0).toFixed(2)}}</span>
              <button onclick="addToCart('${{p.product_id}}')" style="background:var(--accent,#667eea);color:#fff;border:none;padding:8px 16px;border-radius:6px;cursor:pointer">Add to Cart</button>
            </div>
          </div>
        </div>`).join('');
    }} catch(e) {{ console.error('Shop load error', e); }}
  }}

  function addToCart(productId) {{
    // Dispatch a custom event — intercept in your storefront logic
    document.dispatchEvent(new CustomEvent('addToCart', {{ detail: {{ productId }} }}));
    const btn = event.currentTarget;
    btn.textContent = '✓ Added';
    setTimeout(() => btn.textContent = 'Add to Cart', 1500);
  }}

  document.getElementById('shopSearch')?.addEventListener('input', function() {{
    const q = this.value.toLowerCase();
    document.querySelectorAll('.product-card').forEach(c => {{
      c.style.display = c.dataset.name.includes(q) ? '' : 'none';
    }});
  }});

  document.addEventListener('DOMContentLoaded', loadProducts);
}})();
</script>

5. Add this CSS for the product cards inside a <style> block:
.product-card{{background:#fff;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;transition:transform .2s,box-shadow .2s}}
.product-card:hover{{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,.13)}}
.product-img-wrap{{position:relative}}
.cat-badge{{position:absolute;top:10px;left:10px;background:var(--accent,#667eea);color:#fff;font-size:.7rem;padding:3px 8px;border-radius:20px}}
#shopGrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:24px;padding:20px 0}}
"""


def _build_feature_flag_sections(site: Dict[str, Any]) -> str:
    parts = []
    if site.get("enable_livestream"):
        parts.append(
            "\n\n=== Live Stream Section ===\n"
            "Include a Live Stream page (/livestream) on the website. "
            "The page should feature an embedded video player area (placeholder for a "
            "live stream embed such as YouTube Live, Twitch, or a custom RTMP player), "
            "a live viewer count badge, a live chat sidebar, an upcoming streams schedule "
            "section, and a subscribe/notify button. Add a 'Live' link in the main "
            "navigation with a pulsing red dot indicator."
        )
    if site.get("enable_blog"):
        parts.append(
            "\n\n=== Blog Section ===\n"
            "Include Blog as a dedicated /blog page. "
            "Do NOT render blog cards or blog content inline inside index.html. "
            "The separate blog page should display a grid of sample blog post cards, each with "
            "a title, short excerpt, author, date, reading time, and a 'Read More' link. "
            "Include at least 3 realistic sample blog posts relevant to the business niche. "
            "Add a 'Blog' link in the main navigation that points to /blog."
        )
    if site.get("enable_chatbot"):
        parts.append(
            "\n\n=== Chatbot Widget ===\n"
            "Embed a floating customer-support chatbot widget on every page. "
            "The widget should appear as a chat bubble in the bottom-right corner, "
            "open a chat panel on click, greet the visitor, and allow them to send "
            "messages. Include a clean HTML/CSS/JS implementation with a configurable "
            "welcome message and a placeholder for an API endpoint to handle replies."
        )
    return "".join(parts)


def _build_non_cart_catalog_directive(body: BuildRequest) -> str:
    """Ensure imported/listed products are rendered as content, not cart placeholders."""
    if body.include_shopping_cart:
        return ""

    mode = (body.build_mode or "agentic_only").strip().lower()
    combined_hint = (
        "This build is in COMBINED mode with imported website context. "
        "Preserve and modernize product/service listings from imported content. "
        if mode == "combined" or body.existing_website_url or body.existing_website_urls else ""
    )

    return (
        "\n\n=== NON-CART CATALOG DIRECTIVE ===\n"
        f"{combined_hint}"
        "If the brief/imported content contains products, services, SKUs, catalog items, or equipment names, "
        "you MUST render them as visible website content cards/tables with real names and descriptions.\n"
        "Do NOT output generic placeholders like 'Product 1', 'Item A', or empty cards.\n"
        "Do NOT include Add to Cart, Buy Now, checkout, pricing widgets, or cart controls when shopping cart is disabled.\n"
        "Use informational CTAs only (for example: Learn More, View Details, Contact Sales, Request Quote)."
    )


def _build_enrichment_section(
    body: BuildRequest,
    site: Dict[str, Any],
    cats: List[str],
    scraped_images: Optional[List[str]] = None,
) -> str:
    # Prefer scraped title, then user-entered title, then DB slug name
    site_name = body.scraped_title or site.get("title") or site.get("name") or "Business"
    # Strip duplicate suffix e.g. "Foo – Foo" → "Foo"
    if " – " in site_name:
        parts = [p.strip() for p in site_name.split(" – ")]
        site_name = parts[0] if parts[0] == parts[-1] else site_name
    site_desc = site.get("description") or ""

    lines = [
        "\n\n=== CONTENT & STYLE ENRICHMENT ===",
        "You MUST use every piece of information below in the generated website.",
        f"Business Name: {site_name}",
        f"Build Mode: {body.build_mode}",
        f"Output Target: {body.output_target}",
    ]

    class_key = body.classification or site.get("classification", "generic") or "generic"
    class_key = CLASSIFICATION_ALIASES.get(class_key, class_key)
    class_label = body.classification_label or site.get("classification_label") or class_key
    class_group = body.classification_group or site.get("classification_group") or "general"
    lines.append(
        "\nClassification Context:\n"
        f"- Classification Key: {class_key}\n"
        f"- Classification Label: {class_label}\n"
        f"- Classification Group: {class_group}\n"
        "Treat this as a global blueprint standard for layout hierarchy, CTA tone, section ordering, trust signals, and content voice."
    )

    if site_desc:
        lines.append(
            f"Business Description:\n{site_desc}\n"
            "Incorporate this description into the hero tagline, about section, "
            "and category cards."
        )

    if body.niche:
        lines.append(
            f"\nBusiness Niche / Category Hint: {body.niche}\n"
            "Treat this niche as a hard relevance guardrail for hero copy, sections, keywords, and visuals."
        )

    # Page sections / nav groups
    if cats:
        cat_list = "\n".join(f"  - {c}" for c in cats)
        lines.append(
            f"\nPage Sections & Navigation Groups (create a dedicated nav link AND a full visual section with cards/content for EACH):\n{cat_list}\n"
            f"IMPORTANT: Each entry above MUST appear in the top-level navigation AND as a distinct section in the page layout."
        )
        # Only suggest placeholder images if no real scraped images are available
        if not scraped_images:
            image_hints = "\n".join(
                f"  - {c}: https://picsum.photos/seed/{c.lower().replace(' ', '-')}/400/300"
                for c in cats
            )
            lines.append(f"\nSuggested placeholder images per category:\n{image_hints}")
        # Only suggest placeholder images if no real scraped images are available
        if not scraped_images:
            image_hints = "\n".join(
                f"  - {c}: https://picsum.photos/seed/{c.lower().replace(' ', '-')}/400/300"
                for c in cats
            )
            lines.append(f"\nSuggested placeholder images per category:\n{image_hints}")

    # Exact catalog items — strict no-hallucination directive
    catalog = getattr(body, 'catalog_items', None) or []
    if catalog:
        item_list = "\n".join(f"  - {item}" for item in catalog)
        lines.append(
            f"\n=== EXACT PRODUCT / MODEL NAMES (STRICT) ===\n"
            f"The following are the ONLY real product/model names to use in this website:\n"
            f"{item_list}\n"
            f"IMPORTANT RULES:\n"
            f"- Use ONLY the names listed above. Do NOT invent, embellish, or generate any additional product names.\n"
            f"- Do NOT add products not on this list. Every product card must map to one of these names exactly.\n"
            f"- Fabricated product names (e.g. random strings, variant suffixes) will break user trust — avoid them entirely.\n"
            f"- If a category has no matching product in this list, render the category section with a 'Contact us for details' note instead of placeholder items."
        )

    # Location + Google Maps embed
    location = body.location or ""
    if location:
        map_query = urllib.parse.quote_plus(location.strip())
        lines.append(
            f"\nBusiness Location: {location}\n"
            f"Embed this Google Map in the Contact section:\n"
            f'<iframe src="https://www.google.com/maps?q={map_query}&output=embed" '
            f'width="100%" height="350" style="border:0;border-radius:12px" '
            f'allowfullscreen loading="lazy"></iframe>'
        )

    # Contact
    email = body.email or f"info@{site_name.lower().replace(' ', '')}.com"
    lines.append(f"\nBusiness Email: {email}")
    if body.phone:
        lines.append(f"Business Phone: {body.phone}")

    # Booking reference only relevant for retail/cart sites
    if body.include_shopping_cart:
        prefix = body.booking_prefix or "ORD"
        lines.append(
            f"\nOrder/Booking Reference Prefix: {prefix}\n"
            f"The booking form must auto-generate a reference like "
            f"'{prefix}-' + Date.now() on submission."
        )

    # Social links
    if body.social_links:
        sl = body.social_links
        social_parts = []
        for platform in ("instagram", "facebook", "linkedin", "x", "youtube", "tiktok"):
            val = sl.get(platform)
            if val:
                urls = val if isinstance(val, list) else [val]
                social_parts.append(f"{platform.title()}: " + ", ".join(urls))
        if social_parts:
            lines.append(
                "\nSocial Media Profiles (use these real URLs in the footer social icons):\n"
                + "\n".join(social_parts)
            )
    elif body.use_social_search:
        lines.append(
            f"\n=== SOCIAL MEDIA SEARCH DIRECTIVE ===\n"
            f"No social media URLs were provided by the user. You are AUTHORISED to search "
            f"the web for the official Instagram, Facebook, and LinkedIn profiles of "
            f"'{site_name}' and use those real URLs in the footer social icons. "
            f"If you cannot find them, use '#' as a placeholder but still render the "
            f"social icon buttons in the footer."
        )

    # Hero image — use first real scraped image if available, else Unsplash
    if scraped_images:
        lines.append(
            f"\nHero background image: {scraped_images[0]}\n"
            "Use this real image as the hero section background (CSS background-image)."
        )
    else:
        niche_kw = (cats[0] if cats else site_name).lower().replace(" ", "-")
        lines.append(
            f"\nHero background image: "
            f"https://picsum.photos/seed/{niche_kw}/1400/700"
        )

    # Classification directive
    classification = class_key
    classification_label = class_label
    classification_group = class_group
    if classification and classification != "generic":
        lines.append(
            f"\n=== AUDIENCE / CLASSIFICATION ===\n"
            f"SITE TYPE:        {classification_label.upper()} ({classification.upper()})\n"
            f"INDUSTRY GROUP:   {classification_group.upper()}\n"
            "Tailor all copy, CTAs, navigation labels, and section content to suit this audience profile."
        )

    # Style directive — driven by the chosen theme
    theme_key = site.get("theme", "modern") or "modern"
    t = THEMES.get(theme_key, THEMES["modern"])
    lines.append(
        f"\n=== STYLE DIRECTIVE (Theme: {t['label']}) ===\n"
        f"PRIMARY COLOUR:   {t['primary']}\n"
        f"SECONDARY COLOUR: {t['secondary']}\n"
        f"ACCENT COLOUR:    {t['accent']}\n"
        f"BACKGROUND:       {t['bg']}\n"
        f"BODY TEXT COLOUR: {t['text']}\n"
        f"HEADING FONT:     {t['font_heading']}\n"
        f"BODY FONT:        {t['font_body']}\n"
        f"BORDER RADIUS:    {t['radius']}\n"
        f"SHADOW:           {t['shadow']}\n"
        f"HERO GRADIENT:    {t['gradient']}\n"
        "You MUST use these exact colours and fonts throughout the website. "
        "Use the primary colour for the navbar, headings, and key UI elements. "
        "Use the accent colour for buttons and call-to-action elements. "
        "Apply the border-radius value consistently to cards and buttons. "
        "Generous whitespace, smooth hover transitions, NO clip-art. "
        "Sections should feel polished and on-brand — consistent with the selected theme."
    )

    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def build_prompt(
    body: BuildRequest,
    site: Dict[str, Any],
    extra_context: str = "",
) -> tuple[str, List[str]]:
    """
    Assemble the full LLM prompt from the build request, website DB record,
    and pre-fetched external context (web search / social search / URL scrape).

    Returns
    -------
    full_prompt : str
        The complete prompt string ready to pass to build_website().
    cart_features : list[str]
        Parsed list of enabled cart feature keys (used for logging).
    """

    # Use scraped title and nav links if present
    site_title = body.scraped_title or site.get("title") or site.get("name") or "Business"
    site_logo_url = (site.get("logo_url") or "").strip()
    # Strip duplicate suffix e.g. "Foo – Foo" → "Foo"
    if " – " in site_title:
        _parts = [p.strip() for p in site_title.split(" – ")]
        if _parts[0] == _parts[-1]:
            site_title = _parts[0]
    nav_links = body.nav_links or []

    # ── Priority header — placed FIRST so the LLM sees it before anything else ──
    priority_lines = [
        "=== WEBSITE BUILD SPECIFICATION ===",
        f"WEBSITE NAME: {site_title}",
        f"CRITICAL: You MUST use '{site_title}' as the HTML <title>, the navbar logo/text, and the hero heading.",
        f"CRITICAL: Do NOT invent a new brand or company name. Use ONLY '{site_title}' throughout all content.",
        f"BUILD MODE: {body.build_mode}",
        f"OUTPUT TARGET: {body.output_target}",
    ]
    if body.classification_label:
        priority_lines.append(f"CLASSIFICATION LABEL: {body.classification_label}")
    if body.classification_group:
        priority_lines.append(f"CLASSIFICATION GROUP: {body.classification_group}")
    if site_logo_url:
        priority_lines.append(f"Business Logo URL: {site_logo_url}")
    if nav_links:
        priority_lines.append(
            "NAVIGATION (use exactly these items in this order): "
            + " | ".join(nav_links)
        )
    if not body.include_shopping_cart and not _parse_cart_features(site):
        priority_lines.append(
            "SITE TYPE: Informational — NO 'Buy Now', 'Order Now', 'Add to Cart', "
            "or 'Book Now' buttons. CTAs must be 'Learn More', 'Contact Us', 'Get in Touch', etc."
        )

    # Inject an explicit INDUSTRY directive so the LLM never drifts into
    # a different sector (e.g. generating cloud/tech content for a medical supplier).
    site_desc = site.get("description") or ""
    industry_hint = site_desc[:300] if site_desc else (body.requirements or "")[:300]
    priority_lines += [
        "CRITICAL — INDUSTRY LOCK:",
        f"  The business described in this brief is: {industry_hint}",
        "  ALL generated copy, section headings, product names, and service descriptions",
        "  MUST directly relate to this specific business and industry.",
        "  Do NOT generate content for any other industry (cloud, tech, spa, fashion, etc.)",
        "  unless that is explicitly the business described above.",
    ]

    priority_header = "\n".join(priority_lines) + "\n\n"

    # Base: user requirements + any pre-fetched research context
    prompt = priority_header + body.requirements + extra_context
    _DEPTH_DIRECTIVES = {
        'minimal':    "CONTENT DEPTH — MINIMAL: Generate a single-scroll landing page with a bold hero, 2–3 concise content sections, and a compact contact footer. Keep copy short and punchy. Do NOT add extra pages or lengthy descriptions.",
        'standard':   "CONTENT DEPTH — STANDARD: Generate a standard multi-section website with a hero, 3–5 distinct content sections, and a contact area. Include clear headings and supporting copy for each section.",
        'detailed':   "CONTENT DEPTH — DETAILED: Generate a comprehensive website. Each nav section must be a fully developed page section with extended copy, team bios where relevant, testimonials, FAQ, and detailed product/service descriptions.",
        'enterprise': "CONTENT DEPTH — ENTERPRISE: Generate a full enterprise-depth website. Every nav section must be richly developed with multiple subsections, detailed product specs, case studies, extensive social proof, multiple CTAs per section, and a comprehensive multi-column footer.",
    }
    _depth_key = (body.content_depth or 'standard').lower()
    if _depth_key in _DEPTH_DIRECTIVES:
        prompt += "\n\n" + _DEPTH_DIRECTIVES[_depth_key]



    # Cart features (only if shopping cart is enabled)
    cart_features = _parse_cart_features(site)
    if body.include_shopping_cart or cart_features:
        prompt += _build_cart_section(cart_features)


    # Shop navigation (inject live product catalogue if cart is enabled)
    website_id = body.website_id or site.get("website_id", "")
    if (body.include_shopping_cart or cart_features) and website_id:
        prompt += _build_shop_nav_section(website_id)


    # Feature flags (livestream, blog, chatbot)
    prompt += _build_feature_flag_sections(site)


    # Non-cart catalog behavior
    prompt += _build_non_cart_catalog_directive(body)


    # Resolve categories
    cats = list(body.categories or [])
    if not cats:
        cats = _auto_extract_categories(body.requirements)

    # Inject domain-specific services based on classification
    class_key = body.classification or site.get("classification", "generic") or "generic"
    class_key = CLASSIFICATION_ALIASES.get(class_key, class_key)
    class_label = body.classification_label or site.get("classification_label") or class_key
    class_group = body.classification_group or site.get("classification_group") or "general"
    prompt += _get_domain_services_directive(class_key, class_label, class_group)

    # Extract scraped images for enrichment (from extra_context already in prompt)
    import re as _re
    scraped_images: List[str] = []
    for m in _re.finditer(r'(?m)^\s+\d+\. (https?://\S+)', extra_context):
        scraped_images.append(m.group(1))

    # Rich structured content enrichment
    prompt += _build_enrichment_section(body, site, cats, scraped_images=scraped_images or None)

    # CTA / e-commerce guardrail
    if not body.include_shopping_cart and not cart_features:
        prompt += (
            "\n\n=== IMPORTANT — INFORMATIONAL SITE ===\n"
            f"The website name is '{site_title}'. Use this EXACT name as the page <title>, "
            "navbar logo text (or logo image if provided), and hero heading.\n"
            "This is a purely informational website. Do NOT include any 'Order Now', "
            "'Buy Now', 'Add to Cart', 'Book Now', or e-commerce buttons anywhere.\n"
            "All CTAs should be informational: 'Learn More', 'Contact Us', 'Get in Touch', "
            "'View Gallery', 'Join Us', etc.\n"
        )
    else:
        prompt += (
            f"\n\nThe website name is '{site_title}'. Use this EXACT name as the page <title>, "
            "navbar logo, and hero heading.\n"
        )

    logger.debug(
        "build_prompt complete — %d chars, %d cart_features, cats=%s, nav_links=%s",
        len(prompt), len(cart_features), cats, nav_links,
    )
    return prompt, cart_features
