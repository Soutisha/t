import csv
from datetime import datetime, timezone
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.models import User
from app.services.analytics import dashboard, advocacy_funnel, operations, roi_status, report_rows

router = APIRouter()
ADMIN = ("administrator", "eurogrip_admin")


def parse_date(value: str | None, field: str):
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field} must be an ISO-8601 datetime.")


def date_range(start, end):
    a, b = parse_date(start, "start"), parse_date(end, "end")
    if a and b and a >= b:
        raise HTTPException(status_code=422, detail="start must be earlier than end.")
    if a and b and (b - a).days > 366:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 366 days.")
    return a, b


@router.get("/admin/analytics/executive")
def executive(start: str | None = None, end: str | None = None,
              user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    a, b = date_range(start, end)
    return {"data": dashboard(db, a, b), "roi": roi_status()}


@router.get("/admin/analytics/advocacy-funnel")
def funnel(start: str | None = None, end: str | None = None,
           user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    a, b = date_range(start, end)
    return {"data": advocacy_funnel(db, a, b)}


@router.get("/admin/analytics/operations")
def operational(start: str | None = None, end: str | None = None,
                user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    a, b = date_range(start, end)
    return {"data": operations(db, a, b), "roi": roi_status()}


@router.get("/admin/analytics/report.csv")
def export_csv(start: str | None = None, end: str | None = None,
               user: User = Depends(require_roles(*ADMIN)), db: Session = Depends(get_db)):
    a, b = date_range(start, end)
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerows(report_rows(db, a, b))
    stream.seek(0)
    filename = f"eurogrip-analytics-{datetime.now(timezone.utc).date().isoformat()}.csv"
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
