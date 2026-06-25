"""
Logika perhitungan Simulasi & Kredit Koperasi.

Mendukung dua jenis bunga:
- `flat`    : bunga tetap dari pokok awal tiap bulan. Angsuran dibulatkan KE
              ATAS ke kelipatan Rp 1.000; angsuran terakhir disesuaikan agar
              total tepat (mengikuti contoh referensi koperasi).
- `menurun` : bunga dihitung dari sisa pokok (efektif/sliding). Pokok per bulan
              rata; angsuran mengecil tiap bulan.

Semua angka uang diperlakukan sebagai INTEGER Rupiah pada output.
"""

import math
from typing import List, Dict, Any, Tuple


ROUNDING_STEP = 1000          # pembulatan angsuran flat (Rp 1.000)
LATE_FEE_PER_DAY = 20000      # denda keterlambatan default per hari


def _ceil_to_step(value: float, step: int = ROUNDING_STEP) -> int:
    """Bulatkan `value` ke ATAS ke kelipatan `step`."""
    return int(math.ceil(value / step) * step)


def build_schedule(
    principal: float,
    monthly_rate_pct: float,
    tenor: int,
    interest_type: str = "flat",
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Bangun jadwal angsuran.

    Returns (schedule, total_interest, total_payable) dengan setiap baris:
    {month, principal, interest, total, remaining}.
    """
    rate = monthly_rate_pct / 100.0
    schedule: List[Dict[str, Any]] = []

    if interest_type == "menurun":
        principal_per_month = int(round(principal / tenor))
        remaining = int(round(principal))
        acc_principal = 0
        for month in range(1, tenor + 1):
            interest = int(round(remaining * rate))
            if month < tenor:
                pokok = principal_per_month
            else:
                pokok = int(round(principal)) - acc_principal  # sisa pas
            acc_principal += pokok
            remaining -= pokok
            total = pokok + interest
            schedule.append(
                {
                    "month": month,
                    "principal": pokok,
                    "interest": interest,
                    "total": total,
                    "remaining": max(remaining, 0),
                }
            )
    else:  # flat (default)
        monthly_interest = principal * rate
        principal_per_month = principal / tenor
        raw_installment = principal_per_month + monthly_interest
        rounded_installment = _ceil_to_step(raw_installment)
        total_payable = int(round(principal + monthly_interest * tenor))

        accumulated = 0
        remaining = int(round(principal))
        interest_month = int(round(monthly_interest))
        for month in range(1, tenor + 1):
            if month < tenor:
                total = rounded_installment
            else:
                total = total_payable - accumulated  # penyesuaian terakhir
            accumulated += total
            pokok = total - interest_month
            remaining -= pokok
            schedule.append(
                {
                    "month": month,
                    "principal": pokok,
                    "interest": interest_month,
                    "total": total,
                    "remaining": max(remaining, 0),
                }
            )

    total_interest = sum(r["interest"] for r in schedule)
    total_payable = sum(r["total"] for r in schedule)
    return schedule, total_interest, total_payable


def compute_fees(
    loan_amount: float, admin_pct: float, provisi_pct: float, form_fee: float
) -> Dict[str, int]:
    """Hitung biaya potongan awal & dana bersih."""
    admin_fee = int(round(loan_amount * admin_pct / 100.0))
    provisi_fee = int(round(loan_amount * provisi_pct / 100.0))
    form_fee_int = int(round(form_fee))
    total_fees = admin_fee + provisi_fee + form_fee_int
    net_received = int(round(loan_amount)) - total_fees
    return {
        "admin_fee": admin_fee,
        "provisi_fee": provisi_fee,
        "form_fee": form_fee_int,
        "total_fees": total_fees,
        "net_received": net_received,
    }


def simulate_credit(
    loan_amount: float,
    monthly_rate_pct: float,
    tenor: int,
    admin_pct: float,
    provisi_pct: float,
    form_fee: float,
    interest_type: str = "flat",
    late_fee_per_day: int = LATE_FEE_PER_DAY,
) -> Dict[str, Any]:
    """Hitung simulasi kredit lengkap → siap di-serialize ke JSON."""
    if tenor < 1:
        raise ValueError("Tenor minimal 1 bulan")
    if loan_amount <= 0:
        raise ValueError("Jumlah pinjaman harus lebih dari 0")

    schedule, total_interest, total_payable = build_schedule(
        loan_amount, monthly_rate_pct, tenor, interest_type
    )
    fees = compute_fees(loan_amount, admin_pct, provisi_pct, form_fee)

    # Angka contoh untuk panel "Parameter Utama" (ambil dari bulan pertama)
    first = schedule[0]
    raw_installment = round(loan_amount / tenor + loan_amount * monthly_rate_pct / 100.0, 2)

    return {
        "input": {
            "loan_amount": int(round(loan_amount)),
            "monthly_rate_pct": monthly_rate_pct,
            "tenor": tenor,
            "interest_type": interest_type,
            "admin_pct": admin_pct,
            "provisi_pct": provisi_pct,
            "form_fee": fees["form_fee"],
        },
        "main_parameters": {
            "loan_amount": int(round(loan_amount)),
            "monthly_rate_pct": monthly_rate_pct,
            "tenor": tenor,
            "interest_type": interest_type,
            "monthly_interest": first["interest"],
            "installment_exact": raw_installment if interest_type == "flat" else first["total"],
            "installment_rounded": first["total"],
        },
        "schedule": schedule,
        "fees": fees,
        "disbursement": {
            "loan_amount": int(round(loan_amount)),
            "total_fees": fees["total_fees"],
            "net_received": fees["net_received"],
        },
        "total_interest": total_interest,
        "total_payable": total_payable,
        "late_fee_per_day": late_fee_per_day,
    }
