"""
Website scraper tool — fetches an existing website URL and extracts structured
business information that can be used as seed data for rebuilding / modernising
the site.

Improvements over v1:
  - Captures anchor text for nav links (not just title/aria-label)
  - Follows internal sub-pages found in the nav (up to MAX_SUBPAGES)
  - Extracts image URLs (logo, hero, content images)
  - Richer prompt context with a strong redesign directive
"""
import re
import logging
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("website_builder.scraper")

MAX_SUBPAGES  = 4    # max additional pages to follow beyond homepage
PAGE_TIMEOUT  = 10   # seconds per request


# ---------------------------------------------------------------------------
# Internal HTML parser
# ---------------------------------------------------------------------------

class _SiteParser(HTMLParser):
    def __init__(self, base_url: str = ""):
        super().__init__()
        self.base_url = base_url
        self.title: str = ""
        self.meta_description: str = ""
        self.meta_keywords: str = ""
        self.og_title: str = ""
        self.og_description: str = ""
        self.og_image: str = ""
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self.emails: list[str] = []
        self.phones: list[str] = []
        self.nav_links: list[dict] = []   # list of {text, href}
        self.images: list[str] = []
        self.inline_styles: list[str] = []

        self._in_title = False
        self._current_heading: Optional[str] = None
        self._current_para = False
        self._current_nav = False
        self._in_nav_link = False
        self._nav_link_href = ""
        self._buf = ""
        self._skip_tags = {"script", "style", "noscript", "svg", "iframe"}
        self._current_skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag in self._skip_tags:
            self._current_skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            return
        if tag == "meta":
            name = attr.get("name", "").lower()
            prop = attr.get("property", "").lower()
            content = attr.get("content", "")
            if name == "description":        self.meta_description = content
            elif name == "keywords":         self.meta_keywords = content
            elif prop == "og:title":         self.og_title = content
            elif prop == "og:description":   self.og_description = content
            elif prop == "og:image":         self.og_image = content
        if tag in ("h1", "h2", "h3"):
            self._current_heading = tag
            self._buf = ""
        if tag == "p":
            self._current_para = True
            self._buf = ""
        if tag == "nav":
            self._current_nav = True
        if tag == "a":
            href = attr.get("href", "").strip()
            if self._current_nav and href:
                abs_href = urljoin(self.base_url, href)
                self._in_nav_link = True
                self._nav_link_href = abs_href
                self._buf = ""
        if tag == "img":
            src = attr.get("src", "").strip()
            if src and not src.startswith("data:"):
                abs_src = urljoin(self.base_url, src)
                if abs_src not in self.images:
                    self.images.append(abs_src)
        style = attr.get("style", "")
        if style and ("color" in style or "background" in style):
            self.inline_styles.append(style)

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._current_skip_depth = max(0, self._current_skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
            return
        if tag in ("h1", "h2", "h3") and self._current_heading:
            text = self._buf.strip()
            if text and len(text) < 200:
                self.headings.append(text)
            self._current_heading = None
            self._buf = ""
        if tag == "p" and self._current_para:
            text = self._buf.strip()
            if 20 < len(text) < 800:
                self.paragraphs.append(text)
            self._current_para = False
            self._buf = ""
        if tag == "nav":
            self._current_nav = False
        if tag == "a" and self._in_nav_link:
            link_text = self._buf.strip()
            if link_text and len(link_text) < 60:
                self.nav_links.append({"text": link_text, "href": self._nav_link_href})
            self._in_nav_link = False
            self._nav_link_href = ""
            self._buf = ""

    def handle_data(self, data):
        if self._current_skip_depth > 0:
            return
        if self._in_title:
            self.title += data
            return
        text = data.strip()
        if not text:
            return
        if self._current_heading or self._current_para or self._in_nav_link:
            self._buf += data
        for email in re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text):
            if email not in self.emails:
                self.emails.append(email)
        for phone in re.findall(r"(?:\+?\d[\d\s\-().]{7,}\d)", text):
            cleaned = re.sub(r"\s+", " ", phone).strip()
            if len(cleaned) >= 7 and cleaned not in self.phones:
                self.phones.append(cleaned)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_colors(parser: _SiteParser, raw_html: str) -> list[str]:
    colors = set()
    for block in re.findall(r"<style[^>]*>(.*?)</style>", raw_html, re.S | re.I):
        for c in re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", block):
            colors.add(c.upper())
        for c in re.findall(r"rgb\s*\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)", block):
            colors.add(c.replace(" ", ""))
    for style in parser.inline_styles:
        for c in re.findall(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", style):
            colors.add(c.upper())
    exclude = {"#FFFFFF", "#000000", "#FFF", "#000", "#FFFFFE", "#FEFEFE"}
    return [c for c in sorted(colors) if c not in exclude][:20]


def _fetch_html(url: str, timeout: int = PAGE_TIMEOUT) -> tuple[str, str]:
    """Return (raw_html, final_url)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; WebsiteBuilderBot/1.0; "
            "+https://github.com/senthilvasansubbu/agentic-s3-website-builder)"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ct = resp.headers.get_content_type()
            if "html" not in ct:
                raise ValueError(f"URL does not return HTML (got {ct!r})")
            charset = resp.headers.get_param("charset") or "utf-8"
            return resp.read().decode(charset, errors="replace"), resp.geturl()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Could not reach {url}: {exc.reason}") from exc


def _same_domain(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc


def _pick_subpages(nav_links: list[dict], base_url: str, visited: set[str]) -> list[str]:
    seen_texts: set[str] = set()
    pages: list[str] = []
    for link in nav_links:
        href = link.get("href", "").split("#")[0].rstrip("/")
        text = link.get("text", "").lower().strip()
        if (
            href and href not in visited
            and _same_domain(href, base_url)
            and text not in seen_texts
            and not re.search(r"\.(pdf|jpg|png|gif|zip|docx?)$", href, re.I)
        ):
            pages.append(href)
            seen_texts.add(text)
        if len(pages) >= MAX_SUBPAGES:
            break
    return pages


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_website(url: str, timeout: int = PAGE_TIMEOUT) -> dict:
    """Fetch url (+ up to MAX_SUBPAGES internal pages) and return structured data."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not urlparse(url).netloc:
        raise ValueError(f"Invalid URL: {url!r}")

    logger.info("Scraping homepage: %s", url)
    raw_html, final_url = _fetch_html(url, timeout)
    hp = _SiteParser(base_url=final_url)
    try:
        hp.feed(raw_html)
    except Exception as exc:
        logger.warning("HTML parser error on homepage (non-fatal): %s", exc)

    colors = _extract_colors(hp, raw_html)
    visited = {final_url, final_url.rstrip("/")}

    # Deduplicate nav links
    seen_nav: dict[str, str] = {}
    for link in hp.nav_links:
        href = link.get("href", "").split("#")[0].rstrip("/")
        text = link.get("text", "").strip()
        if text and href and href not in seen_nav:
            seen_nav[href] = text
    deduped_nav = [{"text": v, "href": k} for k, v in seen_nav.items()]

    # Scrape sub-pages
    subpage_data: list[dict] = []
    for sp_url in _pick_subpages(deduped_nav, final_url, visited):
        if sp_url in visited:
            continue
        visited.add(sp_url)
        try:
            logger.info("Scraping sub-page: %s", sp_url)
            sp_html, _ = _fetch_html(sp_url, timeout)
            sp = _SiteParser(base_url=sp_url)
            sp.feed(sp_html)
            page_name = seen_nav.get(sp_url, urlparse(sp_url).path.strip("/").replace("/", " › "))
            subpage_data.append({
                "page": page_name,
                "url": sp_url,
                "headings": sp.headings[:8],
                "paragraphs": sp.paragraphs[:6],
                "emails": sp.emails,
                "phones": sp.phones,
                "images": sp.images[:10],
            })
            for e in sp.emails:
                if e not in hp.emails: hp.emails.append(e)
            for p in sp.phones:
                if p not in hp.phones: hp.phones.append(p)
        except Exception as exc:
            logger.warning("Could not scrape sub-page %s: %s", sp_url, exc)

    title = hp.title.strip() or hp.og_title.strip()
    description = (
        hp.meta_description.strip()
        or hp.og_description.strip()
        or (hp.paragraphs[0] if hp.paragraphs else "")
    )

    result = {
        "url": final_url,
        "title": title,
        "description": description,
        "keywords": hp.meta_keywords.strip(),
        "og_image": hp.og_image.strip(),
        "headings": hp.headings[:20],
        "paragraphs": hp.paragraphs[:10],
        "emails": hp.emails[:5],
        "phones": hp.phones[:5],
        "nav_links": deduped_nav[:12],
        "images": hp.images[:15],
        "colors": colors,
        "subpages": subpage_data,
        "raw_text_snippet": " ".join(hp.paragraphs[:6])[:800],
    }
    logger.info(
        "Scraped %s — title=%r emails=%s phones=%s headings=%d colors=%d subpages=%d",
        url, title, result["emails"], result["phones"],
        len(result["headings"]), len(colors), len(subpage_data),
    )
    return result


def scrape_to_prompt_context(url: str) -> str:
    """Scrape url (+ sub-pages) and return a string ready for the AI build prompt."""
    try:
        data = scrape_website(url)
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return f"[Website scraping failed for {url}: {exc}]"

    lines = [
        "=== EXTRACTED FROM EXISTING WEBSITE ===",
        f"Source URL: {data['url']}",
        f"Business Name / Title: {data['title']}",
        f"Description: {data['description']}",
    ]
    if data["keywords"]:
        lines.append(f"Keywords: {data['keywords']}")
    if data["emails"]:
        lines.append(f"Contact Email(s): {', '.join(data['emails'])}")
    if data["phones"]:
        lines.append(f"Contact Phone(s): {', '.join(data['phones'])}")
    if data["nav_links"]:
        nav_text = ", ".join(l["text"] for l in data["nav_links"] if l.get("text"))
        lines.append(f"Navigation Pages: {nav_text}")
    if data["headings"]:
        lines.append("\nKey Headings Found on Site:")
        for h in data["headings"][:12]:
            lines.append(f"  • {h}")
    if data["paragraphs"]:
        lines.append("\nContent Samples (Homepage):")
        for p in data["paragraphs"][:5]:
            lines.append(f"  {p}")

    for sp in data.get("subpages", []):
        lines.append(f"\n--- Page: {sp['page']} ({sp['url']}) ---")
        for h in sp["headings"][:6]:
            lines.append(f"  • {h}")
        for p in sp["paragraphs"][:4]:
            lines.append(f"  {p}")

    if data["colors"]:
        lines.append(f"\nBrand Colours Detected: {', '.join(data['colors'][:8])}")

    # ── Image / Logo directives ────────────────────────────────────────────────
    all_images = data["images"]
    og_image   = data.get("og_image", "")

    # Identify logo: prefer any image whose URL contains "logo", "icon", or "brand";
    # fall back to the first image on the page.
    logo_url = og_image
    if not logo_url:
        for img in all_images:
            if re.search(r"logo|icon|brand", img, re.I):
                logo_url = img
                break
    if not logo_url and all_images:
        logo_url = all_images[0]

    # Gallery images: everything except the logo, up to 10
    gallery_images = [img for img in all_images if img != logo_url][:10]

    if logo_url:
        lines.append(f"\nBrand Logo URL: {logo_url}")
        lines.append(
            "INSTRUCTION: Use this logo image in the navigation bar <img> tag "
            "instead of a text logo, and also in the footer."
        )

    if gallery_images:
        lines.append("\nReal Site Images (use these in hero, gallery, and section backgrounds):")
        for i, img in enumerate(gallery_images, 1):
            lines.append(f"  {i}. {img}")
        lines.append(
            "INSTRUCTION: Use the images above throughout the site instead of "
            "Unsplash placeholders. Assign them to hero background, gallery grid, "
            "about section, and any other relevant sections based on visual context."
        )

    lines.append(
        "\n=== REDESIGN DIRECTIVE ===\n"
        "You have been given the FULL content of an existing business website above.\n"
        "Your task is to COMPLETELY REDESIGN it as a modern, premium website.\n\n"
        "MANDATORY requirements:\n"
        "1. PRESERVE ALL CONTENT — every heading, paragraph, service, contact detail, "
        "and page from the extracted data above must appear in the new site.\n"
        "2. RECREATE ALL PAGES listed in the Navigation — create a dedicated section or "
        "full page for each nav item.\n"
        "3. LOGO — use the Brand Logo URL above as an <img> in the navbar and footer. "
        "Do NOT render the business name as plain text if a logo URL is provided.\n"
        "4. IMAGES — use the Real Site Images listed above for the hero background, "
        "gallery, and section visuals. Do NOT use Unsplash or stock photo placeholders "
        "when real images are available.\n"
        "5. MODERN DESIGN — Playfair Display or Montserrat headings, Inter/Lato body text, "
        "generous whitespace, smooth CSS scroll animations, card-based layouts, "
        "refined palette from brand colours above.\n"
        f"6. HERO SECTION — full-width banner. CSS background-image must be: "
        f"url('{gallery_images[0] if gallery_images else (logo_url or '')}') "
        f"— do NOT use Unsplash, do NOT fabricate a URL. "
        f"Overlay with the business name, tagline, and a Contact Us CTA.\n"
        "7. GALLERY SECTION — create a responsive image grid using all provided site images.\n"
        "8. CONTACT SECTION — include all extracted emails, phone numbers, and an "
        "enquiry form with name, email, message fields.\n"
        "9. RESPONSIVE — mobile-first, hamburger nav on mobile.\n"
        "10. NO Lorem Ipsum — every text must come from real extracted content.\n"
    )
    return "\n".join(lines)
