"""Seed data awal: admin default, sequence nomor, dan setting dasar.

Dipanggil sekali saat startup. Idempotent — aman dijalankan berkali-kali.
"""

import hashlib

from sqlalchemy.orm import Session

from ..models import User, NumberSequence, Setting


def _hash(password: str) -> str:
    # Hash sederhana (cukup untuk app internal lokal). Ganti ke bcrypt
    # bila aplikasi diekspos ke jaringan yang lebih luas.
    return hashlib.sha256(password.encode()).hexdigest()


DEFAULT_SEQUENCES = [
    {"name": "member", "prefix": "AGT"},
    {"name": "loan", "prefix": "PJM"},
    {"name": "payment", "prefix": "KWT"},
]

DEFAULT_SETTINGS = {
    "coop_name": "Koperasi Sejahtera",
    "coop_address": "-",
    "coop_logo": "",
    "printer_size": "58mm",
    "late_fee_per_day": "20000",
    # Alokasi SHU (persen, total 100) — bisa diubah di Pengaturan
    "shu_cadangan": "25",
    "shu_jasa_modal": "20",
    "shu_jasa_usaha": "25",
    "shu_pengurus": "10",
    "shu_dana_sosial": "10",
    "shu_pendidikan": "10",
}


def seed_defaults(db: Session) -> None:
    # Admin default
    if db.query(User).count() == 0:
        db.add(
            User(
                username="admin",
                password_hash=_hash("admin"),
                full_name="Administrator",
                role="admin",
                is_active=1,
            )
        )

    # Sequence nomor otomatis
    for s in DEFAULT_SEQUENCES:
        if db.query(NumberSequence).filter_by(name=s["name"]).first() is None:
            db.add(NumberSequence(name=s["name"], prefix=s["prefix"], current_value=0))

    # Setting dasar
    for key, value in DEFAULT_SETTINGS.items():
        if db.query(Setting).filter_by(key=key).first() is None:
            db.add(Setting(key=key, value=value))

    db.commit()
