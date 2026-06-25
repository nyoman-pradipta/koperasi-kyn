"""Router Simpanan (Modul 8): pokok / wajib / sukarela."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Saving, Member, User
from ..schemas import SavingCreate
from ..services.cash import record_cash

router = APIRouter(prefix="/api/savings", tags=["savings"])

TYPES = ("pokok", "wajib", "sukarela")


def _current_user(db: Session) -> User | None:
    return db.query(User).order_by(User.id.asc()).first()


def _type_balance(db: Session, member_id: int, savings_type: str) -> int:
    last = (
        db.query(Saving)
        .filter(Saving.member_id == member_id, Saving.savings_type == savings_type)
        .order_by(Saving.id.desc())
        .first()
    )
    return last.balance_after if last else 0


@router.get("/balance")
def balance(member_id: int = Query(...), db: Session = Depends(get_db)):
    if not db.get(Member, member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    balances = {t: _type_balance(db, member_id, t) for t in TYPES}
    balances["total"] = sum(balances.values())
    return balances


@router.get("")
def list_savings(
    member_id: int | None = Query(None),
    savings_type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Saving)
    if member_id:
        q = q.filter(Saving.member_id == member_id)
    if savings_type:
        q = q.filter(Saving.savings_type == savings_type)
    rows = q.order_by(Saving.id.desc()).all()
    return [
        {
            "id": s.id,
            "member_id": s.member_id,
            "savings_type": s.savings_type,
            "transaction_type": s.transaction_type,
            "amount": s.amount,
            "balance_after": s.balance_after,
            "transaction_date": s.transaction_date,
            "note": s.note,
        }
        for s in rows
    ]


@router.post("", status_code=201)
def create_saving(payload: SavingCreate, db: Session = Depends(get_db)):
    if payload.savings_type not in TYPES:
        raise HTTPException(400, detail="Jenis simpanan tidak valid")
    if payload.transaction_type not in ("setor", "tarik"):
        raise HTTPException(400, detail="Jenis transaksi tidak valid")
    if not db.get(Member, payload.member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")

    current = _type_balance(db, payload.member_id, payload.savings_type)
    if payload.transaction_type == "setor":
        new_balance = current + payload.amount
    else:
        if payload.amount > current:
            raise HTTPException(400, detail="Saldo simpanan tidak mencukupi")
        new_balance = current - payload.amount

    tx_date = payload.transaction_date or datetime.utcnow()
    officer = _current_user(db)

    saving = Saving(
        member_id=payload.member_id,
        savings_type=payload.savings_type,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        balance_after=new_balance,
        transaction_date=tx_date,
        note=payload.note,
        officer_id=officer.id if officer else None,
    )
    db.add(saving)

    # Setor → kas masuk; Tarik → kas keluar
    record_cash(
        db,
        direction="in" if payload.transaction_type == "setor" else "out",
        amount=payload.amount,
        category=f"simpanan_{payload.savings_type}",
        description=f"Simpanan {payload.savings_type} ({payload.transaction_type})",
        ref_type="savings",
        officer_id=officer.id if officer else None,
        tx_date=tx_date,
    )

    db.commit()
    db.refresh(saving)
    return {
        "id": saving.id,
        "savings_type": saving.savings_type,
        "transaction_type": saving.transaction_type,
        "amount": saving.amount,
        "balance_after": saving.balance_after,
    }
