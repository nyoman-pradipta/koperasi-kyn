"""Router Autentikasi: login, profil, logout."""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services.security import (
    verify_password,
    create_token,
    revoke_token,
    get_current_user,
    _token_from_header,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, detail="Username atau password salah")
    if not user.is_active:
        raise HTTPException(403, detail="Akun nonaktif")
    token = create_token(db, user)
    return {"token": token, "user": _user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/logout")
def logout(authorization: str | None = Header(None), db: Session = Depends(get_db)):
    token = _token_from_header(authorization)
    if token:
        revoke_token(db, token)
    return {"status": "ok"}
