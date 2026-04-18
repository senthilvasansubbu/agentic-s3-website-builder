#!/usr/bin/env python3
"""
End-to-end build tests for the agentic website builder.

Tests:
  1. No cart, no search bar
  2. Shopping cart (categories + images + discounts), no search bar
  3. Shopping cart + search bar

Usage:
    python scripts/run_build_tests.py [--base-url http://localhost:8000] [--email admin@test.com] [--password secret]
"""
import argparse
import json
import sys
import time
import requests
from datetime import datetime

# ── CLI args ───────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--base-url", default="http://localhost:8000")
parser.add_argument("--email",    default="admin@example.com")
parser.add_argument("--password", default="changeme")
args = parser.parse_args()

BASE = args.base_url.rstrip("/")
API  = f"{BASE}/api/v1"

DIVIDER = "=" * 70

# ── Colours ────────────────────────────────────────────────────────────────────
RED   = "\033[31m"
GREEN = "\033[32m"
CYAN  = "\033[36m"
YELLOW= "\033[33m"
BOLD  = "\033[1m"
RESET = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def err(msg):  print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ  {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠  {msg}{RESET}")
def step(msg): print(f"\n{BOLD}{CYAN}{msg}{RESET}")
def section(title):
    print(f"\n{BOLD}{DIVIDER}")
    print(f"  {title}")
    print(f"{DIVIDER}{RESET}")

# ── Test definitions ───────────────────────────────────────────────────────────
TESTS = [
    {
        "label": "Test 1 — Basic site (no cart, no search bar)",
        "create": {
            "name":  "Green Valley Bakery",
            "title": "Green Valley Bakery",
            "description": "Artisan sourdough breads, pastries, and custom cakes crafted fresh daily.",
            "theme": "modern",
            "include_shopping_cart": False,
            "cart_features": [],
            "enable_chatbot": False,
            "num_pages": 1,
        },
        "build": {
            "requirements": (
                "Build a premium bakery website for Green Valley Bakery. "
                "Categories: Sourdough Breads, Croissants, Custom Cakes, Seasonal Pastries. "
                "We are located at 45 Maple Street, Portland OR 97201. "
                "Phone: +1-503-555-0192. Email: hello@greenvalleybakery.com"
            ),
            "use_web_search": False,
            "use_social_search": False,
            "categories": ["Sourdough Breads", "Croissants", "Custom Cakes", "Seasonal Pastries"],
            "location": "45 Maple Street, Portland OR 97201",
            "email": "hello@greenvalleybakery.com",
            "phone": "+1-503-555-0192",
            "booking_prefix": "BKY",
        },
    },
    {
        "label": "Test 2 — Shopping cart, no search bar",
        "create": {
            "name":  "Nova Tech Store",
            "title": "Nova Tech Store",
            "description": "Premium electronics, accessories, and smart home gadgets.",
            "theme": "ecommerce",
            "include_shopping_cart": True,
            "cart_features": ["categories", "images", "discounts", "coupons", "flash_offers", "reviews"],
            "enable_chatbot": False,
            "num_pages": 1,
        },
        "build": {
            "requirements": (
                "Build a sleek e-commerce site for Nova Tech Store selling premium electronics. "
                "Categories: Smartphones, Laptops, Smart Home, Accessories, Wearables. "
                "Include product cards with images, prices, discount badges, and coupon support. "
                "Add a flash-sale countdown section. No search bar needed."
            ),
            "use_web_search": False,
            "use_social_search": False,
            "categories": ["Smartphones", "Laptops", "Smart Home", "Accessories", "Wearables"],
            "location": "280 Silicon Ave, San Jose CA 95110",
            "email": "support@novatechstore.com",
            "phone": "+1-408-555-0177",
            "booking_prefix": "NTS",
        },
    },
    {
        "label": "Test 3 — Shopping cart + search bar",
        "create": {
            "name":  "Lush Garden Centre",
            "title": "Lush Garden Centre",
            "description": "Indoor plants, garden tools, seeds, and landscaping services.",
            "theme": "nature",
            "include_shopping_cart": True,
            "cart_features": ["categories", "images", "price_filter", "discounts",
                              "coupons", "reviews", "wishlist", "search"],
            "enable_chatbot": True,
            "num_pages": 1,
        },
        "build": {
            "requirements": (
                "Build a beautiful garden centre website for Lush Garden Centre. "
                "Categories: Indoor Plants, Outdoor Plants, Seeds & Bulbs, Garden Tools, Pots & Planters. "
                "Include a search bar for products, a price filter, wishlist buttons, and a coupon field at checkout. "
                "Add a chatbot for gardening advice."
            ),
            "use_web_search": False,
            "use_social_search": False,
            "categories": ["Indoor Plants", "Outdoor Plants", "Seeds & Bulbs", "Garden Tools", "Pots & Planters"],
            "location": "12 Bloom Street, Austin TX 78701",
            "email": "hello@lushgardencentre.com",
            "phone": "+1-512-555-0143",
            "booking_prefix": "GRD",
        },
    },
]

# ── Runner ─────────────────────────────────────────────────────────────────────
results = []

def run_test(idx: int, test: dict, token: str) -> dict:
    label   = test["label"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    result  = {"label": label, "passed": False, "website_id": None,
                "output": None, "trace_id": None, "errors": []}

    section(f"[{idx+1}/3] {label}")

    # ── Step 1: Create website record ─────────────────────
    step("  Step 1 of 3 — Creating website record…")
    t0 = time.time()
    r = requests.post(f"{API}/websites", headers=headers, json=test["create"], timeout=30)
    elapsed = time.time() - t0
    if r.status_code not in (200, 201):
        err(f"POST /websites → HTTP {r.status_code}  ({elapsed:.1f}s)")
        err(f"Body: {r.text[:300]}")
        result["errors"].append(f"create HTTP {r.status_code}: {r.text[:200]}")
        return result
    data = r.json()
    website_id = data.get("website_id")
    if not website_id:
        err(f"No website_id in response: {data}")
        result["errors"].append("No website_id returned")
        return result
    ok(f"Created  website_id={website_id}  ({elapsed:.1f}s)")
    result["website_id"] = website_id

    # ── Step 2: Build website ─────────────────────────────
    step("  Step 2 of 3 — Building website (AI / fallback)…")
    info(f"  cart_features = {test['create'].get('cart_features')}")
    info(f"  categories    = {test['build'].get('categories')}")
    t0 = time.time()
    r = requests.post(f"{API}/websites/{website_id}/build",
                      headers=headers, json=test["build"], timeout=300)
    elapsed = time.time() - t0
    if r.status_code != 200:
        err(f"POST /websites/{website_id}/build → HTTP {r.status_code}  ({elapsed:.1f}s)")
        err(f"Body: {r.text[:400]}")
        result["errors"].append(f"build HTTP {r.status_code}: {r.text[:300]}")
        return result
    data = r.json()
    trace_id = data.get("trace_id", "n/a")
    output   = data.get("output") or data.get("message")
    ok(f"Built successfully  trace_id={trace_id}  ({elapsed:.1f}s)")
    info(f"  output → {output}")
    result["output"]   = output
    result["trace_id"] = trace_id

    # ── Step 3: Verify status in DB ───────────────────────
    step("  Step 3 of 3 — Verifying website status…")
    r = requests.get(f"{API}/websites/my", headers=headers, timeout=15)
    if r.status_code == 200:
        sites = r.json()
        match = next((s for s in sites if s.get("website_id") == website_id), None)
        if match:
            status = match.get("status")
            if status == "built":
                ok(f"DB status = 'built'  ✔")
            else:
                warn(f"DB status = '{status}' (expected 'built')")
                result["errors"].append(f"Unexpected DB status: {status}")
        else:
            warn("Website record not found in /websites/my list")
    else:
        warn(f"GET /websites/my → HTTP {r.status_code}")

    result["passed"] = len(result["errors"]) == 0
    return result


def main():
    print(f"\n{BOLD}{DIVIDER}")
    print(f"  Agentic Website Builder — Build Test Suite")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  BASE={BASE}")
    print(f"{DIVIDER}{RESET}")

    # ── Health check ──────────────────────────────────────
    step("Checking server health…")
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        ok(f"Server responding  HTTP {r.status_code}")
    except Exception as e:
        err(f"Server not reachable at {BASE}: {e}")
        sys.exit(1)

    # ── Login ─────────────────────────────────────────────
    step("Authenticating…")
    try:
        r = requests.post(f"{API}/auth/login",
                          json={"email": args.email, "password": args.password}, timeout=15)
        if r.status_code != 200:
            err(f"Login failed HTTP {r.status_code}: {r.text[:200]}")
            sys.exit(1)
        token = r.json().get("access_token") or r.json().get("token")
        if not token:
            err(f"No token in login response: {r.json()}")
            sys.exit(1)
        ok(f"Logged in as {args.email}")
    except Exception as e:
        err(f"Login error: {e}")
        sys.exit(1)

    # ── Run tests ──────────────────────────────────────────
    all_results = []
    for i, test in enumerate(TESTS):
        res = run_test(i, test, token)
        all_results.append(res)

    # ── Summary ────────────────────────────────────────────
    section("SUMMARY")
    passed = 0
    for i, res in enumerate(all_results):
        status = f"{GREEN}PASS{RESET}" if res["passed"] else f"{RED}FAIL{RESET}"
        print(f"  [{i+1}] {status}  {res['label']}")
        if res.get("trace_id"): info(f"       trace_id={res['trace_id']}")
        if res.get("output"):   info(f"       output  ={res['output']}")
        for e in res.get("errors", []):
            err(f"       {e}")
        if res["passed"]:
            passed += 1
    print(f"\n{BOLD}  {passed}/{len(TESTS)} tests passed{RESET}")
    print(f"  Check logs/website_builder.log for full trace details\n")

    sys.exit(0 if passed == len(TESTS) else 1)


if __name__ == "__main__":
    main()
