from crewai import Task, Crew, Process
from agents.theme_agent import theme_agent
from agents.designer_agent import designer_agent
"""
Modular orchestrator entrypoint for website builder (replaces legacy monolith).
All orchestrator logic is now imported from modular wb_* helpers.
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
from config.settings import settings
from tools.theme_builder import THEMES

import logging

# Create a logger for the crew module
logger = logging.getLogger("crew")
logger.setLevel(logging.DEBUG)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Retry helper for CrewAI pipeline
import time
_MAX_RETRIES = 3
def _with_retry(fn, *args, trace_id=None, **kwargs):
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if trace_id:
                logger.warning(f"[{trace_id}] Retry {attempt+1}/{_MAX_RETRIES} failed: {exc}")
            time.sleep(1.5 * (attempt + 1))
    if trace_id:
        logger.error(f"[{trace_id}] All retries failed: {last_exc}")
    raise last_exc

__all__ = [
    "extract_expected_spec",
    "enforce_generated_html_spec",
    "generate_static_fallback",
    "sync_legacy_entrypoint",
    "write_output_target_scaffold",
    "create_website_crew",
    "build_website",
    "inject_products_section",
    "logger",
    "settings",
    "_with_retry",
    "_MAX_RETRIES",
    "THEMES",
    "designer_agent",
    "theme_agent",
    "Task",
    "Crew",
    "Process",
]

# Legacy compatibility for tests/scripts
_enforce_generated_html_spec = enforce_generated_html_spec
_extract_expected_spec = extract_expected_spec

# The orchestrator logic is now fully modularized and imported above.
# Use build_website(...) as the main entrypoint for website generation.

