"""Utility helpers: slug generation, file I/O, text cleaning."""

import re
import unicodedata
from pathlib import Path


def make_slug(text: str) -> str:
    """Convert text to a URL-safe slug (lowercase, hyphens, ASCII-only)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def make_chapter_slug(chapter_slug: str, course_slug: str, module_number: int) -> str:
    """Make a globally unique chapter slug by including module number and course suffix."""
    return f"{chapter_slug}-m{module_number}-{course_slug}"


def clean_title(text: str) -> str:
    """Strip extra whitespace and common numbering artifacts from a title."""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_description(text: str, max_len: int = 200) -> str:
    """Return the first meaningful line of text, truncated to max_len."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("###"):
            if len(line) > max_len:
                return line[: max_len - 3] + "..."
            return line
    return ""


# ── DOCX style-aware reading ────────────────────────────────────────────

_KEYCAP_RE = re.compile(r"(\d)\ufe0f?\u20e3")

# Section headings that appear as Heading 2 or Heading 3 in docx
_SECTION_PREFIXES = (
    "overview", "instructions", "sample prompt", "sample script",
    "sample voice", "key learning", "activity",
)


def _is_section_heading(text: str) -> bool:
    """Check if text is a section heading (Overview, Instructions, etc.)."""
    cleaned = text.strip().lower()
    return any(cleaned.startswith(p) for p in _SECTION_PREFIXES)


def _clean_docx_heading(text: str) -> tuple[int | None, str]:
    """Remove emoji decorators from a heading, extract number if present.

    Returns (number_or_None, cleaned_title).
    """
    text = text.strip()
    num = None

    # Check for leading keycap-ten emoji
    if text.startswith("\U0001f51f"):
        num = 10
        text = text[len("\U0001f51f"):]
    else:
        # Extract leading keycap digit sequence (1..9, 11, 12, etc.)
        digits: list[str] = []
        pos = 0
        while pos < len(text):
            m = _KEYCAP_RE.match(text, pos)
            if m:
                digits.append(m.group(1))
                pos = m.end()
            else:
                break
        if digits:
            num = int("".join(digits))
            text = text[pos:]

    # Strip leading non-ASCII-letter chars (remaining emojis, bullets, symbols)
    text = re.sub(r"^[^a-zA-Z0-9]+", "", text)

    # Remove common docx suffixes
    text = re.sub(
        r"\s*[:\-\u2013\u2014]+\s*Final Structured Module\s*$",
        "", text, flags=re.IGNORECASE,
    )

    return num, text.strip()


def extract_text_from_docx(filepath: str | Path) -> list[str]:
    """Read a .docx file, converting styled headings to text markers.

    - Heading 1 (emoji-prefixed or no number) -> Module N: Title
    - Heading 1 (number-prefixed)             -> Chapter N: Title
    - Heading 2 (numbered)                    -> Chapter N: Title
    - Heading 2 (section name)                -> ### Section Name
    - Heading 3                               -> ### Section Name
    - Normal                                  -> plain text
    """
    from docx import Document
    from config import MODULE_HEADING_RE, CHAPTER_HEADING_RE

    doc = Document(str(filepath))
    lines: list[str] = []
    module_counter = 0
    chapter_counter = 0

    for para in doc.paragraphs:
        text = para.text.strip()
        style = para.style.name if para.style else "Normal"

        if not text:
            lines.append("")
            continue

        # If text already matches "Module N:" or "Chapter N:" pass through as-is
        mod_match = MODULE_HEADING_RE.match(text)
        chap_match = CHAPTER_HEADING_RE.match(text)

        if mod_match:
            module_counter = int(mod_match.group(1))
            chapter_counter = 0
            lines.append(text)
        elif chap_match:
            chapter_counter = int(chap_match.group(1))
            lines.append(text)
        elif style == "Heading 1":
            num, title = _clean_docx_heading(text)
            if num is None:
                module_counter += 1
                chapter_counter = 0
                lines.append(f"Module {module_counter}: {title}")
            else:
                chapter_counter = num
                lines.append(f"Chapter {num}: {title}")
        elif style == "Heading 2":
            num, title = _clean_docx_heading(text)
            if _is_section_heading(title):
                lines.append(f"### {title}")
            else:
                if num:
                    chapter_counter = num
                else:
                    chapter_counter += 1
                lines.append(f"Chapter {chapter_counter}: {title}")
        elif style.startswith("Heading 3") or style.startswith("Heading 4"):
            lines.append(f"### {text}")
        else:
            lines.append(text)

    return lines


def read_document(filepath: str | Path) -> list[str]:
    """Detect file extension and return lines. Supports .txt and .docx."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = filepath.suffix.lower()
    if ext == ".docx":
        return extract_text_from_docx(filepath)
    elif ext == ".txt":
        return filepath.read_text(encoding="utf-8").splitlines()
    else:
        raise ValueError(f"Unsupported file type: {ext} (expected .txt or .docx)")
