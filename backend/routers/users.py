"""Router Manajemen Pengguna (petugas) — khusus admin."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services.security import hash_password, require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)
    full_name: str
    role: str = "petugas"  # admin / petugas


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=4)
    role: Optional[str] = None
    is_active: Optional[int] = None


def _out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
    }


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_out(u) for u in db.query(User).order_by(User.id.asc()).all()]


@router.post("", status_code=201)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(400, detail="Username sudah dipakai")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _out(user)


@router.put("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, detail="Pengguna tidak ditemukan")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _out(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(400, detail="Tidak bisa menghapus akun sendiri")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, detail="Pengguna tidak ditemukan")
    db.delete(user)
    db.commit()
