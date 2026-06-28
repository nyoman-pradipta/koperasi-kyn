<script setup>
import { ref, reactive, onMounted } from 'vue'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import { useCurrency } from '../../composables/useCurrency'
import { useDate } from '../../composables/useDate'
import { useReceipt } from '../../composables/useReceipt'
import BaseModal from '../../components/ui/BaseModal.vue'
import CurrencyInput from '../../components/ui/CurrencyInput.vue'

const ui = useUiStore()
const { rp } = useCurrency()
const { fmtDate } = useDate()
const { printReceipt, shareWhatsApp } = useReceipt()

const activeLoans = ref([])
const outstanding = ref(null)
const receipt = ref(null)
const showReceipt = ref(false)

const form = reactive({
  loan_id: '',
  amount: 0,
  penalty: 0,
  payment_method: 'tunai',
})

async function loadLoans() {
  const { data } = await client.get('/loans', { params: { status: 'active', page_size: 100 } })
  activeLoans.value = data.items
}

async function onSelectLoan() {
  outstanding.value = null
  if (!form.loan_id) return
  const { data } = await client.get(`/payments/outstanding/${form.loan_id}`)
  outstanding.value = data
  if (!data.fully_paid) {
    form.amount = data.next_remaining
    form.penalty = data.suggested_penalty
  }
}

async function pay() {
  if (!form.loan_id || form.amount <= 0) {
    ui.notify('Pilih pinjaman & isi nominal', 'error')
    return
  }
  try {
    const { data } = await client.post('/payments', { ...form })
    receipt.value = data
    showReceipt.value = true
    ui.notify('Pembayaran berhasil — kwitansi ' + data.payment_number)
    await onSelectLoan()
    await loadLoans()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Pembayaran gagal', 'error')
  }
}

onMounted(loadLoans)
</script>

<template>
  <div>
    <h1>Pembayaran Angsuran</h1>
    <p class="sub">Catat pembayaran & cetak kwitansi</p>

    <div class="grid">
      <section class="card">
        <h2>Input Pembayaran</h2>
        <label>
          Pinjaman Aktif
          <select v-model="form.loan_id" @change="onSelectLoan">
            <option value="" disabled>— pilih pinjaman —</option>
            <option v-for="l in activeLoans" :key="l.id" :value="l.id">
              {{ l.loan_number }} — {{ l.member_name }}
            </option>
          </select>
        </label>

        <div v-if="outstanding && !outstanding.fully_paid" class="outstanding">
          <div>Angsuran ke-<strong>{{ outstanding.next_installment_no }}</strong>
            (jatuh tempo {{ fmtDate(outstanding.next_due_date) }})</div>
          <div>Sisa angsuran bulan ini: <strong>{{ rp(outstanding.next_remaining) }}</strong></div>
          <div>Total tagihan tersisa: <strong>{{ rp(outstanding.outstanding_total) }}</strong></div>
          <div v-if="outstanding.overdue_days > 0" class="overdue">
            Terlambat {{ outstanding.overdue_days }} hari → saran denda
            {{ rp(outstanding.suggested_penalty) }}
          </div>
        </div>
        <p v-else-if="outstanding && outstanding.fully_paid" class="muted">
          Pinjaman ini sudah lunas.
        </p>

        <label>Nominal Angsuran (Rp)
          <CurrencyInput v-model="form.amount" />
        </label>
        <label>Denda (Rp)
          <CurrencyInput v-model="form.penalty" />
        </label>
        <label>Metode Bayar
          <select v-model="form.payment_method">
            <option value="tunai">Tunai</option>
            <option value="transfer">Transfer</option>
          </select>
        </label>

        <button class="btn" @click="pay">Bayar & Buat Kwitansi</button>
      </section>

      <section class="card info">
        <h2>Petunjuk</h2>
        <ul>
          <li>Pilih pinjaman aktif untuk melihat tagihan & saran denda otomatis.</li>
          <li>Pembayaran dialokasikan ke angsuran tertua lebih dulu (bunga lalu pokok).</li>
          <li>Kwitansi dapat dicetak Thermal 58mm / A4, atau dikirim via WhatsApp.</li>
        </ul>
      </section>
    </div>

    <BaseModal :show="showReceipt" title="Kwitansi Pembayaran" @close="showReceipt = false">
      <div v-if="receipt" class="receipt-preview">
        <div class="rrow"><span>No. Kwitansi</span><b>{{ receipt.payment_number }}</b></div>
        <div class="rrow"><span>Anggota</span><b>{{ receipt.member_name }}</b></div>
        <div class="rrow"><span>Pinjaman</span><b>{{ receipt.loan_number }}</b></div>
        <div class="rrow"><span>Pokok</span><b>{{ rp(receipt.principal_component) }}</b></div>
        <div class="rrow"><span>Bunga</span><b>{{ rp(receipt.interest_component) }}</b></div>
        <div class="rrow"><span>Denda</span><b>{{ rp(receipt.penalty_component) }}</b></div>
        <div class="rrow total"><span>Total Diterima</span><b>{{ rp(receipt.total_received) }}</b></div>
        <div class="rrow"><span>Sisa Tagihan</span><b>{{ rp(receipt.remaining_balance) }}</b></div>
      </div>
      <template #footer>
        <button class="btn ghost" @click="printReceipt(receipt, '58mm')">🖨 Thermal 58mm</button>
        <button class="btn ghost" @click="printReceipt(receipt, 'a4')">🖨 A4 / PDF</button>
        <button class="btn" :disabled="!receipt.member_phone" @click="shareWhatsApp(receipt)">📲 WhatsApp</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 20px; color: var(--muted); font-size: 0.85rem; }
.grid { display: grid; grid-template-columns: 400px 1fr; gap: 20px; align-items: start; }
@media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
h2 { margin: 0 0 14px; font-size: 1rem; color: var(--primary-dark); }
label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 12px; }
input, select { width: 100%; margin-top: 4px; padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.92rem; font-family: inherit; }
input:focus, select:focus { outline: none; border-color: var(--primary); }
.btn { padding: 11px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.outstanding { background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px; font-size: 0.85rem; margin-bottom: 12px; display: grid; gap: 4px; }
.overdue { color: #b91c1c; font-weight: 600; }
.muted { color: var(--muted); font-size: 0.85rem; margin-bottom: 12px; }
.info ul { margin: 0; padding-left: 18px; color: var(--muted); font-size: 0.85rem; line-height: 1.7; }
.receipt-preview { display: grid; gap: 8px; }
.rrow { display: flex; justify-content: space-between; font-size: 0.9rem; border-bottom: 1px dashed var(--border); padding-bottom: 6px; }
.rrow.total { border-bottom: 2px solid var(--primary); color: var(--primary-dark); }
</style>
