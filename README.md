# Learning Content Pipeline

CLI tool to onboard course content (`.txt`/`.docx`) into the AI Leela LMS database.

## Pipeline Stages

### Stage 1: Split

Parses a source document (`.txt` or `.docx`) into per-module text files.

- Detects `Module N: Title` headings and splits into separate files
- DOCX support: converts styled headings (Heading 1/2/3) into text markers
- Output: `output/1_modules/<slug>/module_01_<title>.txt`

### Stage 2: Convert to JSON

Transforms module text files into structured, LMS-compatible JSON.

- Parses `Chapter N: Title` headings and `### Section` markers within each module
- Sections supported: Overview, Instructions, Sample Prompt, Key Learnings, Activity
- Generates per-module JSON and a combined course JSON
- Optional OpenAI enrichment via `--ai` flag (uses gpt-4o-mini)
- Output: `output/2_json/<slug>.json` and `output/2_json/<slug>/module_*.json`

### Stage 3: Generate SQL

Produces idempotent PostgreSQL SQL from the JSON.

- Generates PL/pgSQL `DO $$` blocks with `IF NOT EXISTS` checks
- Safe to re-run without creating duplicates
- Wraps all inserts in a single `BEGIN`/`COMMIT` transaction
- Output: `output/3_sql/<slug>/full.sql` and per-module `.sql` files

## Setup

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your OpenAI key if using AI enrichment.

## Usage

### Interactive mode (recommended)

```bash
python run.py
```

Main menu:

```
[0] Exit
[1] Create new course          -- from .txt/.docx, runs full 3-stage pipeline
[2] Import course from JSON    -- from LMS export JSON, reconstructs module files
[3] Select existing course     -- view details, add modules/chapters, delete
```

**Create new course** prompts for a name and slug, then asks for a `.txt`/`.docx` file and runs all 3 stages.

**Import course from JSON** reads an LMS export file (with `course` and `modules` keys), registers the course, reconstructs `module_*.txt` files from the JSON content, then runs stages 2-3.

**Select existing course** shows module/JSON/SQL status and offers:

```
[1] Add/update content
    [1] Add module    -- provide a .txt/.docx with a Module heading
    [2] Add chapter   -- pick an existing module, append chapter content
[2] Delete this course
```

### CLI commands

```bash
# Run individual stages
python cli.py split <file> --course <slug>
python cli.py convert --course <slug> [--ai]
python cli.py generate-sql --course <slug>

# Run all stages at once
python cli.py run <file> --course <slug> [--ai]

# Manage courses
python cli.py onboard
python cli.py courses
```

## Output Structure

```
output/
  1_modules/<slug>/          # Per-module .txt files (source of truth)
    module_01_<title>.txt
    module_02_<title>.txt
  2_json/
    <slug>.json              # Combined course JSON
    <slug>/                  # Per-module JSON files
      module_01_<title>.json
  3_sql/
    <slug>/
      full.sql               # Combined SQL (all modules)
      module_01_<title>.sql   # Per-module SQL files
```

## Input Formats

### Text files (.txt)

Documents should use headings like:

```
Module 1: Module Title
Chapter 1: Chapter Title
### Overview
...
### Instructions
...
### Sample Prompt
...
### Key Learnings
...
### Activity
...
```

### Word documents (.docx)

Styled headings are converted automatically:

- **Heading 1** (no number/emoji-prefixed) -> `Module N: Title`
- **Heading 1** (number-prefixed) -> `Chapter N: Title`
- **Heading 2** (numbered) -> `Chapter N: Title`
- **Heading 2** (section name) -> `### Section Name`
- **Heading 3/4** -> `### Section Name`

### LMS export JSON

For importing existing courses. Expected structure:

```json
{
  "export_meta": { ... },
  "course": { "title": "...", "slug": "..." },
  "modules": [
    {
      "title": "...", "order_index": 1,
      "chapters": [
        {
          "title": "...", "order_index": 1,
          "content_data": {
            "languages": {
              "en": { "overview": [], "instructions": [], ... }
            }
          }
        }
      ]
    }
  ]
}
```

## Key Files

| File | Purpose |
|------|---------|
| `run.py` | Interactive entry point, menu system, import/add flows |
| `cli.py` | Click CLI commands (split, convert, generate-sql, run) |
| `config.py` | Paths, regex patterns, defaults |
| `utils.py` | Slug generation, file I/O, DOCX parsing |
| `courses.py` | Course registry CRUD (courses.json) |
| `stage1_split.py` | Stage 1: document -> per-module .txt files |
| `stage2_json.py` | Stage 2: module files -> structured JSON |
| `stage3_sql.py` | Stage 3: JSON -> PostgreSQL SQL |
| `ai_enricher.py` | Optional OpenAI enrichment (gpt-4o-mini) |
