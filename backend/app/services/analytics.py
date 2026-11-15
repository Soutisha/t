from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.models import User, Mechanic, UserStatus
from app.models.advocacy import AdvocacyRecommendation, FitmentRecord, DealerSalesRecord, AdvocacyEventLedger
from app.models.toolbank import ToolProduct, ToolRequest, RewardLedgerEntry, RewardRedemption
from app.models.academy import AcademyEnrollment, AcademyQuizAttempt, AcademyCertificate
from app.models.trustvision import TrustVisionEvidence, TrustVisionFraudCase


def _range(column, start, end):
    clauses = []
    if start:
        clauses.append(column >= start)
    if end:
        clauses.append(column < end)
    return clauses


def _count(db, model, *filters):
    return int(db.scalar(select(func.count()).select_from(model).where(*filters)) or 0)


def dashboard(db: Session, start: datetime | None, end: datetime | None):
    active_users = _count(db, User, User.status == UserStatus.active)
    mechanic_count = _count(db, Mechanic)
    verified_mechanics = _count(db, Mechanic, Mechanic.verification_status == "verified")
    recommendations = _count(db, AdvocacyRecommendation, *_range(AdvocacyRecommendation.created_at, start, end),
                             AdvocacyRecommendation.status == "verified")
    fitments = _count(db, FitmentRecord, *_range(FitmentRecord.fitment_date, start, end),
                      FitmentRecord.verification_status == "verified")
    sales_filters = _range(DealerSalesRecord.sale_date, start, end) + [DealerSalesRecord.verification_status == "verified"]
    sales = db.scalar(select(func.coalesce(func.sum(DealerSalesRecord.quantity), 0)).where(*sales_filters)) or 0
    tool_requests = _count(db, ToolRequest, *_range(ToolRequest.created_at, start, end))
    completed_courses = _count(db, AcademyEnrollment, *_range(AcademyEnrollment.completed_at, start, end),
                               AcademyEnrollment.status == "completed")
    pending_fraud = _count(db, TrustVisionFraudCase, TrustVisionFraudCase.status == "pending_review")
    return {
        "active_users": active_users, "mechanics_registered": mechanic_count,
        "mechanics_verified": verified_mechanics, "verified_recommendations": recommendations,
        "verified_fitments": fitments, "verified_units_sold": int(sales),
        "tool_requests": tool_requests, "course_completions": completed_courses,
        "fraud_cases_pending_review": pending_fraud,
        "period": {"start": start.isoformat() if start else None, "end_exclusive": end.isoformat() if end else None},
        "definitions": {
            "active_users": "Users whose account status is active; this is not a monthly-active-user measure.",
            "verified_units_sold": "Sum of quantities on dealer sales records marked verified; not revenue.",
            "verified_recommendations": "Recommendation records with status verified.",
            "verified_fitments": "Fitment records with verification_status verified."
        }
    }


def advocacy_funnel(db: Session, start, end):
    recs = _count(db, AdvocacyRecommendation, *_range(AdvocacyRecommendation.created_at, start, end),
                  AdvocacyRecommendation.status == "verified")
    fits = _count(db, FitmentRecord, *_range(FitmentRecord.fitment_date, start, end),
                  FitmentRecord.verification_status == "verified")
    linked_fits = _count(db, FitmentRecord, *_range(FitmentRecord.fitment_date, start, end),
                         FitmentRecord.verification_status == "verified", FitmentRecord.recommendation_id.is_not(None))
    sales_filters = _range(DealerSalesRecord.sale_date, start, end) + [DealerSalesRecord.verification_status == "verified"]
    sales_count = _count(db, DealerSalesRecord, *sales_filters)
    linked_sales = _count(db, DealerSalesRecord, *sales_filters, DealerSalesRecord.recommendation_id.is_not(None))
    units = int(db.scalar(select(func.coalesce(func.sum(DealerSalesRecord.quantity), 0)).where(*sales_filters)) or 0)
    return {"verified_recommendations": recs, "verified_fitments": fits,
            "verified_fitments_linked_to_recommendation": linked_fits,
            "verified_sales_records": sales_count, "verified_sales_linked_to_recommendation": linked_sales,
            "verified_units_sold": units,
            "note": "Stages are independently counted records, not a strict cohort conversion funnel. Only explicit recommendation foreign keys are treated as linked; unlinked fitments/sales are not attributed."}


def operations(db: Session, start, end):
    req_filters = _range(ToolRequest.created_at, start, end)
    req_status = db.execute(select(ToolRequest.status, func.count()).where(*req_filters).group_by(ToolRequest.status)).all()
    reward_filters = _range(RewardLedgerEntry.created_at, start, end)
    reward_rows = db.execute(select(RewardLedgerEntry.entry_type, func.coalesce(func.sum(RewardLedgerEntry.points), 0))
                              .where(*reward_filters).group_by(RewardLedgerEntry.entry_type)).all()
    enroll_filters = _range(AcademyEnrollment.enrolled_at, start, end)
    enrollments = _count(db, AcademyEnrollment, *enroll_filters)
    completed = _count(db, AcademyEnrollment, *_range(AcademyEnrollment.completed_at, start, end),
                       AcademyEnrollment.status == "completed")
    certificates = _count(db, AcademyCertificate, *_range(AcademyCertificate.issued_at, start, end))
    attempts = db.execute(select(func.count(), func.coalesce(func.avg(AcademyQuizAttempt.score_percentage), 0),
                                  func.coalesce(func.sum(func.cast(AcademyQuizAttempt.passed, type_=__import__("sqlalchemy").Integer)), 0))
                           .where(*_range(AcademyQuizAttempt.attempted_at, start, end))).one()
    evidence = _count(db, TrustVisionEvidence, *_range(TrustVisionEvidence.created_at, start, end))
    cases = db.execute(select(TrustVisionFraudCase.status, func.count())
                       .where(*_range(TrustVisionFraudCase.created_at, start, end))
                       .group_by(TrustVisionFraudCase.status)).all()
    return {
        "tool_bank": {"active_products": _count(db, ToolProduct, ToolProduct.active.is_(True)),
                      "requests_by_status": {str(k): int(v) for k, v in req_status}},
        "rewards": {"points_by_entry_type": {str(k): int(v) for k, v in reward_rows},
                    "redemptions": _count(db, RewardRedemption, *_range(RewardRedemption.created_at, start, end))},
        "training": {"enrollments": enrollments, "completions": completed, "certificates_issued": certificates,
                     "quiz_attempts": int(attempts[0]), "average_quiz_score": round(float(attempts[1]), 2),
                     "passed_attempts": int(attempts[2])},
        "trustvision": {"evidence_submissions": evidence,
                        "fraud_cases_by_status": {str(k): int(v) for k, v in cases}}
    }


def roi_status():
    return {"status": "not_configured", "currency": None, "benefit": None, "cost": None, "roi_percentage": None,
            "reason": "No approved unit economics, programme costs, or verified monetary sales values are configured. Verified unit counts are not revenue and are not converted into ROI."}


def report_rows(db: Session, start, end):
    data = dashboard(db, start, end)
    ops = operations(db, start, end)
    return [
        ("metric", "value"),
        ("active_users", data["active_users"]),
        ("mechanics_registered", data["mechanics_registered"]),
        ("mechanics_verified", data["mechanics_verified"]),
        ("verified_recommendations", data["verified_recommendations"]),
        ("verified_fitments", data["verified_fitments"]),
        ("verified_units_sold", data["verified_units_sold"]),
        ("tool_requests", data["tool_requests"]),
        ("course_completions", data["course_completions"]),
        ("fraud_cases_pending_review", data["fraud_cases_pending_review"]),
        ("training_enrollments", ops["training"]["enrollments"]),
        ("certificates_issued", ops["training"]["certificates_issued"]),
        ("trustvision_evidence_submissions", ops["trustvision"]["evidence_submissions"]),
        ("roi_status", "not_configured"),
    ]
