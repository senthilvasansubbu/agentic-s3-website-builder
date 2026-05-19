"""Shared staging artifact contract for generated and edited websites.

This module defines the folder layout used by staging, preview, and deploy
flows so the generator, editor, and deployment code can share one source of
truth.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StagingArtifactContract:
    """Describe the canonical on-disk structure for a staged website."""

    entry_html: str = "index.html"
    pages_dir: str = "pages"
    assets_dir: str = "assets"
    css_dir: str = "assets/css"
    js_dir: str = "assets/js"
    images_dir: str = "assets/images"
    audio_dir: str = "assets/audio"
    video_dir: str = "assets/video"
    manifest_file: str = "staging-manifest.json"

    def asset_dirs(self) -> Dict[str, str]:
        return {
            "css": self.css_dir,
            "js": self.js_dir,
            "images": self.images_dir,
            "audio": self.audio_dir,
            "video": self.video_dir,
        }


STAGING_CONTRACT = StagingArtifactContract()
