"""
Catalog scraper — imports product data from a URL into the website builder.

Supported catalog sources (auto-detected):
  1. WhatsApp Business Catalog  (wa.me/c/<id>  or  api.whatsapp.com/catalog/…)
     WhatsApp catalog pages are rendered client-side, so we fetch the Open-Graph /
     meta-data available in the server-rendered HTML shell and also look for any
     embedded JSON-LD or application/json script blocks that some WA business
     pages expose.

  2. JSON catalog  — URL returns a JSON array/object of products.
     Supported shapes:
       • [ { name, price, description, image, … }, … ]
       • { products: [ … ] }
       • { items: [ … ] }
       • { data: [ … ] }

  3. CSV catalog   — URL returns text/csv with headers.
     Expected columns (case-insensitive, partial match):
       name / title, price / cost, description / desc, image / photo / img,
       category, stock / qty / quantity

  4. Generic HTML product page — scrapes structured-data (JSON-LD schema.org
     Product) first, then falls back to heuristic DOM extraction.

All functions return a list of dicts with keys:
    name, price, currency, description, image_url, category, stock
"""

import re
import json
import csv
import io
import logging
import urllib.request
import urllib.error
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger("website_builder.catalog_scraper")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_USER_AGENT = (
    "Mozilla/5.0 (compatible; WebsiteBuilderBot/1.0; "
    "+https://github.com/senthilvasansubbu/agentic-s3-website-builder)"
)

_PRICE_RE = re.compile(r"[\$£€₹₦]?\s*([\d,]+(?:\.\d{1,2})?)")
_CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR", "₹": "INR", "₦": "NGN"}


def _detect_currency(raw: str) -> str:
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in raw:
            return code
    return "USD"


def _parse_price(raw) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    raw = str(raw)
    m = _PRICE_RE.search(raw.replace(",", ""))
    return float(m.group(1)) if m else 0.0


def _fetch(url: str, timeout: int = 15) -> tuple[bytes, str]:
    """Return (raw_bytes, content_type).
    Uses `requests` for automatic gzip/deflate/brotli decompression and
    browser-like headers that pass most anti-scraping checks.
    """
    try:
        import requests as _requests
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json,text/csv,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        resp = _requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip()
        return resp.content, content_type
    except ImportError:
        pass  # fall back to urllib
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    # urllib fallback (no brotli support)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json,text/csv,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get_content_type() or ""
            return resp.read(), content_type
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}: {exc.reason} — {url}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Could not reach {url}: {exc.reason}") from exc


# ---------------------------------------------------------------------------
# JSON catalog parser
# ---------------------------------------------------------------------------

# Field name aliases for common catalog formats
_FIELD_MAP = {
    "name":        ["name", "title", "product_name", "productname", "item_name", "itemname", "label"],
    "price":       ["price", "cost", "sale_price", "saleprice", "amount", "retail_price", "regular_price"],
    "description": ["description", "desc", "details", "about", "summary", "body", "overview"],
    "image_url":   ["image", "img", "photo", "image_url", "imageurl", "thumbnail", "picture", "cover"],
    "category":    ["category", "cat", "type", "group", "department", "collection", "section"],
    "stock":       ["stock", "qty", "quantity", "inventory", "available", "stock_quantity"],
    "currency":    ["currency", "currency_code", "cur"],
    "compare_price": ["compare_price", "original_price", "regular_price", "was_price", "list_price"],
    "discount_pct":  ["discount", "discount_pct", "sale_pct", "off_pct"],
}


def _remap(item: dict) -> Optional[dict]:
    """Map an arbitrary dict to our standard product dict.  Returns None if no name found."""
    lower_item = {k.lower().strip(): v for k, v in item.items()}
    result: dict = {}
    for field, aliases in _FIELD_MAP.items():
        for alias in aliases:
            if alias in lower_item and lower_item[alias] not in ("", None):
                result[field] = lower_item[alias]
                break

    if not result.get("name"):
        return None  # can't use a nameless product

    # Normalise types
    result["price"] = _parse_price(result.get("price", 0))
    result["compare_price"] = _parse_price(result.get("compare_price", 0))
    result["discount_pct"] = _parse_price(result.get("discount_pct", 0))
    result["stock"] = int(float(result.get("stock", 0) or 0))
    result["currency"] = str(result.get("currency", "USD")).upper()[:3]
    result.setdefault("description", "")
    result.setdefault("image_url", "")
    result.setdefault("category", "")

    return result


def _parse_json_catalog(data: bytes) -> list[dict]:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    # Extract list from common wrapper keys
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        for key in ("products", "items", "data", "results", "catalog", "entries", "goods"):
            if isinstance(obj.get(key), list):
                items = obj[key]
                break
        else:
            # Flat object — treat as single product
            items = [obj]
    else:
        raise ValueError("Unexpected JSON root type")

    products = []
    for item in items:
        if not isinstance(item, dict):
            continue
        p = _remap(item)
        if p:
            products.append(p)
    return products


# ---------------------------------------------------------------------------
# CSV catalog parser
# ---------------------------------------------------------------------------

def _parse_csv_catalog(data: bytes) -> list[dict]:
    text = data.decode("utf-8-sig", errors="replace")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))
    products = []
    for row in reader:
        p = _remap(dict(row))
        if p:
            products.append(p)
    return products


# ---------------------------------------------------------------------------
# HTML / JSON-LD product scraper
# ---------------------------------------------------------------------------

class _ProductPageParser(HTMLParser):
    """Extract JSON-LD blocks and basic product meta from HTML."""

    def __init__(self):
        super().__init__()
        self._in_script = False
        self._script_type = ""
        self._buf = ""
        self.json_ld_blocks: list[str] = []
        self.og: dict = {}
        self._skip_depth = 0
        self._skip_tags = {"style", "noscript", "svg", "iframe"}

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag in self._skip_tags:
            self._skip_depth += 1
            return
        if tag == "script":
            stype = attr.get("type", "")
            if stype == "application/ld+json":
                self._in_script = True
                self._script_type = "jsonld"
                self._buf = ""
        if tag == "meta":
            prop = attr.get("property", "") or attr.get("name", "")
            content = attr.get("content", "")
            if prop.startswith("og:") or prop.startswith("product:"):
                self.og[prop] = content

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "script" and self._in_script:
            self._in_script = False
            if self._script_type == "jsonld":
                self.json_ld_blocks.append(self._buf)
            self._buf = ""

    def handle_data(self, data):
        if self._skip_depth > 0:
            return
        if self._in_script:
            self._buf += data


def _extract_jsonld_products(blocks: list[str]) -> list[dict]:
    products = []
    for block in blocks:
        try:
            obj = json.loads(block)
        except json.JSONDecodeError:
            continue
        # Could be a single object or list
        entries = obj if isinstance(obj, list) else [obj]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            schema_type = entry.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = " ".join(schema_type)
            if "Product" not in schema_type and "ItemList" not in schema_type:
                continue

            if "ItemList" in schema_type:
                # Expand item list
                for item in entry.get("itemListElement", []):
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        p = _jsonld_product_to_dict(item)
                        if p:
                            products.append(p)
            else:
                p = _jsonld_product_to_dict(entry)
                if p:
                    products.append(p)
    return products


def _jsonld_product_to_dict(entry: dict) -> Optional[dict]:
    name = entry.get("name", "")
    if not name:
        return None

    # Price — can be under "offers" key
    price = 0.0
    currency = "USD"
    compare_price = 0.0
    offers = entry.get("offers") or entry.get("offer")
    if isinstance(offers, list):
        offers = offers[0]
    if isinstance(offers, dict):
        price = _parse_price(offers.get("price", 0))
        currency = offers.get("priceCurrency", "USD")
        high = offers.get("highPrice")
        if high:
            compare_price = _parse_price(high)

    # Image
    image = entry.get("image", "")
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")

    description = entry.get("description", "")
    if isinstance(description, list):
        description = " ".join(description)

    category = entry.get("category", "")
    if isinstance(category, dict):
        category = category.get("name", "")

    return {
        "name": str(name).strip(),
        "price": price,
        "compare_price": compare_price,
        "discount_pct": 0.0,
        "currency": currency,
        "description": str(description).strip(),
        "image_url": str(image).strip(),
        "category": str(category).strip(),
        "stock": int(entry.get("inventoryLevel", 0) or 0),
    }


def _parse_html_catalog(raw: bytes, base_url: str = "") -> list[dict]:
    html = raw.decode("utf-8", errors="replace")
    parser = _ProductPageParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    # 1. Try JSON-LD structured data (most reliable)
    products = _extract_jsonld_products(parser.json_ld_blocks)
    if products:
        return products

    # 2. Try embedded JSON blobs — extended patterns to cover more store formats
    json_blob_patterns = [
        # window.__STORE_STATE__ = {...}  /  window.catalog = [...]
        r'window\.__(?:STORE_STATE|INITIAL_STATE|DATA|PRELOADED_STATE|NUXT)\s*=\s*(\{.*?\})\s*;',
        # products/items/catalog key containing an array
        r'"(?:products|items|catalog|goods|variants|productList)"\s*:\s*(\[.*?\])',
        # var/let/const products = [...]
        r'(?:var|let|const)\s+(?:products|items|catalog|productList)\s*=\s*(\[.*?\])',
        # products: [...] or items: [...] (JS object property)
        r'(?:products|catalog|items|goods)\s*[:=]\s*(\[.*?\])',
    ]
    for pattern in json_blob_patterns:
        for match in re.finditer(pattern, html, re.S | re.I):
            try:
                data = json.loads(match.group(1))
                # If the matched blob is a dict, try to extract list from it
                if isinstance(data, dict):
                    for key in ("products", "items", "data", "results", "catalog", "entries", "goods"):
                        if isinstance(data.get(key), list) and len(data[key]) > 0:
                            data = data[key]
                            break
                if not isinstance(data, list):
                    continue
                parsed = [_remap(i) for i in data if isinstance(i, dict)]
                parsed = [p for p in parsed if p]
                if len(parsed) > 1:  # at least 2 items to be considered a catalog
                    return parsed
            except Exception:
                continue

    # 2.5 IndiaMart-specific parser (FM_sid_nm / price-N pattern)
    if "indiamart.com" in base_url:
        products = _parse_indiamart(html, base_url)
        if products:
            return products

    # 3. Heuristic DOM extraction — look for repeating product card patterns
    products = _extract_product_cards_heuristic(html, base_url)
    if len(products) > 1:
        return products

    # 4. Open-Graph fallback — synthesise one product from page OG meta
    og = parser.og
    name = og.get("og:title") or og.get("product:title", "")
    if not name:
        return []

    raw_price = og.get("product:price:amount") or og.get("og:price:amount", "0")
    currency = og.get("product:price:currency") or og.get("og:price:currency", "USD")
    description = og.get("og:description", "")
    image = og.get("og:image", "")

    return [{
        "name": name,
        "price": _parse_price(raw_price),
        "compare_price": 0.0,
        "discount_pct": 0.0,
        "currency": currency,
        "description": description,
        "image_url": image,
        "category": "",
        "stock": 0,
    }]


def _parse_indiamart(html: str, base_url: str = "") -> list[dict]:
    """
    Parse IndiaMart seller catalog pages using FM_sid_nm / price-N patterns.

    Category detection strategies (tried in order):
      A. Split HTML on IndiaMart category-section boundaries and track the
         heading text as the active category for subsequent product cards.
      B. For each product card, walk backward in the HTML to find the nearest
         preceding category heading when no section split was found.
      C. Derive a category from the URL path slug as a last resort
         (e.g. /sign-board.html → "Sign Board").
    """

    # ── Strategy C: URL-slug fallback category (used when A and B yield nothing) ──
    url_slug_category = ""
    if base_url:
        m_slug = re.search(r'/([^/?#]+)\.html', base_url)
        if m_slug:
            url_slug_category = m_slug.group(1).replace("-", " ").replace("_", " ").title()

    # ── Strategy A: category-section boundary split ────────────────────────────
    # IndiaMart uses various class names to mark category group headings.
    # Known patterns (server-rendered): FM_catg_nm, cat-nm, catg-nm, prd-catg
    # We also match any <h2>/<h3>/<h4> or <div>/<span> whose class contains
    # 'cat' (case-insensitive) and whose inner text looks like a short label.
    _CATG_SECTION_RE = re.compile(
        r'class="(?:[^"]*\b)(?:FM_catg_nm|cat(?:g)?-nm|prd-catg|catg_nm|category[_-]?(?:title|name|header|heading))[^"]*"'
        r'[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,80})(?:\s*</[^>]+>)*\s*</'
        r'|'
        r'<(?:h[2-4])[^>]*class="[^"]*cat[^"]*"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,80})'
        r'|'
        r'class="[^"]*(?:section|group|catg|catalog)[_-]?(?:title|name|header|heading)[^"]*"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,80})',
        re.I,
    )

    # Split on either a category heading OR a product card start
    _SPLIT_RE = re.compile(
        r'(?='
        r'class="(?:[^"]*\b)(?:FM_catg_nm|cat(?:g)?-nm|prd-catg|catg_nm|category[_-]?(?:title|name|header|heading))[^"]*"'
        r'|'
        r'<(?:h[2-4])[^>]*class="[^"]*cat[^"]*"'
        r'|'
        r'class="[^"]*(?:section|group|catg|catalog)[_-]?(?:title|name|header|heading)[^"]*"'
        r'|'
        r'class="FM_sid_nm'
        r')'
    )
    segments = _SPLIT_RE.split(html)

    current_category_a = ""
    products_a: list[dict] = []
    strategy_a_hit = False  # True once we see at least one category boundary

    for seg in segments:
        # Check if this segment starts with a category heading
        m_cat = _CATG_SECTION_RE.match(seg)
        if m_cat:
            raw = (m_cat.group(1) or m_cat.group(2) or m_cat.group(3) or "").strip()
            raw = re.sub(r'\s+', ' ', raw).strip()
            if raw:
                current_category_a = raw
                strategy_a_hit = True
            continue

        # Check if this segment is a product card
        if not seg.lstrip().startswith('class="FM_sid_nm'):
            continue
        m_name = re.search(
            r'class="FM_sid_nm[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', seg, re.S
        )
        if not m_name:
            continue
        m_price = re.search(r'id="price-\d+"[^>]*>[\u20B9\u20AC\$£₦]\s*([\d,]+)', seg)
        m_unit = re.search(
            r'id="price-\d+"[^>]*>[\s\S]{0,80}?/\s*<span[^>]*>([^<]+)</span>', seg
        )
        m_img = re.search(
            r'<img[^>]+(?:src|data-original|data-src)=["\']([^"\']+)["\']', seg
        )
        price_val = float(m_price.group(1).replace(",", "")) if m_price else 0.0
        unit = m_unit.group(1).strip() if m_unit else ""
        products_a.append({
            "name": m_name.group(1).strip(),
            "price": price_val,
            "compare_price": 0.0,
            "discount_pct": 0.0,
            "currency": "INR",
            "description": f"Per {unit}" if unit else "",
            "image_url": m_img.group(1) if m_img else "",
            "category": current_category_a,
            "stock": 0,
        })

    # If Strategy A found any category labels, use its results
    if strategy_a_hit and products_a:
        return products_a

    # ── Strategy B: backward-scan for nearest preceding category heading ───────
    # Collect all category heading positions in the full HTML
    cat_positions: list[tuple[int, str]] = []
    for m in _CATG_SECTION_RE.finditer(html):
        raw = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        raw = re.sub(r'\s+', ' ', raw).strip()
        if raw:
            cat_positions.append((m.start(), raw))

    def _nearest_category(pos: int) -> str:
        """Return the closest category label that starts before `pos`."""
        best = ""
        for cp, name in cat_positions:
            if cp < pos:
                best = name
            else:
                break
        return best

    products_b: list[dict] = []
    for m_card in re.finditer(r'class="FM_sid_nm', html):
        card_start = m_card.start()
        # Grab ~2 KB of context after the card start to parse its fields
        snippet = html[card_start: card_start + 2048]
        m_name = re.search(
            r'class="FM_sid_nm[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', snippet, re.S
        )
        if not m_name:
            continue
        m_price = re.search(r'id="price-\d+"[^>]*>[\u20B9\u20AC\$£₦]\s*([\d,]+)', snippet)
        m_unit = re.search(
            r'id="price-\d+"[^>]*>[\s\S]{0,80}?/\s*<span[^>]*>([^<]+)</span>', snippet
        )
        m_img = re.search(
            r'<img[^>]+(?:src|data-original|data-src)=["\']([^"\']+)["\']', snippet
        )
        price_val = float(m_price.group(1).replace(",", "")) if m_price else 0.0
        unit = m_unit.group(1).strip() if m_unit else ""
        cat = _nearest_category(card_start)
        products_b.append({
            "name": m_name.group(1).strip(),
            "price": price_val,
            "compare_price": 0.0,
            "discount_pct": 0.0,
            "currency": "INR",
            "description": f"Per {unit}" if unit else "",
            "image_url": m_img.group(1) if m_img else "",
            "category": cat,
            "stock": 0,
        })

    if products_b:
        # If any product got a category via Strategy B, prefer that result set
        if any(p["category"] for p in products_b):
            return products_b
        # Products found but no categories — apply Strategy C url-slug fallback
        if url_slug_category:
            for p in products_b:
                p["category"] = url_slug_category
        return products_b

    # ── Strategy C only: products not found via FM_sid_nm at all ──────────────
    # (rare — means the page loaded without product JS; return empty so the
    # caller can fall through to the heuristic DOM extractor)
    return []


def _extract_product_cards_heuristic(html: str, base_url: str = "") -> list[dict]:
    """
    Look for repeating product card patterns in HTML.
    Targets common e-commerce HTML structures where each product has
    a name, price, and optionally an image wrapped in a card/li/article element.
    """
    products = []
    # Find all price occurrences with surrounding context
    # Pattern: find elements that contain both a price and a nearby heading/title
    card_pattern = re.compile(
        r'<(?:li|article|div|section)[^>]*class=["\'][^"\']*(?:product|item|card|grid-item|col)[^"\']*["\'][^>]*>'
        r'(.*?)'
        r'</(?:li|article|div|section)>',
        re.S | re.I
    )
    name_pattern = re.compile(
        r'<(?:h[1-6]|a|span|p)[^>]*(?:class=["\'][^"\']*(?:name|title|product-name|item-name|product-title)[^"\']*["\'])?[^>]*>\s*([^<]{3,120})\s*</(?:h[1-6]|a|span|p)>',
        re.I
    )
    price_pattern = re.compile(r'[\$£€₹₦]\s?([\d,]+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)\s*(?:USD|GBP|EUR|INR)', re.I)
    img_pattern = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

    seen_names: set = set()
    for card_match in card_pattern.finditer(html):
        card_html = card_match.group(1)
        # Extract name
        name_match = name_pattern.search(card_html)
        if not name_match:
            continue
        name = re.sub(r'\s+', ' ', name_match.group(1)).strip()
        if not name or len(name) < 3 or name.lower() in seen_names:
            continue
        # Extract price
        price_match = price_pattern.search(card_html)
        price = 0.0
        if price_match:
            raw = price_match.group(1) or price_match.group(2) or "0"
            price = _parse_price(raw.replace(",", ""))
        # Extract image
        img_match = img_pattern.search(card_html)
        image_url = ""
        if img_match:
            image_url = img_match.group(1)
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            elif image_url.startswith("/") and base_url:
                from urllib.parse import urlparse as _up
                parsed = _up(base_url)
                image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"

        seen_names.add(name.lower())
        products.append({
            "name": name,
            "price": price,
            "compare_price": 0.0,
            "discount_pct": 0.0,
            "currency": "USD",
            "description": "",
            "image_url": image_url,
            "category": "",
            "stock": 0,
        })

    return products


# ---------------------------------------------------------------------------
# WhatsApp Business catalog shim
# ---------------------------------------------------------------------------

def _is_whatsapp_catalog_url(url: str) -> bool:
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()
    return (
        ("wa.me" in netloc and "/c/" in path)
        or "api.whatsapp.com" in netloc
        or ("business.facebook.com" in netloc and "catalog" in path)
        or ("facebook.com" in netloc and "commerce" in path)
    )


def _scrape_whatsapp_catalog(url: str) -> list[dict]:
    """
    WhatsApp catalog pages (wa.me/c/…) are fully client-side rendered; the
    server-sent HTML shell does not contain product data.

    Strategy:
      1. Check for a Meta Catalog API endpoint if we can extract a catalog_id.
      2. Fetch the URL and look for any JSON-LD / OG / embedded JSON.
      3. If nothing found, return an empty list with a clear message so the
         caller can advise the user to export their catalog as JSON/CSV.
    """
    logger.info("Detected WhatsApp catalog URL: %s", url)

    # Extract phone / catalog id from wa.me/c/<phone_or_id>
    m = re.search(r"wa\.me/c/([^/?#]+)", url)
    catalog_id = m.group(1) if m else None

    # Attempt to fetch the HTML shell and mine any data
    try:
        raw, content_type = _fetch(url)
    except ValueError as exc:
        logger.warning("WhatsApp catalog fetch failed: %s", exc)
        return []

    if "json" in content_type:
        return _parse_json_catalog(raw)
    if "csv" in content_type:
        return _parse_csv_catalog(raw)

    # Try HTML extraction
    products = _parse_html_catalog(raw, base_url=url)
    if products:
        return products

    # Nothing found — return a sentinel so the caller knows the URL type
    logger.info(
        "WhatsApp catalog URL returned no parseable product data. "
        "User should export catalog as JSON or CSV."
    )
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file_catalog(raw: bytes, filename: str, default_currency: str = "USD") -> dict:
    """
    Parse an uploaded file (CSV, JSON, Excel .xlsx/.xls, or plain-text TSV/TXT)
    and return the same ``{ products, source_type, total, warnings }`` dict
    that :func:`scrape_catalog` returns.

    Supported formats (auto-detected from *filename* extension):
      • .csv / .txt / .tsv — tabular with header row
      • .json              — JSON array or object with products list
      • .xlsx / .xls       — Excel workbook (first sheet)
    """
    warnings: list[str] = []
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # ── JSON ──────────────────────────────────────────────────────────────────
    if ext == "json" or (not ext and raw.lstrip()[:1] in (b"[", b"{")):
        try:
            products = _parse_json_catalog(raw)
            if not products:
                warnings.append("No products found in JSON file. Ensure it is an array or object with a 'products' key.")
            return {"products": products, "source_type": "file_json", "total": len(products), "warnings": warnings}
        except Exception as exc:
            return {"products": [], "source_type": "file_json", "total": 0, "warnings": [f"JSON parse error: {exc}"]}

    # ── Excel (.xlsx / .xls) ─────────────────────────────────────────────────
    if ext in ("xlsx", "xls"):
        try:
            import openpyxl  # type: ignore
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return {"products": [], "source_type": "file_excel", "total": 0, "warnings": ["Excel file is empty."]}
            # Convert to CSV-like string for reuse
            header = [str(c).lower().strip() if c is not None else "" for c in rows[0]]
            csv_rows = [header]
            for row in rows[1:]:
                csv_rows.append([str(c) if c is not None else "" for c in row])
            products = _parse_rows(csv_rows, default_currency)
            return {"products": products, "source_type": "file_excel", "total": len(products), "warnings": warnings}
        except ImportError:
            pass  # fall through to CSV attempt
        except Exception as exc:
            return {"products": [], "source_type": "file_excel", "total": 0, "warnings": [f"Excel parse error: {exc}"]}

    # ── CSV / TSV / TXT ───────────────────────────────────────────────────────
    # Try to detect delimiter
    text = raw.decode("utf-8-sig", errors="replace")
    dialect_kw: dict = {}
    sample = text[:4096]
    tab_count = sample.count("\t")
    comma_count = sample.count(",")
    semicolon_count = sample.count(";")
    if tab_count > comma_count and tab_count > semicolon_count:
        dialect_kw["delimiter"] = "\t"
    elif semicolon_count > comma_count:
        dialect_kw["delimiter"] = ";"
    try:
        reader = csv.reader(io.StringIO(text), **dialect_kw)
        rows = [r for r in reader if any(c.strip() for c in r)]
        if len(rows) < 2:
            return {"products": [], "source_type": "file_csv", "total": 0, "warnings": ["CSV file has no data rows."]}
        products = _parse_rows(rows, default_currency)
        if not products:
            warnings.append("No products found. Ensure the file has columns for name/title and price.")
        return {"products": products, "source_type": "file_csv", "total": len(products), "warnings": warnings}
    except Exception as exc:
        return {"products": [], "source_type": "file_csv", "total": 0, "warnings": [f"CSV parse error: {exc}"]}


def _parse_rows(rows: list, default_currency: str = "USD") -> list[dict]:
    """Convert a list of rows (first row = headers) into product dicts."""
    if not rows:
        return []
    raw_headers = [str(c).lower().strip() for c in rows[0]]

    def _col(*candidates):
        for cand in candidates:
            for i, h in enumerate(raw_headers):
                if cand in h:
                    return i
        return None

    idx_name = _col("name", "title", "product")
    idx_price = _col("price", "cost", "amount")
    idx_desc = _col("desc", "detail", "about")
    idx_image = _col("image", "img", "photo", "picture", "url")
    idx_category = _col("categ", "type", "group", "department")
    idx_stock = _col("stock", "qty", "quantity", "inventory")
    idx_currency = _col("currency", "curr")
    idx_compare = _col("compare", "original", "was", "mrp", "rrp")
    idx_discount = _col("discount", "disc", "off")

    products = []
    for row in rows[1:]:
        def _get(idx, default=""):
            if idx is None or idx >= len(row):
                return default
            return str(row[idx]).strip()

        name = _get(idx_name)
        if not name:
            continue
        raw_price = _get(idx_price, "0")
        price = _parse_price(raw_price.replace(",", ""))
        currency = _get(idx_currency, default_currency).upper()[:3] or default_currency
        if not currency:
            currency = _detect_currency(raw_price) or default_currency
        products.append({
            "name": name,
            "price": price,
            "compare_price": _parse_price(_get(idx_compare, "0").replace(",", "")),
            "discount_pct": _parse_price(_get(idx_discount, "0")),
            "currency": currency,
            "description": _get(idx_desc),
            "image_url": _get(idx_image),
            "category": _get(idx_category),
            "stock": int(float(_get(idx_stock, "0") or 0)) if _get(idx_stock) else 0,
        })
    return products


def scrape_catalog(url: str) -> dict:
    """
    Fetch *url* and return::

        {
          "products": [ { name, price, currency, description, image_url,
                          category, stock, compare_price, discount_pct }, … ],
          "source_type": "json" | "csv" | "html_jsonld" | "html_og" | "whatsapp",
          "total": <int>,
          "warnings": [ … ],
        }

    Raises ``ValueError`` on unrecoverable fetch errors.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    warnings: list[str] = []
    source_type = "unknown"

    # WhatsApp catalog URLs need special handling
    if _is_whatsapp_catalog_url(url):
        products = _scrape_whatsapp_catalog(url)
        source_type = "whatsapp"
        if not products:
            warnings.append(
                "WhatsApp catalog pages are rendered by the WhatsApp app and cannot "
                "be scraped directly. Please export your catalog from WhatsApp Business "
                "Manager as a CSV or JSON file and paste that URL instead, or manually "
                "enter products using the Products page."
            )
        return {
            "products": products,
            "source_type": source_type,
            "total": len(products),
            "warnings": warnings,
        }

    raw, content_type = _fetch(url)
    logger.info("Fetched catalog URL %s — content_type=%s  size=%d bytes", url, content_type, len(raw))

    if "json" in content_type:
        products = _parse_json_catalog(raw)
        source_type = "json"
    elif "csv" in content_type or url.lower().endswith(".csv"):
        products = _parse_csv_catalog(raw)
        source_type = "csv"
    elif "html" in content_type or "xml" in content_type:
        products = _parse_html_catalog(raw, base_url=url)
        source_type = "html_jsonld" if products else "html_og"
        if not products:
            warnings.append(
                "No structured product data (JSON-LD / JSON) found on this page. "
                "Try a direct JSON or CSV export URL from your catalog platform."
            )
    else:
        # Try JSON first, then CSV, then HTML
        for parser_fn, stype in [
            (_parse_json_catalog, "json"),
            (_parse_csv_catalog, "csv"),
            (lambda d: _parse_html_catalog(d, url), "html_jsonld"),
        ]:
            try:
                products = parser_fn(raw)
                if products:
                    source_type = stype
                    break
            except Exception:
                continue
        else:
            products = []
            warnings.append(f"Could not parse catalog from content-type {content_type!r}.")

    logger.info(
        "Catalog scrape complete — source=%s  products=%d  warnings=%d",
        source_type, len(products), len(warnings),
    )
    return {
        "products": products,
        "source_type": source_type,
        "total": len(products),
        "warnings": warnings,
    }
