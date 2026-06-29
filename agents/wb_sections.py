"""
Section helpers for modular website builder.
Contains extracted section logic from crew_main_legacy.py.
"""

import re
from typing import List

def inject_products_section(html_code: str, categories: List[str]) -> str:
    """Injects a products section with cards for each category if not present."""
    if not categories:
        return html_code

    cards = []
    for i, cat in enumerate(categories[:6], start=1):
        seed = re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-") or f"product-{i}"
        cards.append(
            f'''
    <article style="background:#fff;border-radius:14px;padding:16px;box-shadow:0 6px 18px rgba(0,0,0,.08)">
    <img src="https://picsum.photos/seed/{seed}/480/320" alt="{cat}" loading="lazy" style="width:100%;height:180px;object-fit:cover;border-radius:10px" />
    <h3 style="margin:12px 0 8px">{cat}</h3>
    <p style="margin:0;color:#475569">High-quality {cat} solutions for laboratory and diagnostic workflows.</p>
    </article>
'''
        )

    section = (
        "\n<section id=\"products\" aria-labelledby=\"products-heading\" style=\"padding:64px 5%;background:#f8fafc\">\n"
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
