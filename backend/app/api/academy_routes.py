import json
import uuid
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.api.deps import current_user, require_roles
from app.db.session import get_db
from app.models.models import User
from app.models.academy import (
    AcademyCourse, AcademyLesson, AcademyQuestion, AcademyEnrollment,
    AcademyLessonCompletion, AcademyQuizAttempt, AcademyCertificate
)
from app.schemas.academy import CourseCreate, QuizSubmission
from app.services.academy import course_progress, public_course, certificate_payload

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")

@router.post("/admin/academy/courses", status_code=201)
def create_course(payload: CourseCreate, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    if db.scalar(select(AcademyCourse).where(AcademyCourse.course_code == payload.course_code)):
        raise HTTPException(status_code=409, detail="Course code already exists.")
    for question in payload.questions:
        if question.correct_option >= len(question.options):
            raise HTTPException(status_code=422, detail="A correct option index is outside its question's option list.")
    course = AcademyCourse(
        course_code=payload.course_code, title=payload.title, description=payload.description,
        category=payload.category, difficulty=payload.difficulty, language=payload.language,
        estimated_minutes=payload.estimated_minutes, pass_percentage=payload.pass_percentage,
        status="draft", created_by=user.id
    )
    db.add(course); db.flush()
    for lesson in payload.lessons:
        db.add(AcademyLesson(course_id=course.id, **lesson.model_dump()))
    for question in payload.questions:
        db.add(AcademyQuestion(course_id=course.id, prompt=question.prompt,
            options_json=json.dumps(question.options), correct_option=question.correct_option,
            explanation=question.explanation, sequence=question.sequence))
    db.commit()
    return {"data": {"course_id": course.id, "course_code": course.course_code,
        "status": course.status, "lesson_count": len(payload.lessons),
        "question_count": len(payload.questions)}}

@router.get("/admin/academy/courses")
def admin_courses(user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    rows = db.scalars(select(AcademyCourse).order_by(AcademyCourse.created_at.desc())).all()
    return {"data": [public_course(db, row, include_lessons=False) for row in rows]}

@router.patch("/admin/academy/courses/{course_id}/publish")
def publish_course(course_id: str, user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    course = db.get(AcademyCourse, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    lesson_count = db.scalar(select(func.count(AcademyLesson.id)).where(AcademyLesson.course_id == course.id)) or 0
    question_count = db.scalar(select(func.count(AcademyQuestion.id)).where(AcademyQuestion.course_id == course.id)) or 0
    if lesson_count < 1 or question_count < 1:
        raise HTTPException(status_code=409, detail="A course needs at least one lesson and one quiz question before publishing.")
    course.status = "published"
    course.published_at = datetime.now(timezone.utc)
    db.commit()
    return {"data": {"course_id": course.id, "status": course.status}}

@router.get("/academy/courses")
def list_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AcademyCourse).where(AcademyCourse.status == "published").order_by(AcademyCourse.title)).all()
    return {"data": [public_course(db, row) for row in rows]}

@router.get("/academy/courses/{course_id}")
def course_detail(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(AcademyCourse, course_id)
    if not course or course.status != "published":
        raise HTTPException(status_code=404, detail="Published course not found.")
    return {"data": public_course(db, course)}

@router.post("/academy/courses/{course_id}/enroll", status_code=201)
def enroll(course_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    course = db.get(AcademyCourse, course_id)
    if not course or course.status != "published":
        raise HTTPException(status_code=404, detail="Published course not found.")
    existing = db.scalar(select(AcademyEnrollment).where(
        AcademyEnrollment.course_id == course_id, AcademyEnrollment.user_id == user.id))
    if existing:
        return {"data": {"enrollment_id": existing.id, "status": existing.status,
            "progress_percentage": existing.progress_percentage, "already_enrolled": True}}
    enrollment = AcademyEnrollment(course_id=course_id, user_id=user.id)
    db.add(enrollment); db.commit()
    return {"data": {"enrollment_id": enrollment.id, "status": enrollment.status,
        "progress_percentage": enrollment.progress_percentage, "already_enrolled": False}}

@router.get("/academy/my-learning")
def my_learning(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AcademyEnrollment).where(
        AcademyEnrollment.user_id == user.id).order_by(AcademyEnrollment.enrolled_at.desc())).all()
    result = []
    for enrollment in rows:
        course = db.get(AcademyCourse, enrollment.course_id)
        if course:
            result.append({"enrollment_id": enrollment.id, "course": public_course(db, course, False),
                "status": enrollment.status, "progress_percentage": enrollment.progress_percentage})
    return {"data": result}

@router.post("/academy/enrollments/{enrollment_id}/lessons/{lesson_id}/complete")
def complete_lesson(enrollment_id: str, lesson_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    enrollment = db.get(AcademyEnrollment, enrollment_id)
    if not enrollment or enrollment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    lesson = db.get(AcademyLesson, lesson_id)
    if not lesson or lesson.course_id != enrollment.course_id:
        raise HTTPException(status_code=404, detail="Lesson not found in this course.")
    completion = db.scalar(select(AcademyLessonCompletion).where(
        AcademyLessonCompletion.enrollment_id == enrollment.id,
        AcademyLessonCompletion.lesson_id == lesson.id))
    if not completion:
        db.add(AcademyLessonCompletion(enrollment_id=enrollment.id, lesson_id=lesson.id))
        db.flush()
    enrollment.progress_percentage = course_progress(db, enrollment)
    db.commit()
    return {"data": {"enrollment_id": enrollment.id, "lesson_id": lesson.id,
        "progress_percentage": enrollment.progress_percentage}}

@router.post("/academy/enrollments/{enrollment_id}/quiz/submit")
def submit_quiz(enrollment_id: str, payload: QuizSubmission,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    enrollment = db.get(AcademyEnrollment, enrollment_id)
    if not enrollment or enrollment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Enrollment not found.")
    course = db.get(AcademyCourse, enrollment.course_id)
    required_ids = db.scalars(select(AcademyLesson.id).where(
        AcademyLesson.course_id == course.id, AcademyLesson.required.is_(True))).all()
    completed_ids = set(db.scalars(select(AcademyLessonCompletion.lesson_id).where(
        AcademyLessonCompletion.enrollment_id == enrollment.id)).all())
    if not set(required_ids).issubset(completed_ids):
        raise HTTPException(status_code=409, detail="Complete all required lessons before attempting the quiz.")
    questions = db.scalars(select(AcademyQuestion).where(
        AcademyQuestion.course_id == course.id).order_by(AcademyQuestion.sequence)).all()
    if not questions:
        raise HTTPException(status_code=409, detail="This course has no quiz configured.")
    question_ids = {q.id for q in questions}
    if set(payload.answers) != question_ids:
        raise HTTPException(status_code=422, detail="Submit exactly one answer for every quiz question.")
    for q in questions:
        options = json.loads(q.options_json)
        if payload.answers[q.id] < 0 or payload.answers[q.id] >= len(options):
            raise HTTPException(status_code=422, detail="An answer option index is invalid.")
    correct = sum(1 for q in questions if payload.answers[q.id] == q.correct_option)
    score = round(correct * 100 / len(questions), 2)
    passed = score >= course.pass_percentage
    attempt = AcademyQuizAttempt(enrollment_id=enrollment.id, score_percentage=score,
        passed=passed, answers_json=json.dumps(payload.answers, separators=(",", ":")))
    db.add(attempt)
    if passed:
        enrollment.status = "completed"
        enrollment.completed_at = datetime.now(timezone.utc)
        enrollment.progress_percentage = 100.0
        certificate = db.scalar(select(AcademyCertificate).where(AcademyCertificate.enrollment_id == enrollment.id))
        if not certificate:
            certificate = AcademyCertificate(
                enrollment_id=enrollment.id,
                certificate_code=f"EURO-{secrets.token_hex(6).upper()}",
                issued_to_user_id=user.id, course_title_snapshot=course.title,
                score_percentage=score
            )
            db.add(certificate)
    db.commit()
    certificate = db.scalar(select(AcademyCertificate).where(AcademyCertificate.enrollment_id == enrollment.id))
    return {"data": {"attempt_id": attempt.id, "score_percentage": score,
        "passed": passed, "pass_percentage": course.pass_percentage,
        "enrollment_status": enrollment.status,
        "certificate": certificate_payload(certificate) if certificate else None}}

@router.get("/academy/certificates/me")
def my_certificates(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AcademyCertificate).where(
        AcademyCertificate.issued_to_user_id == user.id).order_by(AcademyCertificate.issued_at.desc())).all()
    return {"data": [certificate_payload(x) for x in rows]}

@router.get("/academy/certificates/verify/{certificate_code}")
def verify_certificate(certificate_code: str, db: Session = Depends(get_db)):
    certificate = db.scalar(select(AcademyCertificate).where(
        AcademyCertificate.certificate_code == certificate_code))
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    return {"data": {"valid": True, "certificate_code": certificate.certificate_code,
        "course_title": certificate.course_title_snapshot, "score_percentage": certificate.score_percentage,
        "issued_at": certificate.issued_at}}
