"""Autentikasi sederhana untuk app lokal: hash password + token sesi di DB.

Token disimpan di tabel `auth_tokens` (tanpa dependency JWT). Cukup untuk
lingkungan LAN internal. Untuk eksposur lebih luas, ganti hash ke bcrypt/argon2.
"""

import hashlib
import secrets
from contextvars import ContextVar

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, AuthToken

# Diisi oleh middleware auth setiap request agar petugas yang login bisa
# diatribusikan sebagai officer tanpa mengubah signature setiap endpoint.
current_user_id_ctx: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def current_officer(db: Session) -> User | None:
    """User yang sedang login (dari context), fallback ke user pertama."""
    uid = current_user_id_ctx.get()
    if uid is not None:
        user = db.get(User, uid)
        if user:
            return user
    return db.query(User).order_by(User.id.asc()).first()


def hash_password(password: str) -> str:
    """SHA-256 (konsisten dengan seed admin awal)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return secrets.compare_digest(hash_password(password), password_hash)


def create_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(token=token, user_id=user.id))
    db.commit()
    return token


def revoke_token(db: Session, token: str) -> None:
    obj = db.get(AuthToken, token)
    if obj:
        db.delete(obj)
        db.commit()


def _token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: kembalikan User dari Bearer token, atau 401."""
    token = _token_from_header(authorization)
    if not token:
        raise HTTPException(401, detail="Tidak terautentikasi")
    rec = db.get(AuthToken, token)
    if not rec:
        raise HTTPException(401, detail="Sesi tidak valid / kedaluwarsa")
    user = db.get(User, rec.user_id)
    if not user or not user.is_active:
        raise HTTPException(401, detail="Akun tidak aktif")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, detail="Akses khusus admin")
    return user
