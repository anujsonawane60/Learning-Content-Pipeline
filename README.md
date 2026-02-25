# Learning Content Pipeline

CLI tool to onboard course content (`.txt`/`.docx`) into the AI Leela LMS database.

## Pipeline Stages

1. **Split** — Parse a document into per-module text files
2. **Convert** — Transform module files into structured JSON (optional OpenAI enrichment with `--ai`)
3. **Generate SQL** — Produce PostgreSQL INSERT statements ready to run against the LMS database

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

Walks you through creating/selecting a course, picking an input file, and running all 3 stages automatically.

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

## Output

```
output/
  1_modules/<slug>/    # Per-module .txt files
  2_json/<slug>.json   # Structured course JSON
  3_sql/<slug>.sql     # PostgreSQL INSERT statements
```

## Input Format

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

Supports `.txt` files and `.docx` with styled headings (Heading 1/2/3).
