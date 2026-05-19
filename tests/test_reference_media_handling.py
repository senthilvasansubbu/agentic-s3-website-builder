from agents.crew import _enforce_generated_html_spec, _extract_expected_spec


def _prompt_with_media() -> str:
    return """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Demo Site

=== EXTRACTED FROM EXISTING WEBSITE ===
Source URL: https://example.com

Detected Video Assets (re-use these where relevant):
  1. https://cdn.example.com/media/intro.mp4

Detected Audio Assets (re-use these where relevant):
  1. https://cdn.example.com/media/theme.mp3

Detected Embedded Media URLs (YouTube/Vimeo/SoundCloud):
  1. https://www.youtube.com/embed/abc123
"""


def _prompt_with_multiple_media() -> str:
    return """
=== WEBSITE BUILD SPECIFICATION ===
WEBSITE NAME: Demo Site Multi

=== EXTRACTED FROM EXISTING WEBSITE ===
Source URL: https://example.com

Detected Video Assets (re-use these where relevant):
  1. https://cdn.example.com/media/intro.mp4
  2. https://cdn.example.com/media/overview.mp4

Detected Audio Assets (re-use these where relevant):
  1. https://cdn.example.com/media/theme.mp3
  2. https://cdn.example.com/media/voiceover.mp3

Detected Embedded Media URLs (YouTube/Vimeo/SoundCloud):
  1. https://www.youtube.com/embed/abc123
  2. https://player.vimeo.com/video/456789
"""


def test_extract_expected_spec_parses_reference_media_urls():
    spec = _extract_expected_spec(_prompt_with_media())

    assert spec["media_videos"] == ["https://cdn.example.com/media/intro.mp4"]
    assert spec["media_audios"] == ["https://cdn.example.com/media/theme.mp3"]
    assert spec["media_embeds"] == ["https://www.youtube.com/embed/abc123"]


def test_enforce_generated_html_spec_injects_media_section_when_missing():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"hero\"><h1>Welcome</h1></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert 'id="media"' in out
    assert '<video controls preload="metadata"' in out
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out
    assert 'https://cdn.example.com/media/intro.mp4' in out
    assert 'https://cdn.example.com/media/theme.mp3' in out


def test_enforce_generated_html_spec_injects_only_missing_media_types():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"hero\"><h1>Welcome</h1></section>
  <section id=\"existing\"><video controls src=\"https://cdn.example.com/has-video.mp4\"></video></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    assert out.count('<video controls') == 1
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out


def test_enforce_generated_html_spec_enriches_existing_media_section():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"media\"><h2>Media Highlights</h2></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    assert '<video controls preload="metadata"' in out
    assert '<audio controls preload="metadata"' in out
    assert 'https://www.youtube.com/embed/abc123' in out


def test_enforce_generated_html_spec_keeps_video_and_audio_in_single_media_section():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id=\"media\">
    <h2>Media Highlights</h2>
    <video controls preload=\"metadata\">
      <source src=\"https://cdn.example.com/media/intro.mp4\" />
    </video>
  </section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_media())

    assert out.count('id="media"') == 1
    media_start = out.index('<section id="media"')
    media_end = out.index('</section>', media_start)
    media_block = out[media_start:media_end]

    assert '<video controls preload="metadata"' in media_block
    assert '<audio controls preload="metadata"' in media_block
    assert 'https://cdn.example.com/media/intro.mp4' in media_block
    assert 'https://cdn.example.com/media/theme.mp3' in media_block


def test_enforce_generated_html_spec_injects_multiple_media_items_with_selector_and_scroll():
    html = """<!doctype html>
<html>
<head><title>Placeholder</title></head>
<body>
<main>
  <section id="hero"><h1>Welcome</h1></section>
</main>
</body>
</html>"""

    out = _enforce_generated_html_spec(html, _prompt_with_multiple_media())

    assert out.count('<video controls preload="metadata"') == 2
    assert out.count('<audio controls preload="metadata"') == 2
    assert out.count('<iframe src="') >= 2
    assert 'https://cdn.example.com/media/intro.mp4' in out
    assert 'https://cdn.example.com/media/overview.mp4' in out
    assert 'https://cdn.example.com/media/theme.mp3' in out
    assert 'https://cdn.example.com/media/voiceover.mp3' in out
    assert 'https://www.youtube.com/embed/abc123' in out
    assert 'https://player.vimeo.com/video/456789' in out
    assert 'class="media-scroll"' in out
    assert 'aria-label="Choose a video"' in out
    assert 'aria-label="Choose an audio track"' in out
