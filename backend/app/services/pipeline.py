"""Wraps the 3-stage pipeline functions for safe invocation from the API."""

import io
import sys
from contextlib import redirect_stdout

from pipeline.split_course import split_course
from pipeline.module_to_json import convert_course_to_json
from pipeline.json_to_sql import convert_json_to_sql


def run_pipeline(input_path: str) -> dict:
    """Run all 3 pipeline stages on the given input file.

    Returns dict with course_slug, message, and captured logs.
    Raises ValueError if any stage fails.
    """
    logs = io.StringIO()

    try:
        with redirect_stdout(logs):
            # Stage 1: split txt → module files
            slug = split_course(input_path)

            # Stage 2: modules → JSON
            convert_course_to_json(slug)

            # Stage 3: JSON → SQL
            convert_json_to_sql(slug)

    except SystemExit as exc:
        # Pipeline scripts call sys.exit(1) on errors
        captured = logs.getvalue()
        raise ValueError(f"Pipeline failed:\n{captured}") from exc

    return {
        "course_slug": slug,
        "message": "Pipeline completed successfully",
        "logs": logs.getvalue(),
    }
