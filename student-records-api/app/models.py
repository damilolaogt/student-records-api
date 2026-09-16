"""
models.py
──────────────────────────────────────────────────────────────────────────────
SQLAlchemy 2.0 ORM models for the Student Academic Records system.

Design decisions:
  - UUID primary keys for Student (avoids enumeration attacks).
  - Integer PKs for Course and AcademicRecord (simpler FK joins).
  - Grade is stored as a Python Enum for type-safety and DB-level constraint.
  - score is constrained 0–100 at the DB level via CheckConstraint.
  - AcademicRecord has a composite unique constraint on (student_id, course_id,
    semester) to prevent duplicate enrolment records.
  - Timestamps use server_default=func.now() so the DB clock is canonical.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class GradeEnum(str, enum.Enum):
    """Letter grades on a 5-point scale."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


# ─────────────────────────────────────────────────────────────────────────────
# Score → Grade mapping helpers (used in crud.py too)
# ─────────────────────────────────────────────────────────────────────────────

GRADE_THRESHOLDS: list[tuple[float, GradeEnum, float]] = [
    # (min_score_inclusive, grade, grade_point)
    (70.0, GradeEnum.A, 5.0),
    (60.0, GradeEnum.B, 4.0),
    (50.0, GradeEnum.C, 3.0),
    (45.0, GradeEnum.D, 2.0),
    (40.0, GradeEnum.E, 1.0),
    (0.0,  GradeEnum.F, 0.0),
]


def compute_grade(score: float) -> tuple[GradeEnum, float]:
    """Return (GradeEnum, grade_point) for a given numeric score."""
    for threshold, grade, point in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade, point
    return GradeEnum.F, 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Student
# ─────────────────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    matric_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique institutional student identifier, e.g. CSC/2020/001",
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    enrollment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    records: Mapped[list["AcademicRecord"]] = relationship(
        "AcademicRecord",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} matric={self.matric_number}>"


# ─────────────────────────────────────────────────────────────────────────────
# Course
# ─────────────────────────────────────────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"

    __table_args__ = (
        CheckConstraint("credit_units > 0", name="ck_courses_credit_units_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Canonical course identifier, e.g. CS101",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    credit_units: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    records: Mapped[list["AcademicRecord"]] = relationship(
        "AcademicRecord",
        back_populates="course",
    )

    def __repr__(self) -> str:
        return f"<Course code={self.course_code} units={self.credit_units}>"


# ─────────────────────────────────────────────────────────────────────────────
# AcademicRecord
# ─────────────────────────────────────────────────────────────────────────────

class AcademicRecord(Base):
    __tablename__ = "academic_records"

    __table_args__ = (
        # Prevent a student from being enrolled in the same course twice in the
        # same semester.
        UniqueConstraint(
            "student_id", "course_id", "semester",
            name="uq_academic_records_student_course_semester",
        ),
        # Enforce score is within [0, 100]
        CheckConstraint("score >= 0 AND score <= 100", name="ck_academic_records_score_bounds"),
        # Composite index for common query patterns
        Index("ix_academic_records_student_semester", "student_id", "semester"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
    )

    semester: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment='E.g. "First Semester 2024/2025" or "Fall 2025"',
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[GradeEnum] = mapped_column(
        SAEnum(GradeEnum, name="gradeenum"),
        nullable=False,
    )
    grade_point: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="records")
    course: Mapped["Course"] = relationship("Course", back_populates="records")

    def __repr__(self) -> str:
        return (
            f"<AcademicRecord id={self.id} student={self.student_id} "
            f"course={self.course_id} semester={self.semester}>"
        )
