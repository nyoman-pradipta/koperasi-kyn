"""Helper kas: catat transaksi sambil menjaga saldo berjalan."""

from datetime import date, datetime

from sqlalchemy.orm import Session

from ..models import CashTransaction


def current_balance(db: Session) -> int:
    """Saldo kas terakhir (0 bila belum ada transaksi)."""
    last = (
        db.query(CashTransaction)
        .order_by(CashTransaction.id.desc())
        .first()
    )
    return last.balance_after if last else 0


def record_cash(
    db: Session,
    direction: str,          # "in" / "out"
    amount: int,
    category: str,
    description: str = "",
    ref_type: str | None = None,
    ref_id: int | None = None,
    officer_id: int | None = None,
    tx_date: datetime | date | None = None,
) -> CashTransaction:
    """Catat 1 transaksi kas; hitung balance_after otomatis.

    Tidak commit — caller yang commit agar atomik dengan transaksi induk.
    """
    balance = current_balance(db)
    balance = balance + amount if direction == "in" else balance - amount

    if tx_date is None:
        final_date = datetime.utcnow()
    elif isinstance(tx_date, datetime):
        final_date = tx_date
    elif isinstance(tx_date, date):
        if tx_date == date.today():
            final_date = datetime.utcnow()
        else:
            final_date = datetime(tx_date.year, tx_date.month, tx_date.day, 0, 0, 0)
    else:
        final_date = datetime.utcnow()

    tx = CashTransaction(
        transaction_date=final_date,
        direction=direction,
        category=category,
        amount=amount,
        balance_after=balance,
        description=description,
        ref_type=ref_type,
        ref_id=ref_id,
        officer_id=officer_id,
    )
    db.add(tx)
    db.flush()
    return tx
