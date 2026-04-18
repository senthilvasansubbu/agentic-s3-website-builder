import os
import re
from datetime import datetime


def _slugify(name: str) -> str:
    """Convert a project name to a safe folder name, e.g. 'My Shop!' → 'my-shop'."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "website"


def _website_dir(project_name: str) -> str:
    """Return the output subfolder path for a given project, creating it if needed.

    Structure:
        output/
          <website-slug>/
            index.html          ← main page
            pages/              ← additional pages
            assets/
              css/
              js/
              images/
    """
    base = os.getenv("OUTPUT_DIR", "output")
    slug = _slugify(project_name)
    site_dir = os.path.join(base, slug)
    for sub in ("pages", "assets/css", "assets/js", "assets/images"):
        os.makedirs(os.path.join(site_dir, sub), exist_ok=True)
    return site_dir


def generate_html(design_spec: dict, code: str, project_name: str,
                  page_name: str = "index") -> str:
    """Write an HTML page into the website's subfolder.

    - page_name='index'  → saved as  output/<slug>/index.html
    - page_name='about'  → saved as  output/<slug>/pages/about.html
    """
    site_dir = _website_dir(project_name)

    if page_name == "index":
        filepath = os.path.join(site_dir, "index.html")
    else:
        safe = re.sub(r"[^\w-]", "", page_name.lower().replace(" ", "-"))
        filepath = os.path.join(site_dir, "pages", f"{safe}.html")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)

    return filepath


def create_index_html(files: list, project_name: str) -> str:
    """Create (or overwrite) the index.html listing all generated pages."""
    site_dir = _website_dir(project_name)
    filepath = os.path.join(site_dir, "index.html")

    links = "".join(
        f'<li><a href="{os.path.relpath(f, site_dir)}">{os.path.basename(f)}</a></li>'
        for f in files
        if os.path.basename(f) != "index.html"
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{project_name}</title>
  <style>
    body{{font-family:sans-serif;max-width:800px;margin:40px auto;padding:0 20px}}
    h1{{color:#667eea}}ul{{list-style:none;padding:0}}
    li{{margin:10px 0}}a{{color:#667eea;text-decoration:none;font-weight:600}}
    a:hover{{text-decoration:underline}}
  </style>
</head>
<body>
  <h1>{project_name}</h1>
  <p>Generated pages:</p>
  <ul>{links}</ul>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def get_website_dir(project_name: str) -> str:
    """Public helper — returns the website output directory path."""
    return _website_dir(project_name)
