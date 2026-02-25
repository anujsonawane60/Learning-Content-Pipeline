"""CLI entry point — Click command group for the Learning Content Pipeline."""

import click

from config import ensure_dirs
from courses import add_course, get_course, list_courses, load_courses, remove_course
from utils import make_slug


@click.group()
def cli():
    """Learning Content Pipeline - onboard course content into AI Leela LMS."""
    pass


# ── onboard ──────────────────────────────────────────────────────────────
@cli.command()
def onboard():
    """Interactive course onboarding (create or select)."""
    ensure_dirs()
    click.echo("\n=== Course Onboarding ===\n")
    click.echo("  [1] Create new course")
    click.echo("  [2] Select existing course")
    click.echo("  [3] Delete existing course")
    choice = click.prompt("\nChoose an option", type=click.IntRange(1, 3))

    if choice == 1:
        name = click.prompt("Course name").strip()
        if not name:
            raise click.ClickException("Course name cannot be empty.")
        slug = make_slug(name)
        slug = click.prompt("Course slug", default=slug).strip()
        course = add_course(name, slug)
        click.echo(f"\nCreated course: {course['name']}  (slug: {course['slug']})")
    elif choice == 2:
        courses = load_courses()
        if not courses:
            raise click.ClickException(
                "No courses registered yet. Choose option [1] to create one."
            )
        click.echo()
        for i, c in enumerate(courses, 1):
            click.echo(f"  [{i}] {c['name']}  ({c['slug']})")
        idx = click.prompt(
            "\nSelect course number", type=click.IntRange(1, len(courses))
        )
        course = courses[idx - 1]
        click.echo(f"\nSelected course: {course['name']}  (slug: {course['slug']})")
    else:
        courses = load_courses()
        if not courses:
            raise click.ClickException(
                "No courses registered yet. Nothing to delete."
            )
        click.echo()
        for i, c in enumerate(courses, 1):
            click.echo(f"  [{i}] {c['name']}  ({c['slug']})")
        idx = click.prompt(
            "\nSelect course to delete", type=click.IntRange(1, len(courses))
        )
        target = courses[idx - 1]
        click.confirm(
            f"\nDelete '{target['name']}' ({target['slug']}) and all output files?",
            abort=True,
        )
        removed = remove_course(target["slug"])
        click.echo(f"\nDeleted course: {removed['name']}  (slug: {removed['slug']})")


# ── split (Stage 1) ─────────────────────────────────────────────────────
@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--course", required=True, help="Course slug (must exist in registry).")
def split(file, course):
    """Stage 1 - Split a .txt/.docx document into per-module files."""
    from stage1_split import split_document

    split_document(file, course)


# ── convert (Stage 2) ───────────────────────────────────────────────────
@cli.command()
@click.option("--course", required=True, help="Course slug.")
@click.option("--ai", is_flag=True, default=False, help="Use OpenAI to enrich JSON output.")
def convert(course, ai):
    """Stage 2 - Module files to structured JSON."""
    from stage2_json import convert_to_json

    convert_to_json(course, use_ai=ai)


# ── generate-sql (Stage 3) ──────────────────────────────────────────────
@cli.command("generate-sql")
@click.option("--course", required=True, help="Course slug.")
def generate_sql_cmd(course):
    """Stage 3 - JSON to PostgreSQL SQL INSERT statements."""
    from stage3_sql import generate_sql

    generate_sql(course)


# ── run (all stages) ────────────────────────────────────────────────────
@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--course", required=True, help="Course slug.")
@click.option("--ai", is_flag=True, default=False, help="Use OpenAI for Stage 2 enrichment.")
def run(file, course, ai):
    """Run all 3 stages in sequence (split > convert > generate-sql)."""
    from stage1_split import split_document
    from stage2_json import convert_to_json
    from stage3_sql import generate_sql

    click.echo("=" * 50)
    click.echo("Stage 1: Splitting document into modules...")
    click.echo("=" * 50)
    split_document(file, course)

    click.echo()
    click.echo("=" * 50)
    click.echo("Stage 2: Converting modules to JSON...")
    click.echo("=" * 50)
    convert_to_json(course, use_ai=ai)

    click.echo()
    click.echo("=" * 50)
    click.echo("Stage 3: Generating SQL...")
    click.echo("=" * 50)
    generate_sql(course)

    click.echo()
    click.echo("Pipeline complete!")


# ── courses (list) ───────────────────────────────────────────────────────
@cli.command()
def courses():
    """List all registered courses."""
    list_courses()


if __name__ == "__main__":
    cli()
