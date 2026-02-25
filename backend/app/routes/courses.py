"""REST endpoints for course operations."""

import os

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from config import INPUT_DIR, ensure_dirs
from ..services.pipeline import run_pipeline
from ..services.scanner import scan_courses, get_course_detail, get_file_path

router = APIRouter()


@router.post("/courses/upload")
async def upload_course(file: UploadFile = File(...)):
    """Upload a .txt file, run the full pipeline, return result."""
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are accepted")

    ensure_dirs()

    # Save uploaded file to input/
    input_path = os.path.join(INPUT_DIR, file.filename)
    try:
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}")

    # Run pipeline
    try:
        result = run_pipeline(input_path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "course_slug": result["course_slug"],
        "message": result["message"],
    }


@router.get("/courses")
def list_courses():
    """List all processed courses."""
    return scan_courses()


@router.get("/courses/{slug}")
def course_detail(slug: str):
    """Full course detail (read JSON file)."""
    data = get_course_detail(slug)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Course '{slug}' not found")
    return data


@router.get("/courses/{slug}/files/json")
def download_json(slug: str):
    """Download the course JSON file."""
    path = get_file_path(slug, "json")
    if path is None:
        raise HTTPException(status_code=404, detail="JSON file not found")
    return FileResponse(path, media_type="application/json", filename=f"{slug}.json")


@router.get("/courses/{slug}/files/sql")
def download_sql(slug: str):
    """Download the course SQL file."""
    path = get_file_path(slug, "sql")
    if path is None:
        raise HTTPException(status_code=404, detail="SQL file not found")
    return FileResponse(path, media_type="application/sql", filename=f"{slug}.sql")
