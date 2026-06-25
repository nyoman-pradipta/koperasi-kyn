"""Router Pengaturan (Modul 11): get/update setting key-value + backup DB."""

import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db, DB_PATH
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
    """Unduh file koperasi.db untuk dicadangkan (online backup via sqlite3.backup)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(tmp.name)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return FileResponse(
        path=tmp.name,
        filename="koperasi-backup.db",
        media_type="application/octet-stream",
    )
