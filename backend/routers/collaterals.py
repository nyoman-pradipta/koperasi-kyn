"""Router Jaminan: CRUD collateral, upload dokumen, attach ke pinjaman, pengembalian."""

import json
import mimetypes
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Collateral, CollateralDocument, CollateralReturnHistory, CollateralUsageHistory, Loan, Member, User
from ..schemas import CollateralCreate, CollateralUpdate, CollateralOut, ReturnCollateralRequest
from ..services.activity import log_activity
from ..services.security import current_user_id_ctx

router = APIRouter(prefix="/api/collaterals", tags=["collaterals"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COL_DIR = PROJECT_ROOT / "uploads" / "collaterals"


def _to_out(c: Collateral) -> dict:
    data = {col.name: getattr(c, col.name) for col in Collateral.__table__.columns}
    data["member_name"] = c.member.full_name if c.member else None
    return data


# --------------------------------------------------------------------------
@router.get("", response_model=list[CollateralOut])
def list_collaterals(
    member_id: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Collateral)
    if member_id:
        q = q.filter(Collateral.member_id == member_id)
    if status:
        q = q.filter(Collateral.status == status)
    return [_to_out(c) for c in q.order_by(Collateral.id.desc()).all()]


@router.get("/available", response_model=list[CollateralOut])
def list_available_collaterals(
    member_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Daftar jaminan dengan collateral_status=available — untuk dropdown pengajuan pinjaman baru."""
    q = db.query(Collateral).filter(Collateral.collateral_status == "available")
    if member_id:
        q = q.filter(Collateral.member_id == member_id)
    return [_to_out(c) for c in q.order_by(Collateral.id.desc()).all()]


@router.post("", response_model=CollateralOut, status_code=201)
def create_collateral(payload: CollateralCreate, db: Session = Depends(get_db)):
    if not db.get(Member, payload.member_id):
        raise HTTPException(404, detail="Anggota tidak ditemukan")
    c = Collateral(**payload.model_dump(), file_paths="[]", status="tersedia", collateral_status="available")
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("/{col_id}", response_model=CollateralOut)
def get_collateral(col_id: int, db: Session = Depends(get_db)):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    return _to_out(c)


@router.put("/{col_id}", response_model=CollateralOut)
def update_collateral(col_id: int, payload: CollateralUpdate, db: Session = Depends(get_db)):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.post("/{col_id}/upload", response_model=CollateralOut)
async def upload_file(
    col_id: int,
    document_type: str = Form("Dokumen Jaminan"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")

    COL_DIR.mkdir(parents=True, exist_ok=True)
    original_name = file.filename or "file"
    ext = Path(original_name).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".pdf"}:
        raise HTTPException(400, detail="Format file harus JPG/JPEG/PNG/PDF")

    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    stored_name = f"col_{col_id}_{stamp}{ext}"
    dest = COL_DIR / stored_name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="Ukuran file maksimal 10 MB")
    dest.write_bytes(content)

    rel_path = f"uploads/collaterals/{stored_name}"
    mime, _ = mimetypes.guess_type(original_name)

    # Tetap update file_paths JSON untuk backward-compat
    paths = json.loads(c.file_paths or "[]")
    paths.append(rel_path)
    c.file_paths = json.dumps(paths)

    # Simpan ke tabel collateral_documents (sumber kebenaran baru)
    db.add(CollateralDocument(
        collateral_id=col_id,
        document_type=document_type,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=rel_path,
        mime_type=mime,
        file_size=len(content),
        created_by=current_user_id_ctx.get(None),
    ))
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("/{col_id}/documents")
def list_documents(col_id: int, db: Session = Depends(get_db)):
    """Daftar semua dokumen jaminan — TIDAK pernah dihapus meski pinjaman lunas/jaminan dikembalikan."""
    if not db.get(Collateral, col_id):
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    docs = (
        db.query(CollateralDocument)
        .filter(CollateralDocument.collateral_id == col_id)
        .order_by(CollateralDocument.uploaded_at.asc())
        .all()
    )
    return {
        "collateral_id": col_id,
        "documents": [
            {
                "id": d.id,
                "document_type": d.document_type,
                "file_name": d.original_filename,
                "file_path": d.file_path,
                "mime_type": d.mime_type,
                "file_size": d.file_size,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ],
    }


@router.post("/{col_id}/documents")
async def upload_document_typed(
    col_id: int,
    document_type: str = Form("Dokumen Pendukung"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload dokumen jaminan dengan jenis dokumen eksplisit."""
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")

    COL_DIR.mkdir(parents=True, exist_ok=True)
    original_name = file.filename or "file"
    ext = Path(original_name).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".pdf"}:
        raise HTTPException(400, detail="Format file harus JPG/JPEG/PNG/PDF")

    stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    stored_name = f"col_{col_id}_{stamp}{ext}"
    dest = COL_DIR / stored_name
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, detail="Ukuran file maksimal 10 MB")
    dest.write_bytes(content)

    rel_path = f"uploads/collaterals/{stored_name}"
    mime, _ = mimetypes.guess_type(original_name)

    # Update file_paths JSON juga
    paths = json.loads(c.file_paths or "[]")
    paths.append(rel_path)
    c.file_paths = json.dumps(paths)

    doc = CollateralDocument(
        collateral_id=col_id,
        document_type=document_type,
        original_filename=original_name,
        stored_filename=stored_name,
        file_path=rel_path,
        mime_type=mime,
        file_size=len(content),
        created_by=current_user_id_ctx.get(None),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {
        "id": doc.id,
        "document_type": doc.document_type,
        "file_name": doc.original_filename,
        "file_path": doc.file_path,
        "mime_type": doc.mime_type,
        "file_size": doc.file_size,
        "uploaded_at": doc.uploaded_at.isoformat(),
    }


@router.delete("/{col_id}/files/{file_idx}", response_model=CollateralOut)
def delete_file(col_id: int, file_idx: int, db: Session = Depends(get_db)):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    paths = json.loads(c.file_paths or "[]")
    if file_idx < 0 or file_idx >= len(paths):
        raise HTTPException(400, detail="Index file tidak valid")
    target = PROJECT_ROOT / paths[file_idx]
    if target.exists():
        target.unlink()
    paths.pop(file_idx)
    c.file_paths = json.dumps(paths)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.post("/{col_id}/attach/{loan_id}", response_model=CollateralOut)
def attach_to_loan(col_id: int, loan_id: int, db: Session = Depends(get_db)):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    if c.collateral_status == "in_use":
        raise HTTPException(400, detail="Jaminan masih digunakan pada pinjaman aktif.")
    if c.collateral_status != "available":
        raise HTTPException(400, detail="Jaminan tidak tersedia untuk digunakan.")
    if not db.get(Loan, loan_id):
        raise HTTPException(404, detail="Pinjaman tidak ditemukan")

    uid = current_user_id_ctx.get(None)
    c.loan_id = loan_id
    c.status = "dijaminkan"
    c.collateral_status = "in_use"
    db.add(CollateralUsageHistory(
        collateral_id=col_id,
        loan_id=loan_id,
        action="attached",
        created_by=uid,
    ))
    log_activity(db, user_id=uid, action="collateral_attached", entity_type="loan",
                 entity_id=loan_id,
                 description=f"Jaminan #{col_id} ({c.type}) dilampirkan ke pinjaman")
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.post("/{col_id}/return", response_model=CollateralOut)
async def return_collateral(
    col_id: int,
    return_recipient: str = Form(...),
    return_date: str | None = Form(None),
    return_notes: str | None = Form(None),
    proof: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    c = db.get(Collateral, col_id)
    if not c:
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    if c.status not in ("dijaminkan", "menunggu_pengembalian"):
        raise HTTPException(400, detail="Jaminan tidak dalam status yang bisa dikembalikan")

    proof_path = None
    if proof and proof.filename:
        COL_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(proof.filename).suffix.lower()
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        dest = COL_DIR / f"return_{col_id}_{stamp}{ext}"
        dest.write_bytes(await proof.read())
        proof_path = f"uploads/collaterals/{dest.name}"

    ret_date = date.fromisoformat(return_date) if return_date else date.today()
    uid = current_user_id_ctx.get(None)

    # Simpan ke riwayat sebelum update collateral
    db.add(CollateralReturnHistory(
        collateral_id=c.id,
        loan_id=c.loan_id,
        return_date=ret_date,
        return_recipient=return_recipient,
        return_notes=return_notes,
        return_proof_path=proof_path,
        returned_by_user_id=uid,
    ))

    # Update collateral — status arsip, loan_id TETAP untuk menjaga histori relasi
    c.return_date = ret_date
    c.return_recipient = return_recipient
    c.return_notes = return_notes
    if proof_path:
        c.return_proof_path = proof_path
    c.status = "arsip"              # custody per-loan: arsip
    c.collateral_status = "available"  # ketersediaan: kembali available untuk pinjaman baru

    db.add(CollateralUsageHistory(
        collateral_id=c.id,
        loan_id=c.loan_id,
        action="returned",
        notes=f"Dikembalikan kepada {return_recipient}",
        created_by=uid,
    ))

    loan_id_for_log = c.loan_id
    if loan_id_for_log:
        log_activity(db, user_id=uid, action="collateral_returned", entity_type="loan",
                     entity_id=loan_id_for_log,
                     description=f"Jaminan #{c.id} ({c.type}) dikembalikan kepada {return_recipient} pada {ret_date}")

    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.get("/{col_id}/returns")
def list_return_history(col_id: int, db: Session = Depends(get_db)):
    if not db.get(Collateral, col_id):
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    rows = (
        db.query(CollateralReturnHistory)
        .filter(CollateralReturnHistory.collateral_id == col_id)
        .order_by(CollateralReturnHistory.created_at.desc())
        .all()
    )
    result = []
    for h in rows:
        actor = db.get(User, h.returned_by_user_id) if h.returned_by_user_id else None
        result.append({
            "id": h.id,
            "return_date": h.return_date.isoformat() if h.return_date else None,
            "return_recipient": h.return_recipient,
            "return_notes": h.return_notes,
            "return_proof_path": h.return_proof_path,
            "returned_by": actor.full_name if actor else "—",
            "created_at": h.created_at.isoformat(),
        })
    return result


@router.get("/{col_id}/usage-history")
def list_usage_history(col_id: int, db: Session = Depends(get_db)):
    """Riwayat penggunaan jaminan lintas pinjaman (attached/returned)."""
    if not db.get(Collateral, col_id):
        raise HTTPException(404, detail="Jaminan tidak ditemukan")
    rows = (
        db.query(CollateralUsageHistory)
        .filter(CollateralUsageHistory.collateral_id == col_id)
        .order_by(CollateralUsageHistory.created_at.asc())
        .all()
    )
    result = []
    for h in rows:
        actor = db.get(User, h.created_by) if h.created_by else None
        loan = db.get(Loan, h.loan_id) if h.loan_id else None
        result.append({
            "id": h.id,
            "action": h.action,
            "loan_id": h.loan_id,
            "loan_number": loan.loan_number if loan else None,
            "notes": h.notes,
            "actor": actor.full_name if actor else "—",
            "created_at": h.created_at.isoformat(),
        })
    return result
