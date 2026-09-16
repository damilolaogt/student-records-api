"""
routers/students.py
──────────────────────────────────────────────────────────────────────────────
Student CRUD endpoints.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.dependencies import get_db

router = APIRouter(prefix="/students", tags=["Students"])


@router.post(
    "/",
    response_model=schemas.StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new student",
)
def create_student(
    payload: schemas.StudentCreate,
    db: Session = Depends(get_db),
) -> schemas.StudentResponse:
    """
    Register a new student in the system.

    - **matric_number**: must be unique across all students.
    - **email**: must be a valid, unique email address.
    - Returns **201 Created** on success.
    - Returns **400 Bad Request** on duplicate matric_number or email.
    """
    return crud.create_student(db, payload)


@router.get(
    "/",
    response_model=schemas.StudentListResponse,
    summary="List students with optional filters",
)
def list_students(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    search: Optional[str] = Query(
        None, description="Partial match on first_name, last_name, or email"
    ),
    department: Optional[str] = Query(None, description="Filter by department (partial match)"),
    matric_number: Optional[str] = Query(None, description="Exact matric_number lookup"),
) -> schemas.StudentListResponse:
    """
    Return a paginated list of students.

    Supports simultaneous filtering by `search`, `department`, and `matric_number`.
    """
    total, students = crud.list_students(
        db,
        limit=limit,
        offset=offset,
        search=search,
        department=department,
        matric_number=matric_number,
    )
    return schemas.StudentListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[schemas.StudentResponse.model_validate(s) for s in students],
    )


@router.get(
    "/{student_id}",
    response_model=schemas.StudentResponse,
    summary="Get a single student by ID",
)
def get_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> schemas.StudentResponse:
    """
    Fetch full details for a single student.

    - Returns **404 Not Found** if no student with the given UUID exists.
    """
    return crud.get_student(db, student_id)


@router.put(
    "/{student_id}",
    response_model=schemas.StudentResponse,
    summary="Update student demographic info",
)
def update_student(
    student_id: uuid.UUID,
    payload: schemas.StudentUpdate,
    db: Session = Depends(get_db),
) -> schemas.StudentResponse:
    """
    Partially update a student.

    Only fields included in the request body are modified.  All fields are
    optional; an empty body is a no-op.

    - Returns **404 Not Found** if student does not exist.
    - Returns **400 Bad Request** on duplicate email.
    """
    return crud.update_student(db, student_id, payload)


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a student and all their records",
)
def delete_student(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    """
    Permanently delete a student.  All associated academic records are
    cascade-deleted automatically.

    - Returns **204 No Content** on success.
    - Returns **404 Not Found** if student does not exist.
    """
    crud.delete_student(db, student_id)


@router.get(
    "/{student_id}/transcript",
    response_model=schemas.TranscriptResponse,
    summary="Get a student's complete academic transcript",
)
def get_transcript(
    student_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> schemas.TranscriptResponse:
    """
    Return the full academic transcript for a student, grouped by semester.

    Each semester entry includes:
    - All enrolled courses with individual grades and grade points.
    - **Semester GPA** = weighted average of grade points × credit units.
    - **Credit units attempted** and **credit units passed** (grade ≠ F).

    The response also includes:
    - **Cumulative GPA (CGPA)** across all semesters.
    - **Total credit units** attempted and passed.
    """
    data = crud.get_transcript(db, student_id)
    return schemas.TranscriptResponse.model_validate(data)
