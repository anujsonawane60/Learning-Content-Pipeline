"""Scans output directories to discover processed courses."""

import json
import os

from config import MODULES_DIR, JSON_DIR, SQL_DIR


def scan_courses() -> list[dict]:
    """List all processed courses found in output/1_modules/."""
    courses = []

    if not os.path.isdir(MODULES_DIR):
        return courses

    for slug in sorted(os.listdir(MODULES_DIR)):
        course_dir = os.path.join(MODULES_DIR, slug)
        if not os.path.isdir(course_dir):
            continue

        # Read title from _course_meta.txt
        title = slug  # fallback
        meta_path = os.path.join(course_dir, "_course_meta.txt")
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().lower().startswith("course:"):
                        title = line.split(":", 1)[1].strip()
                        break

        # Check if JSON and SQL files exist
        json_path = os.path.join(JSON_DIR, f"{slug}.json")
        sql_path = os.path.join(SQL_DIR, f"{slug}.sql")
        has_json = os.path.isfile(json_path)
        has_sql = os.path.isfile(sql_path)

        # Parse JSON for module/chapter counts
        module_count = 0
        chapter_count = 0
        if has_json:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                modules = data.get("modules", [])
                module_count = len(modules)
                chapter_count = sum(len(m.get("chapters", [])) for m in modules)
            except (json.JSONDecodeError, KeyError):
                pass

        courses.append({
            "slug": slug,
            "title": title,
            "module_count": module_count,
            "chapter_count": chapter_count,
            "has_json": has_json,
            "has_sql": has_sql,
        })

    return courses


def get_course_detail(slug: str) -> dict | None:
    """Read and return full course JSON for a given slug."""
    json_path = os.path.join(JSON_DIR, f"{slug}.json")
    if not os.path.isfile(json_path):
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_path(slug: str, file_type: str) -> str | None:
    """Return the absolute path to a course's JSON or SQL file, or None."""
    if file_type == "json":
        path = os.path.join(JSON_DIR, f"{slug}.json")
    elif file_type == "sql":
        path = os.path.join(SQL_DIR, f"{slug}.sql")
    else:
        return None

    return path if os.path.isfile(path) else None
