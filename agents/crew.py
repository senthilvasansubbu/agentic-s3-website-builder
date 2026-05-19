import logging
import time
import os
import re
import hashlib
import urllib.parse
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


def _extract_expected_spec(user_requirements: str) -> dict:
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

  categories: list[str] = []
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
      # Skip obvious non-product/noise entries.
      if low in {".", "our solutions", "what's new", "what’s new"}:
        continue
      categories.append(s)

  # Keep order, remove duplicates.
  categories = list(dict.fromkeys(categories))[:8]

  nav_links: list[str] = []
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

  def _extract_numbered_urls(section_title: str) -> list[str]:
    block = re.search(
      rf"{re.escape(section_title)}\s*:\s*(.+?)(?:\n\n|\n===|$)",
      text,
      re.I | re.S,
    )
    urls: list[str] = []
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
    "media_videos": media_videos,
    "media_audios": media_audios,
    "media_embeds": media_embeds,
  }


def _inject_products_section(html_code: str, categories: list[str]) -> str:
  if not categories:
    return html_code

  cards = []
  for i, cat in enumerate(categories[:6], start=1):
    seed = re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-") or f"product-{i}"
    cards.append(
      """
    <article style=\"background:#fff;border-radius:14px;padding:16px;box-shadow:0 6px 18px rgba(0,0,0,.08)\">
    <img src=\"https://picsum.photos/seed/%s/480/320\" alt=\"%s\" loading=\"lazy\" style=\"width:100%%;height:180px;object-fit:cover;border-radius:10px\" />
    <h3 style=\"margin:12px 0 8px\">%s</h3>
    <p style=\"margin:0;color:#475569\">High-quality %s solutions for laboratory and diagnostic workflows.</p>
    </article>
""" % (seed, cat, cat, cat)
    )

  section = (
    "\n<section id=\"products\" aria-labelledby=\"products-heading\" style=\"padding:64px 5%%;background:#f8fafc\">\n"
    "  <div style=\"max-width:1200px;margin:0 auto\">\n"
    "    <h2 id=\"products-heading\" style=\"margin:0 0 10px\">Our Products</h2>\n"
    "    <p style=\"margin:0 0 22px;color:#475569\">Selected products and equipment from your referenced diagnostics catalog.</p>\n"
    "    <div style=\"display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px\">\n"
    + "".join(cards)
    + "\n    </div>\n  </div>\n</section>\n"
  )

  if re.search(r"id=[\"']products[\"']|id=[\"']shop[\"']", html_code, re.I):
    return html_code
  if "</main>" in html_code:
    return html_code.replace("</main>", section + "\n</main>", 1)
  if "</body>" in html_code:
    return html_code.replace("</body>", section + "\n</body>", 1)
  return html_code + section


def _enforce_generated_html_spec(html_code: str, user_requirements: str, website_id: str = "") -> str:
  """Force critical fields to match explicit build spec when LLM output drifts."""
  spec = _extract_expected_spec(user_requirements)
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
  media_videos = list(spec.get("media_videos") or [])
  media_audios = list(spec.get("media_audios") or [])
  media_embeds = list(spec.get("media_embeds") or [])

  fixed = html_code
  is_medical_domain = bool(re.search(
    r"\b(medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\s*equipment|reagent|reseller|distributor)\b",
    user_requirements or "",
    re.I,
  ))

  if name:
    # ── Collect all brand-name-like strings appearing in the generated HTML ──
    # These are any text-node strings inside common brand containers that differ
    # from the correct name. We replace them all to prevent any reference-site
    # brand leaking through to the final output.

    # 1. Replace ALL occurrences of text that looks like another brand name in
    #    logo/navbar/footer containers.  Strategy: find every unique visible
    #    text string in brand-sensitive elements and replace any that is NOT
    #    the correct name and appears more than once as a "brand-like" string.

    # First pass: targeted element patterns (navbar-brand, logo class, footer brand, etc.)
    brand_containers = re.findall(
      r'(<(?:a|span|div|p|h[1-6])[^>]*(?:logo|brand|site-?name|navbar-?brand|footer-?brand|company)[^>]*>)(.*?)(</(?:a|span|div|p|h[1-6])>)',
      fixed, re.I | re.S,
    )
    for open_tag, content, close_tag in brand_containers:
      stripped = re.sub(r"<[^>]+>", "", content).strip()
      if stripped and stripped.lower() != name.lower():
        new_content = content.replace(stripped, name)
        fixed = fixed.replace(open_tag + content + close_tag, open_tag + new_content + close_tag, 1)

    # Second pass: brute-force replace any remaining occurrence of the wrong brand
    # name in the HTML (exact match, case-insensitive).
    # We collect candidate wrong names from: first <title>, first <h1>, first .logo text.
    wrong_names: list[str] = []
    for pat in [
      r"<title>(.*?)</title>",
      r"<h1[^>]*>(.*?)</h1>",
      r'class=["\'][^"\']*logo[^"\']*["\'][^>]*>(.*?)</',
      r'class=["\'][^"\']*brand[^"\']*["\'][^>]*>(.*?)</',
    ]:
      m = re.search(pat, fixed, re.I | re.S)
      if m:
        candidate = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if candidate and candidate.lower() != name.lower() and len(candidate) > 2:
          wrong_names.append(candidate)

    for wrong in wrong_names:
      # Replace all occurrences (literal, case-insensitive)
      fixed = re.sub(re.escape(wrong), name, fixed, flags=re.I)

    # Secondary pass: detect orphaned brand-residue text nodes in body copy.
    # Strategy: build a set of "significant" words from all wrong_names, then
    # scan every text node between HTML tags. If a short node (≤6 words) has
    # ≥50% of its meaningful words drawn from residue words, replace the node.
    # Content-neutral — no specific org/religion/domain strings hardcoded.
    stop_words = {
      "the", "and", "for", "our", "your", "from", "with", "this", "that",
      "are", "was", "were", "has", "have", "been", "will", "would",
      "what", "when", "where", "which", "who", "how", "all", "any",
      "to", "in", "of", "a", "an", "is", "it", "at", "by", "on",
    }
    residue_words: set[str] = set()
    for wrong in wrong_names:
      for w in re.split(r"\s+", wrong):
        w_clean = re.sub(r"[^a-zA-Z]", "", w)
        if len(w_clean) > 3 and w_clean.lower() not in stop_words:
          residue_words.add(w_clean.lower())

    if residue_words:
      def _maybe_replace_text_node(m: re.Match) -> str:
        text = m.group(1)
        words = [w for w in re.split(r"\s+", text.strip()) if w]
        if not words or len(words) > 6:
          return m.group(0)
        meaningful = [
          re.sub(r"[^a-z]", "", w.lower()) for w in words
          if len(re.sub(r"[^a-z]", "", w)) > 1
          and re.sub(r"[^a-z]", "", w.lower()) not in stop_words
        ]
        if not meaningful:
          return m.group(0)
        residue_count = sum(1 for w in meaningful if w in residue_words)
        if residue_count >= max(1, len(meaningful) // 2):
          return m.group(0).replace(text, name, 1)
        return m.group(0)

      fixed = re.sub(r">([^<]{1,100})<", _maybe_replace_text_node, fixed)

    # Replace generic template placeholder text that an LLM might emit.
    # These are content-neutral placeholders only — no religion, domain, or
    # business-type specific strings.  Actual brand scrubbing is handled
    # structurally above via brand_containers + wrong_names detection.
    generic_placeholder_patterns = [
      r"Your Business Name",
      r"Your Company Name",
      r"Company Name",
      r"Site Name",
      r"Business Name",
      r"Organization Name",
    ]
    for pat in generic_placeholder_patterns:
      fixed = re.sub(pat, name, fixed, flags=re.I)

    # Force page title.
    if re.search(r"<title>.*?</title>", fixed, re.I | re.S):
      fixed = re.sub(r"<title>.*?</title>", f"<title>{name}</title>", fixed, count=1, flags=re.I | re.S)
    # Align first H1 to site name for brand consistency.
    if re.search(r"<h1[^>]*>.*?</h1>", fixed, re.I | re.S):
      fixed = re.sub(r"<h1[^>]*>.*?</h1>", f"<h1>{name}</h1>", fixed, count=1, flags=re.I | re.S)

    # Derive booking prefix from the actual site name (content-neutral).
    initials = "".join([w[0] for w in re.split(r"\s+", name) if w and w[0].isalnum()][:3]).upper() or "SITE"
    # Replace any residual ALL-CAPS 2-4 char prefix on booking IDs that doesn't
    # match the correct initials (catches template leftovers without naming them).
    fixed = re.sub(r"\b[A-Z]{2,4}-BK-", f"{initials}-BK-", fixed)

    # Ensure a logo image appears before brand text in the header/logo block.
    # Priority: explicit Business Logo URL; fallback to any existing image URL
    # in the generated HTML that looks like a logo asset.
    resolved_logo_src = logo_url.strip()
    if not resolved_logo_src:
      logo_match = re.search(r'<img[^>]+src=["\']([^"\']*logo[^"\']*)["\']', fixed, re.I)
      if logo_match:
        resolved_logo_src = (logo_match.group(1) or "").strip()

    if resolved_logo_src:
      def _ensure_logo_img(m: re.Match) -> str:
        open_tag, content, close_tag = m.group(1), m.group(2), m.group(3)
        if re.search(r"<img\b", content, re.I):
          return m.group(0)
        logo_img = f'<img src="{resolved_logo_src}" alt="{name} logo" loading="lazy" />'
        return open_tag + logo_img + content + close_tag

      fixed = re.sub(
        r'(<(?:a|div|span)[^>]*class=["\'][^"\']*logo[^"\']*["\'][^>]*>)(.*?)(</(?:a|div|span)>)',
        _ensure_logo_img,
        fixed,
        count=1,
        flags=re.I | re.S,
      )

  if email:
    # Replace ALL mailto: hrefs
    fixed = re.sub(r"mailto:[^\"'\s]+", f"mailto:{email}", fixed, flags=re.I)
    # Replace ALL visible email text nodes (text that looks like an email address)
    fixed = re.sub(r">[^<]*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^<]*<",
                   f">{email}<", fixed)

  if phone:
    tel_value = re.sub(r"[^+\d]", "", phone)
    if tel_value:
      # Replace ALL tel: hrefs
      fixed = re.sub(r"tel:[^\"'\s]+", f"tel:{tel_value}", fixed, flags=re.I)
      # Replace visible phone text only inside anchors that already point to tel:
      # (avoid corrupting unrelated numeric content like prices, years, IDs, etc.)
      fixed = re.sub(
        r'(<a[^>]*href=["\']tel:[^"\']+["\'][^>]*>)(.*?)(</a>)',
        lambda m: f"{m.group(1)}{phone}{m.group(3)}",
        fixed,
        flags=re.I | re.S,
      )

  # Enforce user-provided nav items (from manual chips/import) to prevent template overwrite.
  # Replace ALL top-nav menu lists (desktop + mobile variants), not just one list.
  # Feature placeholders are always appended when those feature flags are enabled.
  feature_nav_items: list[tuple[str, str]] = []
  if enable_blog:
    feature_nav_items.append(("Blog", "/blog"))
  if enable_shopping_cart:
    feature_nav_items.append(("Shop", "/shop"))
  if enable_livestream:
    feature_nav_items.append(("Live", "#livestream"))
  feature_anchor_by_label = {
    re.sub(r"[^a-z0-9]+", "", lbl.lower()): anchor
    for lbl, anchor in feature_nav_items
  }

  def _ensure_feature_nav_placeholders(existing_nav_items: list[str], id_set: set[str]) -> list[str]:
    merged = list(existing_nav_items or [])
    existing_norm = {re.sub(r"[^a-z0-9]+", "", n.lower()) for n in merged}
    for label, anchor in feature_nav_items:
      label_norm = re.sub(r"[^a-z0-9]+", "", label.lower())
      if label_norm in existing_norm:
        continue
      # Always append enabled feature placeholders; section anchors are enforced below.
      merged.append(label)
      existing_norm.add(label_norm)
    return merged

  if nav_links:
    id_set = {m.group(1).lower() for m in re.finditer(r'id=["\']([^"\']+)["\']', fixed, re.I)}
    nav_links = _ensure_feature_nav_placeholders(nav_links, id_set)

    def _to_anchor(label: str) -> str:
      norm = re.sub(r"[^a-z0-9]+", "", label.lower())
      if norm in feature_anchor_by_label:
        return feature_anchor_by_label[norm]
      slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "section"
      candidates = [
        slug,
        slug.replace("about-us", "about"),
        slug.replace("contact-us", "contact"),
        slug.replace("home", "home"),
      ]
      for c in candidates:
        if c in id_set:
          return f"#{c}"
      if "about" in slug and "about-us" in id_set:
        return "#about-us"
      if "contact" in slug and "contact" in id_set:
        return "#contact"
      return f"#{slug}"

    nav_items_html = "".join([f'<li><a href="{_to_anchor(item)}">{item}</a></li>' for item in nav_links])
    canonical_menu = f'<ul id="primary-navigation" class="nav-links">{nav_items_html}</ul>'
    menu_container_pattern = (
      r'<(?:ul|div)[^>]*(?:id=["\'](?:primary-navigation|primary-menu)["\']|'
      r'class=["\'][^"\']*(?:nav-links|mobile-menu|desktop-menu)[^"\']*["\'])[^>]*>.*?</(?:ul|div)>'
    )

    def _normalize_first_nav_block(m: re.Match) -> str:
      open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
      seen = {"kept": False}

      def _replace_menu(_m: re.Match) -> str:
        if not seen["kept"]:
          seen["kept"] = True
          return canonical_menu
        return ""

      inner = re.sub(menu_container_pattern, _replace_menu, inner, flags=re.I | re.S)
      if not seen["kept"]:
        inner += canonical_menu
      return open_tag + inner + close_tag

    fixed, nav_replaced = re.subn(
      r'(<nav[^>]*>)(.*?)(</nav>)',
      _normalize_first_nav_block,
      fixed,
      count=1,
      flags=re.I | re.S,
    )

    # If no nav exists at all, inject a canonical nav shell at the top of body.
    if nav_replaced == 0:
      nav_shell = (
        '<nav><div class="container">'
        + canonical_menu +
        '</div></nav>'
      )
      if "<body>" in fixed:
        fixed = fixed.replace("<body>", "<body>\n" + nav_shell, 1)
      else:
        fixed = nav_shell + fixed
  elif feature_nav_items:
    # No explicit nav_links were provided by user; still append feature placeholders
    # to existing nav menus for discoverability.
    nav_list_pattern = (
      r'(<(?:ul|div)[^>]*(?:id=["\'](?:primary-navigation|primary-menu)["\']|'
      r'class=["\'][^"\']*(?:nav-links|mobile-menu|desktop-menu)[^"\']*["\'])[^>]*>)(.*?)(</(?:ul|div)>)'
    )

    def _append_feature_items(m: re.Match) -> str:
      open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
      existing_hrefs = {h.lower() for h in re.findall(r'href=["\']([^"\']+)["\']', inner, re.I)}
      additions = []
      for label, anchor in feature_nav_items:
        if anchor.lower() in existing_hrefs:
          continue
        additions.append(f'<li><a href="{anchor}">{label}</a></li>')
      return open_tag + inner + "".join(additions) + close_tag

    fixed = re.sub(nav_list_pattern, _append_feature_items, fixed, flags=re.I | re.S)

  # Blog is a separate page entry point; remove any inline homepage blog section.
  if enable_blog:
    fixed = re.sub(
      r'\s*<section[^>]*id=["\']blog["\'][^>]*>.*?</section>\s*',
      '\n',
      fixed,
      flags=re.I | re.S,
    )

  # Live Stream placeholder (feature selected but operational integration may come later).
  livestream_section_present = bool(re.search(r'id=["\']livestream["\']', fixed, re.I))
  if enable_livestream and not livestream_section_present:
    livestream_section = (
      "\n<section id=\"livestream\" aria-labelledby=\"livestream-heading\" class=\"reveal\">\n"
      "  <h2 id=\"livestream-heading\">Live Streaming</h2>\n"
      "  <p class=\"subheading\">Live stream feature placeholder. This section is reserved for upcoming live sessions.</p>\n"
      "</section>\n"
    )
    if "</main>" in fixed:
      fixed = fixed.replace("</main>", livestream_section + "\n</main>", 1)
    elif "</body>" in fixed:
      fixed = fixed.replace("</body>", livestream_section + "\n</body>", 1)
    else:
      fixed += livestream_section

  # Deterministic media fallback: if scraped/reference media URLs are available
  # in the prompt but the LLM omitted playable media, enrich an existing media
  # section or inject a reusable section.
  current_video_count = len(re.findall(r"<video\b", fixed, re.I))
  current_audio_count = len(re.findall(r"<audio\b", fixed, re.I))
  current_embed_count = len(re.findall(r"<iframe[^>]+src=[\"\'][^\"\']*(youtube|youtu\.be|vimeo|soundcloud)[^\"\']*[\"\']", fixed, re.I))
  has_media_section = bool(re.search(r'id=["\'](?:media|multimedia|video|audio)["\']', fixed, re.I))
  missing_video = len(media_videos) > current_video_count
  missing_audio = len(media_audios) > current_audio_count
  missing_embed = len(media_embeds) > current_embed_count
  missing_any_media = (missing_video or missing_audio or missing_embed)
  if missing_any_media:
    def _remaining_unique(urls: list[str], current_count: int) -> list[str]:
      deduped: list[str] = []
      seen: set[str] = set()
      for raw in urls:
        u = (raw or "").strip()
        if not u:
          continue
        low = u.lower()
        if low in seen:
          continue
        seen.add(low)
        deduped.append(u)
      if current_count >= len(deduped):
        return []
      return deduped[current_count:]

    inject_embeds = _remaining_unique(media_embeds, current_embed_count) if missing_embed else []
    inject_videos = _remaining_unique(media_videos, current_video_count) if missing_video else []
    inject_audios = _remaining_unique(media_audios, current_audio_count) if missing_audio else []

    media_blocks: list[str] = []

    if inject_embeds:
      media_blocks += [
        "  <div class=\"media-group media-group-embed\" style=\"margin:16px 0\">",
        "    <div style=\"display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px\">",
        "      <h3 style=\"margin:0\">Embedded Media</h3>",
      ]
      if len(inject_embeds) > 1:
        media_blocks += [
          "      <label style=\"display:flex;align-items:center;gap:8px;font-size:0.95rem\">",
          "        <span>Choose:</span>",
          "        <select aria-label=\"Choose embedded media\" onchange=\"var t=this.closest('.media-group').querySelector('#'+this.value);if(t){t.scrollIntoView({behavior:'smooth',inline:'start',block:'nearest'});}\">",
        ]
        for idx in range(len(inject_embeds)):
          item_id = f"media-embed-{current_embed_count + idx + 1}"
          media_blocks.append(f"          <option value=\"{item_id}\">Embed {idx + 1}</option>")
        media_blocks += [
          "        </select>",
          "      </label>",
        ]
      media_blocks += [
        "    </div>",
        "    <div class=\"media-scroll\" style=\"display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px\">",
      ]
      for idx, embed_src in enumerate(inject_embeds, start=1):
        embed_id = f"media-embed-{current_embed_count + idx}"
        media_blocks += [
          f"      <article id=\"{embed_id}\" class=\"media-item\" style=\"flex:0 0 min(560px,100%);scroll-snap-align:start\">",
          f"        <iframe src=\"{embed_src}\" title=\"Embedded media {idx}\" loading=\"lazy\" allowfullscreen style=\"width:100%;min-height:360px;border:0;border-radius:12px\"></iframe>",
          "      </article>",
        ]
      media_blocks += [
        "    </div>",
        "  </div>",
      ]

    if inject_videos:
      media_blocks += [
        "  <div class=\"media-group media-group-video\" style=\"margin:16px 0\">",
        "    <div style=\"display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px\">",
        "      <h3 style=\"margin:0\">Video Playlist</h3>",
      ]
      if len(inject_videos) > 1:
        media_blocks += [
          "      <label style=\"display:flex;align-items:center;gap:8px;font-size:0.95rem\">",
          "        <span>Choose:</span>",
          "        <select aria-label=\"Choose a video\" onchange=\"var t=this.closest('.media-group').querySelector('#'+this.value);if(t){t.scrollIntoView({behavior:'smooth',inline:'start',block:'nearest'});}\">",
        ]
        for idx in range(len(inject_videos)):
          item_id = f"media-video-{current_video_count + idx + 1}"
          media_blocks.append(f"          <option value=\"{item_id}\">Video {idx + 1}</option>")
        media_blocks += [
          "        </select>",
          "      </label>",
        ]
      media_blocks += [
        "    </div>",
        "    <div class=\"media-scroll\" style=\"display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px\">",
      ]
      for idx, video_src in enumerate(inject_videos, start=1):
        video_id = f"media-video-{current_video_count + idx}"
        media_blocks += [
          f"      <article id=\"{video_id}\" class=\"media-item\" style=\"flex:0 0 min(560px,100%);scroll-snap-align:start\">",
          "        <video controls preload=\"metadata\" style=\"width:100%;border-radius:12px\">",
          f"          <source src=\"{video_src}\">",
          "          Your browser does not support the video tag.",
          "        </video>",
          "      </article>",
        ]
      media_blocks += [
        "    </div>",
        "  </div>",
      ]

    if inject_audios:
      media_blocks += [
        "  <div class=\"media-group media-group-audio\" style=\"margin:16px 0\">",
        "    <div style=\"display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px\">",
        "      <h3 style=\"margin:0\">Audio Playlist</h3>",
      ]
      if len(inject_audios) > 1:
        media_blocks += [
          "      <label style=\"display:flex;align-items:center;gap:8px;font-size:0.95rem\">",
          "        <span>Choose:</span>",
          "        <select aria-label=\"Choose an audio track\" onchange=\"var t=this.closest('.media-group').querySelector('#'+this.value);if(t){t.scrollIntoView({behavior:'smooth',inline:'start',block:'nearest'});}\">",
        ]
        for idx in range(len(inject_audios)):
          item_id = f"media-audio-{current_audio_count + idx + 1}"
          media_blocks.append(f"          <option value=\"{item_id}\">Audio {idx + 1}</option>")
        media_blocks += [
          "        </select>",
          "      </label>",
        ]
      media_blocks += [
        "    </div>",
        "    <div class=\"media-scroll\" style=\"display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px\">",
      ]
      for idx, audio_src in enumerate(inject_audios, start=1):
        audio_id = f"media-audio-{current_audio_count + idx}"
        media_blocks += [
          f"      <article id=\"{audio_id}\" class=\"media-item\" style=\"flex:0 0 min(460px,100%);scroll-snap-align:start;padding:14px;border:1px solid rgba(0,0,0,.08);border-radius:12px\">",
          f"        <h4 style=\"margin:0 0 10px\">Track {idx}</h4>",
          "        <audio controls preload=\"metadata\" style=\"width:100%\">",
          f"          <source src=\"{audio_src}\">",
          "          Your browser does not support the audio tag.",
          "        </audio>",
          "      </article>",
        ]
      media_blocks += [
        "    </div>",
        "  </div>",
      ]

    if media_blocks:
      media_payload = "\n" + "\n".join(media_blocks) + "\n"
      if has_media_section:
        media_section_pattern = re.compile(
          r'(<section[^>]*id=["\'](?:media|multimedia|video|audio)["\'][^>]*>)(.*?)(</section>)',
          re.I | re.S,
        )
        m = media_section_pattern.search(fixed)
        if m:
          new_section = m.group(1) + m.group(2) + media_payload + m.group(3)
          fixed = fixed[:m.start()] + new_section + fixed[m.end():]
        else:
          has_media_section = False

      if not has_media_section:
        parts: list[str] = [
          "\n<section id=\"media\" aria-labelledby=\"media-heading\" class=\"reveal\">",
          "  <h2 id=\"media-heading\">Media Highlights</h2>",
          "  <p class=\"subheading\">Curated media from your reference links.</p>",
          *media_blocks,
          "</section>\n",
        ]
        media_section = "\n".join(parts)
        if "</main>" in fixed:
          fixed = fixed.replace("</main>", media_section + "\n</main>", 1)
        elif "</body>" in fixed:
          fixed = fixed.replace("</body>", media_section + "\n</body>", 1)
        else:
          fixed += media_section

  # Shop/cart is a separate page entry point; remove any inline homepage shop section.
  if enable_shopping_cart:
    fixed = re.sub(
      r'\s*<section[^>]*id=["\']shop["\'][^>]*>.*?</section>\s*',
      '\n',
      fixed,
      flags=re.I | re.S,
    )

  # ── Layout guardrail for top section alignment (navbar + hero) ────────────
  # Some LLM outputs omit robust nav/hero layout rules, causing first section
  # misalignment on desktop/mobile. Inject a minimal corrective style block.
  guardrail_css = (
    "\n<style id=\"agentic-layout-guardrail\">\n"
    "nav{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:nowrap;padding:8px 0;}\n"
    "nav>.container,nav .container,.navbar-container{max-width:1200px;width:100%;margin:0 auto;padding:0 20px;display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:nowrap;}\n"
    ".logo{display:flex;align-items:center;gap:10px;min-width:0;max-width:40%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-right:auto;text-align:left;flex:0 1 auto;}\n"
    ".logo img{height:42px;max-width:42px;width:auto;object-fit:contain;flex:0 0 auto;}\n"
    ".logo span{display:inline-block;min-width:0;max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.15;}\n"
    "#primary-menu,#primary-navigation,.nav-links,.desktop-menu{display:flex;align-items:center;gap:clamp(10px,1.2vw,18px);list-style:none;margin:0;padding:0;justify-content:flex-end;min-width:0;flex-wrap:nowrap;margin-left:auto;text-align:right;}\n"
    ".mobile-menu{display:none;list-style:none;margin:0;padding:0;}\n"
    "#primary-menu li,#primary-navigation li,.nav-links li,.desktop-menu li,.mobile-menu li{margin:0;}\n"
    "#primary-menu a,#primary-navigation a,.nav-links a,.desktop-menu a,.mobile-menu a{font-size:.95rem;line-height:1.2;white-space:nowrap;}\n"
    ".nav-desktop{margin-left:auto;min-width:0;}\n"
    ".nav-btn,.nav-cta{white-space:nowrap;flex:0 0 auto;margin-left:14px;}\n"
    ".newsletter form,.newsletter-form,#newsletter form,.footer-newsletter,footer form[aria-label*='Newsletter'],footer form[aria-label*='newsletter']{display:flex;align-items:stretch;gap:8px;flex-wrap:nowrap;}\n"
    ".newsletter input[type='email'],.newsletter-form input[type='email'],#newsletter input[type='email'],.footer-newsletter input,footer form[aria-label*='Newsletter'] input[type='email'],footer form[aria-label*='newsletter'] input[type='email']{height:42px;min-width:0;flex:1;border:1px solid color-mix(in srgb,var(--accent) 35%,#ffffff);background:color-mix(in srgb,var(--bg) 92%,#ffffff);color:var(--text);padding:0 12px;}\n"
    ".newsletter button,.newsletter-form button,#newsletter button,.footer-newsletter button,footer form[aria-label*='Newsletter'] button,footer form[aria-label*='newsletter'] button{height:42px;white-space:nowrap;min-width:112px;padding:0 16px;flex:0 0 auto;border:1px solid transparent;background:var(--accent);color:var(--bg);font-weight:700;}\n"
    "button,.btn,input[type='submit'],input[type='button'],a[role='button']{transition:transform .16s ease,box-shadow .16s ease,background-color .16s ease,color .16s ease;border-radius:10px;}\n"
    "button:hover,.btn:hover,input[type='submit']:hover,input[type='button']:hover,a[role='button']:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(0,0,0,.16);}\n"
    "button:active,.btn:active,input[type='submit']:active,input[type='button']:active,a[role='button']:active{transform:translateY(0);box-shadow:0 2px 8px rgba(0,0,0,.18);}\n"
    "button:focus-visible,.btn:focus-visible,input[type='submit']:focus-visible,input[type='button']:focus-visible,a[role='button']:focus-visible,#primary-menu a:focus-visible,#primary-navigation a:focus-visible,.nav-links a:focus-visible,.desktop-menu a:focus-visible,.mobile-menu a:focus-visible{outline:2px solid currentColor;outline-offset:2px;box-shadow:0 0 0 3px rgba(255,255,255,.22);}\n"
    ".social-icons,.social-links{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;}\n"
    ".social-icons a,.social-links a{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:34px;padding:0 10px;border:1px solid rgba(255,255,255,.25);border-radius:999px;font-size:.78rem;font-weight:700;line-height:1;}\n"
    "footer .footer-container,footer .container-footer{max-width:1200px;width:min(100%,1200px);margin:0 auto;display:grid !important;grid-template-columns:repeat(4,minmax(0,1fr));column-gap:24px;row-gap:14px;align-items:start;}\n"
    "footer .footer-col{min-width:0;margin:0 !important;padding:0 !important;}\n"
    "footer .footer-col h4{margin:0 0 10px;}\n"
    "footer .footer-col ul{list-style:none;margin:0;padding:0;display:grid;gap:8px;}\n"
    "footer .footer-col li{margin:0;}\n"
    "footer .footer-col a{display:inline-flex;align-items:center;line-height:1.35;}\n"
    "footer .newsletter,#newsletter{min-width:0;grid-column:span 2;}\n"
    "footer .newsletter p{margin:0 0 10px;}\n"
    "footer .copyright,[class*='copyright']{text-align:center;padding-top:14px;}\n"
    ".footer-copyright,#footer-copyright{text-align:center;}\n"
    ".hero,header.hero{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:96px 20px 64px;}\n"
    "@media (max-width: 1200px){nav>.container,nav .container,.navbar-container{padding:0 16px;gap:12px;}.logo{max-width:34%;}#primary-menu,#primary-navigation,.nav-links,.desktop-menu{gap:10px;}#primary-menu a,#primary-navigation a,.nav-links a,.desktop-menu a{font-size:.9rem;}.nav-btn,.nav-cta{margin-left:10px;padding:.55rem .85rem;}}\n"
    "@media (max-width: 1024px){.hamburger{display:inline-flex;align-items:center;justify-content:center;}#primary-menu,#primary-navigation,.nav-links,.desktop-menu{display:none;}.mobile-menu{display:none;width:100%;flex-direction:column;align-items:flex-start;gap:12px;margin:10px 0 0 0;text-align:left;}#primary-menu.open,#primary-menu.active,#primary-menu.show,#primary-navigation.open,#primary-navigation.active,#primary-navigation.show,.nav-links.open,.nav-links.active,.nav-links.show,.desktop-menu.open,.desktop-menu.active,.desktop-menu.show,.mobile-menu.open,.mobile-menu.active,.mobile-menu.show{display:flex;}nav>.container,nav .container,.navbar-container{flex-wrap:wrap;}.logo{max-width:100%;}.nav-btn,.nav-cta{margin-left:auto;}footer .footer-container,footer .container-footer{grid-template-columns:repeat(2,minmax(0,1fr));}footer .newsletter,#newsletter{grid-column:1 / -1;}.hero,header.hero{padding-top:84px;}}\n"
    "@media (max-width: 640px){nav>.container,nav .container,.navbar-container{padding:0 12px;gap:10px;}.logo{max-width:calc(100% - 56px);} .logo img{height:34px;max-width:34px;} .logo span{font-size:clamp(1rem,4.4vw,1.25rem);} .mobile-menu a,#primary-menu a,#primary-navigation a,.nav-links a,.desktop-menu a{font-size:1rem;} .nav-btn,.nav-cta{width:100%;margin:8px 0 0 0;text-align:center;} footer .footer-container,footer .container-footer{grid-template-columns:1fr;gap:16px;} footer .newsletter,#newsletter{grid-column:auto;} .newsletter form,.newsletter-form,#newsletter form,.footer-newsletter{flex-wrap:wrap;} .newsletter input[type='email'],.newsletter-form input[type='email'],#newsletter input[type='email'],.footer-newsletter input,.newsletter button,.newsletter-form button,#newsletter button,.footer-newsletter button{width:100%;min-width:0;} .hero,header.hero{padding:80px 16px 56px;}}\n"
    "</style>\n"
  )
  if "agentic-layout-guardrail" not in fixed:
    if "</head>" in fixed:
      fixed = fixed.replace("</head>", guardrail_css + "</head>", 1)
    else:
      fixed = guardrail_css + fixed

  if location:
    location_clean = re.sub(r"\s+", " ", location).strip(" ,;")
    # Split on newlines/semicolons in case multiple addresses were concatenated
    location_lines = [line.strip() for line in re.split(r"[\n;]", location_clean) if line.strip()]
    # Use only the first address (user-entered), ignore any fallback/template duplicates
    location_clean = location_lines[0] if location_lines else location_clean
    map_query = urllib.parse.quote_plus(location_clean)
    canonical_map_src = f"https://www.google.com/maps?q={map_query}&output=embed"

    if re.search(r"<address[^>]*>.*?</address>", fixed, re.I | re.S):
      # Overwrite first free-text line inside every <address> block
      fixed = re.sub(
        r"(<address[^>]*>\s*)([^<\n]+)",
        r"\1" + location_clean,
        fixed,
        flags=re.I,
      )
    # Also replace generic placeholder address text patterns throughout
    fixed = re.sub(
      r">\s*\d+[^<]{5,50}(?:Street|St|Ave|Road|Rd|Lane|Ln|Blvd|Drive|Dr|Way)[^<]*<",
      f">{location_clean}<", fixed, flags=re.I,
    )

    # Remove duplicate address lines (placeholder/fallback addresses on separate lines)
    # This handles cases where both user location and template defaults appear
    if location_clean:
      address_pattern = r'(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z]{2}|\s+[A-Z]{2})?\s*\d{5}|[0-9]{5,6}|USA|India|UK)'
      lines = fixed.split('<br')
      if len(lines) > 1:
        # Keep the line containing user's location, remove other address-like lines
        cleaned_lines = []
        primary_found = False
        for i, line in enumerate(lines):
          if location_clean.lower() in line.lower():
            cleaned_lines.append(line)
            primary_found = True
          elif primary_found and re.search(address_pattern, line, re.I) and '/' not in line:
            # Skip this line if it's an address pattern and we already have the primary
            continue
          else:
            cleaned_lines.append(line)
        fixed = '<br'.join(cleaned_lines)
      
      # Also handle newline-separated duplicate addresses
      lines = fixed.split('\n')
      cleaned = []
      addr_seen = False
      for line in lines:
        if location_clean.lower() in line.lower():
          cleaned.append(line)
          addr_seen = True
        elif addr_seen and re.search(r'[0-9]{5,6}.*(?:USA|India|UK|[A-Z]{2})|[A-Z][a-z]+.*[A-Z]{2}.*[0-9]{5}', line):
          # Skip duplicate address line
          continue
        else:
          cleaned.append(line)
      fixed = '\n'.join(cleaned)

    # Normalize existing Google Maps iframe sources to a stable embed URL.
    fixed = re.sub(
      r'(<iframe[^>]*src=["\'])(https?://(?:www\.)?(?:maps\.google\.com|google\.com/maps)[^"\']*)(["\'][^>]*>)',
      r"\1" + canonical_map_src + r"\3",
      fixed,
      flags=re.I,
    )

    # Ensure at least one map iframe exists even if model output omitted it.
    has_map_iframe = bool(re.search(
      r'<iframe[^>]*src=["\'][^"\']*(?:maps\.google\.com|google\.com/maps)[^"\']*["\'][^>]*>',
      fixed,
      flags=re.I,
    ))
    if not has_map_iframe:
      map_block = (
        f'<div class="map-container" style="margin-top:16px">'
        f'<iframe src="{canonical_map_src}" allowfullscreen loading="lazy" '
        f'title="Our Location" style="width:100%;height:360px;border:0;border-radius:12px"></iframe>'
        f'</div>'
      )
      contact_match = re.search(r'(<section[^>]*id=["\']contact["\'][^>]*>)(.*?)(</section>)', fixed, re.I | re.S)
      if contact_match:
        injected = contact_match.group(1) + contact_match.group(2) + "\n" + map_block + "\n" + contact_match.group(3)
        fixed = fixed[:contact_match.start()] + injected + fixed[contact_match.end():]
      elif "</body>" in fixed:
        fixed = fixed.replace("</body>", map_block + "\n</body>", 1)
      else:
        fixed += "\n" + map_block

  # ── Medical domain relevance guardrail ─────────────────────────────────────
  # For medical/diagnostic reseller briefs, rewrite common off-domain drift
  # terms from enterprise-tech language to relevant medical catalog language.
  if is_medical_domain:
    replacements = [
      (r"Enterprise Solutions Group", name or "Medical Equipment Solutions"),
      (r"Cloud Services", "Diagnostic Equipment Supply"),
      (r"Custom Software Development", "Laboratory Instruments & Devices"),
      (r"Cybersecurity Solutions", "Reagents & Consumables"),
      (r"Data Analytics\s*&\s*BI", "After-Sales Service & Support"),
      (r"Explore Our Solutions", "Explore Our Product Range"),
      (r"technology solutions", "medical equipment solutions"),
      (r"enterprise technology", "medical diagnostics and laboratory solutions"),
    ]
    for old, new in replacements:
      fixed = re.sub(old, new, fixed, flags=re.I)

    fixed = re.sub(
      r"<p>\s*Scalable, secure, and innovative[^<]*</p>",
      "<p>Trusted reseller of quality medical and diagnostic products for hospitals, clinics, and laboratories.</p>",
      fixed,
      flags=re.I,
    )

    fixed = re.sub(
      r'(<meta\s+name=["\']description["\']\s+content=["\'])([^"\']*)(["\'])',
      r"\1" + f"{name or 'Our company'} supplies reliable medical and diagnostic equipment, reagents, and lab products with expert support." + r"\3",
      fixed,
      count=1,
      flags=re.I,
    )

    # Replace generic tech service options with medical-specific ones in booking form dropdowns
    tech_services = [
      "Cloud Integration Services", "Enterprise Software Development", "IT Consulting & Strategy",
      "Cloud Services", "Custom Software Development", "Cybersecurity Solutions",
      "Data Analytics & BI", "IT Support", "Technology Solutions", "Enterprise Solutions",
    ]
    medical_services = [
      "Equipment Consultation", "Product Demonstration", "Installation & Training",
      "Maintenance & Support", "Replacement Parts", "Reagent Supply", "Warranty & Service",
    ]
    for tech_svc in tech_services:
      if tech_svc.lower() in fixed.lower():
        # Replace with corresponding medical service (cycle through list)
        med_idx = tech_services.index(tech_svc) % len(medical_services)
        fixed = re.sub(
          re.escape(tech_svc),
          medical_services[med_idx],
          fixed,
          flags=re.I,
        )

  # ── Mobile menu behavior guardrail ─────────────────────────────────────────
  menu_script = (
    '\n<script id="agentic-menu-guardrail">\n'
    '(function(){\n'
    '  var btn=document.querySelector(".hamburger,[aria-controls=\"primary-menu\"]");\n'
    '  var menu=null;\n'
    '  if(btn){\n'
    '    var cid=btn.getAttribute("aria-controls");\n'
    '    if(cid){menu=document.getElementById(cid);}\n'
    '  }\n'
    '  if(!menu){menu=document.getElementById("primary-menu")||document.querySelector(".nav-links");}\n'
    '  if(!btn||!menu){return;}\n'
    '  function closeMenu(){menu.classList.remove("open","active","show");btn.setAttribute("aria-expanded","false");}\n'
    '  function openMenu(){menu.classList.add("open");btn.setAttribute("aria-expanded","true");}\n'
    '  btn.addEventListener("click",function(e){e.preventDefault();var ex=btn.getAttribute("aria-expanded")==="true";if(ex){closeMenu();}else{openMenu();}});\n'
    '  menu.querySelectorAll("a").forEach(function(a){a.addEventListener("click",closeMenu);});\n'
    '  document.addEventListener("click",function(e){if(!menu.contains(e.target)&&!btn.contains(e.target)){closeMenu();}});\n'
    '  window.addEventListener("resize",function(){if(window.innerWidth>900){closeMenu();}});\n'
    '})();\n'
    '</script>\n'
  )
  if "agentic-menu-guardrail" not in fixed:
    if "</body>" in fixed:
      fixed = fixed.replace("</body>", menu_script + "</body>", 1)
    else:
      fixed += menu_script

  # ── Wire contact/consultation forms to the backend feedback endpoint ───────
  if website_id:
    # Find any <form> that submits to "#" or has no valid action, and inject
    # a JS handler that POSTs to the feedback API instead of a page reload.
    form_script = (
      f'\n<script>\n'
      f'(function(){{\n'
      f'  document.querySelectorAll(\'form[action="#"],form:not([action]),form[action=""]\').forEach(function(f){{\n'
      f'    f.addEventListener("submit",function(e){{\n'
      f'      e.preventDefault();\n'
      f'      var data={{}};\n'
      f'      new FormData(f).forEach(function(v,k){{data[k]=v;}});\n'
      f'      fetch("/api/websites/{website_id}/feedback",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{message:JSON.stringify(data),rating:5}})}});\n'
      f'      f.innerHTML=\'<p style="padding:24px;text-align:center;color:#16a34a;font-weight:600;">✅ Thank you! Your message has been received. We will be in touch soon.</p>\';\n'
      f'    }});\n'
      f'  }});\n'
      f'}})();\n'
      f'</script>\n'
    )
    if "</body>" in fixed:
      fixed = fixed.replace("</body>", form_script + "</body>", 1)
    else:
      fixed += form_script

  # Normalize social links to stable text-icon pills and include LinkedIn.
  fixed = re.sub(
    r'(<(?:nav|div)[^>]*class=["\'][^"\']*(?:social-icons|social-links)[^"\']*["\'][^>]*>)(.*?)(</(?:nav|div)>)',
    (
      r'\1'
      '<a href="https://twitter.com" target="_blank" rel="noopener" aria-label="Twitter" title="Twitter">TW</a>'
      '<a href="https://linkedin.com" target="_blank" rel="noopener" aria-label="LinkedIn" title="LinkedIn">IN</a>'
      '<a href="https://youtube.com" target="_blank" rel="noopener" aria-label="YouTube" title="YouTube">YT</a>'
      '<a href="https://facebook.com" target="_blank" rel="noopener" aria-label="Facebook" title="Facebook">FB</a>'
      r'\3'
    ),
    fixed,
    count=1,
    flags=re.I | re.S,
  )

  if name:
    # Keep copyright deterministic for the selected business name.
    fixed = re.sub(
      r'(<p[^>]*id=["\']footer-copyright["\'][^>]*>).*?(</p>)',
      r'\1&copy; ' + name + ' <span id="copyright-year"></span>. All rights reserved.\2',
      fixed,
      flags=re.I | re.S,
    )
    fixed = re.sub(
      r'(<span[^>]*>)\s*[©&copy;].*?All rights reserved\.?\s*(</span>)',
      r'\1&copy; <span id="yr"></span> ' + name + '. All rights reserved.\2',
      fixed,
      flags=re.I | re.S,
    )
    fixed = re.sub(
      r'(<div[^>]*class=["\'][^"\']*copyright[^"\']*["\'][^>]*>)\s*[©&copy;].*?All rights reserved\.?\s*(</div>)',
      r'\1&copy; <span id="yr"></span> ' + name + '. All rights reserved.\2',
      fixed,
      flags=re.I | re.S,
    )
    fixed = re.sub(
      r'(<(?:div|p|span)[^>]*(?:id=["\']copyright["\']|class=["\'][^"\']*copyright[^"\']*["\'])[^>]*>)\s*.*?All rights reserved\.?\s*(</(?:div|p|span)>)',
      r'\1&copy; <span id="yr"></span> ' + name + '. All rights reserved.\2',
      fixed,
      flags=re.I | re.S,
    )
    fixed = re.sub(
      r'[©&copy;]\s*(?:\d{4}|<span[^>]*>\s*\d{4}\s*</span>)?\s*[^<]{0,140}All rights reserved\.?',
      '&copy; <span id="yr"></span> ' + name + '. All rights reserved.',
      fixed,
      count=1,
      flags=re.I,
    )

    if not re.search(r'id=["\']agentic-year-guardrail["\']', fixed, re.I):
      year_script = (
        '\n<script id="agentic-year-guardrail">(function(){'
        'var y=(new Date()).getFullYear();'
        'var a=document.getElementById("copyright-year"); if(a){a.textContent=String(y);} '
        'var b=document.getElementById("yr"); if(b){b.textContent=String(y);} '
        '})();</script>\n'
      )
      if "</body>" in fixed:
        fixed = fixed.replace("</body>", year_script + "</body>", 1)
      else:
        fixed += year_script

  # ── Remove empty white boxes (divs/sections/articles with no real content) ─
  # A "ghost" element: block element whose inner text (stripped of tags) is
  # empty or only whitespace, and contains no <img> tag.
  def _has_real_content(inner: str) -> bool:
    has_img = bool(re.search(r"<img\b", inner, re.I))
    text = re.sub(r"<[^>]+>", "", inner).strip()
    return bool(text) or has_img

  # Iterate removing leaf-level empty block elements (cards, articles, sections)
  for tag in ("article", "div", "section"):
    pattern = rf"<{tag}(\s[^>]*)?>(\s*)</{tag}>"
    fixed = re.sub(pattern, "", fixed, flags=re.I | re.S)

  # Remove empty card/box containers (single pass for nested empties)
  fixed = re.sub(
    r'<(?:div|article|section)[^>]*class=["\'][^"\']*(?:card|box|tile|panel)[^"\']*["\'][^>]*>\s*</(?:div|article|section)>',
    "", fixed, flags=re.I | re.S,
  )

  # Ensure product list exists when categories are present in spec.
  fixed = _inject_products_section(fixed, categories)
  return fixed


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


def _write_output_target_scaffold(site_dir: str, output_target: str, html_code: str) -> None:
    """Create target-specific project scaffolds alongside generated HTML."""
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
            "package.json": """{
  \"name\": \"agentic-site-react\",
  \"private\": true,
  \"version\": \"0.1.0\",
  \"type\": \"module\",
  \"scripts\": {
    \"dev\": \"vite\",
    \"build\": \"vite build\",
    \"preview\": \"vite preview\"
  },
  \"dependencies\": {
    \"react\": \"^18.3.1\",
    \"react-dom\": \"^18.3.1\"
  },
  \"devDependencies\": {
    \"vite\": \"^5.4.8\"
  }
}
""",
            "index.html": """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Agentic React Output</title>
  </head>
  <body>
    <div id=\"root\"></div>
    <script type=\"module\" src=\"/src/main.jsx\"></script>
  </body>
</html>
""",
            "src/main.jsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
""",
            "src/App.jsx": """export default function App() {
  return (
    <main style={{padding: '24px', fontFamily: 'Arial, sans-serif'}}>
      <h1>Agentic Build Output (React)</h1>
      <p>""" + staging_note + """ Edit the staged index.html for page-level customization.</p>
    </main>
  );
}
""",
        }
    elif target == "vue":
        files = {
            "package.json": """{
  \"name\": \"agentic-site-vue\",
  \"private\": true,
  \"version\": \"0.1.0\",
  \"type\": \"module\",
  \"scripts\": {
    \"dev\": \"vite\",
    \"build\": \"vite build\",
    \"preview\": \"vite preview\"
  },
  \"dependencies\": {
    \"vue\": \"^3.5.11\"
  },
  \"devDependencies\": {
    \"@vitejs/plugin-vue\": \"^5.1.4\",
    \"vite\": \"^5.4.8\"
  }
}
""",
            "index.html": """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Agentic Vue Output</title>
  </head>
  <body>
    <div id=\"app\"></div>
    <script type=\"module\" src=\"/src/main.js\"></script>
  </body>
</html>
""",
            "vite.config.js": """import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({ plugins: [vue()] });
""",
            "src/main.js": """import { createApp } from 'vue';
import App from './App.vue';

createApp(App).mount('#app');
""",
            "src/App.vue": """<template>
  <main style=\"padding:24px;font-family:Arial,sans-serif\">
    <h1>Agentic Build Output (Vue)</h1>
    <p>""" + staging_note + """ Edit the staged index.html for page-level customization.</p>
  </main>
</template>
""",
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


def _sync_legacy_entrypoint(site_dir: str, html_code: str) -> None:
    """Mirror legacy output to parent staging folder for consistent preview entrypoint."""
    if os.path.basename(site_dir).lower() != "legacy":
        return
    parent = os.path.dirname(site_dir)
    os.makedirs(parent, exist_ok=True)

    mirrored = re.sub(
      r'((?:src|href)=["\'])assets/',
      r'\1legacy/assets/',
      html_code,
      flags=re.I,
    )
    with open(os.path.join(parent, "index.html"), "w", encoding="utf-8") as f:
        f.write(mirrored)


def _generate_static_fallback(user_requirements: str, theme_key: str = "modern") -> str:
    """Generate a content-rich static HTML website when no API key is available."""
    t = THEMES.get(theme_key, THEMES["modern"])
    import re

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
    # Also honor explicit non-cart directives from requirements_analyst.
    if "=== NON-CART CATALOG DIRECTIVE ===" in user_requirements:
      is_informational = True
    if re.search(r"Do NOT include Add to Cart|no 'Buy Now'|NO 'Buy Now'", user_requirements, re.I):
      is_informational = True

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

    # Location
    loc_match = re.search(r'Business Location:\s*(.+)', user_requirements)
    location = loc_match.group(1).strip() if loc_match else "123 Main Street, New York, NY 10001, USA"
    location = re.sub(r"\s+", " ", location).strip(" ,;")
    # If multiple addresses were concatenated (separated by newline/semicolon), use only the first
    location_lines = [line.strip() for line in re.split(r"[\n;]", location) if line.strip()]
    location = location_lines[0] if location_lines else location
    map_query = urllib.parse.quote_plus(location)

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

    booking_section_html = ""
    if not is_informational:
        booking_section_html = f"""
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
"""

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
      <a href="{'#contact' if is_informational else '#booking'}" class="btn btn-light" style="background:var(--accent);color:#fff;margin-top:8px">{'Contact Sales' if is_informational else 'Order Today'}</a>
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

{booking_section_html}

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
        <iframe src="https://www.google.com/maps?q={map_query}&output=embed" allowfullscreen loading="lazy" title="Our Location"></iframe>
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
        {'<li><a href="#booking">Book an Order</a></li>' if not is_informational else ''}
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


def create_website_crew(
  theme_key: str = "modern",
  classification: str = "generic",
  classification_label: str = "Generic",
  classification_group: str = "general",
  build_mode: str = "agentic_only",
  output_target: str = "legacy",
):
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
    classification_note = (
      f"AUDIENCE/CLASSIFICATION KEY: {classification.upper()}\n"
      f"AUDIENCE/CLASSIFICATION LABEL: {classification_label.upper()}\n"
      f"AUDIENCE/CLASSIFICATION GROUP: {classification_group.upper()}\n"
      "Tailor all content, CTA labels, navigation, section types, trust signals, and information architecture to this profile.\n\n"
      f"BUILD MODE: {build_mode.upper()}\n"
      f"OUTPUT TARGET: {output_target.upper()}\n\n"
    )

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
    logger.info("[%s] ▶ build_website START  project=%r  ai=%s  mode=%s  target=%s",
                trace_id, project_name or "(auto)",
          "enabled" if settings.OPENAI_API_KEY else "disabled (fallback)",
          build_mode, output_target)

    # Derive project name from requirements if not provided
    if not project_name:
        project_name = " ".join(user_requirements.split()[:5]).title()

    if not settings.OPENAI_API_KEY:
        logger.warning("[%s] ⚠  No OPENAI_API_KEY — generating static fallback", trace_id)
        t1 = time.time()
        html_code = _generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index", output_target=output_target)
        site_dir = get_website_dir(project_name, output_target=output_target)
        _write_output_target_scaffold(site_dir, output_target, html_code)
        _sync_legacy_entrypoint(site_dir, html_code)
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
        html_code = _generate_static_fallback(user_requirements, theme_key=theme_key)
        filepath = generate_html({}, html_code, project_name, page_name="index", output_target=output_target)
        site_dir = get_website_dir(project_name, output_target=output_target)
        _write_output_target_scaffold(site_dir, output_target, html_code)
        _sync_legacy_entrypoint(site_dir, html_code)
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
    # Strip markdown code fences that LLMs sometimes wrap around HTML output
    html_code = html_code.strip()
    if html_code.startswith("```"):
        # Remove opening fence (```html or ```)
        html_code = re.sub(r'^```[a-zA-Z]*\n?', '', html_code)
        # Remove closing fence
        html_code = re.sub(r'\n?```\s*$', '', html_code)
        html_code = html_code.strip()

    # Enforce critical website spec fields (name/contact/products) when LLM output drifts.
    html_code = _enforce_generated_html_spec(html_code, user_requirements, website_id=website_id)

    # --- Asset extraction logic ---
    design_spec = {'css': {}, 'js': {}, 'images': {}, 'audio': {}, 'video': {}}

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

    # Build a cycle of reference images so we can round-robin them for placeholder substitution
    _ref_imgs: list = list(reference_images) if reference_images else []
    _ref_img_idx = 0
    _medical_mode = bool(re.search(
      r"\b(medical|medicinal|diagnostic|diagnostics|pharma|pharmaceutical|laboratory|lab\s*equipment|reagent|reseller|distributor)\b",
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

    url_to_fname: dict[str, str] = {}
    for m in image_matches:
        img_url = m.group(1)
        original_url = img_url   # the URL actually embedded in the HTML (may be a placeholder)
        logger.info(f"Processing image URL: {img_url}")
        if img_url.startswith('http://') or img_url.startswith('https://'):
            if img_url in url_to_fname:
                html_code = html_code.replace(img_url, f"assets/images/{url_to_fname[img_url]}")
                continue

            # If this is a placeholder/picsum URL and we have real reference images, use one instead
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

            # URLs from providers like picsum often end with only size paths (e.g., /1200/800),
            # which would collide to filenames like "800". Use a deterministic URL hash instead.
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
                    # Non-200 (e.g. 503 deprecated Unsplash endpoint) — skip immediately, no retry
                    logger.warning(f"Skipping image {img_url}: HTTP {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to download image {img_url}: {e}")

    # Extract media URLs (<audio>, <video>, <source>), download and relink locally.
    media_matches = list(re.finditer(
      r'<(audio|video|source)\b[^>]*\bsrc=["\']([^"\'>]+)["\']',
      html_code,
      re.IGNORECASE,
    ))
    logger.info(f"Found {len(media_matches)} media tags in HTML.")

    media_url_to_local: dict[str, str] = {}
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
    site_dir = get_website_dir(project_name, output_target=output_target)
    _write_output_target_scaffold(site_dir, output_target, html_code)
    _sync_legacy_entrypoint(site_dir, html_code)
    logger.info("[%s] ✅ AI website saved to %s  (total %.1fs)", trace_id, site_dir, time.time()-t0)

    return {
        "status": "success",
        "result": result,
        "output_dir": site_dir,
        "index": filepath,
        "requirements": user_requirements,
        "trace_id": trace_id,
    }

