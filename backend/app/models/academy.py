import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.core.security import utcnow

def _id(): return str(uuid.uuid4())

class AcademyCourse(Base):
    __tablename__ = "academy_courses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    course_code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(60), default="technical")
    difficulty: Mapped[str] = mapped_column(String(30), default="beginner")
    language: Mapped[str] = mapped_column(String(12), default="en")
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=30)
    pass_percentage: Mapped[float] = mapped_column(Float, default=70.0)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AcademyLesson(Base):
    __tablename__ = "academy_lessons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text, default="")
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=5)
    asset_type: Mapped[str] = mapped_column(String(30), default="article")
    asset_reference: Mapped[str] = mapped_column(String(500), default="")
    required: Mapped[bool] = mapped_column(Boolean, default=True)

class AcademyQuestion(Base):
    __tablename__ = "academy_questions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id", ondelete="CASCADE"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text)
    correct_option: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text, default="")
    sequence: Mapped[int] = mapped_column(Integer, default=1)

class AcademyEnrollment(Base):
    __tablename__ = "academy_enrollments"
    __table_args__ = (UniqueConstraint("course_id", "user_id", name="uq_academy_course_user"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    course_id: Mapped[str] = mapped_column(ForeignKey("academy_courses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AcademyLessonCompletion(Base):
    __tablename__ = "academy_lesson_completions"
    __table_args__ = (UniqueConstraint("enrollment_id", "lesson_id", name="uq_academy_enrollment_lesson"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("academy_enrollments.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("academy_lessons.id", ondelete="CASCADE"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AcademyQuizAttempt(Base):
    __tablename__ = "academy_quiz_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("academy_enrollments.id", ondelete="CASCADE"), index=True)
    score_percentage: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    answers_json: Mapped[str] = mapped_column(Text)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AcademyCertificate(Base):
    __tablename__ = "academy_certificates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("academy_enrollments.id", ondelete="CASCADE"), unique=True, index=True)
    certificate_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    issued_to_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    course_title_snapshot: Mapped[str] = mapped_column(String(200))
    score_percentage: Mapped[float] = mapped_column(Float)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
