"""
schemas.py
──────────────────────────────────────────────────────────────────────────────
Pydantic v2 request/response schemas.

Conventions:
  - *Create  – fields required for creation (no id/timestamps).
  - *Update  – all fields Optional for partial PATCH-style updates.
  - *Response – returned to the caller; includes computed/DB fields.
  - TranscriptResponse – nested response for the /transcript endpoint.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import GradeEnum


# ─────────────────────────────────────────────────────────────────────────────
# Shared config mixin
# ─────────────────────────────────────────────────────────────────────────────

class _ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# Student schemas
# ─────────────────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    matric_number: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["CSC/2020/001"],
        description="Unique institutional student identifier",
    )
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: Optional[str] = Field(None, max_length=150)
    enrollment_year: Optional[int] = Field(
        None, ge=1900, le=2100, description="Four-digit enrollment year"
    )

    @field_validator("matric_number")
    @classmethod
    def matric_number_strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("first_name", "last_name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        return v.strip()


class StudentUpdate(BaseModel):
    """All fields are optional to support partial updates."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, max_length=150)
    enrollment_year: Optional[int] = Field(None, ge=1900, le=2100)

    @field_validator("first_name", "last_name")
    @classmethod
    def name_strip(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class StudentResponse(_ORMBase):
    id: uuid.UUID
    matric_number: str
    first_name: str
    last_name: str
    email: str
    department: Optional[str]
    enrollment_year: Optional[int]
    created_at: datetime
    updated_at: datetime


class StudentListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[StudentResponse]


# ─────────────────────────────────────────────────────────────────────────────
# Course schemas
# ─────────────────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    course_code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        examples=["CS101"],
        description='Canonical course code, e.g. "CS101"',
    )
    title: str = Field(..., min_length=2, max_length=255)
    credit_units: int = Field(..., gt=0, description="Must be greater than zero")

    @field_validator("course_code")
    @classmethod
    def code_upper(cls, v: str) -> str:
        return v.strip().upper()


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    credit_units: Optional[int] = Field(None, gt=0)


class CourseResponse(_ORMBase):
    id: int
    course_code: str
    title: str
    credit_units: int


# ─────────────────────────────────────────────────────────────────────────────
# AcademicRecord schemas
# ─────────────────────────────────────────────────────────────────────────────

class RecordCreate(BaseModel):
    student_id: uuid.UUID
    course_id: int
    semester: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["First Semester 2024/2025"],
    )
    score: float = Field(..., ge=0.0, le=100.0)

    # grade and grade_point are computed server-side; not accepted from client


class RecordUpdate(BaseModel):
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    semester: Optional[str] = Field(None, min_length=3, max_length=50)


class RecordResponse(_ORMBase):
    id: int
    student_id: uuid.UUID
    course_id: int
    semester: str
    score: float
    grade: GradeEnum
    grade_point: float
    # Nested objects for convenience
    course: Optional[CourseResponse] = None


# ─────────────────────────────────────────────────────────────────────────────
# Transcript schemas
# ─────────────────────────────────────────────────────────────────────────────

class SemesterGPADetail(BaseModel):
    semester: str
    records: list[RecordResponse]
    credit_units_attempted: int
    credit_units_passed: int
    semester_gpa: float


class TranscriptResponse(BaseModel):
    student: StudentResponse
    semesters: list[SemesterGPADetail]
    total_credit_units_attempted: int
    total_credit_units_passed: int
    cgpa: float
