<script setup>
import { ref, reactive } from 'vue'
import client from '../api/client'
import CurrencyInput from './ui/CurrencyInput.vue'

// --- State form (default mengikuti referensi) ---
const form = reactive({
  loan_amount: 20000000,
  monthly_rate_pct: 2.5,
  tenor: 6,
  admin_pct: 4.0,
  provisi_pct: 1.0,
  form_fee: 200000,
  interest_type: 'flat',
})

const result = ref(null)
const loading = ref(false)
const error = ref('')

// --- Helper format Rupiah ---
function rp(value) {
  if (value === null || value === undefined) return '-'
  return 'Rp ' + Number(value).toLocaleString('id-ID')
}

function rpExact(value) {
  // tampilkan dengan 2 desimal (untuk angka pasti sebelum pembulatan)
  return 'Rp ' + Number(value).toLocaleString('id-ID', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function cetakPDF() { window.print() }

// --- Panggil API backend ---
async function hitung() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await client.post('/simulate', form)
    result.value = data
  } catch (e) {
    error.value = 'Gagal menghitung: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="grid">
    <!-- ============ FORM INPUT ============ -->
    <section class="card form-card">
      <h2>Form Pengajuan Kredit</h2>

      <label>
        Jumlah Pinjaman (Rp)
        <CurrencyInput v-model="form.loan_amount" />
      </label>

      <label>
        Suku Bunga / Bulan (%)
        <input type="number" v-model.number="form.monthly_rate_pct" min="0" step="0.1" />
      </label>

      <label>
        Jangka Waktu / Tenor (bulan)
        <input type="number" v-model.number="form.tenor" min="1" step="1" />
      </label>

      <label>
        Tipe Bunga
        <select v-model="form.interest_type">
          <option value="flat">Flat (Tetap)</option>
          <option value="menurun">Menurun (Efektif)</option>
        </select>
      </label>

      <label>
        Biaya Administrasi (%)
        <input type="number" v-model.number="form.admin_pct" min="0" step="0.1" />
      </label>

      <label>
        Biaya Provisi (%)
        <input type="number" v-model.number="form.provisi_pct" min="0" step="0.1" />
      </label>

      <label>
        Biaya Form &amp; Pemeriksaan (Rp, tetap)
        <CurrencyInput v-model="form.form_fee" />
      </label>

      <button class="btn" :disabled="loading" @click="hitung">
        {{ loading ? 'Menghitung…' : 'Hitung Simulasi' }}
      </button>
      <button v-if="result" class="btn btn-pdf" @click="cetakPDF()">
        🖨 Cetak / Simpan PDF
      </button>

      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <!-- ============ HASIL ============ -->
    <section v-if="result" class="card result-card">
      <h2>Hasil Simulasi Kredit</h2>

      <!-- Bagian 1: Parameter Utama -->
      <h3>1. Parameter Utama</h3>
      <table class="tbl">
        <tbody>
          <tr>
            <td>Jumlah Pinjaman</td>
            <td class="num">{{ rp(result.main_parameters.loan_amount) }}</td>
          </tr>
          <tr>
            <td>Suku Bunga (per bulan)</td>
            <td class="num">{{ result.main_parameters.monthly_rate_pct }}% ({{ result.input.interest_type === 'menurun' ? 'Menurun' : 'Flat' }})</td>
          </tr>
          <tr>
            <td>Jangka Waktu (Tenor)</td>
            <td class="num">{{ result.main_parameters.tenor }} bulan</td>
          </tr>
          <tr>
            <td>Angsuran Bunga (per bulan)</td>
            <td class="num">{{ rp(result.main_parameters.monthly_interest) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- Bagian 2: Rincian Angsuran Per Bulan -->
      <h3>2. Rincian Angsuran Per Bulan</h3>
      <p class="note">
        Angsuran pasti per bulan
        {{ rpExact(result.main_parameters.installment_exact) }} —
        dibulatkan ke atas (kelipatan Rp 1.000); bulan terakhir disesuaikan
        agar total tepat.
      </p>
      <table class="tbl striped">
        <thead>
          <tr>
            <th>Bulan ke-</th>
            <th class="num">Angsuran Pokok</th>
            <th class="num">Angsuran Bunga</th>
            <th class="num">Total Angsuran</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in result.schedule" :key="row.month">
            <td>{{ row.month }}</td>
            <td class="num">{{ rp(row.principal) }}</td>
            <td class="num">{{ rp(row.interest) }}</td>
            <td class="num strong">{{ rp(row.total) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="3">Total Keseluruhan Dibayar</td>
            <td class="num strong">{{ rp(result.total_payable) }}</td>
          </tr>
        </tfoot>
      </table>

      <!-- Bagian 3: Biaya-Biaya -->
      <h3>3. Biaya-Biaya (Potongan Awal)</h3>
      <table class="tbl">
        <tbody>
          <tr>
            <td>Biaya Administrasi ({{ result.input.admin_pct }}%)</td>
            <td class="num">{{ rp(result.fees.admin_fee) }}</td>
          </tr>
          <tr>
            <td>Biaya Provisi ({{ result.input.provisi_pct }}%)</td>
            <td class="num">{{ rp(result.fees.provisi_fee) }}</td>
          </tr>
          <tr>
            <td>Biaya Form &amp; Pemeriksaan</td>
            <td class="num">{{ rp(result.fees.form_fee) }}</td>
          </tr>
          <tr class="total-row">
            <td>TOTAL POTONGAN BIAYA</td>
            <td class="num strong">{{ rp(result.fees.total_fees) }}</td>
          </tr>
        </tbody>
      </table>

      <!-- Bagian 4: Pengesahan Dana -->
      <h3>4. Pengesahan Dana</h3>
      <table class="tbl">
        <tbody>
          <tr>
            <td>Jumlah Pinjaman</td>
            <td class="num">{{ rp(result.disbursement.loan_amount) }}</td>
          </tr>
          <tr>
            <td>Total Potongan Biaya</td>
            <td class="num">- {{ rp(result.disbursement.total_fees) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="net-box">
        <span>JUMLAH BERSIH DITERIMA (SISA DANA)</span>
        <strong>{{ rp(result.disbursement.net_received) }}</strong>
      </div>

      <p class="late-fee">
        * Denda keterlambatan sebesar {{ rp(result.late_fee_per_day) }} / Hari
      </p>
    </section>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  align-items: start;
}

@media (max-width: 820px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

h2 {
  margin: 0 0 16px;
  font-size: 1.05rem;
  color: var(--primary-dark);
}

h3 {
  margin: 22px 0 8px;
  font-size: 0.92rem;
  color: var(--primary-dark);
  border-left: 4px solid var(--primary);
  padding-left: 8px;
}

.form-card label {
  display: block;
  font-size: 0.82rem;
  color: var(--muted);
  margin-bottom: 12px;
}

.form-card input,
.form-card select {
  width: 100%;
  margin-top: 4px;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.95rem;
}

.form-card input:focus,
.form-card select:focus {
  outline: none;
  border-color: var(--primary);
}

.btn {
  width: 100%;
  margin-top: 6px;
  padding: 11px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.btn:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  color: #b91c1c;
  font-size: 0.85rem;
  margin-top: 10px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.tbl td,
.tbl th {
  padding: 9px 12px;
  border: 1px solid var(--border);
  text-align: left;
}

.tbl th {
  background: #f1f5f9;
  font-weight: 600;
}

.tbl .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.tbl .strong {
  font-weight: 700;
}

.striped tbody tr:nth-child(even) {
  background: #fafafa;
}

.tbl tfoot td {
  background: #f1f5f9;
  font-weight: 700;
}

.total-row td {
  background: #eef6f0;
  font-weight: 700;
  color: var(--primary-dark);
}

.note {
  font-size: 0.8rem;
  color: var(--muted);
  margin: 0 0 10px;
}

.net-box {
  margin-top: 16px;
  background: var(--primary);
  color: #fff;
  border-radius: 10px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.net-box span {
  font-size: 0.85rem;
  letter-spacing: 0.3px;
}

.net-box strong {
  font-size: 1.35rem;
}

.late-fee {
  margin-top: 14px;
  padding: 10px 12px;
  background: var(--accent);
  border: 1px solid var(--accent-border);
  border-radius: 8px;
  font-size: 0.82rem;
  color: #92400e;
}

.btn-pdf {
  background: #7c3aed;
  margin-top: 8px;
}
.btn-pdf:hover {
  background: #6d28d9;
}

@media print {
  .form-card { display: none !important; }
  .grid { display: block !important; }
  .result-card { border: none; box-shadow: none; padding: 0; }
  h2 { font-size: 1.1rem; }
  h3 { font-size: 0.95rem; }
  .tbl td, .tbl th { padding: 5px 8px; font-size: 0.8rem; }
  .net-box { background: #1a5c2a !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
</style>
