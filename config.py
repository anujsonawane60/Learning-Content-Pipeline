"""Configuration: paths, constants, defaults, and regex patterns."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent
INPUT_DIR = ROOT_DIR / "input"
OUTPUT_DIR = ROOT_DIR / "output"
MODULES_DIR = OUTPUT_DIR / "1_modules"
JSON_DIR = OUTPUT_DIR / "2_json"
SQL_DIR = OUTPUT_DIR / "3_sql"
COURSES_FILE = ROOT_DIR / "courses.json"

# ── Heading regex (case-insensitive, supports : - – —) ──────────────────
MODULE_HEADING_RE = re.compile(
    r"^Module\s+(\d+)\s*[:\-\u2013\u2014]\s*(.+)$", re.IGNORECASE
)
CHAPTER_HEADING_RE = re.compile(
    r"^Chapter\s+(\d+)\s*[:\-\u2013\u2014]\s*(.+)$", re.IGNORECASE
)
SECTION_HEADING_RE = re.compile(r"^###\s+(.+)$")

# ── Default field values ─────────────────────────────────────────────────
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
    "requires_activity": True,
    "min_activities_required": 1,
    "estimated_duration_minutes": None,
}


def ensure_dirs():
    """Create all required output directories if they don't exist."""
    for d in (INPUT_DIR, MODULES_DIR, JSON_DIR, SQL_DIR):
        d.mkdir(parents=True, exist_ok=True)
