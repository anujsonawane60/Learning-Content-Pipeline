"""
Stage 2: Convert module .txt files into a structured JSON file.

Reads module files from output/1_modules/{course_slug}/, parses chapter
headings and content, and writes a single JSON file to output/2_json/.

Usage:
    python -m pipeline.module_to_json                   # auto-detect
    python -m pipeline.module_to_json intro-web-dev     # specify slug
"""

import json
import os
import re
import sys

from config import (
    MODULES_DIR, JSON_DIR, MODULE_HEADING_RE, CHAPTER_HEADING_RE,
    make_slug, MODULE_DEFAULTS, CHAPTER_DEFAULTS, ensure_dirs
)


def parse_course_meta(course_dir):
    """Read _course_meta.txt and extract course title, slug, and description."""
    meta_path = os.path.join(course_dir, "_course_meta.txt")
    if not os.path.isfile(meta_path):
        print(f"ERROR: _course_meta.txt not found in {course_dir}")
        sys.exit(1)

    with open(meta_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    title = None
    slug = None
    desc_lines = []
    past_header = False

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("course:"):
            title = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("slug:"):
            slug = stripped.split(":", 1)[1].strip()
        elif title and slug:
            past_header = True
            desc_lines.append(line)

    description = "".join(desc_lines).strip()
    return title, slug, description


def extract_description(text, max_len=200):
    """Extract a short description from the first non-empty line of text."""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            if len(stripped) > max_len:
                return stripped[:max_len].rsplit(" ", 1)[0] + "..."
            return stripped
    return ""


def parse_chapters(lines):
    """Split module content lines into chapters based on Chapter headings.

    Returns (module_description, chapters_list).
    """
    chapters = []
    current_number = None
    current_title = None
    current_lines = []
    pre_chapter_lines = []

    for line in lines:
        match = CHAPTER_HEADING_RE.match(line.strip())
        if match:
            if current_title is not None:
                chapters.append((current_number, current_title, current_lines))
            current_number = int(match.group(1))
            current_title = match.group(2).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
        else:
            pre_chapter_lines.append(line)

    # Save last chapter
    if current_title is not None:
        chapters.append((current_number, current_title, current_lines))

    module_desc = "".join(pre_chapter_lines).strip()
    return module_desc, chapters


def parse_module_file(filepath):
    """Parse a single module .txt file into structured data."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # First line should be the module heading — extract it
    module_title = None
    module_number = None
    content_start = 0

    for i, line in enumerate(lines):
        match = MODULE_HEADING_RE.match(line.strip())
        if match:
            module_number = int(match.group(1))
            module_title = match.group(2).strip()
            content_start = i + 1
            break

    if module_title is None:
        # Fallback: use filename
        basename = os.path.splitext(os.path.basename(filepath))[0]
        module_title = basename.replace("_", " ").title()
        module_number = 0

    content_lines = lines[content_start:]
    module_desc, chapters_raw = parse_chapters(content_lines)

    module_slug = make_slug(module_title)

    # Build chapter objects
    chapter_objects = []
    for ch_num, ch_title, ch_lines in chapters_raw:
        body = "".join(ch_lines).strip()
        ch_slug = make_slug(ch_title)
        description = extract_description(body)

        chapter = {
            "title": ch_title,
            "slug": ch_slug,
            "description": description,
            "content_data": {
                "type": "text",
                "body": body
            },
            **CHAPTER_DEFAULTS,
        }
        chapter_objects.append(chapter)

    module = {
        "title": module_title,
        "slug": module_slug,
        "description": module_desc if module_desc else extract_description(module_title),
        **MODULE_DEFAULTS,
        "chapters": chapter_objects,
    }

    return module_number, module


def convert_course_to_json(course_slug):
    """Main function: read all module files and produce a single JSON."""
    ensure_dirs()

    course_dir = os.path.join(MODULES_DIR, course_slug)
    if not os.path.isdir(course_dir):
        print(f"ERROR: Module directory not found: {course_dir}")
        print("  Run stage 1 first: python -m pipeline.split_course")
        sys.exit(1)

    # Read course metadata
    title, slug, description = parse_course_meta(course_dir)
    print(f"  Course: {title}")
    print(f"  Slug:   {slug}")

    # Find module files (sorted by filename → by module number)
    module_files = sorted([
        f for f in os.listdir(course_dir)
        if f.startswith("module_") and f.endswith(".txt")
    ])

    if not module_files:
        print(f"ERROR: No module files found in {course_dir}")
        sys.exit(1)

    # Parse each module
    modules = []
    total_chapters = 0
    for mf in module_files:
        filepath = os.path.join(course_dir, mf)
        mod_num, module_data = parse_module_file(filepath)
        modules.append((mod_num, module_data))
        ch_count = len(module_data["chapters"])
        total_chapters += ch_count
        print(f"  Module {mod_num}: {module_data['title']}  ({ch_count} chapter(s))")

    # Sort by module number
    modules.sort(key=lambda x: x[0])

    # Build output JSON
    output = {
        "course_title": title,
        "course_slug": slug,
        "course_description": description,
        "modules": [m[1] for m in modules],
    }

    # Write JSON
    json_path = os.path.join(JSON_DIR, f"{slug}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone — {len(modules)} module(s), {total_chapters} chapter(s)")
    print(f"  Written to: output/2_json/{slug}.json")
    return slug


def find_course_slug(slug=None):
    """Find course slug. Auto-detect if none specified."""
    if slug:
        course_dir = os.path.join(MODULES_DIR, slug)
        if not os.path.isdir(course_dir):
            print(f"ERROR: No module directory found for slug '{slug}'")
            sys.exit(1)
        return slug

    # Auto-detect: find subdirectories in MODULES_DIR
    if not os.path.isdir(MODULES_DIR):
        print(f"ERROR: No modules directory found at {MODULES_DIR}")
        print("  Run stage 1 first: python -m pipeline.split_course")
        sys.exit(1)

    dirs = [d for d in os.listdir(MODULES_DIR)
            if os.path.isdir(os.path.join(MODULES_DIR, d))]

    if not dirs:
        print(f"ERROR: No course directories found in {MODULES_DIR}")
        print("  Run stage 1 first: python -m pipeline.split_course")
        sys.exit(1)

    if len(dirs) > 1:
        print(f"Multiple courses found: {', '.join(dirs)}")
        print("  Specify which: python -m pipeline.module_to_json <slug>")
        sys.exit(1)

    return dirs[0]


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    course_slug = find_course_slug(arg)
    convert_course_to_json(course_slug)
