"""
main.py
──────────────────────────────────────────────────────────────────────────────
FastAPI application factory for the Student Academic Records Management API.

Start the development server:
    uvicorn app.main:app --reload --port 8000

Web UI:     http://localhost:8000/ui
API docs:   http://localhost:8000/docs

Production (e.g., via Gunicorn):
    gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import verify_database_connection
from app.routers import courses, records, students

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown hooks)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup checks before accepting traffic."""
    logger.info("Starting up Student Academic Records API…")
    try:
        verify_database_connection()
        logger.info("✓ Database connection verified.")
    except Exception as exc:
        logger.critical("✗ Database connection FAILED: %s", exc)
        raise

    yield  # application is now running

    logger.info("Shutting down Student Academic Records API.")


# ─────────────────────────────────────────────────────────────────────────────
# Application instance
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Student Academic Records Management API",
    description=(
        "A production-ready REST API for managing university student records, "
        "course enrolments, grades, and GPA/CGPA analytics.\n\n"
        "**Grade scale (5-point)**\n"
        "| Score Range | Grade | Grade Point |\n"
        "|-------------|-------|-------------|\n"
        "| 70 – 100    | A     | 5.0         |\n"
        "| 60 – 69     | B     | 4.0         |\n"
        "| 50 – 59     | C     | 3.0         |\n"
        "| 45 – 49     | D     | 2.0         |\n"
        "| 40 – 44     | E     | 1.0         |\n"
        "| 0  – 39     | F     | 0.0         |\n"
    ),
    version="1.0.0",
    contact={"name": "Academic Registry", "email": "registry@university.edu"},
    license_info={"name": "MIT"},
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS middleware (adjust origins for production)
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Global exception handler (catch-all for unexpected errors)
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception for %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(students.router)
app.include_router(courses.router)
app.include_router(records.router)


# ─────────────────────────────────────────────────────────────────────────────
# Health-check endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health check")
def health_check() -> dict:
    """Returns 200 OK when the API is running."""
    return {"status": "ok", "service": "student-academic-records-api"}


@app.get("/", tags=["Root"], include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect root to the web UI."""
    return RedirectResponse(url="/ui")


# ─────────────────────────────────────────────────────────────────────────────
# Web UI — served from the frontend/ directory
# Must be mounted AFTER all API routes so /ui/* doesn't shadow API paths.
# ─────────────────────────────────────────────────────────────────────────────

app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")
