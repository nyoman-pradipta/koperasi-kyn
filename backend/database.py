"""
Konfigurasi database PostgreSQL (Supabase/Neon via DATABASE_URL).
"""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Baca DATABASE_URL dari environment (contoh dari Render/Neon)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set. Supabase/Postgres is required.")

# Render/Neon kadang memberi URL postgres://, SQLAlchemy butuh postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SQLALCHEMY_DATABASE_URL = DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



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
