"""Interactive entry point for the Learning Content Pipeline."""

import sys
from pathlib import Path

import click

from config import INPUT_DIR, MODULES_DIR, JSON_DIR, SQL_DIR, ensure_dirs
from config import MODULE_HEADING_RE, CHAPTER_HEADING_RE
from courses import add_course, get_course, load_courses, remove_course
from utils import make_slug, read_document, clean_title


ROOT = Path(__file__).resolve().parent


def ask_for_filepath(prompt_label: str, allowed_extensions: tuple = (".txt", ".docx")):
    """Prompt user for a file path directly. Returns Path or None if empty."""
    raw = click.prompt(f"  {prompt_label}", default="", show_default=False).strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.exists():
        raise click.ClickException(f"File not found: {raw}")
    if p.suffix.lower() not in allowed_extensions:
        ext_list = ", ".join(allowed_extensions)
        raise click.ClickException(
            f"Unsupported extension '{p.suffix}'. Allowed: {ext_list}"
        )
    return p


def run_stages_2_and_3(slug: str):
    """Run Stage 2 (JSON) and Stage 3 (SQL) only -- skip split."""
    from stage2_json import convert_to_json
    from stage3_sql import generate_sql

    click.echo()
    click.echo("=" * 50)
    click.echo("  Stage 2: Converting modules to JSON...")
    click.echo("=" * 50)
    convert_to_json(slug)

    click.echo()
    click.echo("=" * 50)
    click.echo("  Stage 3: Generating SQL...")
    click.echo("=" * 50)
    generate_sql(slug)

    click.echo("\n  Stages 2-3 complete!\n")


def add_module_flow(slug: str):
    """Add a single module file from a .txt/.docx, then regenerate JSON+SQL."""
    click.echo("\n--- Add Module ---\n")
    filepath = ask_for_filepath("Path to module file (empty to go back)")
    if filepath is None:
        return

    lines = read_document(filepath)

    # Find first non-blank line and match Module heading
    mod_match = None
    for line in lines:
        if line.strip():
            mod_match = MODULE_HEADING_RE.match(line.strip())
            break

    if not mod_match:
        raise click.ClickException(
            "First non-blank line must be a module heading "
            "(e.g. 'Module 1: Introduction')."
        )

    mod_num = int(mod_match.group(1))
    mod_title = clean_title(mod_match.group(2))
    filename = f"module_{mod_num:02d}_{make_slug(mod_title)}.txt"

    course_mod_dir = MODULES_DIR / slug
    course_mod_dir.mkdir(parents=True, exist_ok=True)
    dest = course_mod_dir / filename

    if dest.exists():
        click.confirm(
            f"  '{filename}' already exists. Overwrite?", abort=True
        )

    dest.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"\n  Saved: {dest.relative_to(ROOT)}")

    run_stages_2_and_3(slug)


def add_chapter_flow(slug: str):
    """Append chapter content to an existing module, then regenerate JSON+SQL."""
    click.echo("\n--- Add Chapter ---\n")

    course_mod_dir = MODULES_DIR / slug
    if not course_mod_dir.exists():
        raise click.ClickException(
            f"No modules directory found for '{slug}'. Add a module first."
        )

    mod_files = sorted(course_mod_dir.glob("module_*.txt"))
    if not mod_files:
        raise click.ClickException(
            f"No module files found for '{slug}'. Add a module first."
        )

    # List modules with their first-line title
    click.echo("  Existing modules:")
    click.echo("  [0] Back")
    for i, mf in enumerate(mod_files, 1):
        first_line = mf.read_text(encoding="utf-8").split("\n", 1)[0].strip()
        click.echo(f"  [{i}] {first_line or mf.name}")

    idx = click.prompt(
        "\n  Select module", type=click.IntRange(0, len(mod_files))
    )
    if idx == 0:
        return

    selected = mod_files[idx - 1]
    click.echo(f"\n  Target: {selected.name}")

    filepath = ask_for_filepath("Path to chapter file (empty to go back)")
    if filepath is None:
        return

    lines = read_document(filepath)

    # Validate at least one Chapter heading exists
    has_chapter = any(CHAPTER_HEADING_RE.match(l.strip()) for l in lines if l.strip())
    if not has_chapter:
        raise click.ClickException(
            "File must contain at least one chapter heading "
            "(e.g. 'Chapter 1: Getting Started')."
        )

    # Append to module file with blank-line separator
    existing = selected.read_text(encoding="utf-8")
    separator = "\n\n" if existing.rstrip() else ""
    selected.write_text(
        existing.rstrip() + separator + "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    click.echo(f"\n  Appended to: {selected.relative_to(ROOT)}")

    run_stages_2_and_3(slug)


def _reconstruct_module_txt(module: dict) -> str:
    """Reconstruct a module .txt file from LMS export JSON data."""
    lines = []
    order = module.get("order_index", 1)
    title = module.get("title", "Untitled")
    lines.append(f"Module {order}: {title}")

    # Module description -> text before first chapter
    desc = module.get("description", "")
    if desc:
        lines.append(desc)
    lines.append("")

    for ch in module.get("chapters", []):
        ch_order = ch.get("order_index", 1)
        ch_title = ch.get("title", "Untitled")
        lines.append(f"Chapter {ch_order}: {ch_title}")

        # Extract content from languages.en
        content_data = ch.get("content_data", {})
        languages = content_data.get("languages", {})
        en = languages.get("en", {})

        sections = [
            ("Overview", en.get("overview", [])),
            ("Instructions", en.get("instructions", [])),
            ("Sample Prompt", en.get("prompt_text", [])),
            ("Key Learnings", en.get("key_learnings", [])),
            ("Activity", en.get("activity_text", [])),
        ]

        for section_name, section_lines in sections:
            if section_lines:
                lines.append(f"### {section_name}")
                for sl in section_lines:
                    lines.append(sl)
                lines.append("")

        lines.append("")

    return "\n".join(lines)


def import_course_flow():
    """Import an existing course from an LMS export JSON file."""
    import json as _json

    click.echo("\n--- Import Course from JSON ---\n")

    filepath = ask_for_filepath(
        "Path to export JSON (empty to go back)",
        allowed_extensions=(".json",),
    )
    if filepath is None:
        return

    data = _json.loads(filepath.read_text(encoding="utf-8"))

    # Validate structure
    if "course" not in data or "modules" not in data:
        raise click.ClickException(
            "Invalid export JSON. Expected 'course' and 'modules' keys."
        )

    course_info = data["course"]
    name = course_info.get("title", "")
    slug = course_info.get("slug", "")

    if not name or not slug:
        raise click.ClickException("Export JSON missing course title or slug.")

    modules = data["modules"]
    total_ch = sum(len(m.get("chapters", [])) for m in modules)

    click.echo(f"  Course:   {name}")
    click.echo(f"  Slug:     {slug}")
    click.echo(f"  Modules:  {len(modules)}")
    click.echo(f"  Chapters: {total_ch}")

    # Check if course already exists
    existing = get_course(slug)
    if existing:
        raise click.ClickException(
            f"Course '{slug}' already exists in registry."
        )

    click.confirm("\n  Import this course?", abort=True)

    # Register course
    course = add_course(name, slug)
    click.echo(f"\n  Registered: {course['name']} ({course['slug']})")

    # Generate module .txt files
    course_mod_dir = MODULES_DIR / slug
    course_mod_dir.mkdir(parents=True, exist_ok=True)

    for mod in modules:
        mod_order = mod.get("order_index", 1)
        mod_title = mod.get("title", "Untitled")
        mod_slug = make_slug(mod_title)
        filename = f"module_{mod_order:02d}_{mod_slug}.txt"

        txt_content = _reconstruct_module_txt(mod)
        dest = course_mod_dir / filename
        dest.write_text(txt_content, encoding="utf-8")

        ch_count = len(mod.get("chapters", []))
        click.echo(f"    {filename} ({ch_count} chapters)")

    click.echo(f"\n  Generated {len(modules)} module file(s) in {course_mod_dir.relative_to(ROOT)}/")

    # Run stages 2+3
    run_stages_2_and_3(slug)


def show_banner():
    click.echo("\n" + "=" * 50)
    click.echo("  Learning Content Pipeline")
    click.echo("  AI Leela LMS - Course Onboarding Tool")
    click.echo("=" * 50)


def create_new_course():
    """Prompt for name & slug, register the course, then ask for a file."""
    click.echo("\n--- Create New Course ---\n")
    name = click.prompt("  Course name").strip()
    if not name:
        raise click.ClickException("Course name cannot be empty.")
    slug = make_slug(name)
    slug = click.prompt("  Course slug", default=slug).strip()
    course = add_course(name, slug)
    click.echo(f"\n  Created: {course['name']}  (slug: {course['slug']})")

    # Ask for content file
    click.echo()
    filepath = ask_for_file()
    if filepath is None:
        return
    run_pipeline(course["slug"], filepath)


def show_existing_course(course: dict):
    """Show course details: module files, JSON, SQL, and option to add more."""
    slug = course["slug"]
    click.echo(f"\n--- {course['name']} ({slug}) ---")

    # Module files
    mod_dir = MODULES_DIR / slug
    if mod_dir.exists():
        mod_files = sorted(f for f in mod_dir.glob("module_*.txt"))
        if mod_files:
            click.echo(f"\n  Module files ({len(mod_files)}):")
            for f in mod_files:
                click.echo(f"    - {f.name}")
        else:
            click.echo("\n  Module files: none")
    else:
        click.echo("\n  Module files: none")

    # JSON
    json_path = JSON_DIR / f"{slug}.json"
    if json_path.exists():
        import json
        data = json.loads(json_path.read_text(encoding="utf-8"))
        modules = data.get("modules", [])
        total_ch = sum(len(m.get("chapters", [])) for m in modules)
        click.echo(f"\n  JSON: {json_path.name}  ({len(modules)} modules, {total_ch} chapters)")
    else:
        click.echo("\n  JSON: not generated yet")

    # SQL
    sql_path = SQL_DIR / slug / "full.sql"
    if sql_path.exists():
        click.echo(f"  SQL:  {slug}/full.sql")
    else:
        click.echo("  SQL:  not generated yet")

    # Action menu
    click.echo("\n  [0] Back to main menu")
    click.echo("  [1] Add/update content")
    click.echo("  [2] Delete this course")
    choice = click.prompt("\n  Choose", type=click.IntRange(0, 2))

    if choice == 0:
        return
    if choice == 1:
        click.echo("\n  [0] Back")
        click.echo("  [1] Add module")
        click.echo("  [2] Add chapter")
        sub = click.prompt("\n  Choose", type=click.IntRange(0, 2))
        if sub == 1:
            add_module_flow(slug)
        elif sub == 2:
            add_chapter_flow(slug)
        return
    if choice == 2:
        click.confirm(
            f"\n  Delete '{course['name']}' ({slug}) and all its output files?",
            abort=True,
        )
        removed = remove_course(slug)
        click.echo(f"\n  Deleted course: {removed['name']}  (slug: {removed['slug']})\n")


def ask_for_file():
    """Prompt user for the input document path. Returns None if user picks back."""
    input_files = []
    if INPUT_DIR.exists():
        input_files += [f for f in INPUT_DIR.iterdir() if f.suffix in (".txt", ".docx")]

    click.echo("  [0] Back to main menu")
    if input_files:
        for i, f in enumerate(input_files, 1):
            try:
                display = f.relative_to(ROOT)
            except ValueError:
                display = f
            click.echo(f"  [{i}] {display}")
        click.echo(f"  [{len(input_files) + 1}] Enter a custom path")

        choice = click.prompt(
            "\n  Select file", type=click.IntRange(0, len(input_files) + 1)
        )
        if choice == 0:
            return None
        if choice <= len(input_files):
            return str(input_files[choice - 1])

    else:
        choice = click.prompt(
            "\n  [1] Enter a custom path\n\n  Select", type=click.IntRange(0, 1)
        )
        if choice == 0:
            return None

    filepath = click.prompt("  Enter file path (.txt or .docx)").strip()
    if not Path(filepath).exists():
        raise click.ClickException(f"File not found: {filepath}")
    return filepath


def run_pipeline(slug: str, filepath: str):
    """Run all 3 stages automatically."""
    from stage1_split import split_document
    from stage2_json import convert_to_json
    from stage3_sql import generate_sql

    click.echo("\n" + "=" * 50)
    click.echo("  Stage 1: Splitting document into modules...")
    click.echo("=" * 50)
    split_document(filepath, slug)

    click.echo()
    click.echo("=" * 50)
    click.echo("  Stage 2: Converting modules to JSON...")
    click.echo("=" * 50)
    convert_to_json(slug)

    click.echo()
    click.echo("=" * 50)
    click.echo("  Stage 3: Generating SQL...")
    click.echo("=" * 50)
    generate_sql(slug)

    click.echo("\n  Pipeline complete!\n")


def main_menu():
    """Main menu: create new or select existing."""
    ensure_dirs()
    show_banner()

    courses = load_courses()

    click.echo("\n  [0] Exit")
    click.echo("  [1] Create new course")
    click.echo("  [2] Import course from JSON")
    if courses:
        click.echo("  [3] Select existing course")
        max_choice = 3
    else:
        max_choice = 2

    choice = click.prompt("\n  Choose an option", type=click.IntRange(0, max_choice))

    if choice == 0:
        click.echo("\n  Goodbye!\n")
        sys.exit(0)

    if choice == 1:
        create_new_course()
    elif choice == 2:
        import_course_flow()
    elif choice == 3:
        click.echo()
        click.echo("  [0] Back to main menu")
        for i, c in enumerate(courses, 1):
            click.echo(f"  [{i}] {c['name']}  ({c['slug']})")
        idx = click.prompt(
            "\n  Select course", type=click.IntRange(0, len(courses))
        )
        if idx == 0:
            return
        show_existing_course(courses[idx - 1])


if __name__ == "__main__":
    try:
        while True:
            main_menu()
    except (KeyboardInterrupt, EOFError, click.Abort):
        click.echo("\n\n  Goodbye!\n")
