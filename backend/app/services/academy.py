import json
import secrets
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.academy import (
    AcademyCourse, AcademyLesson, AcademyQuestion, AcademyEnrollment,
    AcademyLessonCompletion, AcademyQuizAttempt, AcademyCertificate
)

def course_progress(db: Session, enrollment: AcademyEnrollment) -> float:
    required_ids = db.scalars(select(AcademyLesson.id).where(
        AcademyLesson.course_id == enrollment.course_id,
        AcademyLesson.required.is_(True)
    )).all()
    if not required_ids:
        return 0.0
    completed = db.scalar(select(func.count(AcademyLessonCompletion.id)).where(
        AcademyLessonCompletion.enrollment_id == enrollment.id,
        AcademyLessonCompletion.lesson_id.in_(required_ids)
    )) or 0
    return round(100 * completed / len(required_ids), 2)

def public_course(db: Session, course: AcademyCourse, include_lessons: bool = True) -> dict:
    lessons = db.scalars(select(AcademyLesson).where(
        AcademyLesson.course_id == course.id
    ).order_by(AcademyLesson.sequence)).all() if include_lessons else []
    questions = db.scalars(select(AcademyQuestion).where(
        AcademyQuestion.course_id == course.id
    ).order_by(AcademyQuestion.sequence)).all() if include_lessons else []
    return {
        "course_id": course.id, "course_code": course.course_code,
        "title": course.title, "description": course.description,
        "category": course.category, "difficulty": course.difficulty,
        "language": course.language, "estimated_minutes": course.estimated_minutes,
        "pass_percentage": course.pass_percentage, "status": course.status,
        "lessons": [{
            "lesson_id": x.id, "title": x.title, "content": x.content,
            "sequence": x.sequence, "estimated_minutes": x.estimated_minutes,
            "asset_type": x.asset_type, "asset_reference": x.asset_reference,
            "required": x.required
        } for x in lessons],
        "quiz_questions": [{
            "question_id": q.id, "prompt": q.prompt,
            "options": json.loads(q.options_json), "sequence": q.sequence
        } for q in questions]
    }

def certificate_payload(certificate: AcademyCertificate) -> dict:
    return {"certificate_id": certificate.id, "certificate_code": certificate.certificate_code,
        "course_title": certificate.course_title_snapshot,
        "score_percentage": certificate.score_percentage,
        "issued_at": certificate.issued_at}
