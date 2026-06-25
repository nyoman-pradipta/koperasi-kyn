"""
Konfigurasi database SQLite.

File database (`koperasi.db`) disimpan di FOLDER ROOT project, dihitung
relatif terhadap lokasi file ini. Dengan begitu, memindahkan seluruh folder
project ke komputer lain otomatis ikut membawa datanya — tidak ada path
absolut yang di-hardcode.
"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# .../koperasi/backend/database.py -> root = .../koperasi
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "koperasi.db"

# check_same_thread=False diperlukan agar SQLite bisa dipakai lintas thread FastAPI
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    """Tegakkan FOREIGN KEY (SQLite mematikannya secara default)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_db():
    """Dependency FastAPI: buka sesi DB lalu pastikan tertutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Buat tabel-tabel jika belum ada (dipanggil saat startup)."""
    # import model agar terdaftar di metadata sebelum create_all
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
