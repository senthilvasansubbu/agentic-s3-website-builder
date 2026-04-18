import os
import json
from datetime import datetime

def generate_html(design_spec: dict, code: str, project_name: str) -> str:
    """Generate a complete HTML file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project_name.replace(' ', '_')}_{timestamp}.html"
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
    
    return filepath


def create_index_html(files: list, project_name: str) -> str:
    """Create an index HTML file listing all generated files"""
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "index.html")

    links = "".join(
        f'<li><a href="{os.path.basename(f)}">{os.path.basename(f)}</a></li>'
        for f in files
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{project_name}</title></head>
<body>
<h1>{project_name}</h1>
<ul>{links}</ul>
</body>
</html>"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filepath