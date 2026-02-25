"""Interactive entry point for the Learning Content Pipeline."""

import sys
from pathlib import Path

import click

from config import INPUT_DIR, MODULES_DIR, JSON_DIR, SQL_DIR, ensure_dirs
from courses import add_course, get_course, load_courses, remove_course
from utils import make_slug


ROOT = Path(__file__).resolve().parent


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
    sql_path = SQL_DIR / f"{slug}.sql"
    if sql_path.exists():
        click.echo(f"  SQL:  {sql_path.name}")
    else:
        click.echo("  SQL:  not generated yet")

    # Action menu
    click.echo("\n  [0] Back to main menu")
    click.echo("  [1] Add/update content (provide a file)")
    click.echo("  [2] Delete this course")
    choice = click.prompt("\n  Choose", type=click.IntRange(0, 2))

    if choice == 0:
        return
    if choice == 1:
        filepath = ask_for_file()
        if filepath is None:
            return
        run_pipeline(slug, filepath)
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

    sample_dir = ROOT / "sample"
    if sample_dir.exists():
        input_files += [f for f in sample_dir.iterdir() if f.suffix in (".txt", ".docx")]

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
    if courses:
        click.echo("  [2] Select existing course")
        max_choice = 2
    else:
        max_choice = 1

    choice = click.prompt("\n  Choose an option", type=click.IntRange(0, max_choice))

    if choice == 0:
        click.echo("\n  Goodbye!\n")
        sys.exit(0)

    if choice == 1:
        create_new_course()
    elif choice == 2:
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
    except (KeyboardInterrupt, EOFError):
        click.echo("\n\n  Goodbye!\n")
