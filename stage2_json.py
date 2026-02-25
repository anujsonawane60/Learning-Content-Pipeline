"""Stage 2: Module text files -> structured JSON (LMS-compatible schema)."""

import json
import re
from pathlib import Path

import click

from config import (
    CHAPTER_DEFAULTS,
    CHAPTER_HEADING_RE,
    JSON_DIR,
    MODULE_DEFAULTS,
    MODULE_HEADING_RE,
    MODULES_DIR,
    SECTION_HEADING_RE,
    ensure_dirs,
)
from courses import get_course
from utils import clean_title, extract_description, make_chapter_slug, make_slug


def _parse_meta(meta_path: Path) -> dict:
    """Parse _course_meta.txt into a dict."""
    meta = {}
    text = meta_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta


def _get_section_field(section_name: str) -> str:
    """Map a section heading name to a content_data language field."""
    name = section_name.strip().lower()
    if name.startswith("overview"):
        return "overview"
    if name.startswith("instruction"):
        return "instructions"
    if name.startswith("sample") or name.startswith("prompt"):
        return "prompt_text"
    if name.startswith("key learning"):
        return "key_learnings"
    if name.startswith("activity"):
        return "activity_text"
    return "overview"


def _parse_chapter_content(content_body: str) -> dict:
    """Parse chapter body into sectioned fields using ### markers.

    Returns dict with keys: overview, instructions, prompt_text,
    key_learnings, activity_text. Each value is a list of strings.
    """
    fields = {
        "overview": [],
        "instructions": [],
        "prompt_text": [],
        "key_learnings": [],
        "activity_text": [],
    }

    lines = content_body.splitlines()
    current_field = "overview"

    for line in lines:
        section_match = SECTION_HEADING_RE.match(line.strip())
        if section_match:
            current_field = _get_section_field(section_match.group(1))
            continue

        stripped = line.strip()
        if stripped:
            fields[current_field].append(stripped)

    return fields


def _parse_chapters(body: str, module_number: int, course_slug: str) -> list[dict]:
    """Split module body text into chapters using CHAPTER_HEADING_RE."""
    lines = body.splitlines()
    chapter_starts: list[dict] = []

    for idx, line in enumerate(lines):
        m = CHAPTER_HEADING_RE.match(line.strip())
        if m:
            chapter_starts.append({
                "number": int(m.group(1)),
                "title": clean_title(m.group(2)),
                "start": idx,
            })

    if not chapter_starts:
        return []

    chapters = []
    seen_slugs: dict[str, int] = {}

    for i, ch in enumerate(chapter_starts):
        end = chapter_starts[i + 1]["start"] if i + 1 < len(chapter_starts) else len(lines)
        content_lines = lines[ch["start"] + 1 : end]
        content_body = "\n".join(content_lines).strip()

        # Slug (deduplicated within module)
        slug = make_slug(ch["title"])
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 1

        global_slug = make_chapter_slug(slug, course_slug, module_number)

        # Parse content into sectioned fields (overview, instructions, etc.)
        fields = _parse_chapter_content(content_body)

        # Description from first non-empty field
        desc = ""
        for f in ("overview", "instructions", "prompt_text"):
            if fields[f]:
                desc = fields[f][0]
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                break

        chapter_data = {
            "title": ch["title"],
            "slug": global_slug,
            "description": desc,
            **CHAPTER_DEFAULTS,
            "order_index": ch["number"],
            "content_data": {
                "version": "2.0",
                "module_number": module_number,
                "ppt_link": [],
                "pdf_link": "",
                "gallery_images": [],
                "languages": {
                    "en": {
                        "chapter_title": ch["title"],
                        "overview": fields["overview"],
                        "video_link": "",
                        "instructions": fields["instructions"],
                        "prompt_text": fields["prompt_text"],
                        "prompts": [],
                        "activity_text": fields["activity_text"],
                        "activity_prompts": [],
                        "key_learnings": fields["key_learnings"],
                        "features": [],
                        "resources": [],
                    },
                    "hi": {},
                    "mr": {},
                },
                "metadata": {
                    "ai_generated": False,
                    "last_ai_update": None,
                    "content_quality_score": None,
                },
            },
        }
        chapters.append(chapter_data)

    return chapters


def convert_to_json(course_slug: str, use_ai: bool = False) -> None:
    """Read module files and produce a single structured JSON for the course."""
    course = get_course(course_slug)
    if course is None:
        raise click.ClickException(
            f"Course '{course_slug}' not found in registry. Run 'python cli.py onboard' first."
        )

    ensure_dirs()
    mod_dir = MODULES_DIR / course_slug

    if not mod_dir.exists():
        raise click.ClickException(
            f"No module files found at {mod_dir}. Run 'python cli.py split' first (Stage 1)."
        )

    # Read course meta
    meta_path = mod_dir / "_course_meta.txt"
    if meta_path.exists():
        meta = _parse_meta(meta_path)
    else:
        meta = {
            "course_name": course["name"],
            "course_slug": course_slug,
            "course_description": "",
        }

    # Read module files (sorted)
    module_files = sorted(mod_dir.glob("module_*.txt"))
    if not module_files:
        raise click.ClickException(
            f"No module_*.txt files in {mod_dir}. Run Stage 1 first."
        )

    modules = []
    for mf in module_files:
        text = mf.read_text(encoding="utf-8")
        lines = text.splitlines()

        # First line should be the module heading
        mod_title = ""
        mod_number = len(modules) + 1
        if lines:
            heading_match = MODULE_HEADING_RE.match(lines[0].strip())
            if heading_match:
                mod_number = int(heading_match.group(1))
                mod_title = clean_title(heading_match.group(2))
                body = "\n".join(lines[1:]).strip()
            else:
                mod_title = clean_title(lines[0])
                body = "\n".join(lines[1:]).strip()
        else:
            body = ""

        # Text before first chapter -> module description
        chapter_match = CHAPTER_HEADING_RE.search(body)
        if chapter_match:
            desc_text = body[: chapter_match.start()].strip()
        else:
            desc_text = body
        # Strip ### section markers from description
        desc_text = SECTION_HEADING_RE.sub("", desc_text).strip()

        chapters = _parse_chapters(body, mod_number, course_slug)

        # AI enrichment (if requested)
        if use_ai and chapters:
            try:
                from ai_enricher import enrich_chapters

                chapters = enrich_chapters(chapters, mod_title)
            except Exception as e:
                click.echo(f"  Warning: AI enrichment failed for module '{mod_title}': {e}")
                click.echo("  Falling back to mechanical parsing.")

        module_data = {
            "title": mod_title,
            "slug": make_slug(mod_title),
            "description": extract_description(desc_text),
            "order_index": mod_number,
            **MODULE_DEFAULTS,
            "chapters": chapters,
        }
        modules.append(module_data)

        ch_count = len(chapters)
        if ch_count == 0:
            click.echo(f"  Warning: Module '{mod_title}' has no chapters.")
        else:
            click.echo(f"  Module {mod_number}: {mod_title} - {ch_count} chapter(s)")

    # Build final JSON
    result = {
        "course_title": meta.get("course_name", course["name"]),
        "course_slug": course_slug,
        "course_description": meta.get("course_description", ""),
        "modules": modules,
    }

    out_path = JSON_DIR / f"{course_slug}.json"
    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    total_chapters = sum(len(m["chapters"]) for m in modules)
    click.echo(
        f"\nStage 2 complete - {len(modules)} module(s), "
        f"{total_chapters} chapter(s) -> {out_path}"
    )
