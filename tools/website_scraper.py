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
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse, unquote

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
        self.videos: list[str] = []
        self.audios: list[str] = []
        self.embeds: list[str] = []
        self.inline_styles: list[str] = []

        self._in_title = False
        self._current_heading: Optional[str] = None
        self._current_para = False
        self._current_nav = False
        self._in_nav_link = False
        self._in_video = False
        self._in_audio = False
        self._nav_link_href = ""
        self._buf = ""
        self._skip_tags = {"script", "style", "noscript", "svg", "iframe"}
        self._current_skip_depth = 0

    @staticmethod
    def _is_video_url(url: str) -> bool:
        return bool(re.search(r"\.(mp4|webm|ogv|mov|m4v|m3u8)(?:$|[?#])", url, re.I))

    @staticmethod
    def _is_audio_url(url: str) -> bool:
        return bool(re.search(r"\.(mp3|wav|ogg|m4a|aac|flac)(?:$|[?#])", url, re.I))

    def _add_video(self, src: str):
        if src and src not in self.videos:
            self.videos.append(src)

    def _add_audio(self, src: str):
        if src and src not in self.audios:
            self.audios.append(src)

    def _add_embed(self, src: str):
        if src and src not in self.embeds:
            self.embeds.append(src)

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag == "iframe":
            src = attr.get("src", "").strip()
            if src and not src.startswith("data:"):
                abs_src = urljoin(self.base_url, src)
                # Keep common playable embeds to re-use in rebuilt sites.
                if re.search(r"youtube\.com|youtu\.be|vimeo\.com|soundcloud\.com", abs_src, re.I):
                    self._add_embed(abs_src)
                    if re.search(r"youtube\.com|youtu\.be|vimeo\.com", abs_src, re.I):
                        self._add_video(abs_src)
            self._current_skip_depth += 1
            return
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
            if href:
                abs_href = urljoin(self.base_url, href)
                if self._is_video_url(abs_href):
                    self._add_video(abs_href)
                elif self._is_audio_url(abs_href):
                    self._add_audio(abs_href)
            if self._current_nav and href:
                abs_href = urljoin(self.base_url, href)
                self._in_nav_link = True
                self._nav_link_href = abs_href
                self._buf = ""
        if tag == "video":
            self._in_video = True
            src = (
                attr.get("src", "").strip()
                or attr.get("data-src", "").strip()
                or attr.get("data-original", "").strip()
            )
            if src and not src.startswith("data:"):
                self._add_video(urljoin(self.base_url, src))
        if tag == "audio":
            self._in_audio = True
            src = (
                attr.get("src", "").strip()
                or attr.get("data-src", "").strip()
                or attr.get("data-original", "").strip()
            )
            if src and not src.startswith("data:"):
                self._add_audio(urljoin(self.base_url, src))
        if tag == "source":
            src = (
                attr.get("src", "").strip()
                or attr.get("data-src", "").strip()
                or attr.get("data-original", "").strip()
            )
            if src and not src.startswith("data:"):
                abs_src = urljoin(self.base_url, src)
                media_type = attr.get("type", "").lower().strip()
                if self._in_video or media_type.startswith("video/") or self._is_video_url(abs_src):
                    self._add_video(abs_src)
                elif self._in_audio or media_type.startswith("audio/") or self._is_audio_url(abs_src):
                    self._add_audio(abs_src)
        if tag == "img":
            # Support lazy-loaded carousels that often use data-* attributes.
            src = (
                attr.get("src", "").strip()
                or attr.get("data-src", "").strip()
                or attr.get("data-lazy-src", "").strip()
                or attr.get("data-original", "").strip()
            )
            if not src:
                srcset = attr.get("data-srcset", "").strip() or attr.get("srcset", "").strip()
                if srcset:
                    src = srcset.split(",")[0].strip().split(" ")[0].strip()
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
        if tag == "video":
            self._in_video = False
        if tag == "audio":
            self._in_audio = False

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


def _extract_jsonld_products(raw_html: str, base_url: str) -> list[dict]:
    """Extract Product name/image pairs from JSON-LD blobs."""
    products: list[dict] = []
    blocks = re.findall(r"<script[^>]*type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", raw_html, re.I | re.S)
    for b in blocks:
        text = b.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
            nodes = obj if isinstance(obj, list) else [obj]
        except Exception:
            continue
        for n in nodes:
            if not isinstance(n, dict):
                continue
            ntype = str(n.get("@type", "")).lower()
            if "product" not in ntype:
                continue
            name = str(n.get("name", "")).strip()
            img = n.get("image", "")
            if isinstance(img, list):
                img = img[0] if img else ""
            img = str(img or "").strip()
            if not name and not img:
                continue
            if img and not img.startswith("data:"):
                img = urljoin(base_url, img)
            products.append({"name": name, "image": img})
    return products


def _extract_carousel_products(raw_html: str, base_url: str) -> list[dict]:
    """Heuristic extraction for product carousels (swiper/slick/owl/slider)."""
    products: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # Capture likely slide/item blocks.
    block_pat = re.compile(
        r"<(?:div|li|article|section)[^>]*class=[\"'][^\"']*(?:carousel|swiper|slick|owl|slide|slider)[^\"']*[\"'][^>]*>(.*?)</(?:div|li|article|section)>",
        re.I | re.S,
    )
    text_pat = re.compile(r"<(?:h[1-6]|a|span|p)[^>]*>(.*?)</(?:h[1-6]|a|span|p)>", re.I | re.S)
    img_pat = re.compile(
        r"<(?:img|source)[^>]*(?:src|data-src|data-lazy-src|data-original|data-srcset|srcset)=[\"']([^\"']+)[\"'][^>]*>",
        re.I,
    )

    for m in block_pat.finditer(raw_html):
        block = m.group(1)

        imgs: list[str] = []
        for im in img_pat.findall(block):
            val = im.split(",")[0].strip().split(" ")[0].strip()
            if not val or val.startswith("data:"):
                continue
            imgs.append(urljoin(base_url, val))

        labels: list[str] = []
        for t in text_pat.findall(block):
            txt = re.sub(r"<[^>]+>", " ", t)
            txt = re.sub(r"\s+", " ", txt).strip()
            if not txt:
                continue
            if len(txt) < 4 or len(txt) > 90:
                continue
            low = txt.lower()
            if low in {"read more", "learn more", "shop now", "view details", "next", "prev", "previous"}:
                continue
            labels.append(txt)

        if not imgs and not labels:
            continue

        if labels:
            for i, label in enumerate(labels[:8]):
                img = imgs[i] if i < len(imgs) else (imgs[0] if imgs else "")
                key = (label.lower(), img)
                if key in seen:
                    continue
                seen.add(key)
                products.append({"name": label, "image": img})
        elif imgs:
            for img in imgs[:8]:
                key = ("", img)
                if key in seen:
                    continue
                seen.add(key)
                products.append({"name": "", "image": img})

    return products


def _clean_label_from_asset_path(path_or_url: str) -> str:
    name = unquote(path_or_url or "")
    name = name.split("?")[0].split("#")[0]
    name = name.rsplit("/", 1)[-1]
    name = re.sub(r"\.(?:png|jpe?g|webp|gif|svg)$", "", name, flags=re.I)
    # Remove bundler hash suffixes like "-C0RQ820i"
    name = re.sub(r"-[A-Za-z0-9]{6,}$", "", name)
    name = re.sub(r"[_\-]+", " ", name).strip()
    if not name:
        return ""
    low = name.lower()
    if re.fullmatch(r"product\d*", low):
        return ""
    if low in {"image", "img", "banner", "hero", "thumbnail", "assets", "asset", "sharer"}:
        return ""
    if len(name) < 3 or len(name) > 80:
        return ""
    return name


def _extract_products_from_asset_chunks(base_url: str, raw_html: str, timeout: int = PAGE_TIMEOUT) -> list[dict]:
    """
    Fallback for JS-heavy sites: inspect Vite/Webpack asset bundles for
    product image URLs and derive labels from filenames/paths.
    """
    products: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # Discover entry scripts from homepage HTML.
    script_srcs = re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", raw_html, re.I)
    entry_js = [urljoin(base_url, s) for s in script_srcs if "/assets/" in s and s.endswith(".js")]
    entry_js = entry_js[:3]
    if not entry_js:
        return products

    chunk_names: set[str] = set()
    for js_url in entry_js:
        try:
            txt, _ = _fetch_text(js_url, timeout=timeout)
        except Exception:
            continue
        # Extract likely product-related chunks.
        for c in re.findall(r"([A-Za-z0-9_-]*(?:Product|product)[A-Za-z0-9_-]*\.js)", txt):
            chunk_names.add(c)

    if not chunk_names:
        return products

    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    for c in list(chunk_names)[:8]:
        chunk_url = f"{origin}/assets/{c}"
        try:
            txt, _ = _fetch_text(chunk_url, timeout=timeout)
        except Exception:
            continue

        # Absolute and relative asset image URLs in JS bundles.
        abs_imgs = re.findall(r"https?://[^\"']+/assets/[^\"']+\.(?:png|jpe?g|webp|gif|svg)", txt, re.I)
        rel_imgs = re.findall(r"/assets/[^\"']+\.(?:png|jpe?g|webp|gif|svg)", txt, re.I)

        # Product detail links can also yield good labels.
        prod_links = re.findall(r"https?://[^\"']+/(?:[a-z0-9-]+/){1,6}", txt, re.I)

        link_labels = []
        for link in prod_links[:120]:
            slug = link.rstrip("/").rsplit("/", 1)[-1]
            lbl = _clean_label_from_asset_path(slug)
            if lbl:
                link_labels.append(lbl)

        all_imgs = abs_imgs + [urljoin(origin, p) for p in rel_imgs]
        for i, img in enumerate(all_imgs[:120]):
            lbl = _clean_label_from_asset_path(img)
            if not lbl and i < len(link_labels):
                lbl = link_labels[i]
            key = (lbl.lower(), img)
            if key in seen:
                continue
            seen.add(key)
            products.append({"name": lbl, "image": img})

    return products


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


def _fetch_text(url: str, timeout: int = PAGE_TIMEOUT) -> tuple[str, str]:
    """Return (text, final_url) for text-like responses (JS/JSON/HTML)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; WebsiteBuilderBot/1.0; "
            "+https://github.com/senthilvasansubbu/agentic-s3-website-builder)"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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

    # Enrich extraction with carousel/json-ld product signals that are often
    # missed by simple static parsers on modern JS-heavy storefront pages.
    carousel_products = _extract_carousel_products(raw_html, final_url)
    jsonld_products = _extract_jsonld_products(raw_html, final_url)
    js_chunk_products = _extract_products_from_asset_chunks(final_url, raw_html, timeout=timeout)
    merged_products: list[dict] = []
    seen_prod: set[tuple[str, str]] = set()
    for p in (carousel_products + jsonld_products + js_chunk_products):
        nm = str(p.get("name", "")).strip()
        im = str(p.get("image", "")).strip()
        key = (nm.lower(), im)
        if key in seen_prod:
            continue
        seen_prod.add(key)
        merged_products.append({"name": nm, "image": im})
        if nm and nm not in hp.headings:
            hp.headings.append(nm)
        if im and im not in hp.images:
            hp.images.append(im)

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
        "videos": hp.videos[:15],
        "audios": hp.audios[:15],
        "embeds": hp.embeds[:15],
        "carousel_products": merged_products[:24],
        "colors": colors,
        "subpages": subpage_data,
        "raw_text_snippet": " ".join(hp.paragraphs[:6])[:800],
    }
    logger.info(
        "Scraped %s — title=%r emails=%s phones=%s headings=%d colors=%d subpages=%d media(v=%d,a=%d,e=%d)",
        url, title, result["emails"], result["phones"],
        len(result["headings"]), len(colors), len(subpage_data),
        len(result["videos"]), len(result["audios"]), len(result["embeds"]),
    )
    return result


def prompt_context_from_scraped_data(data: dict) -> str:
    """Build AI prompt context text from an already-scraped website payload."""
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

    if data.get("carousel_products"):
        lines.append("\nProduct Hints Detected (Carousel / JSON-LD):")
        for p in data["carousel_products"][:12]:
            nm = (p.get("name") or "").strip()
            im = (p.get("image") or "").strip()
            if nm and im:
                lines.append(f"  • {nm} — {im}")
            elif nm:
                lines.append(f"  • {nm}")
            elif im:
                lines.append(f"  • {im}")

    for sp in data.get("subpages", []):
        lines.append(f"\n--- Page: {sp['page']} ({sp['url']}) ---")
        for h in sp["headings"][:6]:
            lines.append(f"  • {h}")
        for p in sp["paragraphs"][:4]:
            lines.append(f"  {p}")

    if data["colors"]:
        lines.append(f"\nBrand Colours Detected: {', '.join(data['colors'][:8])}")

    if data.get("videos"):
        lines.append("\nDetected Video Assets (re-use these where relevant):")
        for i, v in enumerate(data["videos"][:10], 1):
            lines.append(f"  {i}. {v}")
    if data.get("audios"):
        lines.append("\nDetected Audio Assets (re-use these where relevant):")
        for i, a in enumerate(data["audios"][:10], 1):
            lines.append(f"  {i}. {a}")
    if data.get("embeds"):
        lines.append("\nDetected Embedded Media URLs (YouTube/Vimeo/SoundCloud):")
        for i, e in enumerate(data["embeds"][:10], 1):
            lines.append(f"  {i}. {e}")

    # ── Image / Logo directives ────────────────────────────────────────────────
    all_images = data["images"]
    og_image = data.get("og_image", "")

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

    if data.get("videos") or data.get("audios") or data.get("embeds"):
        lines.append(
            "INSTRUCTION: If media sections are included, prefer the detected "
            "audio/video/embed URLs above instead of placeholders."
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


def scrape_to_prompt_context(url: str) -> str:
    """Scrape url (+ sub-pages) and return a string ready for the AI build prompt."""
    try:
        data = scrape_website(url)
    except Exception as exc:
        logger.warning("Failed to scrape %s: %s", url, exc)
        return f"[Website scraping failed for {url}: {exc}]"
    return prompt_context_from_scraped_data(data)
