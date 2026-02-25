"""
Shared configuration for the Learning Content Pipeline.

Paths, regex patterns, slug helpers, and default values used by all stages.
"""

import os
import re

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(ROOT_DIR, "input")
MODULES_DIR = os.path.join(ROOT_DIR, "output", "1_modules")
JSON_DIR = os.path.join(ROOT_DIR, "output", "2_json")
SQL_DIR = os.path.join(ROOT_DIR, "output", "3_sql")

# ──────────────────────────────────────────────
# Regex patterns
# ──────────────────────────────────────────────

MODULE_HEADING_RE = re.compile(r"^Module\s+(\d+)\s*:\s*(.+)$", re.IGNORECASE)
CHAPTER_HEADING_RE = re.compile(r"^Chapter\s+(\d+)\s*:\s*(.+)$", re.IGNORECASE)

# ──────────────────────────────────────────────
# Slug helpers
# ──────────────────────────────────────────────

def make_slug(text):
    """Convert a title to a URL-friendly slug.

    Example: 'Getting Started with Python!' → 'getting-started-with-python'
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)   # remove non-word chars (except hyphens)
    text = re.sub(r"[\s_]+", "-", text)    # spaces/underscores → hyphens
    text = re.sub(r"-+", "-", text)        # collapse multiple hyphens
    return text.strip("-")


def make_chapter_slug(original_slug, course_slug):
    """Append course suffix to chapter slug for global uniqueness.

    Example: 'getting-started' + 'intro-web-dev' → 'getting-started-introwebdev'
    """
    suffix = course_slug.replace("-", "")
    return f"{original_slug}-{suffix}"

# ──────────────────────────────────────────────
# Defaults
# ──────────────────────────────────────────────

MODULE_DEFAULTS = {
    "is_published": True,
    "is_preview": False,
    "estimated_duration_hours": None,
}

CHAPTER_DEFAULTS = {
    "chapter_type": "lesson",
    "is_published": True,
    "is_free": False,
    "is_preview": False,
    "estimated_duration_minutes": None,
    "requires_activity": True,
    "min_activities_required": 1,
}

# ──────────────────────────────────────────────
# Directory setup
# ──────────────────────────────────────────────

def ensure_dirs():
    """Create all output directories if they don't exist."""
    for d in [INPUT_DIR, MODULES_DIR, JSON_DIR, SQL_DIR]:
        os.makedirs(d, exist_ok=True)
