"""
routers/records.py
──────────────────────────────────────────────────────────────────────────────
Academic record CRUD endpoints.

Grade letters and grade points are computed server-side from the submitted
score — clients never send grade/grade_point directly.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.dependencies import get_db

router = APIRouter(prefix="/records", tags=["Academic Records"])


@router.post(
    "/",
    response_model=schemas.RecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an academic record (enrol + grade a student in a course)",
)
def create_record(
    payload: schemas.RecordCreate,
    db: Session = Depends(get_db),
) -> schemas.RecordResponse:
    """
    Record a student's grade for a specific course and semester.

    - **score** must be in range [0.0, 100.0].
    - **grade** and **grade_point** are automatically computed:
      - ≥ 70 → A / 5.0
      - ≥ 60 → B / 4.0
      - ≥ 50 → C / 3.0
      - ≥ 45 → D / 2.0
      - ≥ 40 → E / 1.0
      - < 40 → F / 0.0
    - Returns **400** if a record for (student, course, semester) already exists.
    - Returns **404** if student_id or course_id does not exist.
    """
    return crud.create_record(db, payload)


@router.get(
    "/{record_id}",
    response_model=schemas.RecordResponse,
    summary="Fetch a single academic record",
)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
) -> schemas.RecordResponse:
    """Retrieve an academic record by its integer primary key."""
    return crud.get_record(db, record_id)


@router.put(
    "/{record_id}",
    response_model=schemas.RecordResponse,
    summary="Update an academic record (score or semester)",
)
def update_record(
    record_id: int,
    payload: schemas.RecordUpdate,
    db: Session = Depends(get_db),
) -> schemas.RecordResponse:
    """
    Update a previously entered academic record.

    - If **score** is updated, **grade** and **grade_point** are recomputed.
    - If **semester** is updated, uniqueness constraint is re-validated.
    - Returns **404** if the record does not exist.
    - Returns **400** on duplicate (student, course, semester).
    """
    return crud.update_record(db, record_id, payload)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an erroneous academic record",
)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Permanently remove an academic record.

    - Returns **204 No Content** on success.
    - Returns **404 Not Found** if record does not exist.
    """
    crud.delete_record(db, record_id)
