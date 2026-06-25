"""Generator nomor otomatis berbasis tabel `number_sequences`.

Format: PREFIX-TAHUN-NNNN, mis. AGT-2026-0001 / PJM-2026-0007 / KWT-2026-0012.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from ..models import NumberSequence


def next_number(db: Session, name: str, pad: int = 4) -> str:
    """Naikkan counter `name` lalu kembalikan nomor terformat.

    Caller bertanggung jawab melakukan commit (biasanya bersama insert
    entitasnya, agar nomor & data tersimpan atomik).
    """
    seq = db.query(NumberSequence).filter(NumberSequence.name == name).first()
    if seq is None:
        # fallback bila seed belum membuatnya
        seq = NumberSequence(name=name, prefix=name[:3].upper(), current_value=0)
        db.add(seq)
        db.flush()

    seq.current_value += 1
    year = datetime.now().year
    return f"{seq.prefix}-{year}-{seq.current_value:0{pad}d}"
