import re
from agents.crew import _extract_expected_spec, _enforce_generated_html_spec
from tools.website_scraper import scrape_website, prompt_context_from_scraped_data

refs = [
    "https://www.w3schools.com/html/html5_video.asp",
    "https://www.w3schools.com/html/html5_audio.asp",
]
ctx = []
for url in refs:
    data = scrape_website(url)
    ctx.append(prompt_context_from_scraped_data(data))

prompt = "=== WEBSITE BUILD SPECIFICATION ===\nWEBSITE NAME: Media Reference Demo\n\n" + "\n\n".join(ctx)
spec = _extract_expected_spec(prompt)
print("SPEC_COUNTS", len(spec.get("media_videos", [])), len(spec.get("media_audios", [])), len(spec.get("media_embeds", [])))

with open("output/staging/media-reference-e2e-demo-v2/legacy/index.html", "r", encoding="utf-8", errors="ignore") as fh:
    html = fh.read()

print("BEFORE_COUNTS", len(re.findall(r"<video\\b", html, flags=re.I)), len(re.findall(r"<audio\\b", html, flags=re.I)))
out = _enforce_generated_html_spec(html, prompt)
print("AFTER_COUNTS", len(re.findall(r"<video\\b", out, flags=re.I)), len(re.findall(r"<audio\\b", out, flags=re.I)))

m = re.search(r'(<section[^>]*id=["\']media["\'][^>]*>.*?</section>)', out, flags=re.I | re.S)
if m:
    sec = m.group(1)
    print("MEDIA_SECTION_START")
    print(sec[:1200])
    print("MEDIA_SECTION_END")
else:
    print("NO_MEDIA_SECTION_MATCH")
