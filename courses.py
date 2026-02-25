"""Course registry — CRUD operations on courses.json."""

import json
import shutil
from datetime import datetime

import click

from config import COURSES_FILE, JSON_DIR, MODULES_DIR, SQL_DIR


def load_courses() -> list[dict]:
    """Load all courses from the registry file."""
    if not COURSES_FILE.exists():
        return []
    data = COURSES_FILE.read_text(encoding="utf-8").strip()
    if not data:
        return []
    return json.loads(data)


def save_courses(courses: list[dict]) -> None:
    """Write the full course list back to the registry file."""
    COURSES_FILE.write_text(
        json.dumps(courses, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_course(name: str, slug: str) -> dict:
    """Add a new course to the registry and return it."""
    courses = load_courses()
    # Check for duplicate slug
    if any(c["slug"] == slug for c in courses):
        raise click.ClickException(f"Course with slug '{slug}' already exists.")
    course = {
        "name": name,
        "slug": slug,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    courses.append(course)
    save_courses(courses)
    return course


def get_course(slug: str) -> dict | None:
    """Find a course by slug, or return None."""
    for c in load_courses():
        if c["slug"] == slug:
            return c
    return None


def remove_course(slug: str) -> dict:
    """Remove a course from the registry and delete its output files."""
    courses = load_courses()
    course = None
    for c in courses:
        if c["slug"] == slug:
            course = c
            break
    if course is None:
        raise click.ClickException(f"Course '{slug}' not found in registry.")

    courses.remove(course)
    save_courses(courses)

    # Clean up output directories and files
    removed = []
    modules_dir = MODULES_DIR / slug
    if modules_dir.exists():
        shutil.rmtree(modules_dir)
        removed.append(str(modules_dir))

    json_file = JSON_DIR / f"{slug}.json"
    if json_file.exists():
        json_file.unlink()
        removed.append(str(json_file))

    sql_file = SQL_DIR / f"{slug}.sql"
    if sql_file.exists():
        sql_file.unlink()
        removed.append(str(sql_file))

    if removed:
        click.echo("Cleaned up output files:")
        for p in removed:
            click.echo(f"  - {p}")

    return course


def list_courses() -> None:
    """Print a formatted table of all registered courses."""
    courses = load_courses()
    if not courses:
        click.echo("No courses registered yet. Run 'python cli.py onboard' first.")
        return
    click.echo(f"\n{'#':<4} {'Name':<40} {'Slug':<30} {'Created'}")
    click.echo("-" * 90)
    for i, c in enumerate(courses, 1):
        click.echo(
            f"{i:<4} {c['name']:<40} {c['slug']:<30} {c.get('created_at', 'N/A')}"
        )
    click.echo()
