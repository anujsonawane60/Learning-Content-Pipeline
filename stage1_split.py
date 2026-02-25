"""Stage 1: Split a document into per-module text files."""

import click

from config import MODULE_HEADING_RE, MODULES_DIR, ensure_dirs
from courses import get_course
from utils import clean_title, make_slug, read_document


def split_document(filepath: str, course_slug: str) -> None:
    """Read a .txt/.docx file and split it into module files under output/1_modules/{slug}/."""
    course = get_course(course_slug)
    if course is None:
        raise click.ClickException(
            f"Course '{course_slug}' not found in registry. Run 'python cli.py onboard' first."
        )

    ensure_dirs()
    lines = read_document(filepath)

    if not lines or all(l.strip() == "" for l in lines):
        raise click.ClickException("Document is empty - nothing to process.")

    # ── Detect modules ───────────────────────────────────────────────────
    modules: list[dict] = []          # [{number, title, start_line}, ...]
    for idx, line in enumerate(lines):
        m = MODULE_HEADING_RE.match(line.strip())
        if m:
            modules.append({
                "number": int(m.group(1)),
                "title": clean_title(m.group(2)),
                "start": idx,
            })

    if not modules:
        raise click.ClickException(
            "No module headings found. Expected format: 'Module N: Title' "
            "(supports : - \u2013 \u2014 separators)."
        )

    # ── Preamble (text before first module) → course description ─────────
    preamble_lines = lines[: modules[0]["start"]]
    course_description = "\n".join(preamble_lines).strip()

    # ── Slice content per module ─────────────────────────────────────────
    for i, mod in enumerate(modules):
        end = modules[i + 1]["start"] if i + 1 < len(modules) else len(lines)
        mod["content"] = "\n".join(lines[mod["start"] + 1 : end]).strip()

    # ── Deduplicate slugs ────────────────────────────────────────────────
    seen_slugs: dict[str, int] = {}
    for mod in modules:
        slug = make_slug(mod["title"])
        if slug in seen_slugs:
            seen_slugs[slug] += 1
            slug = f"{slug}-{seen_slugs[slug]}"
        else:
            seen_slugs[slug] = 1
        mod["slug"] = slug

    # ── Write files ──────────────────────────────────────────────────────
    out_dir = MODULES_DIR / course_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # _course_meta.txt
    meta_path = out_dir / "_course_meta.txt"
    meta_path.write_text(
        f"course_name: {course['name']}\n"
        f"course_slug: {course_slug}\n"
        f"course_description: {course_description}\n",
        encoding="utf-8",
    )

    # Module files
    for mod in modules:
        fname = f"module_{mod['number']:02d}_{mod['slug']}.txt"
        fpath = out_dir / fname
        header = f"Module {mod['number']}: {mod['title']}\n\n"
        fpath.write_text(header + mod["content"], encoding="utf-8")
        if not mod["content"]:
            click.echo(f"  Warning: Module {mod['number']} ('{mod['title']}') has no content.")

    click.echo(f"\nStage 1 complete - {len(modules)} module(s) written to {out_dir}")
    for mod in modules:
        click.echo(f"  Module {mod['number']:>2}: {mod['title']}")
