"""Router Pinjaman: pengajuan (3), persetujuan (5), pencairan & data (6)."""

import json
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..calculations import compute_fees, build_schedule
from ..models import (
    Loan,
    Member,
    User,
    LoanApproval,
    LoanDocument,
    InstallmentSchedule,
    Collateral,
    ActivityLog,
    Setting,
)
from ..schemas import (
    LoanCreate,
    LoanUpdate,
    LoanOut,
    LoanListResponse,
    DecisionRequest,
    DisburseRequest,
)
from ..services.numbering import next_number
from ..services.schedule import generate_schedule
from ..services.cash import record_cash
from ..services.activity import log_activity
from ..services.security import current_user_id_ctx

router = APIRouter(prefix="/api/loans", tags=["loans"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_DIR = PROJECT_ROOT / "uploads" / "loan_docs"


def _current_user_id(db: Session) -> int | None:
    return _actor(db)


def _apply_calculations(loan: Loan) -> None:
    """Isi field biaya & total dari parameter pinjaman."""
    fees = compute_fees(
        loan.principal_amount, loan.admin_pct, loan.provisi_pct, loan.form_fee
    )
    _schedule, _interest, total_payable = build_schedule(
        loan.principal_amount, loan.interest_rate, loan.tenor, loan.interest_type
    )
    loan.admin_fee = fees["admin_fee"]
    loan.provisi_fee = fees["provisi_fee"]
    loan.total_fees = fees["total_fees"]
    loan.net_received = fees["net_received"]
    loan.total_payable = total_payable


def _actor(db: Session) -> int | None:
    uid = current_user_id_ctx.get(None)
    if uid:
        return uid
    user = db.query(User).order_by(User.id.asc()).first()
    return user.id if user else None


def _to_out(loan: Loan) -> dict:
    data = {c.name: getattr(loan, c.name) for c in Loan.__table__.columns}
    data["member_name"] = loan.member.full_name if loan.member else None
    col = loan.collaterals[0] if loan.collaterals else None
    if col:
        data["collateral"] = {
            "id": col.id,
            "type": col.type,
            "doc_number": col.doc_number,
            "owner_name": col.owner_name,
            "status": col.status,
            "collateral_status": col.collateral_status,
            "doc_status": col.doc_status,
            "storage_location": col.storage_location,
            "estimated_value": col.estimated_value,
            "notes": col.notes,
            "file_paths": json.loads(col.file_paths or "[]"),
            "return_date": col.return_date.isoformat() if col.return_date else None,
            "return_recipient": col.return_recipient,
            "return_notes": col.return_notes,
            "return_proof_path": col.return_proof_path,
        }
    else:
        data["collateral"] = None
    return data


# --------------------------------------------------------------------------
@router.get("", response_model=LoanListResponse)
def list_loans(
    search: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Loan).join(Member, Loan.member_id == Member.id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Loan.loan_number.ilike(like)) | (Member.full_name.ilike(like))
        )
    if status:
        query = query.filter(Loan.status == status)

    total = query.count()
    items = (
        query.order_by(Loan.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [_to_out(l) for l in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=LoanOut, status_code=201)
def create_loan(payload: LoanCreate, db: Session = Depends(get_db)):
    member = db.get(Member, payload.member_id)
    if not member:
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    if member.status != "aktif":
        raise HTTPException(400, detail="Pengajuan pinjaman hanya dapat dilakukan untuk anggota dengan status aktif")

    max_no_col_setting = db.get(Setting, "max_loan_without_collateral")
    max_no_col = int(max_no_col_setting.value) if max_no_col_setting else 5000000
    
    requires_col = payload.requires_collateral
    if payload.principal_amount > max_no_col:
        requires_col = True

    uid = _actor(db)
    loan_data = payload.model_dump()
    loan_data["requires_collateral"] = 1 if requires_col else 0

    loan = Loan(
        loan_number=next_number(db, "loan"),
        status="draft",
        created_by=uid,
        **loan_data,
    )
    _apply_calculations(loan)
    db.add(loan)
    db.flush()
    log_activity(db, user_id=uid, action="loan_created", entity_type="loan",
                 entity_id=loan.id, description=f"Pengajuan pinjaman dibuat (draft) oleh petugas")
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.get("/{loan_id}", response_model=LoanOut)
def get_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    return _to_out(loan)


@router.put("/{loan_id}", response_model=LoanOut)
def update_loan(loan_id: int, payload: LoanUpdate, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status != "draft":
        raise HTTPException(400, detail="Hanya pengajuan berstatus draft yang bisa diubah")

    max_no_col_setting = db.get(Setting, "max_loan_without_collateral")
    max_no_col = int(max_no_col_setting.value) if max_no_col_setting else 5000000

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, field, value)
        
    if loan.principal_amount > max_no_col:
        loan.requires_collateral = 1
    elif "requires_collateral" in payload.model_dump(exclude_unset=True):
        loan.requires_collateral = 1 if payload.requires_collateral else 0
    _apply_calculations(loan)
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.post("/{loan_id}/submit", response_model=LoanOut)
def submit_loan(loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status != "draft":
        raise HTTPException(400, detail="Hanya draft yang bisa diajukan")
    if loan.requires_collateral and len(loan.collaterals) == 0:
        raise HTTPException(400, detail="Jaminan wajib untuk nominal pinjaman ini.")
    loan.status = "pending"
    log_activity(db, user_id=_actor(db), action="loan_submitted", entity_type="loan",
                 entity_id=loan.id, description="Pengajuan diajukan ke komite untuk persetujuan")
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.post("/{loan_id}/approve", response_model=LoanOut)
def approve_loan(loan_id: int, payload: DecisionRequest, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status != "pending":
        raise HTTPException(400, detail="Hanya pengajuan menunggu yang bisa disetujui")

    uid = _actor(db)
    loan.status = "approved"
    db.add(LoanApproval(loan_id=loan.id, approver_id=uid, decision="approve", note=payload.note))
    note_text = f" — Catatan: {payload.note}" if payload.note else ""
    log_activity(db, user_id=uid, action="loan_approved", entity_type="loan",
                 entity_id=loan.id, description=f"Pinjaman disetujui{note_text}")
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.post("/{loan_id}/reject", response_model=LoanOut)
def reject_loan(loan_id: int, payload: DecisionRequest, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status != "pending":
        raise HTTPException(400, detail="Hanya pengajuan menunggu yang bisa ditolak")

    uid = _actor(db)
    loan.status = "rejected"
    db.add(LoanApproval(loan_id=loan.id, approver_id=uid, decision="reject", note=payload.note))
    reason = f" — Alasan: {payload.note}" if payload.note else ""
    log_activity(db, user_id=uid, action="loan_rejected", entity_type="loan",
                 entity_id=loan.id, description=f"Pinjaman ditolak{reason}")
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.post("/{loan_id}/disburse", response_model=LoanOut)
def disburse_loan(loan_id: int, payload: DisburseRequest, db: Session = Depends(get_db)):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    if loan.status != "approved":
        raise HTTPException(400, detail="Hanya pinjaman disetujui yang bisa dicairkan")

    uid = _actor(db)
    loan.disbursement_date = payload.disbursement_date or date.today()
    loan.status = "active"

    generate_schedule(db, loan)
    record_cash(
        db,
        direction="out",
        amount=loan.net_received,
        category="pencairan",
        description=f"Pencairan {loan.loan_number}",
        ref_type="loan",
        ref_id=loan.id,
        officer_id=uid,
        tx_date=loan.disbursement_date,
    )
    log_activity(db, user_id=uid, action="loan_disbursed", entity_type="loan",
                 entity_id=loan.id,
                 description=f"Dana dicairkan pada {loan.disbursement_date}, bersih diterima Rp {loan.net_received:,}")
    db.commit()
    db.refresh(loan)
    return _to_out(loan)


@router.get("/{loan_id}/schedule")
def loan_schedule(loan_id: int, db: Session = Depends(get_db)):
    if not db.get(Loan, loan_id):
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    rows = (
        db.query(InstallmentSchedule)
        .filter(InstallmentSchedule.loan_id == loan_id)
        .order_by(InstallmentSchedule.installment_no.asc())
        .all()
    )
    return [
        {
            "installment_no": r.installment_no,
            "due_date": r.due_date,
            "principal_due": r.principal_due,
            "interest_due": r.interest_due,
            "total_due": r.total_due,
            "paid_amount": r.paid_amount,
            "status": r.status,
        }
        for r in rows
    ]


from ..services.storage import upload_file

@router.post("/{loan_id}/documents")
async def upload_document(
    loan_id: int,
    doc_type: str = "lampiran",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    loan = db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")

    file_url = upload_file(file, "loan_docs")

    doc = LoanDocument(
        loan_id=loan_id,
        doc_type=doc_type,
        file_path=file_url,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "file_path": doc.file_path, "doc_type": doc.doc_type}


@router.get("/{loan_id}/audit")
def loan_audit(loan_id: int, db: Session = Depends(get_db)):
    if not db.get(Loan, loan_id):
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.entity_type == "loan", ActivityLog.entity_id == loan_id)
        .order_by(ActivityLog.created_at.asc())
        .all()
    )
    result = []
    for lg in logs:
        actor = db.get(User, lg.user_id) if lg.user_id else None
        result.append({
            "id": lg.id,
            "action": lg.action,
            "description": lg.description,
            "actor": actor.full_name if actor else "Sistem",
            "created_at": lg.created_at.isoformat(),
        })
    return result
