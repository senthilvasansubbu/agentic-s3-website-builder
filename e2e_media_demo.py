import os
import re

from agents.crew import build_website
from tools.website_scraper import prompt_context_from_scraped_data, scrape_website


def main() -> None:
    refs = [
        "https://www.w3schools.com/html/html5_video.asp",
        "https://mmgk.org/tutorial/",
    ]
    project_name = "media-reference-dual-demo"

    ctx_parts = []
    for url in refs:
        print("SCRAPE", url)
        data = scrape_website(url)
        print("MEDIA_COUNTS", len(data.get("videos", [])), len(data.get("audios", [])), len(data.get("embeds", [])))
        ctx_parts.append(prompt_context_from_scraped_data(data))

    prompt = (
        "=== WEBSITE BUILD SPECIFICATION ===\n"
        "WEBSITE NAME: Media Reference Demo (Video + Audio)\n"
        "CRITICAL: Include usable media content from detected reference URLs.\n\n"
        "Create a clean demo website with hero, about, and media sections.\n\n"
        + "\n\n".join(ctx_parts)
    )

    result = build_website(
        user_requirements=prompt,
        project_name=project_name,
        theme_key="modern",
        build_mode="combined",
        output_target="legacy",
    )

    output_dir = result.get("output_dir", "")
    index_path = os.path.join(output_dir, "index.html")
    print("OUTPUT_DIR", output_dir)
    print("FALLBACK", result.get("fallback", False))
    print("INDEX", index_path)

    with open(index_path, "r", encoding="utf-8", errors="ignore") as fh:
        html = fh.read()

    print("VIDEO_COUNT", len(re.findall(r"<video\\b", html, flags=re.I)))
    print("AUDIO_COUNT", len(re.findall(r"<audio\\b", html, flags=re.I)))
    print("IFRAME_COUNT", len(re.findall(r"<iframe\\b", html, flags=re.I)))
    print("HAS_MEDIA_ID", bool(re.search(r"id=[\"']media[\"']", html, flags=re.I)))

    print("HITS_START")
    patterns = [r"<video\\b", r"<audio\\b", r"<source\\b", r"<iframe\\b", r"id=[\"']media[\"']"]
    shown = 0
    for line in html.splitlines():
        s = line.strip()
        if any(re.search(pattern, s, flags=re.I) for pattern in patterns):
            print(s)
            shown += 1
            if shown >= 12:
                break
    print("HITS_END")


if __name__ == "__main__":
    main()
