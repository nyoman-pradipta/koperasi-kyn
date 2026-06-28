"""
Model SQLAlchemy lengkap untuk Sistem Koperasi Simpan Pinjam.

Konvensi:
- Uang disimpan sebagai INTEGER Rupiah (tanpa sen).
- Timestamp pakai DateTime (UTC); tanggal kalender pakai Date.
- File upload (KTP/jaminan/dokumen) disimpan PATH-nya, bukan blob.
"""

from datetime import datetime, date

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from .database import Base


# --------------------------------------------------------------------------
# Auth & konfigurasi
# --------------------------------------------------------------------------
class User(Base):
    """Akun operator/petugas untuk login & audit."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="petugas")  # admin / petugas
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AuthToken(Base):
    """Token sesi login (DB-backed, tanpa dependency JWT eksternal)."""

    __tablename__ = "auth_tokens"

    token = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Setting(Base):
    """Pengaturan key-value (logo, ukuran printer, template kwitansi, dll)."""

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text)


class NumberSequence(Base):
    """Counter untuk format nomor otomatis (anggota/pinjaman/kwitansi)."""

    __tablename__ = "number_sequences"

    name = Column(String, primary_key=True)  # member / loan / payment
    prefix = Column(String, nullable=False)
    current_value = Column(Integer, nullable=False, default=0)
    reset_period = Column(String, default="yearly")  # yearly / never


# --------------------------------------------------------------------------
# Master data anggota
# --------------------------------------------------------------------------
class Member(Base):
    """Data master anggota koperasi (Modul 2)."""

    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    member_number = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    nik = Column(String, unique=True, index=True)
    ktp_photo_path = Column(String)
    address = Column(Text)
    phone = Column(String)
    email = Column(String)
    join_date = Column(Date)
    status = Column(String, nullable=False, default="aktif")  # aktif / nonaktif / diblokir / diarsipkan
    is_deleted = Column(Integer, nullable=False, default=0)   # soft-delete flag
    deleted_at = Column(DateTime)
    deleted_by = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    loans = relationship("Loan", back_populates="member")
    savings = relationship("Saving", back_populates="member")
    collaterals = relationship("Collateral", back_populates="member")


# --------------------------------------------------------------------------
# Perkreditan
# --------------------------------------------------------------------------
class Loan(Base):
    """Pengajuan + siklus hidup pinjaman (Modul 3 & 6)."""

    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    loan_number = Column(String, unique=True, nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)

    principal_amount = Column(Integer, nullable=False)
    interest_rate = Column(Float, nullable=False)  # % per bulan
    interest_type = Column(String, nullable=False, default="flat")  # flat / menurun
    tenor = Column(Integer, nullable=False)  # bulan

    admin_pct = Column(Float, default=0)
    provisi_pct = Column(Float, default=0)
    form_fee = Column(Integer, default=0)
    admin_fee = Column(Integer, default=0)
    provisi_fee = Column(Integer, default=0)
    total_fees = Column(Integer, default=0)
    net_received = Column(Integer, default=0)
    total_payable = Column(Integer, default=0)

    disbursement_date = Column(Date)
    purpose = Column(Text)
    requires_collateral = Column(Integer, default=1)
    # draft / pending / approved / rejected / active / paid_off
    status = Column(String, nullable=False, default="draft")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    member = relationship("Member", back_populates="loans")
    schedule = relationship("InstallmentSchedule", back_populates="loan")
    payments = relationship("Payment", back_populates="loan")
    documents = relationship("LoanDocument", back_populates="loan")
    approvals = relationship("LoanApproval", back_populates="loan")
    collaterals = relationship("Collateral", back_populates="loan")


class LoanApproval(Base):
    """Keputusan persetujuan kredit (Modul 5)."""

    __tablename__ = "loan_approvals"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)  # approve / reject
    note = Column(Text)
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    loan = relationship("Loan", back_populates="approvals")


class LoanDocument(Base):
    """Dokumen pengajuan terupload (Modul 3)."""

    __tablename__ = "loan_documents"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    doc_type = Column(String)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    loan = relationship("Loan", back_populates="documents")


class Collateral(Base):
    """Jaminan milik anggota / atas pinjaman (Modul 2 & 3)."""

    __tablename__ = "collaterals"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)

    # Identitas jaminan
    type = Column(String, nullable=False)           # Sertifikat Tanah / BPKB Motor / BPKB Mobil / Lainnya
    doc_number = Column(String)                     # Nomor dokumen / BPKB
    owner_name = Column(String)                     # Nama pemilik sesuai dokumen
    estimated_value = Column(Integer, default=0)   # Estimasi nilai (Rp)
    notes = Column(Text)                            # Catatan opsional

    # Dokumen fisik
    file_paths = Column(Text, default="[]")         # JSON list of relative paths
    doc_status = Column(String, default="belum_diterima")   # belum_diterima / sudah_diterima
    doc_received_date = Column(Date)
    receiver_officer = Column(String)               # Nama petugas penerima
    storage_location = Column(String, default="brankas")    # brankas / lemari

    # Status jaminan (legacy, tracks custody per-loan)
    status = Column(String, nullable=False, default="tersedia")
    # tersedia / dijaminkan / menunggu_pengembalian / arsip

    # Status ketersediaan jaminan lintas pinjaman
    collateral_status = Column(String, nullable=False, default="available")
    # available / in_use / returned / archived

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Pengembalian jaminan
    return_date = Column(Date)
    return_recipient = Column(String)
    return_proof_path = Column(String)
    return_notes = Column(Text)

    member = relationship("Member", back_populates="collaterals")
    loan = relationship("Loan", back_populates="collaterals")
    return_history = relationship("CollateralReturnHistory", back_populates="collateral", order_by="CollateralReturnHistory.created_at.desc()")
    col_documents = relationship("CollateralDocument", back_populates="collateral", order_by="CollateralDocument.uploaded_at.asc()")
    usage_history = relationship("CollateralUsageHistory", back_populates="collateral", order_by="CollateralUsageHistory.created_at.asc()")


class CollateralDocument(Base):
    """Dokumen fisik jaminan — satu jaminan bisa punya banyak file dengan tipe berbeda."""

    __tablename__ = "collateral_documents"

    id = Column(Integer, primary_key=True, index=True)
    collateral_id = Column(Integer, ForeignKey("collaterals.id"), nullable=False)
    document_type = Column(String, nullable=False, default="Dokumen Pendukung")
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)   # relative: uploads/collaterals/...
    mime_type = Column(String)
    file_size = Column(Integer, default=0)       # bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    collateral = relationship("Collateral", back_populates="col_documents")


class CollateralReturnHistory(Base):
    """Riwayat setiap pengembalian jaminan (satu jaminan bisa dikembalikan lebih dari sekali lintas pinjaman)."""

    __tablename__ = "collateral_return_history"

    id = Column(Integer, primary_key=True, index=True)
    collateral_id = Column(Integer, ForeignKey("collaterals.id"), nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    return_date = Column(Date, nullable=False)
    return_recipient = Column(String, nullable=False)
    return_notes = Column(Text)
    return_proof_path = Column(String)
    returned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    collateral = relationship("Collateral", back_populates="return_history")


class CollateralUsageHistory(Base):
    """Riwayat penggunaan jaminan lintas pinjaman — attached / returned."""

    __tablename__ = "collateral_usage_history"

    id = Column(Integer, primary_key=True, index=True)
    collateral_id = Column(Integer, ForeignKey("collaterals.id"), nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=True)
    action = Column(String, nullable=False)   # attached / returned
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    collateral = relationship("Collateral", back_populates="usage_history")


class InstallmentSchedule(Base):
    """Jadwal/rincian angsuran per bulan (Modul 6 & 7)."""

    __tablename__ = "installment_schedule"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    installment_no = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    principal_due = Column(Integer, nullable=False)
    interest_due = Column(Integer, nullable=False)
    total_due = Column(Integer, nullable=False)
    paid_amount = Column(Integer, default=0)
    paid_date = Column(Date)
    status = Column(String, nullable=False, default="unpaid")  # unpaid/partial/paid

    loan = relationship("Loan", back_populates="schedule")


class Payment(Base):
    """Pembayaran angsuran + data kwitansi (Modul 7)."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String, unique=True, nullable=False, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("installment_schedule.id"))

    payment_date = Column(Date, nullable=False)
    amount_paid = Column(Integer, nullable=False)
    principal_component = Column(Integer, default=0)
    interest_component = Column(Integer, default=0)
    penalty_component = Column(Integer, default=0)
    payment_method = Column(String)  # tunai / transfer
    remaining_balance = Column(Integer)
    officer_id = Column(Integer, ForeignKey("users.id"))
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    loan = relationship("Loan", back_populates="payments")


# --------------------------------------------------------------------------
# Simpanan & Kas
# --------------------------------------------------------------------------
class Saving(Base):
    """Transaksi simpanan pokok/wajib/sukarela (Modul 8)."""

    __tablename__ = "savings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    savings_type = Column(String, nullable=False)  # pokok/wajib/sukarela
    transaction_type = Column(String, nullable=False)  # setor/tarik
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    note = Column(Text)
    officer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    member = relationship("Member", back_populates="savings")


class CashTransaction(Base):
    """Kas masuk/keluar & jurnal (Modul 9)."""

    __tablename__ = "cash_transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_date = Column(DateTime, nullable=False)
    direction = Column(String, nullable=False)  # in / out
    category = Column(String)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(Text)
    ref_type = Column(String)  # payment/savings/loan/manual
    ref_id = Column(Integer)
    officer_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ActivityLog(Base):
    """Feed aktivitas terbaru untuk dashboard (Modul 1)."""

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# --------------------------------------------------------------------------
# Riwayat simulasi (dari boilerplate awal)
# --------------------------------------------------------------------------
class SimulationLog(Base):
    """Riwayat setiap simulasi kredit yang dijalankan user."""

    __tablename__ = "simulation_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    loan_amount = Column(Float, nullable=False)
    monthly_rate_pct = Column(Float, nullable=False)
    tenor = Column(Integer, nullable=False)
    admin_pct = Column(Float, nullable=False)
    provisi_pct = Column(Float, nullable=False)
    form_fee = Column(Float, nullable=False)

    total_fees = Column(Integer, nullable=False)
    net_received = Column(Integer, nullable=False)
    total_payable = Column(Integer, nullable=False)


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("installment_schedule.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    loan_id = Column(Integer, ForeignKey("loans.id"), nullable=False)
    channel = Column(String, default="whatsapp")
    phone = Column(String, nullable=True)
    sent_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
