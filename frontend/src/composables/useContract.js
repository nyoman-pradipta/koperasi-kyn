// Cetak Surat Perjanjian Kredit (kontrak) ukuran A4 di jendela terpisah.

import { fmtDateLong, fmtDate } from './useDate'

function rp(v) {
  return 'Rp ' + Number(v || 0).toLocaleString('id-ID')
}

function contractHtml(loan, schedule, coop) {
  const rows = (schedule || [])
    .map(
      (r) =>
        `<tr><td style="text-align:center">${r.installment_no}</td><td>${fmtDate(r.due_date)}</td>` +
        `<td style="text-align:right">${rp(r.principal_due)}</td>` +
        `<td style="text-align:right">${rp(r.interest_due)}</td>` +
        `<td style="text-align:right">${rp(r.total_due)}</td></tr>`
    )
    .join('')

  const today = fmtDateLong(new Date().toISOString())

  return `<!doctype html><html><head><meta charset="utf-8"><title>Kontrak ${loan.loan_number}</title>
  <style>
    @page { size: A4; margin: 18mm; }
    body { font-family: 'Times New Roman', serif; font-size: 12pt; color:#000; line-height:1.5; }
    h1 { text-align:center; font-size: 15pt; margin: 0; }
    h2 { text-align:center; font-size: 12pt; font-weight:normal; margin: 0 0 4px; }
    .sub { text-align:center; font-size: 10pt; color:#333; border-bottom: 2px solid #000; padding-bottom: 8px; margin-bottom: 16px; }
    table.det { width:100%; border-collapse:collapse; margin: 8px 0; }
    table.det td { padding: 3px 6px; vertical-align: top; }
    table.sched { width:100%; border-collapse:collapse; margin-top: 8px; font-size: 10pt; }
    table.sched th, table.sched td { border:1px solid #000; padding: 4px 6px; }
    table.sched th { background:#eee; }
    .sign { display:flex; justify-content: space-between; margin-top: 40px; text-align:center; }
    .sign div { width: 45%; }
    .gap { height: 60px; }
  </style></head><body>
    <h1>${coop.coop_name || 'KOPERASI'}</h1>
    <h2>${coop.coop_address || ''}</h2>
    <div class="sub">SURAT PERJANJIAN KREDIT — No. ${loan.loan_number}</div>

    <p>Pada hari ini, ${today}, telah disepakati perjanjian kredit antara koperasi
    dengan anggota berikut:</p>

    <table class="det">
      <tr><td style="width:32%">Nama Anggota</td><td>: ${loan.member_name}</td></tr>
      <tr><td>Jumlah Pinjaman</td><td>: ${rp(loan.principal_amount)}</td></tr>
      <tr><td>Jenis & Suku Bunga</td><td>: ${loan.interest_type} ${loan.interest_rate}% per bulan</td></tr>
      <tr><td>Jangka Waktu</td><td>: ${loan.tenor} bulan</td></tr>
      <tr><td>Total Biaya Potongan</td><td>: ${rp(loan.total_fees)}</td></tr>
      <tr><td>Dana Bersih Diterima</td><td>: ${rp(loan.net_received)}</td></tr>
      <tr><td>Total Kewajiban</td><td>: ${rp(loan.total_payable)}</td></tr>
      <tr><td>Tanggal Pencairan</td><td>: ${loan.disbursement_date ? fmtDate(loan.disbursement_date) : '-'}</td></tr>
    </table>

    <p>Anggota wajib membayar angsuran sesuai jadwal berikut, dan tunduk pada
    ketentuan denda keterlambatan yang berlaku di koperasi.</p>

    <table class="sched">
      <thead><tr><th>Bln</th><th>Jatuh Tempo</th><th>Pokok</th><th>Bunga</th><th>Total</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>

    <div class="sign">
      <div>Pihak Koperasi,<div class="gap"></div>( ............................ )</div>
      <div>Anggota Peminjam,<div class="gap"></div>( ${loan.member_name} )</div>
    </div>
  </body></html>`
}

export function useContract() {
  function printContract(loan, schedule, coop) {
    const w = window.open('', '_blank', 'width=800,height=900')
    if (!w) return
    w.document.write(contractHtml(loan, schedule, coop))
    w.document.close()
    w.focus()
    setTimeout(() => w.print(), 300)
  }
  return { printContract }
}
