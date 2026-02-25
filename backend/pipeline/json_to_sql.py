"""
Stage 3: Convert structured JSON to PostgreSQL SQL INSERT statements.

Reads a course JSON file from output/2_json/{course_slug}.json and generates
a .sql file with BEGIN/COMMIT wrapped INSERT statements using CTEs.

Adapted from import_course_json.py (CSV queue mode removed).

Usage:
    python -m pipeline.json_to_sql                   # auto-detect
    python -m pipeline.json_to_sql intro-web-dev     # specify slug
"""

import json
import os
import sys
from datetime import datetime

from config import JSON_DIR, SQL_DIR, make_chapter_slug, ensure_dirs


# ──────────────────────────────────────────────
# SQL helpers
# ──────────────────────────────────────────────

def escape_sql(value):
    """Escape a string value for safe use in SQL single-quoted literals."""
    if value is None:
        return "NULL"
    return str(value).replace("'", "''")


def sql_string(value):
    """Wrap a value in single quotes for SQL, or return NULL."""
    if value is None:
        return "NULL"
    return f"'{escape_sql(value)}'"


def sql_bool(value):
    """Convert a Python bool to SQL boolean literal."""
    if value is None:
        return "true"
    return "true" if value else "false"


def sql_number(value, default=None):
    """Convert a number for SQL, with optional default."""
    if value is None:
        return str(default) if default is not None else "NULL"
    return str(value)


def sql_jsonb(value):
    """Convert a Python dict/list to a SQL jsonb literal."""
    if value is None:
        return "NULL"
    json_str = json.dumps(value, ensure_ascii=False)
    return f"'{escape_sql(json_str)}'::jsonb"


# ──────────────────────────────────────────────
# JSON loading & validation
# ──────────────────────────────────────────────

def load_json(file_path):
    """Load and return JSON data from a file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_json(data):
    """Validate JSON structure for module+chapter import."""
    if not isinstance(data, dict):
        return False, "JSON root must be an object"

    modules = data.get("modules")
    if not isinstance(modules, list) or len(modules) == 0:
        return False, "No modules found in JSON"

    for i, module in enumerate(modules):
        if not module.get("title") or not module.get("slug"):
            return False, f"Module {i+1} missing title or slug"
        for j, chapter in enumerate(module.get("chapters", [])):
            if not chapter.get("title") or not chapter.get("slug"):
                return False, f"Module {i+1}, Chapter {j+1} missing title or slug"

    return True, None


# ──────────────────────────────────────────────
# SQL generation
# ──────────────────────────────────────────────

def build_chapter_values(chapter, order_expr, module_ref, course_slug):
    """Build SQL VALUES tuple for a single chapter."""
    content_data = chapter.get("content_data")
    chapter_slug = make_chapter_slug(chapter["slug"], course_slug)
    lines = []
    lines.append(f"  (")
    lines.append(f"    {module_ref},")
    lines.append(f"    {sql_string(chapter['title'])},")
    lines.append(f"    {sql_string(chapter_slug)},")
    lines.append(f"    {sql_string(chapter.get('description'))},")
    lines.append(f"    {sql_string(chapter.get('chapter_type', 'lesson'))},")
    lines.append(f"    {order_expr},")
    lines.append(f"    {sql_bool(chapter.get('is_published', True))},")
    lines.append(f"    {sql_bool(chapter.get('is_free', False))},")
    lines.append(f"    {sql_bool(chapter.get('is_preview', False))},")
    lines.append(f"    {sql_number(chapter.get('estimated_duration_minutes'))},")
    lines.append(f"    {sql_jsonb(content_data)},")
    lines.append(f"    {sql_bool(chapter.get('requires_activity', True))},")
    lines.append(f"    {sql_number(chapter.get('min_activities_required', 1))},")
    lines.append(f"    NOW(), NOW()")
    lines.append(f"  )")
    return "\n".join(lines)


def generate_sql(data, course_slug, source_file):
    """Generate SQL for adding modules with chapters to a course."""
    modules = data["modules"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_chapters = sum(len(m.get("chapters", [])) for m in modules)

    course_id_sq = f"(SELECT id FROM course WHERE slug = {sql_string(course_slug)})"

    lines = []
    lines.append(f"-- =============================================================")
    lines.append(f"-- Course Content Import — Modules + Chapters")
    lines.append(f"-- Source:       {source_file}")
    lines.append(f"-- Generated:   {timestamp}")
    lines.append(f"-- Course slug:  {course_slug}")
    lines.append(f"-- Modules:      {len(modules)}")
    lines.append(f"-- Chapters:     {total_chapters}")
    lines.append(f"-- =============================================================")
    lines.append(f"")
    lines.append(f"BEGIN;")
    lines.append(f"")

    for i, module in enumerate(modules):
        cte_name = f"new_module_{i + 1}"
        chapter_count = len(module.get("chapters", []))

        base_order = (
            f"(SELECT COALESCE(MAX(order_index), -1) + 1 FROM course_module "
            f"WHERE course_id = {course_id_sq})"
        )
        order_expr = f"({base_order} + {i})" if i > 0 else base_order
        chapters = module.get("chapters", [])

        lines.append(f"-- Module {i + 1}: {module['title']} ({chapter_count} chapter(s))")

        if chapters:
            lines.append(f"WITH {cte_name} AS (")
            lines.append(f"  INSERT INTO course_module (course_id, title, slug, description, order_index, is_published, is_preview, estimated_duration_hours, created_at, updated_at)")
            lines.append(f"  VALUES (")
            lines.append(f"    {course_id_sq},")
            lines.append(f"    {sql_string(module['title'])},")
            lines.append(f"    {sql_string(module['slug'])},")
            lines.append(f"    {sql_string(module.get('description', ''))},")
            lines.append(f"    {order_expr},")
            lines.append(f"    {sql_bool(module.get('is_published', True))},")
            lines.append(f"    {sql_bool(module.get('is_preview', False))},")
            lines.append(f"    {sql_number(module.get('estimated_duration_hours'), default='NULL')},")
            lines.append(f"    NOW(), NOW()")
            lines.append(f"  )")
            lines.append(f"  RETURNING id")
            lines.append(f")")
            lines.append(f"INSERT INTO course_chapter (module_id, title, slug, description, chapter_type, order_index, is_published, is_free, is_preview, estimated_duration_minutes, content_data, requires_activity, min_activities_required, created_at, updated_at)")
            lines.append(f"VALUES")

            chapter_values = []
            for j, chapter in enumerate(chapters):
                module_ref = f"(SELECT id FROM {cte_name})"
                chapter_values.append(build_chapter_values(chapter, str(j), module_ref, course_slug))

            lines.append(",\n".join(chapter_values) + ";")
        else:
            lines.append(f"INSERT INTO course_module (course_id, title, slug, description, order_index, is_published, is_preview, estimated_duration_hours, created_at, updated_at)")
            lines.append(f"VALUES (")
            lines.append(f"  {course_id_sq},")
            lines.append(f"  {sql_string(module['title'])},")
            lines.append(f"  {sql_string(module['slug'])},")
            lines.append(f"  {sql_string(module.get('description', ''))},")
            lines.append(f"  {order_expr},")
            lines.append(f"  {sql_bool(module.get('is_published', True))},")
            lines.append(f"  {sql_bool(module.get('is_preview', False))},")
            lines.append(f"  {sql_number(module.get('estimated_duration_hours'), default='NULL')},")
            lines.append(f"  NOW(), NOW()")
            lines.append(f");")

        lines.append(f"")

    lines.append(f"COMMIT;")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def convert_json_to_sql(course_slug):
    """Main function: read JSON and produce SQL file."""
    ensure_dirs()

    json_path = os.path.join(JSON_DIR, f"{course_slug}.json")
    if not os.path.isfile(json_path):
        print(f"ERROR: JSON file not found: {json_path}")
        print("  Run stage 2 first: python -m pipeline.module_to_json")
        sys.exit(1)

    print(f"Reading: {json_path}")

    data = load_json(json_path)

    # Validate
    valid, error = validate_json(data)
    if not valid:
        print(f"ERROR: Invalid JSON — {error}")
        sys.exit(1)

    modules = data["modules"]
    total_chapters = sum(len(m.get("chapters", [])) for m in modules)
    print(f"  Course slug: {course_slug}")
    print(f"  Modules:     {len(modules)}")
    print(f"  Chapters:    {total_chapters}")

    # Generate SQL
    source_file = f"{course_slug}.json"
    sql = generate_sql(data, course_slug, source_file)

    # Write output
    sql_path = os.path.join(SQL_DIR, f"{course_slug}.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql)

    print(f"\nDone — SQL written to output/3_sql/{course_slug}.sql")
    return sql_path


def find_course_slug(slug=None):
    """Find course slug. Auto-detect if none specified."""
    if slug:
        json_path = os.path.join(JSON_DIR, f"{slug}.json")
        if not os.path.isfile(json_path):
            print(f"ERROR: No JSON file found for slug '{slug}'")
            sys.exit(1)
        return slug

    # Auto-detect: find .json files in JSON_DIR
    if not os.path.isdir(JSON_DIR):
        print(f"ERROR: No JSON directory found at {JSON_DIR}")
        print("  Run stage 2 first: python -m pipeline.module_to_json")
        sys.exit(1)

    json_files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]

    if not json_files:
        print(f"ERROR: No .json files found in {JSON_DIR}")
        print("  Run stage 2 first: python -m pipeline.module_to_json")
        sys.exit(1)

    if len(json_files) > 1:
        slugs = [f.replace(".json", "") for f in json_files]
        print(f"Multiple JSON files found: {', '.join(slugs)}")
        print("  Specify which: python -m pipeline.json_to_sql <slug>")
        sys.exit(1)

    return json_files[0].replace(".json", "")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    course_slug = find_course_slug(arg)
    convert_json_to_sql(course_slug)
