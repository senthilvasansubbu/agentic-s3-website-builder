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
    categories: Optional[List[str]] = None
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_prefix: Optional[str] = None
    social_links: Optional[Dict[str, Any]] = None
    website_id: Optional[str] = None
    include_shopping_cart: bool = False
    scraped_title: Optional[str] = None  # New: scraped business/site title
    nav_links: Optional[list] = None     # New: scraped nav links (list of str)


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
   links to  #shop  (same-page anchor) OR to  /pages/shop.html  if generating
   a multi-page site.
2. Create a dedicated Shop section (id="shop") with:
   - A search bar (input type="text" id="shopSearch") that filters the product
     grid in real time.
   - A product grid (CSS grid, 3-4 columns on desktop, 2 on tablet, 1 on mobile).
   - Each product card must show: product image, name, price (formatted with
     currency symbol), a short description snippet, category badge, and an
     "Add to Cart" button styled with the site accent colour.
3. Load products dynamically with this JavaScript (place before </body>):

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

4. Add this CSS for the product cards inside a <style> block:
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
            "Include a Blog section on the website with a dedicated /blog page. "
            "The blog page should display a grid of sample blog post cards, each with "
            "a title, short excerpt, author, date, reading time, and a 'Read More' link. "
            "Include at least 3 realistic sample blog posts relevant to the business niche. "
            "Add a 'Blog' link in the main navigation."
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


def _build_enrichment_section(
    body: BuildRequest,
    site: Dict[str, Any],
    cats: List[str],
    scraped_images: Optional[List[str]] = None,
) -> str:
    # Prefer scraped title (real business name) over the DB record name
    site_name = body.scraped_title or site.get("name") or site.get("title") or "Business"
    # Strip duplicate suffix e.g. "Foo – Foo" → "Foo"
    if " – " in site_name:
        parts = [p.strip() for p in site_name.split(" – ")]
        site_name = parts[0] if parts[0] == parts[-1] else site_name
    site_desc = site.get("description") or ""

    lines = [
        "\n\n=== CONTENT & STYLE ENRICHMENT ===",
        "You MUST use every piece of information below in the generated website.",
        f"Business Name: {site_name}",
    ]

    if site_desc:
        lines.append(
            f"Business Description:\n{site_desc}\n"
            "Incorporate this description into the hero tagline, about section, "
            "and category cards."
        )

    # Categories
    if cats:
        cat_list = "\n".join(f"  - {c}" for c in cats)
        lines.append(
            f"\nProduct/Service Categories (create a visual card for EACH):\n{cat_list}"
        )
        # Only suggest Unsplash if no real scraped images are available
        if not scraped_images:
            unsplash_hints = "\n".join(
                f"  - {c}: https://source.unsplash.com/featured/400x300/"
                f"?{c.lower().replace(' ', ',')}"
                for c in cats
            )
            lines.append(f"\nSuggested Unsplash images per category:\n{unsplash_hints}")

    # Location + Google Maps embed
    location = body.location or ""
    if location:
        map_query = urllib.parse.quote(location)
        lines.append(
            f"\nBusiness Location: {location}\n"
            f"Embed this Google Map in the Contact section:\n"
            f'<iframe src="https://maps.google.com/maps?q={map_query}&output=embed" '
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
        for platform in ("instagram", "facebook", "linkedin"):
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
        niche_kw = (cats[0] if cats else site_name).lower().replace(" ", ",")
        lines.append(
            f"\nHero background image: "
            f"https://source.unsplash.com/featured/1400x700/?{niche_kw}"
        )

    # Classification directive
    classification = site.get("classification", "generic") or "generic"
    if classification and classification != "generic":
        lines.append(
            f"\n=== AUDIENCE / CLASSIFICATION ===\n"
            f"SITE TYPE:        {classification.upper()}\n"
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
        f"You MUST use '{site_title}' as the HTML <title>, the navbar logo/text, and the hero heading.",
    ]
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
    priority_header = "\n".join(priority_lines) + "\n\n"

    # Base: user requirements + any pre-fetched research context
    prompt = priority_header + body.requirements + extra_context


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


    # Resolve categories
    cats = list(body.categories or [])
    if not cats:
        cats = _auto_extract_categories(body.requirements)


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
