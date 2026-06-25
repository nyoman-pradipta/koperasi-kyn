"""Generate jadwal angsuran (installment_schedule) saat pinjaman dicairkan."""

from datetime import date
from calendar import monthrange

from sqlalchemy.orm import Session

from ..calculations import build_schedule
from ..models import InstallmentSchedule, Loan


def _add_month(d: date, n: int) -> date:
    """Tambah n bulan ke tanggal d (aman utk akhir bulan)."""
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def generate_schedule(db: Session, loan: Loan) -> list[InstallmentSchedule]:
    """Buat baris installment_schedule berdasarkan parameter loan.

    Tidak commit — caller yang commit. due_date jatuh tempo bulanan dihitung
    dari disbursement_date (atau hari ini bila kosong).
    """
    start = loan.disbursement_date or date.today()
    rows, _total_interest, _total_payable = build_schedule(
        loan.principal_amount,
        loan.interest_rate,
        loan.tenor,
        loan.interest_type,
    )

    created = []
    for row in rows:
        item = InstallmentSchedule(
            loan_id=loan.id,
            installment_no=row["month"],
            due_date=_add_month(start, row["month"]),
            principal_due=row["principal"],
            interest_due=row["interest"],
            total_due=row["total"],
            status="unpaid",
        )
        db.add(item)
        created.append(item)
    return created
