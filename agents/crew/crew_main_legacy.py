"""
Legacy orchestrator entrypoint using modular wb_* helpers.
This file wires up the orchestrator using the modularized logic from wb_websitebuilder.py and related modules.
"""

from agents.wb_websitebuilder import (
    extract_expected_spec,
    enforce_generated_html_spec,
    generate_static_fallback,
    sync_legacy_entrypoint,
    write_output_target_scaffold,
    create_website_crew,
    build_website,
)
from agents.wb_sections import inject_products_section

# Optionally, re-export for compatibility
__all__ = [
    "extract_expected_spec",
    "enforce_generated_html_spec",
    "generate_static_fallback",
    "sync_legacy_entrypoint",
    "write_output_target_scaffold",
    "create_website_crew",
    "build_website",
    "inject_products_section",
]

# The orchestrator logic is now fully modularized and imported above.
# You can call build_website(...) as the main entrypoint for website generation.
