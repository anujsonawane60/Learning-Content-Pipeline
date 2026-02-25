"""
Stage 1: Split a course .txt file into separate module files.

Reads a course text file from input/, detects Module headings,
and writes each module to its own file under output/1_modules/{course_slug}/.

Usage:
    python -m pipeline.split_course                  # auto-detect
    python -m pipeline.split_course my_course.txt    # specify file
"""

import os
import sys

from config import (
    INPUT_DIR, MODULES_DIR, MODULE_HEADING_RE, make_slug, ensure_dirs
)


def parse_course_header(lines):
    """Extract course title and slug from the first lines of the file.

    Expects:
        Course: Some Title
        Slug: some-slug
    """
    title = None
    slug = None

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("course:"):
            title = stripped.split(":", 1)[1].strip()
        elif stripped.lower().startswith("slug:"):
            slug = stripped.split(":", 1)[1].strip()
        # Stop scanning after first blank line following header
        if title and slug:
            break

    if not title:
        print("ERROR: No 'Course: ...' line found at the top of the file.")
        sys.exit(1)

    if not slug:
        slug = make_slug(title)
        print(f"  No 'Slug:' line found — generated slug: {slug}")

    return title, slug


def find_header_end(lines):
    """Find where the header (Course/Slug lines) ends.

    Returns the index of the first line after the header block.
    """
    found_header = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("course:") or stripped.lower().startswith("slug:"):
            found_header = True
            continue
        if found_header and stripped == "":
            continue
        if found_header:
            return i
    return 0


def split_into_modules(lines):
    """Split lines into modules based on Module headings.

    Returns list of (module_number, module_title, content_lines).
    """
    modules = []
    current_number = None
    current_title = None
    current_lines = []

    for line in lines:
        match = MODULE_HEADING_RE.match(line.strip())
        if match:
            # Save previous module if any
            if current_title is not None:
                modules.append((current_number, current_title, current_lines))
            current_number = int(match.group(1))
            current_title = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save last module
    if current_title is not None:
        modules.append((current_number, current_title, current_lines))

    return modules


def extract_preamble(lines):
    """Extract text between header and first module heading (course description)."""
    preamble_lines = []
    for line in lines:
        if MODULE_HEADING_RE.match(line.strip()):
            break
        preamble_lines.append(line)

    # Trim leading/trailing blank lines
    text = "".join(preamble_lines).strip()
    return text


def split_course(input_path):
    """Main function: split a course file into module files."""
    ensure_dirs()

    print(f"Reading: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # Parse header
    title, slug = parse_course_header(all_lines)
    print(f"  Course: {title}")
    print(f"  Slug:   {slug}")

    # Find where content starts (after header)
    content_start = find_header_end(all_lines)
    content_lines = all_lines[content_start:]

    # Extract preamble (course description)
    preamble = extract_preamble(content_lines)

    # Split into modules
    modules = split_into_modules(content_lines)

    if not modules:
        print("ERROR: No modules found. Expected lines like 'Module 1: Title'")
        sys.exit(1)

    # Create output directory
    course_dir = os.path.join(MODULES_DIR, slug)
    os.makedirs(course_dir, exist_ok=True)

    # Write course metadata
    meta_path = os.path.join(course_dir, "_course_meta.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"Course: {title}\n")
        f.write(f"Slug: {slug}\n")
        if preamble:
            f.write(f"\n{preamble}\n")

    print(f"  Wrote: _course_meta.txt")

    # Write each module
    for mod_num, mod_title, mod_lines in modules:
        mod_slug = make_slug(mod_title)
        filename = f"module_{mod_num:02d}_{mod_slug}.txt"
        mod_path = os.path.join(course_dir, filename)

        content = "".join(mod_lines).strip()
        if not content:
            print(f"  WARNING: Module {mod_num} '{mod_title}' is empty")

        with open(mod_path, "w", encoding="utf-8") as f:
            f.write(f"Module {mod_num}: {mod_title}\n\n")
            f.write(content + "\n")

        print(f"  Wrote: {filename}  ({mod_title})")

    print(f"\nDone — {len(modules)} module(s) written to output/1_modules/{slug}/")
    return slug


def find_input_file(filename=None):
    """Find the input file. Auto-detect if no filename specified."""
    if filename:
        # Try as-is first, then relative to INPUT_DIR
        if os.path.isfile(filename):
            return filename
        path = os.path.join(INPUT_DIR, filename)
        if os.path.isfile(path):
            return path
        print(f"ERROR: File not found: {filename}")
        sys.exit(1)

    # Auto-detect: find .txt files in input/
    txt_files = [f for f in os.listdir(INPUT_DIR)
                 if f.endswith(".txt") and not f.startswith(".")]

    if not txt_files:
        print(f"ERROR: No .txt files found in {INPUT_DIR}/")
        print("  Place a course .txt file in the input/ folder, or specify a filename.")
        sys.exit(1)

    if len(txt_files) > 1:
        print(f"Multiple .txt files found in input/: {', '.join(txt_files)}")
        print("  Specify which file to use: python -m pipeline.split_course <filename>")
        sys.exit(1)

    return os.path.join(INPUT_DIR, txt_files[0])


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = find_input_file(arg)
    split_course(path)
