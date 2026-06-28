/**
 * useDate — Utilitas pemformatan tanggal & waktu terpusat.
 *
 * Aturan:
 *  - Database menyimpan semua timestamp dalam UTC.
 *  - Tampilan selalu dikonversi ke WIB (Asia/Jakarta, UTC+7).
 *  - Format tanggal : "24 Jun 2026"
 *  - Format date+time: "24 Jun 2026, 23:16:16 WIB"
 */

const TZ = 'Asia/Jakarta'

const LOCALE = 'id-ID'

/** 
 * Helper untuk mengonversi string datetime mentah (naive) dari backend
 * yang tidak memiliki informasi zona waktu menjadi UTC eksplisit (tambah 'Z').
 */
function parseUTC(value) {
  if (!value) return new Date()
  
  if (typeof value === 'string') {
    // Jika hanya YYYY-MM-DD, tambahkan T00:00:00Z
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return new Date(value + 'T00:00:00Z')
    }
    // Jika tidak ada Z atau offset timezone, asumsikan dari backend adalah UTC
    if (!/(Z|[+-]\d{2}:\d{2})$/.test(value)) {
      return new Date(value + 'Z')
    }
  }
  return new Date(value)
}

/** Format hanya tanggal: "24 Jun 2026" (Diubah ke format Date+Time berdasarkan request) */
export function fmtDate(value) {
  return fmtDateTime(value)
}

/** Format tanggal + waktu: "24 Jun 2026, 23:16 WIB" */
export function fmtDateTime(value) {
  if (!value) return '—'
  const d = parseUTC(value)
  if (isNaN(d)) return String(value)
  
  // Jika waktu aslinya adalah tepat tengah malam (00:00:00 UTC)
  // Sembunyikan jamnya untuk mencegah kebingungan (07:00 WIB).
  const isDateOnly = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
  const hasZeroTime = typeof value === 'string' && value.includes('T00:00:00');
    
  if (isDateOnly || hasZeroTime) {
    return d.toLocaleDateString(LOCALE, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: TZ,
    })
  }

  const part = d.toLocaleString(LOCALE, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: TZ,
  })
  return part + ' WIB'
}

/** Format tanggal panjang: "24 Juni 2026" */
export function fmtDateLong(value) {
  if (!value) return '—'
  const d = parseUTC(value)
  if (isNaN(d)) return String(value)
  return d.toLocaleDateString(LOCALE, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: TZ,
  })
}

/**
 * Composable untuk dipakai di dalam <script setup>.
 *
 * Contoh:
 *   import { useDate } from '@/composables/useDate'
 *   const { fmtDate, fmtDateTime } = useDate()
 */
export function useDate() {
  return { fmtDate, fmtDateTime, fmtDateLong }
}
