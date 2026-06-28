"""Router Pengingat Jatuh Tempo: query tagihan, log pengiriman WhatsApp."""

from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import InstallmentSchedule, Loan, Member, Setting, ReminderLog
from ..services.security import current_user_id_ctx

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


def _coop_name(db: Session) -> str:
    s = db.query(Setting).filter(Setting.key == "coop_name").first()
    return s.value if s else "Koperasi"


def _fmt_phone(phone: str | None) -> str | None:
    """Konversi 08xxx → 628xxx untuk format wa.me."""
    if not phone:
        return None
    p = phone.strip().replace(" ", "").replace("-", "")
    if p.startswith("0"):
        p = "62" + p[1:]
    elif p.startswith("+"):
        p = p[1:]
    return p


def _build_message(coop_name: str, member_name: str, loan_number: str,
                   due_date: date, amount: int) -> str:
    months_id = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    if isinstance(due_date, str):
        due_date = date.fromisoformat(due_date)
    due_str = f"{due_date.day} {months_id[due_date.month]} {due_date.year}"
    amount_str = f"{amount:,}".replace(",", ".")
    return (
        f"PENGINGAT JATUH TEMPO ANGSURAN\n\n"
        f"Koperasi: {coop_name}\n\n"
        f"Halo {member_name},\n"
        f"Kami ingin mengingatkan bahwa angsuran pinjaman Anda akan/telah jatuh tempo.\n\n"
        f"No. Pinjaman             : {loan_number}\n"
        f"Tanggal Jatuh Tempo      : {due_str}\n"
        f"Jumlah Tagihan Bulan Ini : Rp {amount_str}\n\n"
        f"Mohon segera melakukan pembayaran sebelum tanggal jatuh tempo. "
        f"Jika Anda sudah melakukan pembayaran, abaikan pesan ini.\n\n"
        f"Terima kasih."
    )


@router.get("/due")
def get_due_installments(
    days_ahead: int = Query(30, ge=0, le=365),
    include_overdue: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Daftar angsuran yang akan/sudah jatuh tempo beserta info anggota."""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    coop_name = _coop_name(db)

    query = (
        db.query(InstallmentSchedule, Loan, Member)
        .join(Loan, InstallmentSchedule.loan_id == Loan.id)
        .join(Member, Loan.member_id == Member.id)
        .filter(InstallmentSchedule.status.in_(["unpaid", "partial"]))
        .filter(Member.is_deleted == 0)
    )

    if include_overdue:
        query = query.filter(InstallmentSchedule.due_date <= cutoff)
    else:
        query = query.filter(
            InstallmentSchedule.due_date >= today,
            InstallmentSchedule.due_date <= cutoff,
        )

    rows = query.order_by(InstallmentSchedule.due_date.asc()).all()

    # last sent_at per schedule_id
    sent_map: dict[int, str] = {}
    if rows:
        sids = [s.id for s, _, _ in rows]
        placeholders = ",".join(str(x) for x in sids)
        result = db.execute(
            text(f"SELECT schedule_id, MAX(sent_at) FROM reminder_logs WHERE schedule_id IN ({placeholders}) GROUP BY schedule_id")
        )
        for sid, sat in result:
            sent_map[sid] = sat

    items = []
    for sched, loan, member in rows:
        remaining = (sched.total_due or 0) - (sched.paid_amount or 0)
        wa_phone  = _fmt_phone(member.phone)
        message   = _build_message(coop_name, member.full_name, loan.loan_number,
                                   sched.due_date, remaining)
        is_overdue = sched.due_date < today

        items.append({
            "schedule_id":    sched.id,
            "loan_id":        loan.id,
            "member_id":      member.id,
            "loan_number":    loan.loan_number,
            "member_name":    member.full_name,
            "phone":          member.phone or "",
            "wa_phone":       wa_phone,
            "installment_no": sched.installment_no,
            "due_date":       sched.due_date.isoformat(),
            "total_due":      sched.total_due,
            "paid_amount":    sched.paid_amount or 0,
            "remaining":      remaining,
            "status":         sched.status,
            "is_overdue":     is_overdue,
            "has_phone":      bool(wa_phone),
            "wa_message":     message,
            "last_sent_at":   sent_map.get(sched.id),
        })

    return {"coop_name": coop_name, "today": today.isoformat(), "items": items}


@router.post("/log")
def log_reminder(
    schedule_id: int,
    member_id: int,
    loan_id: int,
    phone: str | None = None,
    db: Session = Depends(get_db),
):
    """Catat bahwa pengingat WhatsApp sudah dikirim."""
    uid = current_user_id_ctx.get(None)
    log_entry = ReminderLog(
        schedule_id=schedule_id,
        member_id=member_id,
        loan_id=loan_id,
        channel="whatsapp",
        phone=phone,
        sent_by=uid
    )
    try:
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"DB Error: {str(e)}")

    return {"ok": True, "sent_at": datetime.utcnow().isoformat()}
