"""Router Kas & Keuangan (Modul 9): mutasi kas, entri manual, rekap."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CashTransaction, User
from ..schemas import CashCreate
from ..services.cash import record_cash, current_balance

router = APIRouter(prefix="/api/cash", tags=["cash"])


def _current_user(db: Session) -> User | None:
    return db.query(User).order_by(User.id.asc()).first()


@router.get("")
def list_cash(
    start: date | None = Query(None),
    end: date | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(CashTransaction)
    if start:
        q = q.filter(CashTransaction.transaction_date >= start)
    if end:
        q = q.filter(CashTransaction.transaction_date <= end)
    rows = q.order_by(CashTransaction.id.desc()).all()
    return [
        {
            "id": t.id,
            "transaction_date": t.transaction_date,
            "direction": t.direction,
            "category": t.category,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "description": t.description,
        }
        for t in rows
    ]


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    rows = db.query(CashTransaction).all()
    today = date.today()
    total_in = sum(t.amount for t in rows if t.direction == "in")
    total_out = sum(t.amount for t in rows if t.direction == "out")
    today_in = sum(
        t.amount for t in rows if t.direction == "in" and t.transaction_date.date() == today
    )
    today_out = sum(
        t.amount for t in rows if t.direction == "out" and t.transaction_date.date() == today
    )
    return {
        "balance": current_balance(db),
        "total_in": total_in,
        "total_out": total_out,
        "today_in": today_in,
        "today_out": today_out,
    }


@router.post("", status_code=201)
def create_cash(payload: CashCreate, db: Session = Depends(get_db)):
    officer = _current_user(db)
    tx = record_cash(
        db,
        direction=payload.direction,
        amount=payload.amount,
        category=payload.category,
        description=payload.description or "",
        ref_type="manual",
        officer_id=officer.id if officer else None,
        tx_date=payload.transaction_date or datetime.utcnow(),
    )
    db.commit()
    db.refresh(tx)
    return {
        "id": tx.id,
        "direction": tx.direction,
        "amount": tx.amount,
        "balance_after": tx.balance_after,
    }
