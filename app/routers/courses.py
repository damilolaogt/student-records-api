"""
routers/courses.py
──────────────────────────────────────────────────────────────────────────────
Course CRUD endpoints.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.dependencies import get_db

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post(
    "/",
    response_model=schemas.CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course",
)
def create_course(
    payload: schemas.CourseCreate,
    db: Session = Depends(get_db),
) -> schemas.CourseResponse:
    """
    Register a new course.

    - **course_code**: automatically upper-cased; must be unique.
    - **credit_units**: must be greater than zero.
    - Returns **400 Bad Request** on duplicate course_code.
    """
    return crud.create_course(db, payload)


@router.get(
    "/",
    response_model=dict,
    summary="List all courses (paginated)",
)
def list_courses(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Return a paginated list of courses ordered by course_code."""
    total, courses = crud.list_courses(db, limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [schemas.CourseResponse.model_validate(c) for c in courses],
    }


@router.get(
    "/{course_id}",
    response_model=schemas.CourseResponse,
    summary="Get a single course by ID",
)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
) -> schemas.CourseResponse:
    """Fetch a course by its integer primary key. Returns **404** if absent."""
    return crud.get_course(db, course_id)


@router.put(
    "/{course_id}",
    response_model=schemas.CourseResponse,
    summary="Update course info",
)
def update_course(
    course_id: int,
    payload: schemas.CourseUpdate,
    db: Session = Depends(get_db),
) -> schemas.CourseResponse:
    """Partially update a course's title and/or credit_units."""
    return crud.update_course(db, course_id, payload)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course",
)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete a course.

    - Returns **400 Bad Request** if academic records reference this course
      (FK RESTRICT prevents orphaned records).
    - Returns **204 No Content** on success.
    """
    crud.delete_course(db, course_id)
