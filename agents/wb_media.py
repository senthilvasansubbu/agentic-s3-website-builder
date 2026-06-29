"""
Media section injection and enrichment helpers for website builder.
Extracted from legacy orchestrator for modular use.
"""

import re
from typing import List

def inject_or_enrich_media_section(
    html_code: str,
    media_videos: List[str],
    media_audios: List[str],
    media_embeds: List[str],
) -> str:
    """
    Inject or enrich a <section id="media"> block with video, audio, and embed elements as needed.
    Ensures all reference media are present in the output HTML.
    """
    fixed = html_code
    current_video_count = len(re.findall(r"<video\\b", fixed, re.I))
    current_audio_count = len(re.findall(r"<audio\\b", fixed, re.I))
    current_embed_count = len(re.findall(r"<iframe[^>]+src=[\"']?[^\"'>]*(youtube|youtu\\.be|vimeo|soundcloud)[^\"'>]*[\"']?", fixed, re.I))
    has_media_section = bool(re.search(r'id=["\'](?:media|multimedia|video|audio)["\']', fixed, re.I))


    inject_videos = []
    inject_audios = []
    inject_embeds = []

    # Only inject a video if there are no <video> tags anywhere
    if media_videos and current_video_count == 0:
        inject_videos = media_videos

    # Only inject an audio if there are no <audio> tags anywhere
    if media_audios and current_audio_count == 0:
        inject_audios = media_audios

    # Only inject an embed if there are no known embeds
    if media_embeds and current_embed_count == 0:
        inject_embeds = media_embeds

    # Only inject the media section if at least one type is missing
    if not (inject_videos or inject_audios or inject_embeds):
        return fixed

    media_blocks: List[str] = []

    if inject_embeds:
        media_blocks += [
            '  <div class="media-group media-group-embed" style="margin:16px 0">',
            '    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px">',
            '      <h3 style="margin:0">Embedded Media</h3>',
        ]
        if len(inject_embeds) > 1:
            media_blocks += [
                '      <label style="display:flex;align-items:center;gap:8px;font-size:0.95rem">',
                '        <span>Choose:</span>',
                '        <select aria-label="Choose embedded media" onchange="var t=this.closest(\'.media-group\').querySelector(\'#\'+this.value);if(t){t.scrollIntoView({behavior:\'smooth\',inline:\'start\',block:\'nearest\'});}">',
            ]
            for idx in range(len(inject_embeds)):
                item_id = f"media-embed-{current_embed_count + idx + 1}"
                media_blocks.append(f"          <option value=\"{item_id}\">Embed {idx + 1}</option>")
            media_blocks += [
                '        </select>',
                '      </label>',
            ]
        media_blocks += [
            '    </div>',
            '    <div class="media-scroll" style="display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px">',
        ]
        for idx, embed_src in enumerate(inject_embeds, start=1):
            embed_id = f"media-embed-{current_embed_count + idx}"
            media_blocks += [
                f'      <article id="{embed_id}" class="media-item" style="flex:0 0 min(560px,100%);scroll-snap-align:start">',
                f'        <iframe src="{embed_src}" title="Embedded media {idx}" loading="lazy" allowfullscreen style="width:100%;min-height:360px;border:0;border-radius:12px"></iframe>',
                '      </article>',
            ]
        media_blocks += [
            '    </div>',
            '  </div>',
        ]

    if inject_videos:
        media_blocks += [
            '  <div class="media-group media-group-video" style="margin:16px 0">',
            '    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px">',
            '      <h3 style="margin:0">Video Playlist</h3>',
        ]
        if len(inject_videos) > 1:
            media_blocks += [
                '      <label style="display:flex;align-items:center;gap:8px;font-size:0.95rem">',
                '        <span>Choose:</span>',
                '        <select aria-label="Choose a video" onchange="var t=this.closest(\'.media-group\').querySelector(\'#\'+this.value);if(t){t.scrollIntoView({behavior:\'smooth\',inline:\'start\',block:\'nearest\'});}">',
            ]
            for idx in range(len(inject_videos)):
                item_id = f"media-video-{current_video_count + idx + 1}"
                media_blocks.append(f"          <option value=\"{item_id}\">Video {idx + 1}</option>")
            media_blocks += [
                '        </select>',
                '      </label>',
            ]
        media_blocks += [
            '    </div>',
            '    <div class="media-scroll" style="display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px">',
        ]
        for idx, video_src in enumerate(inject_videos, start=1):
            video_id = f"media-video-{current_video_count + idx}"
            media_blocks += [
                f'      <article id="{video_id}" class="media-item" style="flex:0 0 min(560px,100%);scroll-snap-align:start">',
                '        <video controls preload="metadata" style="width:100%;border-radius:12px">',
                f'          <source src="{video_src}">',
                '          Your browser does not support the video tag.',
                '        </video>',
                '      </article>',
            ]
        media_blocks += [
            '    </div>',
            '  </div>',
        ]

    if inject_audios:
        media_blocks += [
            '  <div class="media-group media-group-audio" style="margin:16px 0">',
            '    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px">',
            '      <h3 style="margin:0">Audio Playlist</h3>',
        ]
        if len(inject_audios) > 1:
            media_blocks += [
                '      <label style="display:flex;align-items:center;gap:8px;font-size:0.95rem">',
                '        <span>Choose:</span>',
                '        <select aria-label="Choose an audio track" onchange="var t=this.closest(\'.media-group\').querySelector(\'#\'+this.value);if(t){t.scrollIntoView({behavior:\'smooth\',inline:\'start\',block:\'nearest\'});}">',
            ]
            for idx in range(len(inject_audios)):
                item_id = f"media-audio-{current_audio_count + idx + 1}"
                media_blocks.append(f"          <option value=\"{item_id}\">Audio {idx + 1}</option>")
            media_blocks += [
                '        </select>',
                '      </label>',
            ]
        media_blocks += [
            '    </div>',
            '    <div class="media-scroll" style="display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:8px">',
        ]
        for idx, audio_src in enumerate(inject_audios, start=1):
            audio_id = f"media-audio-{current_audio_count + idx}"
            media_blocks += [
                f'      <article id="{audio_id}" class="media-item" style="flex:0 0 min(460px,100%);scroll-snap-align:start;padding:14px;border:1px solid rgba(0,0,0,.08);border-radius:12px">',
                f'        <h4 style="margin:0 0 10px">Track {idx}</h4>',
                '        <audio controls preload="metadata" style="width:100%">',
                f'          <source src="{audio_src}">',
                '          Your browser does not support the audio tag.',
                '        </audio>',
                '      </article>',
            ]
        media_blocks += [
            '    </div>',
            '  </div>',
        ]

    if media_blocks:
        media_payload = "\n" + "\n".join(media_blocks) + "\n"
        media_section_pattern = re.compile(
            r'(<section[^>]*id=["\'](?:media|multimedia|video|audio)["\'][^>]*>)(.*?)(</section>)',
            re.I | re.S,
        )
        m = media_section_pattern.search(fixed)
        if m:
            new_section = m.group(1) + m.group(2) + media_payload + m.group(3)
            fixed = fixed[:m.start()] + new_section + fixed[m.end():]
        else:
            # Insert new media section before </main> or </body>
            parts = [
                '\n<section id="media" aria-labelledby="media-heading" class="reveal">',
                '  <h2 id="media-heading">Media Highlights</h2>',
                '  <p class="subheading">Curated media from your reference links.</p>',
                *media_blocks,
                '</section>\n',
            ]
            media_section = "\n".join(parts)
            if "</main>" in fixed:
                fixed = fixed.replace("</main>", media_section + "\n</main>", 1)
            elif "</body>" in fixed:
                fixed = fixed.replace("</body>", media_section + "\n</body>", 1)
            else:
                fixed += media_section
    return fixed
