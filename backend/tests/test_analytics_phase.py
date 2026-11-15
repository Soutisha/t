from datetime import datetime, timezone
from app.services.analytics import roi_status, dashboard, advocacy_funnel, operations
from app.db.base import Base
from app.db.session import engine, SessionLocal


def test_analytics_empty_database_is_zero_and_roi_unconfigured():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        result = dashboard(db, start, end)
        assert result["mechanics_registered"] == 0
        assert result["verified_units_sold"] == 0
        assert advocacy_funnel(db, start, end)["verified_sales_records"] == 0
        assert operations(db, start, end)["training"]["enrollments"] == 0
        assert roi_status()["status"] == "not_configured"
    finally:
        db.close()
