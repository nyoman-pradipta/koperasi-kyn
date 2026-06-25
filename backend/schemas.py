"""Schema Pydantic untuk validasi request/response API."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    """Input form dari user. Nilai default mengikuti contoh referensi."""

    loan_amount: float = Field(20_000_000, gt=0, description="Jumlah pinjaman (Rp)")
    monthly_rate_pct: float = Field(2.5, ge=0, description="Suku bunga per bulan (%)")
    tenor: int = Field(6, ge=1, le=360, description="Jangka waktu (bulan)")
    interest_type: str = Field("flat", description="flat / menurun")
    admin_pct: float = Field(4.0, ge=0, description="Biaya administrasi (%)")
    provisi_pct: float = Field(1.0, ge=0, description="Biaya provisi (%)")
    form_fee: float = Field(200_000, ge=0, description="Biaya form & pemeriksaan (Rp)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "loan_amount": 20000000,
                "monthly_rate_pct": 2.5,
                "tenor": 6,
                "admin_pct": 4.0,
                "provisi_pct": 1.0,
                "form_fee": 200000,
            }
        }
    }


# --------------------------------------------------------------------------
# Data Anggota (Modul 2)
# --------------------------------------------------------------------------
class MemberBase(BaseModel):
    full_name: str = Field(..., min_length=1)
    nik: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    join_date: Optional[date] = None
    status: str = "aktif"


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1)
    nik: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    join_date: Optional[date] = None
    status: Optional[str] = None


class MemberOut(MemberBase):
    id: int
    member_number: str
    ktp_photo_path: Optional[str] = None
    is_deleted: int = 0
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    created_at: datetime
    # computed fields (populated by router, not ORM)
    active_loans_count: int = 0
    total_loans_count: int = 0
    has_any_data: bool = False

    model_config = {"from_attributes": True}


class MemberListResponse(BaseModel):
    items: list[MemberOut]
    total: int
    page: int
    page_size: int


# --------------------------------------------------------------------------
# Pengajuan & Pinjaman (Modul 3, 5, 6)
# --------------------------------------------------------------------------
class LoanCreate(BaseModel):
    member_id: int
    principal_amount: int = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0)
    interest_type: str = "flat"  # flat / menurun
    tenor: int = Field(..., ge=1, le=360)
    admin_pct: float = 0
    provisi_pct: float = 0
    form_fee: int = 0
    purpose: Optional[str] = None
    requires_collateral: bool = True


class LoanUpdate(BaseModel):
    principal_amount: Optional[int] = Field(None, gt=0)
    interest_rate: Optional[float] = Field(None, ge=0)
    interest_type: Optional[str] = None
    tenor: Optional[int] = Field(None, ge=1, le=360)
    admin_pct: Optional[float] = None
    provisi_pct: Optional[float] = None
    form_fee: Optional[int] = None
    purpose: Optional[str] = None
    requires_collateral: Optional[bool] = None


class DecisionRequest(BaseModel):
    note: Optional[str] = None


class DisburseRequest(BaseModel):
    disbursement_date: Optional[date] = None


class LoanOut(BaseModel):
    id: int
    loan_number: str
    member_id: int
    member_name: Optional[str] = None
    principal_amount: int
    interest_rate: float
    interest_type: str
    tenor: int
    admin_pct: float
    provisi_pct: float
    form_fee: int
    admin_fee: int
    provisi_fee: int
    total_fees: int
    net_received: int
    total_payable: int
    disbursement_date: Optional[date] = None
    purpose: Optional[str] = None
    requires_collateral: bool = True
    status: str
    created_at: datetime
    collateral: Optional[dict] = None

    model_config = {"from_attributes": True}


class LoanListResponse(BaseModel):
    items: list[LoanOut]
    total: int
    page: int
    page_size: int


# --------------------------------------------------------------------------
# Pembayaran Angsuran (Modul 7)
# --------------------------------------------------------------------------
class PaymentCreate(BaseModel):
    loan_id: int
    amount: int = Field(..., gt=0, description="Nominal angsuran dibayar (Rp)")
    penalty: int = Field(0, ge=0, description="Denda keterlambatan (Rp)")
    payment_date: Optional[date] = None
    payment_method: str = "tunai"  # tunai / transfer
    note: Optional[str] = None


# --------------------------------------------------------------------------
# Simpanan (Modul 8)
# --------------------------------------------------------------------------
class SavingCreate(BaseModel):
    member_id: int
    savings_type: str = Field(..., description="pokok / wajib / sukarela")
    transaction_type: str = Field(..., description="setor / tarik")
    amount: int = Field(..., gt=0)
    transaction_date: Optional[datetime] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------
# Jaminan (Modul 3 - Data Jaminan)
# --------------------------------------------------------------------------
class CollateralCreate(BaseModel):
    member_id: int
    type: str = Field(..., description="Sertifikat Tanah / BPKB Motor / BPKB Mobil / Lainnya")
    doc_number: Optional[str] = None
    owner_name: Optional[str] = None
    estimated_value: int = 0
    notes: Optional[str] = None
    doc_status: str = "belum_diterima"
    doc_received_date: Optional[date] = None
    receiver_officer: Optional[str] = None
    storage_location: str = "brankas"


class CollateralUpdate(BaseModel):
    type: Optional[str] = None
    doc_number: Optional[str] = None
    owner_name: Optional[str] = None
    estimated_value: Optional[int] = None
    notes: Optional[str] = None
    doc_status: Optional[str] = None
    doc_received_date: Optional[date] = None
    receiver_officer: Optional[str] = None
    storage_location: Optional[str] = None


class ReturnCollateralRequest(BaseModel):
    return_date: Optional[date] = None
    return_recipient: str
    return_notes: Optional[str] = None


class CollateralOut(BaseModel):
    id: int
    member_id: int
    loan_id: Optional[int] = None
    type: str
    doc_number: Optional[str] = None
    owner_name: Optional[str] = None
    estimated_value: int
    notes: Optional[str] = None
    file_paths: str = "[]"
    doc_status: str
    doc_received_date: Optional[date] = None
    receiver_officer: Optional[str] = None
    storage_location: str
    status: str
    collateral_status: str = "available"
    created_at: datetime
    return_date: Optional[date] = None
    return_recipient: Optional[str] = None
    return_proof_path: Optional[str] = None
    return_notes: Optional[str] = None
    member_name: Optional[str] = None

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------
# Kas & Keuangan (Modul 9)
# --------------------------------------------------------------------------
class CashCreate(BaseModel):
    direction: str = Field(..., description="in / out")
    amount: int = Field(..., gt=0)
    category: str = "operasional"
    description: Optional[str] = None
    transaction_date: Optional[datetime] = None

