"""Router Dashboard (Modul 1)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import reports

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    return reports.dashboard_summary(db)


@router.get("/chart")
def chart(months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db)):
    return reports.dashboard_chart(db, months)


@router.get("/activities")
def activities(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    return reports.dashboard_activities(db, limit)


@router.get("/reminders")
def reminders(days_ahead: int = Query(7, ge=1, le=60), db: Session = Depends(get_db)):
    return reports.dashboard_reminders(db, days_ahead)
