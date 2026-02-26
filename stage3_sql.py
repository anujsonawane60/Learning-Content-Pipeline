"""Stage 3: JSON -> Idempotent PostgreSQL SQL (PL/pgSQL DO $$ blocks)."""

import json
import time
from pathlib import Path

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


def _build_module_sql_block(mod: dict, course_slug: str) -> str:
    """Build a PL/pgSQL DO $$ block for one module + its chapters.

    The block is idempotent: it uses IF NOT EXISTS checks so re-running
    the same SQL will not create duplicate rows.
    """
    mod_title = mod["title"]
    mod_slug = mod["slug"]
    mod_desc = mod.get("description", "")
    mod_order = mod.get("order_index", 1)
    mod_published = mod.get("is_published", True)
    mod_preview = mod.get("is_preview", False)
    mod_duration = mod.get("estimated_duration_hours")
    chapters = mod.get("chapters", [])

    lines: list[str] = []
    lines.append(f"-- Module {mod_order}: {mod_title} ({len(chapters)} chapter(s))")
    lines.append("DO $$")
    lines.append("DECLARE")
    lines.append("  _course_id INT;")
    lines.append("  _module_id INT;")
    lines.append("BEGIN")
    lines.append(f"  SELECT id INTO _course_id FROM course WHERE slug = {_sql_str(course_slug)};")
    lines.append("")
    lines.append(f"  SELECT id INTO _module_id FROM course_module")
    lines.append(f"    WHERE slug = {_sql_str(mod_slug)} AND course_id = _course_id;")
    lines.append("")
    lines.append("  IF _module_id IS NULL THEN")
    lines.append("    INSERT INTO course_module")
    lines.append("      (course_id, title, slug, description, order_index,")
    lines.append("       is_published, is_preview, estimated_duration_hours, created_at, updated_at)")
    lines.append("    VALUES (")
    lines.append(f"      _course_id,")
    lines.append(f"      {_sql_str(mod_title)},")
    lines.append(f"      {_sql_str(mod_slug)},")
    lines.append(f"      {_sql_str(mod_desc)},")
    lines.append(f"      {_sql_int(mod_order)},")
    lines.append(f"      {_sql_str(mod_published)},")
    lines.append(f"      {_sql_str(mod_preview)},")
    lines.append(f"      {_sql_int(mod_duration)},")
    lines.append("      NOW(), NOW()")
    lines.append("    ) RETURNING id INTO _module_id;")
    lines.append("  END IF;")

    for ch in chapters:
        ch_title = ch["title"]
        ch_slug = ch["slug"]
        ch_desc = ch.get("description") or None
        ch_type = ch.get("chapter_type", "lesson")
        ch_order = ch.get("order_index", 0)
        ch_published = ch.get("is_published", True)
        ch_free = ch.get("is_free", False)
        ch_preview = ch.get("is_preview", False)
        ch_duration = ch.get("estimated_duration_minutes")
        ch_requires = ch.get("requires_activity", True)
        ch_min_act = ch.get("min_activities_required", 1)
        content_data = ch.get("content_data", {})

        lines.append("")
        lines.append(f"  -- Chapter: {ch_title}")
        lines.append(f"  IF NOT EXISTS (")
        lines.append(f"    SELECT 1 FROM course_chapter WHERE slug = {_sql_str(ch_slug)} AND module_id = _module_id")
        lines.append(f"  ) THEN")
        lines.append(f"    INSERT INTO course_chapter")
        lines.append(f"      (module_id, title, slug, description, chapter_type, order_index,")
        lines.append(f"       is_published, is_free, is_preview, estimated_duration_minutes,")
        lines.append(f"       content_data, requires_activity, min_activities_required, created_at, updated_at)")
        lines.append(f"    VALUES (")
        lines.append(f"      _module_id,")
        lines.append(f"      {_sql_str(ch_title)},")
        lines.append(f"      {_sql_str(ch_slug)},")
        lines.append(f"      {_sql_str(ch_desc)},")
        lines.append(f"      {_sql_str(ch_type)},")
        lines.append(f"      {_sql_int(ch_order)},")
        lines.append(f"      {_sql_str(ch_published)},")
        lines.append(f"      {_sql_str(ch_free)},")
        lines.append(f"      {_sql_str(ch_preview)},")
        lines.append(f"      {_sql_int(ch_duration)},")
        lines.append(f"      {_sql_jsonb(content_data)},")
        lines.append(f"      {_sql_str(ch_requires)},")
        lines.append(f"      {ch_min_act},")
        lines.append(f"      NOW(), NOW()")
        lines.append(f"    );")
        lines.append(f"  END IF;")

    lines.append("")
    lines.append("END $$;")
    return "\n".join(lines)


def generate_sql(course_slug: str) -> None:
    """Read the JSON for a course and produce idempotent SQL files."""
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

    # Build per-module DO $$ blocks
    module_blocks: list[str] = []
    for mod in modules:
        block = _build_module_sql_block(mod, course_slug)
        module_blocks.append(block)

    # -- Header ----------------------------------------------------------------
    header_lines = [
        "-- =============================================================",
        "-- Course Content Import -- Idempotent (IF NOT EXISTS)",
        f"-- Course:      {data.get('course_title', course_slug)}",
        f"-- Course slug: {course_slug}",
        f"-- Modules:     {len(modules)}",
        f"-- Chapters:    {total_chapters}",
        f"-- Generated:   {timestamp}",
        "-- =============================================================",
        "",
        "BEGIN;",
        "",
    ]
    header = "\n".join(header_lines)
    footer = "\nCOMMIT;\n"

    # -- Output directory ------------------------------------------------------
    out_dir = SQL_DIR / course_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- full.sql (combined) ---------------------------------------------------
    full_sql = header + "\n\n".join(module_blocks) + footer
    full_path = out_dir / "full.sql"
    full_path.write_text(full_sql, encoding="utf-8")

    # -- Per-module SQL files --------------------------------------------------
    for mod, block in zip(modules, module_blocks):
        mod_order = mod.get("order_index", 1)
        mod_slug = mod["slug"]
        mod_filename = f"module_{mod_order:02d}_{mod_slug}.sql"
        mod_path = out_dir / mod_filename
        mod_path.write_text(block + "\n", encoding="utf-8")

    click.echo(
        f"\nStage 3 complete - {len(modules)} module(s), "
        f"{total_chapters} chapter(s) -> {out_dir}/full.sql"
    )
    click.echo(f"  Per-module SQLs -> {out_dir}/")
