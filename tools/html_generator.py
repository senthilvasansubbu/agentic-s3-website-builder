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
          staging/
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
    site_dir = os.path.join(base, "staging", slug)
    for sub in ("pages", "assets/css", "assets/js", "assets/images"):
        os.makedirs(os.path.join(site_dir, sub), exist_ok=True)
    return site_dir


def generate_html(design_spec: dict, code: str, project_name: str,
                  page_name: str = "index") -> str:
    """Write an HTML page into the website's subfolder.

    - page_name='index'  → saved as  output/staging/<slug>/index.html
    - page_name='about'  → saved as  output/staging/<slug>/pages/about.html
    """

    site_dir = _website_dir(project_name)

    # Save images, CSS, JS to their respective folders (support nested folders)
    images = design_spec.get('images', {})
    for fname, img_bytes in images.items():
        img_folder, img_file = os.path.split(fname)
        img_dir = os.path.join(site_dir, 'assets/images', img_folder)
        os.makedirs(img_dir, exist_ok=True)
        img_path = os.path.join(img_dir, img_file)
        with open(img_path, 'wb') as imgf:
            imgf.write(img_bytes)

    css_files = design_spec.get('css', {})
    for fname, css_code in css_files.items():
        css_folder, css_file = os.path.split(fname)
        css_dir = os.path.join(site_dir, 'assets/css', css_folder)
        os.makedirs(css_dir, exist_ok=True)
        css_path = os.path.join(css_dir, css_file)
        with open(css_path, 'w', encoding='utf-8') as cssf:
            cssf.write(css_code)

    js_files = design_spec.get('js', {})
    for fname, js_code in js_files.items():
        js_folder, js_file = os.path.split(fname)
        js_dir = os.path.join(site_dir, 'assets/js', js_folder)
        os.makedirs(js_dir, exist_ok=True)
        js_path = os.path.join(js_dir, js_file)
        with open(js_path, 'w', encoding='utf-8') as jsf:
            jsf.write(js_code)

    # Update HTML code to use relative paths for images, CSS, JS (support nested folders)
    html_code = code
    for fname in images:
        rel_path = f"assets/images/{fname}"
        html_code = html_code.replace(f'/static/uploads/{fname}', rel_path)
        html_code = html_code.replace(f'uploads/{fname}', rel_path)
    for fname in css_files:
        rel_path = f"assets/css/{fname}"
        html_code = html_code.replace(f'/static/css/{fname}', rel_path)
    for fname in js_files:
        rel_path = f"assets/js/{fname}"
        html_code = html_code.replace(f'/static/js/{fname}', rel_path)

    if page_name == "index":
        filepath = os.path.join(site_dir, "index.html")
    else:
        safe = re.sub(r"[^\w-]", "", page_name.lower().replace(" ", "-"))
        filepath = os.path.join(site_dir, "pages", f"{safe}.html")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_code)

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
