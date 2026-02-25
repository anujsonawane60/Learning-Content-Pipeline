"""FastAPI application — CORS, router mount."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.courses import router as courses_router

app = FastAPI(title="Learning Content Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
