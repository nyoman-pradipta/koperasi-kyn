// Format angka ke Rupiah. Dipakai lintas modul.
export function useCurrency() {
  function rp(value) {
    if (value === null || value === undefined || value === '') return '-'
    return 'Rp ' + Number(value).toLocaleString('id-ID')
  }

  function rpExact(value) {
    return 'Rp ' + Number(value).toLocaleString('id-ID', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  return { rp, rpExact }
}
