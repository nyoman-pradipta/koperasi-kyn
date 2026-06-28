"""Router Pengaturan (Modul 11): get/update setting key-value."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    """Kembalikan semua setting sebagai objek {key: value}."""
    return {s.key: s.value for s in db.query(Setting).all()}


@router.put("")
def update_settings(payload: dict[str, str], db: Session = Depends(get_db)):
    """Upsert beberapa setting sekaligus."""
    for key, value in payload.items():
        setting = db.get(Setting, key)
        if setting:
            setting.value = value
        else:
            db.add(Setting(key=key, value=value))
    db.commit()
    return {s.key: s.value for s in db.query(Setting).all()}


@router.get("/backup")
def backup_db():
    """Backup dilakukan langsung dari Supabase Dashboard."""
    return JSONResponse(
        {"message": "Backup database bisa dilakukan dari Supabase Dashboard."},
        status_code=200,
    )

