// Cetak kwitansi & share WhatsApp. Mencetak lewat window baru agar terisolasi
// dari styling aplikasi (mendukung thermal 58mm maupun A4).

function rp(v) {
  return 'Rp ' + Number(v || 0).toLocaleString('id-ID')
}

function receiptHtml(r, size) {
  const width = size === '58mm' ? '58mm' : '210mm'
  const pad = size === '58mm' ? '4mm' : '18mm'
  const font = size === '58mm' ? '11px' : '13px'
  const rows = [
    ['No. Kwitansi', r.payment_number],
    ['Tanggal', r.payment_date],
    ['Anggota', `${r.member_name} (${r.member_number})`],
    ['Pinjaman', r.loan_number],
    ['Angsuran Pokok', rp(r.principal_component)],
    ['Angsuran Bunga', rp(r.interest_component)],
    ['Denda', rp(r.penalty_component)],
    ['Total Diterima', rp(r.total_received)],
    ['Metode', r.payment_method],
    ['Sisa Tagihan', rp(r.remaining_balance)],
  ]
  return `<!doctype html><html><head><meta charset="utf-8"><title>${r.payment_number}</title>
  <style>
    @page { size: ${width} auto; margin: 0; }
    body { font-family: 'Courier New', monospace; font-size: ${font}; width: ${width}; padding: ${pad}; margin: 0; color:#000; }
    h2 { text-align:center; font-size: ${size === '58mm' ? '13px' : '18px'}; margin: 0 0 2px; }
    .center { text-align:center; }
    hr { border:none; border-top:1px dashed #000; margin:6px 0; }
    table { width:100%; border-collapse:collapse; }
    td { padding:2px 0; vertical-align:top; }
    td.r { text-align:right; font-weight:bold; }
    .total td { border-top:1px solid #000; padding-top:4px; font-weight:bold; }
    .sign { margin-top: ${size === '58mm' ? '24px' : '40px'}; text-align:right; }
  </style></head><body>
    <h2>${r.coop_name}</h2>
    <div class="center">KWITANSI PEMBAYARAN</div>
    <hr/>
    <table>
      ${rows
        .map(
          ([k, v], i) =>
            `<tr class="${k === 'Total Diterima' ? 'total' : ''}"><td>${k}</td><td class="r">${v}</td></tr>`
        )
        .join('')}
    </table>
    <hr/>
    <div class="sign">Petugas,<br/><br/><br/>( ${r.officer_name} )</div>
  </body></html>`
}

export function useReceipt() {
  function printReceipt(r, size = '58mm') {
    const w = window.open('', '_blank', 'width=420,height=640')
    if (!w) return
    w.document.write(receiptHtml(r, size))
    w.document.close()
    w.focus()
    setTimeout(() => {
      w.print()
    }, 250)
  }

  function shareWhatsApp(r) {
    const rawText = `KWITANSI PEMBAYARAN ANGSURAN

Koperasi: ${r.coop_name}

No. Kwitansi : ${r.payment_number}
Nama Anggota : ${r.member_name}
No. Pinjaman : ${r.loan_number}

Total Pembayaran : ${rp(r.total_received)}
Sisa Tagihan : ${rp(r.remaining_balance)}

Terima kasih atas pembayaran Anda.
Simpan pesan ini sebagai bukti pembayaran.`
    const text = encodeURIComponent(rawText)
    const phone = (r.member_phone || '').replace(/[^0-9]/g, '')
    const base = phone
      ? `https://wa.me/${phone.startsWith('0') ? '62' + phone.slice(1) : phone}`
      : 'https://wa.me/'
    window.open(`${base}?text=${text}`, '_blank')
  }

  return { printReceipt, shareWhatsApp }
}
