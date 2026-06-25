"""Agregasi untuk Dashboard (Modul 1) & Laporan (Modul 10)."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..models import (
    Member,
    Loan,
    Payment,
    Saving,
    CashTransaction,
    InstallmentSchedule,
    Setting,
)
from .cash import current_balance


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
def _savings_net(db: Session) -> int:
    rows = db.query(Saving).all()
    return sum(s.amount if s.transaction_type == "setor" else -s.amount for s in rows)


def dashboard_summary(db: Session) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    active_loans = db.query(Loan).filter(Loan.status == "active").all()
    active_ids = [l.id for l in active_loans]

    # outstanding & tunggakan dari installment_schedule
    outstanding = 0
    arrears = 0
    if active_ids:
        scheds = (
            db.query(InstallmentSchedule)
            .filter(InstallmentSchedule.loan_id.in_(active_ids))
            .all()
        )
        for s in scheds:
            remaining = s.total_due - s.paid_amount
            if remaining > 0:
                outstanding += remaining
                if s.due_date < today and s.status != "paid":
                    arrears += remaining

    disbursed_month = sum(
        l.net_received for l in db.query(Loan).all()
        if l.disbursement_date and l.disbursement_date >= month_start
    )
    payments_month = sum(
        p.amount_paid + p.penalty_component
        for p in db.query(Payment).filter(Payment.payment_date >= month_start).all()
    )

    return {
        "total_members": db.query(Member).count(),
        "active_loans_count": len(active_loans),
        "active_loans_outstanding": outstanding,
        "total_savings": _savings_net(db),
        "cash_balance": current_balance(db),
        "arrears": arrears,
        "disbursed_this_month": disbursed_month,
        "payments_this_month": payments_month,
    }


def dashboard_chart(db: Session, months: int = 6) -> dict:
    today = date.today()
    labels, ins, outs = [], [], []
    # bangun ember per bulan (mundur `months` bulan)
    cursor = today.replace(day=1)
    buckets = []
    for _ in range(months):
        buckets.append(cursor)
        # mundur 1 bulan
        prev_month = cursor.month - 1 or 12
        prev_year = cursor.year - 1 if cursor.month == 1 else cursor.year
        cursor = date(prev_year, prev_month, 1)
    buckets.reverse()

    rows = db.query(CashTransaction).all()
    for b in buckets:
        nxt_month = b.month % 12 + 1
        nxt_year = b.year + 1 if b.month == 12 else b.year
        nxt = date(nxt_year, nxt_month, 1)
        labels.append(b.strftime("%b %Y"))
        ins.append(sum(t.amount for t in rows if t.direction == "in" and b <= t.transaction_date.date() < nxt))
        outs.append(sum(t.amount for t in rows if t.direction == "out" and b <= t.transaction_date.date() < nxt))
    return {"labels": labels, "masuk": ins, "keluar": outs}


def dashboard_activities(db: Session, limit: int = 8) -> list:
    rows = (
        db.query(CashTransaction)
        .order_by(CashTransaction.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "date": t.transaction_date,
            "direction": t.direction,
            "category": t.category,
            "description": t.description,
            "amount": t.amount,
        }
        for t in rows
    ]


def dashboard_reminders(db: Session, days_ahead: int = 7) -> list:
    today = date.today()
    horizon = today + timedelta(days=days_ahead)
    active_ids = [l.id for l in db.query(Loan).filter(Loan.status == "active").all()]
    if not active_ids:
        return []
    scheds = (
        db.query(InstallmentSchedule)
        .filter(
            InstallmentSchedule.loan_id.in_(active_ids),
            InstallmentSchedule.status != "paid",
            InstallmentSchedule.due_date <= horizon,
        )
        .order_by(InstallmentSchedule.due_date.asc())
        .all()
    )
    out = []
    for s in scheds:
        loan = db.get(Loan, s.loan_id)
        member = db.get(Member, loan.member_id) if loan else None
        out.append(
            {
                "loan_number": loan.loan_number if loan else "-",
                "member_name": member.full_name if member else "-",
                "installment_no": s.installment_no,
                "due_date": s.due_date,
                "amount": s.total_due - s.paid_amount,
                "overdue": s.due_date < today,
            }
        )
    return out


# --------------------------------------------------------------------------
# Laporan (Modul 10) — semua kembalikan {title, columns, rows, summary}
# --------------------------------------------------------------------------
def _cols(*pairs):
    return [{"key": k, "label": l} for k, l in pairs]


def report_loans(db: Session, start: date | None, end: date | None) -> dict:
    q = db.query(Loan, Member.full_name).join(Member, Loan.member_id == Member.id)
    rows = []
    total_principal = 0
    for loan, name in q.all():
        d = loan.created_at.date()
        if start and d < start:
            continue
        if end and d > end:
            continue
        total_principal += loan.principal_amount
        rows.append({
            "loan_number": loan.loan_number,
            "member_name": name,
            "principal_amount": loan.principal_amount,
            "interest": f"{loan.interest_type} {loan.interest_rate}%",
            "tenor": loan.tenor,
            "status": loan.status,
            "total_payable": loan.total_payable,
        })
    return {
        "title": "Laporan Pinjaman",
        "columns": _cols(
            ("loan_number", "No. Pinjaman"), ("member_name", "Nama"),
            ("principal_amount", "Pokok"), ("interest", "Bunga"),
            ("tenor", "Tenor"), ("status", "Status"), ("total_payable", "Total Bayar"),
        ),
        "rows": rows,
        "summary": {"Jumlah Pinjaman": len(rows), "Total Pokok": total_principal},
    }


def report_payments(db: Session, start: date | None, end: date | None) -> dict:
    q = db.query(Payment, Member.full_name).join(Member, Payment.member_id == Member.id)
    rows, total, total_int, total_pen = [], 0, 0, 0
    for p, name in q.all():
        if start and p.payment_date < start:
            continue
        if end and p.payment_date > end:
            continue
        total += p.amount_paid
        total_int += p.interest_component
        total_pen += p.penalty_component
        rows.append({
            "payment_number": p.payment_number,
            "payment_date": str(p.payment_date),
            "member_name": name,
            "principal_component": p.principal_component,
            "interest_component": p.interest_component,
            "penalty_component": p.penalty_component,
            "amount_paid": p.amount_paid,
        })
    return {
        "title": "Laporan Pembayaran",
        "columns": _cols(
            ("payment_number", "No. Kwitansi"), ("payment_date", "Tanggal"),
            ("member_name", "Nama"), ("principal_component", "Pokok"),
            ("interest_component", "Bunga"), ("penalty_component", "Denda"),
            ("amount_paid", "Angsuran"),
        ),
        "rows": rows,
        "summary": {"Total Angsuran": total, "Total Bunga": total_int, "Total Denda": total_pen},
    }


def report_savings(db: Session, start: date | None, end: date | None) -> dict:
    q = db.query(Saving, Member.full_name).join(Member, Saving.member_id == Member.id)
    rows, net = [], 0
    for s, name in q.all():
        if start and s.transaction_date.date() < start:
            continue
        if end and s.transaction_date.date() > end:
            continue
        net += s.amount if s.transaction_type == "setor" else -s.amount
        rows.append({
            "transaction_date": str(s.transaction_date),
            "member_name": name,
            "savings_type": s.savings_type,
            "transaction_type": s.transaction_type,
            "amount": s.amount,
            "balance_after": s.balance_after,
        })
    return {
        "title": "Laporan Simpanan",
        "columns": _cols(
            ("transaction_date", "Tanggal"), ("member_name", "Nama"),
            ("savings_type", "Jenis"), ("transaction_type", "Transaksi"),
            ("amount", "Nominal"), ("balance_after", "Saldo"),
        ),
        "rows": rows,
        "summary": {"Jumlah Transaksi": len(rows), "Net Simpanan": net},
    }


def report_arrears(db: Session, start: date | None, end: date | None) -> dict:
    today = date.today()
    active_ids = [l.id for l in db.query(Loan).filter(Loan.status == "active").all()]
    rows, total = [], 0
    if active_ids:
        scheds = (
            db.query(InstallmentSchedule)
            .filter(
                InstallmentSchedule.loan_id.in_(active_ids),
                InstallmentSchedule.status != "paid",
                InstallmentSchedule.due_date < today,
            )
            .all()
        )
        for s in scheds:
            loan = db.get(Loan, s.loan_id)
            member = db.get(Member, loan.member_id) if loan else None
            remaining = s.total_due - s.paid_amount
            total += remaining
            rows.append({
                "loan_number": loan.loan_number if loan else "-",
                "member_name": member.full_name if member else "-",
                "installment_no": s.installment_no,
                "due_date": str(s.due_date),
                "days_late": (today - s.due_date).days,
                "outstanding": remaining,
            })
    return {
        "title": "Laporan Tunggakan",
        "columns": _cols(
            ("loan_number", "No. Pinjaman"), ("member_name", "Nama"),
            ("installment_no", "Angsuran ke-"), ("due_date", "Jatuh Tempo"),
            ("days_late", "Telat (hari)"), ("outstanding", "Tunggakan"),
        ),
        "rows": rows,
        "summary": {"Jumlah Tunggakan": len(rows), "Total Tunggakan": total},
    }


def report_cash(db: Session, start: date | None, end: date | None) -> dict:
    rows, tin, tout = [], 0, 0
    for t in db.query(CashTransaction).order_by(CashTransaction.id.asc()).all():
        if start and t.transaction_date.date() < start:
            continue
        if end and t.transaction_date.date() > end:
            continue
        if t.direction == "in":
            tin += t.amount
        else:
            tout += t.amount
        rows.append({
            "transaction_date": str(t.transaction_date),
            "direction": t.direction,
            "category": t.category,
            "description": t.description,
            "amount": t.amount,
            "balance_after": t.balance_after,
        })
    return {
        "title": "Rekap Kas",
        "columns": _cols(
            ("transaction_date", "Tanggal"), ("direction", "Arah"),
            ("category", "Kategori"), ("description", "Keterangan"),
            ("amount", "Nominal"), ("balance_after", "Saldo"),
        ),
        "rows": rows,
        "summary": {"Total Masuk": tin, "Total Keluar": tout, "Saldo Akhir": current_balance(db)},
    }


def _in_range(d, start, end):
    if d is None:
        return False
    if hasattr(d, "date"):
        d = d.date()
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def _shu_pct(db: Session) -> dict:
    """Persentase alokasi SHU dari settings (default bila kosong)."""
    defaults = {
        "shu_cadangan": 25, "shu_jasa_modal": 20, "shu_jasa_usaha": 25,
        "shu_pengurus": 10, "shu_dana_sosial": 10, "shu_pendidikan": 10,
    }
    out = {}
    for key, dflt in defaults.items():
        s = db.get(Setting, key)
        try:
            out[key] = float(s.value) if s else dflt
        except (TypeError, ValueError):
            out[key] = dflt
    return out


def _shu_surplus(db: Session, start, end) -> dict:
    interest = sum(p.interest_component for p in db.query(Payment).all() if _in_range(p.payment_date, start, end))
    penalty = sum(p.penalty_component for p in db.query(Payment).all() if _in_range(p.payment_date, start, end))
    fees = sum(l.total_fees for l in db.query(Loan).all() if _in_range(l.disbursement_date, start, end))
    operational = sum(
        t.amount for t in db.query(CashTransaction).all()
        if t.direction == "out" and t.category == "operasional" and _in_range(t.transaction_date, start, end)
    )
    shu = interest + penalty + fees - operational
    return {"interest": interest, "penalty": penalty, "fees": fees, "operational": operational, "shu": shu}


def report_shu(db: Session, start: date | None, end: date | None) -> dict:
    """SHU: hitung surplus lalu alokasikan sesuai persentase koperasi."""
    s = _shu_surplus(db, start, end)
    shu = s["shu"]
    pct = _shu_pct(db)

    rows = [
        {"item": "Pendapatan Bunga", "amount": s["interest"]},
        {"item": "Pendapatan Denda", "amount": s["penalty"]},
        {"item": "Pendapatan Biaya (admin + provisi + form)", "amount": s["fees"]},
        {"item": "Beban Operasional", "amount": -s["operational"]},
        {"item": "SISA HASIL USAHA (SHU)", "amount": shu},
    ]
    # Alokasi SHU
    alloc_labels = {
        "shu_cadangan": "Cadangan", "shu_jasa_modal": "Jasa Modal (Simpanan)",
        "shu_jasa_usaha": "Jasa Usaha (Partisipasi)", "shu_pengurus": "Pengurus & Pengawas",
        "shu_dana_sosial": "Dana Sosial", "shu_pendidikan": "Dana Pendidikan",
    }
    for key, label in alloc_labels.items():
        rows.append({"item": f"  → Alokasi {label} ({pct[key]:g}%)", "amount": int(round(shu * pct[key] / 100))})

    return {
        "title": "Laporan SHU (Sisa Hasil Usaha)",
        "columns": _cols(("item", "Komponen"), ("amount", "Jumlah")),
        "rows": rows,
        "summary": {"SHU Periode": shu},
    }


def report_shu_members(db: Session, start: date | None, end: date | None) -> dict:
    """Distribusi SHU per anggota: jasa modal (∝ simpanan) + jasa usaha (∝ bunga dibayar)."""
    s = _shu_surplus(db, start, end)
    pct = _shu_pct(db)
    shu = s["shu"]
    pool_modal = shu * pct["shu_jasa_modal"] / 100
    pool_usaha = shu * pct["shu_jasa_usaha"] / 100

    members = db.query(Member).all()
    # simpanan net per anggota
    simpanan = {m.id: 0 for m in members}
    for sv in db.query(Saving).all():
        simpanan[sv.member_id] = simpanan.get(sv.member_id, 0) + (sv.amount if sv.transaction_type == "setor" else -sv.amount)
    # partisipasi = bunga dibayar dalam periode per anggota
    partisipasi = {m.id: 0 for m in members}
    for p in db.query(Payment).all():
        if _in_range(p.payment_date, start, end):
            partisipasi[p.member_id] = partisipasi.get(p.member_id, 0) + p.interest_component

    total_simpanan = sum(max(v, 0) for v in simpanan.values()) or 1
    total_partisipasi = sum(partisipasi.values()) or 1

    rows, tot = [], 0
    for m in members:
        jm = int(round(pool_modal * max(simpanan.get(m.id, 0), 0) / total_simpanan))
        ju = int(round(pool_usaha * partisipasi.get(m.id, 0) / total_partisipasi))
        total = jm + ju
        tot += total
        rows.append({
            "member_name": m.full_name,
            "simpanan": max(simpanan.get(m.id, 0), 0),
            "jasa_modal": jm,
            "partisipasi": partisipasi.get(m.id, 0),
            "jasa_usaha": ju,
            "total_shu": total,
        })
    return {
        "title": "Distribusi SHU per Anggota",
        "columns": _cols(
            ("member_name", "Nama"), ("simpanan", "Simpanan"),
            ("jasa_modal", "Jasa Modal"), ("partisipasi", "Partisipasi (Bunga)"),
            ("jasa_usaha", "Jasa Usaha"), ("total_shu", "Total SHU"),
        ),
        "rows": rows,
        "summary": {"SHU Dibagikan ke Anggota": tot, "SHU Periode": shu},
    }


REPORTS = {
    "loans": report_loans,
    "payments": report_payments,
    "savings": report_savings,
    "arrears": report_arrears,
    "cash": report_cash,
    "shu": report_shu,
    "shu_members": report_shu_members,
}
