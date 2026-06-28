"""
Entry-point aplikasi Koperasi (FastAPI).

Server ini hanya menyediakan REST API di bawah prefix `/api`.
Frontend dihosting secara terpisah di Vercel.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .calculations import simulate_credit
from .database import get_db, init_db, SessionLocal
from .models import SimulationLog
from .schemas import SimulationRequest
from .routers import (
    members,
    loans,
    payments,
    savings,
    cash,
    dashboard,
    reports,
    auth,
    users,
    settings as settings_router,
    collaterals,
    reminders,
)
from .models import AuthToken
from .services.seed import seed_defaults
from .services.security import current_user_id_ctx

# Path /api yang boleh diakses tanpa login.
AUTH_WHITELIST = {"/api/health", "/api/auth/login"}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_ROOT / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: buat tabel SQLite bila belum ada, lalu seed data awal.
    init_db()
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    yield
    # Shutdown: tidak ada yang perlu dibersihkan.


app = FastAPI(title="Koperasi Simpan Pinjam", version="1.0.0", lifespan=lifespan)

# Izinkan semua origin agar Vercel dapat mengakses API ini.
# Untuk produksi lebih ketat, ganti ["*"] dengan URL frontend Vercel Anda.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_guard(request, call_next):
    """Wajibkan token Bearer untuk /api/* (kecuali whitelist) & set context
    petugas yang sedang login."""
    path = request.url.path
    if path.startswith("/api") and path not in AUTH_WHITELIST:
        header = request.headers.get("authorization", "")
        token = header[7:] if header.lower().startswith("bearer ") else None
        db = SessionLocal()
        try:
            rec = db.get(AuthToken, token) if token else None
            if not rec:
                return JSONResponse({"detail": "Tidak terautentikasi"}, status_code=401)
            current_user_id_ctx.set(rec.user_id)
        finally:
            db.close()
    return await call_next(request)


# ----------------------------- API -----------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/simulate")
def simulate(payload: SimulationRequest, db: Session = Depends(get_db)):
    """Hitung simulasi kredit lalu simpan ringkasannya ke SQLite."""
    result = simulate_credit(
        loan_amount=payload.loan_amount,
        monthly_rate_pct=payload.monthly_rate_pct,
        tenor=payload.tenor,
        admin_pct=payload.admin_pct,
        provisi_pct=payload.provisi_pct,
        form_fee=payload.form_fee,
        interest_type=payload.interest_type,
    )

    log = SimulationLog(
        loan_amount=payload.loan_amount,
        monthly_rate_pct=payload.monthly_rate_pct,
        tenor=payload.tenor,
        admin_pct=payload.admin_pct,
        provisi_pct=payload.provisi_pct,
        form_fee=payload.form_fee,
        total_fees=result["fees"]["total_fees"],
        net_received=result["disbursement"]["net_received"],
        total_payable=result["total_payable"],
    )
    db.add(log)
    db.commit()

    return result


# ----------------------- Router per modul ----------------------------------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(members.router)
app.include_router(loans.router)
app.include_router(payments.router)
app.include_router(savings.router)
app.include_router(cash.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(settings_router.router)
app.include_router(collaterals.router)
app.include_router(reminders.router)


# ------------------- File upload (KTP/dokumen) -----------------------------

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# ------------------- Root Endpoint ----------------------------

@app.get("/")
def dev_hint():
    return JSONResponse(
        {
            "message": "API Koperasi aktif.",
            "petunjuk": "Gunakan frontend Vercel untuk mengakses sistem.",
            "api_docs": "/docs",
        }
    )
