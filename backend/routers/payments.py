"""Router Pembayaran Angsuran (Modul 7): bayar, alokasi, kwitansi."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Loan, Member, User, Payment, InstallmentSchedule, Setting
from ..schemas import PaymentCreate
from ..services.numbering import next_number
from ..services.cash import record_cash
from ..services.security import current_officer

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _current_user(db: Session) -> User | None:
    return current_officer(db)


def _late_fee_per_day(db: Session) -> int:
    s = db.get(Setting, "late_fee_per_day")
    try:
        return int(s.value) if s else 20000
    except (TypeError, ValueError):
        return 20000


def _unpaid_installments(db: Session, loan_id: int) -> list[InstallmentSchedule]:
    return (
        db.query(InstallmentSchedule)
        .filter(
            InstallmentSchedule.loan_id == loan_id,
            InstallmentSchedule.status != "paid",
        )
        .order_by(InstallmentSchedule.installment_no.asc())
        .all()
    )


def _outstanding_total(db: Session, loan_id: int) -> int:
    rows = (
        db.query(InstallmentSchedule)
        .filter(InstallmentSchedule.loan_id == loan_id)
        .all()
    )
    return sum(r.total_due - r.paid_amount for r in rows)


@router.get("/outstanding/{loan_id}")
def outstanding(loan_id: int, db: Session = Depends(get_db)):
    """Info tagihan untuk membantu input pembayaran (& saran denda)."""
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")

    unpaid = _unpaid_installments(db, loan_id)
    total_outstanding = _outstanding_total(db, loan_id)
    if not unpaid:
        return {
            "loan_number": loan.loan_number,
            "fully_paid": True,
            "outstanding_total": 0,
        }

    nxt = unpaid[0]
    overdue_days = max(0, (date.today() - nxt.due_date).days)
    fee_per_day = _late_fee_per_day(db)
    return {
        "loan_number": loan.loan_number,
        "fully_paid": False,
        "next_installment_no": nxt.installment_no,
        "next_due_date": nxt.due_date,
        "next_total_due": nxt.total_due,
        "next_remaining": nxt.total_due - nxt.paid_amount,
        "outstanding_total": total_outstanding,
        "overdue_days": overdue_days,
        "late_fee_per_day": fee_per_day,
        "suggested_penalty": overdue_days * fee_per_day,
    }


@router.post("", status_code=201)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    loan = db.get(Loan, payload.loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status not in ("active",):
        raise HTTPException(400, detail="Hanya pinjaman aktif yang bisa menerima pembayaran")

    unpaid = _unpaid_installments(db, loan.id)
    if not unpaid:
        raise HTTPException(400, detail="Pinjaman sudah lunas")

    pay_date = payload.payment_date or date.today()
    remaining_amount = payload.amount
    principal_component = 0
    interest_component = 0

    # Alokasikan pembayaran ke angsuran tertua dulu; dalam tiap angsuran,
    # bunga dilunasi lebih dulu lalu pokok.
    for inst in unpaid:
        if remaining_amount <= 0:
            break
        due_remaining = inst.total_due - inst.paid_amount
        pay = min(remaining_amount, due_remaining)

        old_paid = inst.paid_amount
        new_paid = old_paid + pay
        old_int = min(old_paid, inst.interest_due)
        new_int = min(new_paid, inst.interest_due)
        interest_component += new_int - old_int
        principal_component += (new_paid - new_int) - (old_paid - old_int)

        inst.paid_amount = new_paid
        if new_paid >= inst.total_due:
            inst.status = "paid"
            inst.paid_date = pay_date
        else:
            inst.status = "partial"
        remaining_amount -= pay

    if remaining_amount > 0:
        raise HTTPException(
            400,
            detail=f"Nominal melebihi sisa tagihan (kelebihan Rp {remaining_amount:,})",
        )

    remaining_balance = _outstanding_total(db, loan.id)
    if remaining_balance <= 0:
        loan.status = "paid_off"

    officer = _current_user(db)
    payment = Payment(
        payment_number=next_number(db, "payment"),
        loan_id=loan.id,
        member_id=loan.member_id,
        schedule_id=unpaid[0].id,
        payment_date=pay_date,
        amount_paid=payload.amount,
        principal_component=principal_component,
        interest_component=interest_component,
        penalty_component=payload.penalty,
        payment_method=payload.payment_method,
        remaining_balance=remaining_balance,
        officer_id=officer.id if officer else None,
        note=payload.note,
    )
    db.add(payment)

    # Kas masuk = angsuran + denda
    record_cash(
        db,
        direction="in",
        amount=payload.amount + payload.penalty,
        category="angsuran",
        description=f"Angsuran {loan.loan_number}",
        ref_type="payment",
        ref_id=None,
        officer_id=officer.id if officer else None,
        tx_date=pay_date,
    )

    db.commit()
    db.refresh(payment)
    return _receipt(db, payment)


@router.get("")
def list_payments(
    loan_id: int | None = Query(None),
    member_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Payment)
    if loan_id:
        q = q.filter(Payment.loan_id == loan_id)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    rows = q.order_by(Payment.id.desc()).all()
    return [
        {
            "id": p.id,
            "payment_number": p.payment_number,
            "loan_id": p.loan_id,
            "member_id": p.member_id,
            "payment_date": p.payment_date,
            "amount_paid": p.amount_paid,
            "penalty_component": p.penalty_component,
            "remaining_balance": p.remaining_balance,
        }
        for p in rows
    ]


def _receipt(db: Session, payment: Payment) -> dict:
    member = db.get(Member, payment.member_id)
    loan = db.get(Loan, payment.loan_id)
    officer = db.get(User, payment.officer_id) if payment.officer_id else None
    coop = db.get(Setting, "coop_name")
    return {
        "payment_number": payment.payment_number,
        "coop_name": coop.value if coop else "Koperasi",
        "member_name": member.full_name if member else "-",
        "member_number": member.member_number if member else "-",
        "member_phone": member.phone if member else None,
        "loan_number": loan.loan_number if loan else "-",
        "payment_date": payment.payment_date,
        "amount_paid": payment.amount_paid,
        "principal_component": payment.principal_component,
        "interest_component": payment.interest_component,
        "penalty_component": payment.penalty_component,
        "total_received": payment.amount_paid + payment.penalty_component,
        "payment_method": payment.payment_method,
        "remaining_balance": payment.remaining_balance,
        "officer_name": officer.full_name if officer else "-",
    }


@router.get("/{payment_id}/receipt")
def receipt(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(404, detail="Pembayaran tidak ditemukan")
    return _receipt(db, payment)
