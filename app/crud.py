"""
crud.py
──────────────────────────────────────────────────────────────────────────────
All database operations for the Student Academic Records system.

Principles:
  - Pure SQLAlchemy 2.0 ORM style (select() + session.scalars / session.execute).
  - No raw SQL strings.
  - IntegrityError translated to HTTPException(400) at service boundary.
  - GPA/CGPA computed in Python from loaded ORM objects (avoids complex SQL
    aggregation that is harder to maintain; acceptable at typical university
    scale; can be pushed to DB window functions if needed later).
"""

import uuid
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import AcademicRecord, Course, GradeEnum, Student, compute_grade
from app.schemas import (
    CourseCreate,
    CourseUpdate,
    RecordCreate,
    RecordUpdate,
    StudentCreate,
    StudentUpdate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Student CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def create_student(db: Session, payload: StudentCreate) -> Student:
    """Create a new student; raise 400 on duplicate email or matric_number."""
    student = Student(**payload.model_dump())
    db.add(student)
    try:
        db.commit()
        db.refresh(student)
    except IntegrityError as exc:
        db.rollback()
        _handle_student_integrity_error(exc)
    return student


def get_student(db: Session, student_id: uuid.UUID) -> Student:
    """Fetch a single student by UUID; raise 404 if absent."""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with id '{student_id}' not found.",
        )
    return student


def list_students(
    db: Session,
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    department: Optional[str] = None,
    matric_number: Optional[str] = None,
) -> tuple[int, list[Student]]:
    """
    Return (total_count, page_of_students).

    Filters:
      search         – partial match on first_name OR last_name OR email.
      department     – exact match on department.
      matric_number  – exact match on matric_number.
    """
    stmt = select(Student)

    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.email.ilike(like),
            )
        )
    if department:
        stmt = stmt.where(Student.department.ilike(f"%{department}%"))
    if matric_number:
        stmt = stmt.where(Student.matric_number == matric_number)

    # Count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Student.last_name, Student.first_name).offset(offset).limit(limit)
    students = list(db.scalars(stmt).all())

    return total, students


def update_student(
    db: Session, student_id: uuid.UUID, payload: StudentUpdate
) -> Student:
    """Partially update a student; raise 404 / 400 as appropriate."""
    student = get_student(db, student_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student, field, value)

    try:
        db.commit()
        db.refresh(student)
    except IntegrityError as exc:
        db.rollback()
        _handle_student_integrity_error(exc)
    return student


def delete_student(db: Session, student_id: uuid.UUID) -> None:
    """Delete a student and cascade-delete their academic records."""
    student = get_student(db, student_id)
    db.delete(student)
    db.commit()


# ─── helpers ────────────────────────────────────────────────────────────────

def _handle_student_integrity_error(exc: IntegrityError) -> None:
    msg = str(exc.orig).lower()
    if "email" in msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email address already exists.",
        )
    if "matric_number" in msg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this matric number already exists.",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Database integrity error. Check for duplicate values.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Course CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def create_course(db: Session, payload: CourseCreate) -> Course:
    course = Course(**payload.model_dump())
    db.add(course)
    try:
        db.commit()
        db.refresh(course)
    except IntegrityError as exc:
        db.rollback()
        msg = str(exc.orig).lower()
        if "course_code" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course code '{payload.course_code}' already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Database integrity error.",
        )
    return course


def get_course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id '{course_id}' not found.",
        )
    return course


def list_courses(db: Session, limit: int = 20, offset: int = 0) -> tuple[int, list[Course]]:
    count_stmt = select(func.count(Course.id))
    total = db.execute(count_stmt).scalar_one()
    courses = list(
        db.scalars(select(Course).order_by(Course.course_code).offset(offset).limit(limit))
    )
    return total, courses


def update_course(db: Session, course_id: int, payload: CourseUpdate) -> Course:
    course = get_course(db, course_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, course_id: int) -> None:
    """
    Delete a course. Raises 400 if academic records reference it (FK RESTRICT).
    """
    course = get_course(db, course_id)
    db.delete(course)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete course: academic records exist for this course.",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AcademicRecord CRUD
# ═══════════════════════════════════════════════════════════════════════════════

def create_record(db: Session, payload: RecordCreate) -> AcademicRecord:
    """
    Create an academic record.  Grade and grade_point are derived automatically
    from the submitted score.  Raises 404 for missing student/course; 400 for
    duplicate (student, course, semester).
    """
    # Validate FK targets exist
    get_student(db, payload.student_id)
    get_course(db, payload.course_id)

    grade, grade_point = compute_grade(payload.score)

    record = AcademicRecord(
        student_id=payload.student_id,
        course_id=payload.course_id,
        semester=payload.semester,
        score=payload.score,
        grade=grade,
        grade_point=grade_point,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "An academic record for this student, course, and semester "
                "already exists."
            ),
        )
    # Eager-load course for the response
    db.refresh(record, ["course"])
    return record


def get_record(db: Session, record_id: int) -> AcademicRecord:
    stmt = (
        select(AcademicRecord)
        .options(joinedload(AcademicRecord.course))
        .where(AcademicRecord.id == record_id)
    )
    record = db.scalars(stmt).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Academic record with id '{record_id}' not found.",
        )
    return record


def update_record(db: Session, record_id: int, payload: RecordUpdate) -> AcademicRecord:
    """
    Update score and/or semester.  If score changes, grade and grade_point are
    recomputed automatically.
    """
    record = get_record(db, record_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "score" in update_data:
        new_score = update_data["score"]
        grade, grade_point = compute_grade(new_score)
        record.score = new_score
        record.grade = grade
        record.grade_point = grade_point

    if "semester" in update_data:
        record.semester = update_data["semester"]

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Updating this record would create a duplicate "
                "(student, course, semester) combination."
            ),
        )
    db.refresh(record, ["course"])
    return record


def delete_record(db: Session, record_id: int) -> None:
    record = get_record(db, record_id)
    db.delete(record)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Transcript / Analytics
# ═══════════════════════════════════════════════════════════════════════════════

def get_transcript(db: Session, student_id: uuid.UUID) -> dict:
    """
    Build a comprehensive academic transcript for a student.

    Returns a plain dict matching the TranscriptResponse schema:
    {
        "student": <Student ORM obj>,
        "semesters": [
            {
                "semester": str,
                "records": [...],
                "credit_units_attempted": int,
                "credit_units_passed": int,
                "semester_gpa": float,
            }, ...
        ],
        "total_credit_units_attempted": int,
        "total_credit_units_passed": int,
        "cgpa": float,
    }
    """
    student = get_student(db, student_id)

    # Load all records with their courses in one query
    stmt = (
        select(AcademicRecord)
        .options(joinedload(AcademicRecord.course))
        .where(AcademicRecord.student_id == student_id)
        .order_by(AcademicRecord.semester, AcademicRecord.id)
    )
    records: list[AcademicRecord] = list(db.scalars(stmt).unique().all())

    # Group records by semester
    semester_map: dict[str, list[AcademicRecord]] = defaultdict(list)
    for r in records:
        semester_map[r.semester].append(r)

    semesters_detail = []
    cgpa_numerator = 0.0
    cgpa_denominator = 0

    for semester_name in sorted(semester_map.keys()):
        sem_records = semester_map[semester_name]

        units_attempted = sum(r.course.credit_units for r in sem_records)
        units_passed = sum(
            r.course.credit_units for r in sem_records if r.grade != GradeEnum.F
        )
        gpa_numerator = sum(r.grade_point * r.course.credit_units for r in sem_records)
        semester_gpa = (gpa_numerator / units_attempted) if units_attempted > 0 else 0.0

        cgpa_numerator += gpa_numerator
        cgpa_denominator += units_attempted

        semesters_detail.append(
            {
                "semester": semester_name,
                "records": sem_records,
                "credit_units_attempted": units_attempted,
                "credit_units_passed": units_passed,
                "semester_gpa": round(semester_gpa, 2),
            }
        )

    total_attempted = sum(s["credit_units_attempted"] for s in semesters_detail)
    total_passed = sum(s["credit_units_passed"] for s in semesters_detail)
    cgpa = round(cgpa_numerator / cgpa_denominator, 2) if cgpa_denominator > 0 else 0.0

    return {
        "student": student,
        "semesters": semesters_detail,
        "total_credit_units_attempted": total_attempted,
        "total_credit_units_passed": total_passed,
        "cgpa": cgpa,
    }
