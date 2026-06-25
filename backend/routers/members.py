"""Router Data Anggota (Modul 2): CRUD, upload KTP, riwayat, soft-delete."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Member, Loan, Payment, Collateral, ActivityLog, Saving, User
from ..schemas import MemberCreate, MemberUpdate, MemberOut, MemberListResponse
from ..services.numbering import next_number
from ..services.security import current_user_id_ctx

router = APIRouter(prefix="/api/members", tags=["members"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KTP_DIR = PROJECT_ROOT / "uploads" / "ktp"

ACTIVE_LOAN_STATUSES = {"draft", "pending", "approved", "active"}


def _active_loans_count(member_id: int, db: Session) -> int:
    return (
        db.query(Loan)
        .filter(Loan.member_id == member_id, Loan.status.in_(ACTIVE_LOAN_STATUSES))
        .count()
    )


def _has_any_data(member_id: int, db: Session) -> bool:
    """True jika anggota pernah memiliki pinjaman, jaminan, pembayaran, atau simpanan."""
    if db.query(Loan).filter(Loan.member_id == member_id).first():
        return True
    if db.query(Collateral).filter(Collateral.member_id == member_id).first():
        return True
    if db.query(Payment).filter(Payment.member_id == member_id).first():
        return True
    if db.query(Saving).filter(Saving.member_id == member_id).first():
        return True
    return False


def _to_out(m: Member, db: Session) -> dict:
    d = {c.name: getattr(m, c.name) for c in Member.__table__.columns}
    d["active_loans_count"] = _active_loans_count(m.id, db)
    d["total_loans_count"]  = db.query(Loan).filter(Loan.member_id == m.id).count()
    d["has_any_data"]       = _has_any_data(m.id, db)
    return d


# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=MemberListResponse)
def list_members(
    search: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Member).filter(Member.is_deleted == 0)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Member.full_name.ilike(like), Member.member_number.ilike(like), Member.nik.ilike(like))
        )
    if status:
        query = query.filter(Member.status == status)

    total = query.count()
    items = query.order_by(Member.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_to_out(m, db) for m in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=MemberOut, status_code=201)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)):
    if payload.nik:
        exists = db.query(Member).filter(Member.nik == payload.nik, Member.is_deleted == 0).first()
        if exists:
            raise HTTPException(400, detail="NIK sudah terdaftar")
    member = Member(member_number=next_number(db, "member"), **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return _to_out(member, db)


@router.get("/{member_id}", response_model=MemberOut)
def get_member(member_id: int, db: Session = Depends(get_db)):
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    return _to_out(m, db)


@router.put("/{member_id}", response_model=MemberOut)
def update_member(member_id: int, payload: MemberUpdate, db: Session = Depends(get_db)):
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")

    new_status = payload.model_dump(exclude_unset=True).get("status")
    if new_status and new_status != "aktif":
        if _active_loans_count(m.id, db) > 0:
            raise HTTPException(
                400,
                detail="Anggota tidak dapat dinonaktifkan karena masih memiliki pinjaman atau pengajuan yang aktif.",
            )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.post("/{member_id}/set-status")
def set_member_status(
    member_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
):
    """Ubah status anggota dengan validasi bisnis."""
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")

    allowed = {"aktif", "nonaktif", "diblokir", "diarsipkan"}
    if status not in allowed:
        raise HTTPException(400, detail=f"Status tidak valid. Pilihan: {', '.join(allowed)}")

    if status != "aktif" and _active_loans_count(m.id, db) > 0:
        raise HTTPException(
            400,
            detail="Anggota tidak dapat dinonaktifkan karena masih memiliki pinjaman atau pengajuan yang aktif.",
        )

    m.status = status
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db)):
    """Soft-delete. Hanya boleh jika tidak pernah memiliki data apapun."""
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")

    if _has_any_data(m.id, db):
        raise HTTPException(
            400,
            detail="Anggota memiliki riwayat data koperasi dan tidak dapat dihapus. Gunakan Arsipkan.",
        )
    if _active_loans_count(m.id, db) > 0:
        raise HTTPException(400, detail="Anggota masih memiliki pinjaman aktif.")

    uid = current_user_id_ctx.get(None)
    actor = db.get(User, uid) if uid else None
    m.is_deleted = 1
    m.deleted_at = datetime.utcnow()
    m.deleted_by = actor.full_name if actor else "Admin"
    db.commit()


@router.post("/{member_id}/archive")
def archive_member(member_id: int, db: Session = Depends(get_db)):
    """Arsipkan anggota yang memiliki riwayat data (tidak bisa dihapus keras)."""
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    if _active_loans_count(m.id, db) > 0:
        raise HTTPException(
            400,
            detail="Anggota tidak dapat diarsipkan karena masih memiliki pinjaman aktif.",
        )
    m.status = "diarsipkan"
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.post("/{member_id}/ktp", response_model=MemberOut)
async def upload_ktp(member_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    m = db.get(Member, member_id)
    if not m or m.is_deleted:
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    KTP_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix or ".jpg"
    dest = KTP_DIR / f"member_{member_id}{ext}"
    dest.write_bytes(await file.read())
    m.ktp_photo_path = f"uploads/ktp/{dest.name}"
    db.commit()
    db.refresh(m)
    return _to_out(m, db)


@router.get("/{member_id}/loans")
def member_loans(member_id: int, db: Session = Depends(get_db)):
    if not db.get(Member, member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    loans = db.query(Loan).filter(Loan.member_id == member_id).order_by(Loan.id.desc()).all()
    return [
        {
            "id": l.id,
            "loan_number": l.loan_number,
            "principal_amount": l.principal_amount,
            "total_payable": l.total_payable,
            "interest_rate": l.interest_rate,
            "interest_type": l.interest_type,
            "tenor": l.tenor,
            "status": l.status,
            "disbursement_date": l.disbursement_date.isoformat() if l.disbursement_date else None,
            "created_at": l.created_at.isoformat(),
        }
        for l in loans
    ]


@router.get("/{member_id}/payments")
def member_payments(member_id: int, db: Session = Depends(get_db)):
    if not db.get(Member, member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    payments = db.query(Payment).filter(Payment.member_id == member_id).order_by(Payment.id.desc()).all()
    return [
        {
            "id": p.id,
            "payment_number": p.payment_number,
            "amount_paid": p.amount_paid,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "note": p.note,
        }
        for p in payments
    ]


@router.get("/{member_id}/collaterals")
def member_collaterals(member_id: int, db: Session = Depends(get_db)):
    if not db.get(Member, member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    cols = db.query(Collateral).filter(Collateral.member_id == member_id).order_by(Collateral.id.desc()).all()
    return [
        {
            "id": c.id,
            "type": c.type,
            "doc_number": c.doc_number,
            "owner_name": c.owner_name,
            "estimated_value": c.estimated_value,
            "status": c.status,
            "collateral_status": c.collateral_status,
            "loan_id": c.loan_id,
        }
        for c in cols
    ]


@router.get("/{member_id}/audit")
def member_audit(member_id: int, db: Session = Depends(get_db)):
    if not db.get(Member, member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    loan_ids = [l.id for l in db.query(Loan).filter(Loan.member_id == member_id).all()]
    if not loan_ids:
        return []
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.entity_type == "loan", ActivityLog.entity_id.in_(loan_ids))
        .order_by(ActivityLog.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        {
            "id": lg.id,
            "action": lg.action,
            "description": lg.description,
            "actor": (db.get(User, lg.user_id).full_name if lg.user_id else "Sistem"),
            "created_at": lg.created_at.isoformat(),
        }
        for lg in logs
    ]
