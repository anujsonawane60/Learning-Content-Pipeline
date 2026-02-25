"""Stage 3: JSON -> PostgreSQL SQL INSERT statements."""

import json
import time

import click

from config import JSON_DIR, SQL_DIR, ensure_dirs
from courses import get_course


def _sql_str(value) -> str:
    """Escape a Python value for SQL string literal."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # String -- escape single quotes
    s = str(value).replace("'", "''")
    return f"'{s}'"


def _sql_int(value) -> str:
    """Format an integer value for SQL (NULL-safe)."""
    if value is None:
        return "NULL"
    return str(int(value))


def _sql_jsonb(obj) -> str:
    """Serialize a Python object to a SQL jsonb literal."""
    s = json.dumps(obj, ensure_ascii=False).replace("'", "''")
    return f"'{s}'::jsonb"


def generate_sql(course_slug: str) -> None:
    """Read the JSON for a course and produce a .sql file with INSERT statements."""
    course = get_course(course_slug)
    if course is None:
        raise click.ClickException(
            f"Course '{course_slug}' not found in registry. Run 'python cli.py onboard' first."
        )

    ensure_dirs()
    json_path = JSON_DIR / f"{course_slug}.json"

    if not json_path.exists():
        raise click.ClickException(
            f"JSON file not found at {json_path}. Run 'python cli.py convert' first (Stage 2)."
        )

    data = json.loads(json_path.read_text(encoding="utf-8"))
    modules = data.get("modules", [])

    if not modules:
        raise click.ClickException("JSON contains no modules - nothing to generate.")

    total_chapters = sum(len(m.get("chapters", [])) for m in modules)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []

    # -- Header ----------------------------------------------------------------
    lines.append("-- =============================================================")
    lines.append("-- Course Content Import -- Modules + Chapters")
    lines.append(f"-- Course:      {data.get('course_title', course_slug)}")
    lines.append(f"-- Course slug: {course_slug}")
    lines.append(f"-- Modules:     {len(modules)}")
    lines.append(f"-- Chapters:    {total_chapters}")
    lines.append(f"-- Generated:   {timestamp}")
    lines.append("-- =============================================================")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    course_id_expr = f"(SELECT id FROM course WHERE slug = {_sql_str(course_slug)})"

    for mod in modules:
        mod_title = mod["title"]
        mod_slug = mod["slug"]
        mod_desc = mod.get("description", "")
        mod_order = mod.get("order_index", 1)
        mod_published = mod.get("is_published", True)
        mod_preview = mod.get("is_preview", False)
        mod_duration = mod.get("estimated_duration_hours")
        chapters = mod.get("chapters", [])

        cte_alias = f"new_module_{mod_order}"

        # -- Module INSERT (CTE) -----------------------------------------------
        lines.append(f"-- Module {mod_order}: {mod_title} ({len(chapters)} chapter(s))")
        lines.append(f"WITH {cte_alias} AS (")
        lines.append(f"  INSERT INTO course_module (course_id, title, slug, description, order_index, is_published, is_preview, estimated_duration_hours, created_at, updated_at)")
        lines.append(f"  VALUES (")
        lines.append(f"    {course_id_expr},")
        lines.append(f"    {_sql_str(mod_title)},")
        lines.append(f"    {_sql_str(mod_slug)},")
        lines.append(f"    {_sql_str(mod_desc)},")
        lines.append(f"    (SELECT COALESCE(MAX(order_index), -1) + 1 FROM course_module WHERE course_id = {course_id_expr}),")
        lines.append(f"    {_sql_str(mod_published)},")
        lines.append(f"    {_sql_str(mod_preview)},")
        lines.append(f"    {_sql_int(mod_duration)},")
        lines.append(f"    NOW(), NOW()")
        lines.append(f"  )")
        lines.append(f"  RETURNING id")
        lines.append(f")")

        if chapters:
            # -- Chapter INSERT (VALUES tuples) ---------------------------------
            lines.append("INSERT INTO course_chapter (module_id, title, slug, description, chapter_type, order_index, is_published, is_free, is_preview, estimated_duration_minutes, content_data, requires_activity, min_activities_required, created_at, updated_at)")
            lines.append("VALUES")

            for ci, ch in enumerate(chapters):
                ch_title = ch["title"]
                ch_slug = ch["slug"]
                ch_desc = ch.get("description") or None
                ch_type = ch.get("chapter_type", "lesson")
                ch_published = ch.get("is_published", True)
                ch_free = ch.get("is_free", False)
                ch_preview = ch.get("is_preview", False)
                ch_duration = ch.get("estimated_duration_minutes")
                ch_requires = ch.get("requires_activity", True)
                ch_min_act = ch.get("min_activities_required", 1)
                content_data = ch.get("content_data", {})

                is_last = ci == len(chapters) - 1
                comma = ";" if is_last else ","

                lines.append(f"  (")
                lines.append(f"    (SELECT id FROM {cte_alias}),")
                lines.append(f"    {_sql_str(ch_title)},")
                lines.append(f"    {_sql_str(ch_slug)},")
                lines.append(f"    {_sql_str(ch_desc)},")
                lines.append(f"    {_sql_str(ch_type)},")
                lines.append(f"    {ci},")
                lines.append(f"    {_sql_str(ch_published)},")
                lines.append(f"    {_sql_str(ch_free)},")
                lines.append(f"    {_sql_str(ch_preview)},")
                lines.append(f"    {_sql_int(ch_duration)},")
                lines.append(f"    {_sql_jsonb(content_data)},")
                lines.append(f"    {_sql_str(ch_requires)},")
                lines.append(f"    {ch_min_act},")
                lines.append(f"    NOW(), NOW()")
                lines.append(f"  ){comma}")
        else:
            # No chapters -- just close the module CTE with a SELECT
            lines.append(f"SELECT id FROM {cte_alias};")

        lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    # -- Write output ----------------------------------------------------------
    out_path = SQL_DIR / f"{course_slug}.sql"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    click.echo(
        f"\nStage 3 complete - {len(modules)} module(s), "
        f"{total_chapters} chapter(s) -> {out_path}"
    )
