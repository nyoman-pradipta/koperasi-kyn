<script setup>
import { ref, reactive, onMounted } from 'vue'
import client from '../api/client'
import { useUiStore } from '../stores/ui'
import { useCurrency } from '../composables/useCurrency'
import { useDate } from '../composables/useDate'
import CurrencyInput from '../components/ui/CurrencyInput.vue'
import BaseModal from '../components/ui/BaseModal.vue'

const ui = useUiStore()
const { rp } = useCurrency()
const { fmtDate } = useDate()

const summary = ref({ balance: 0, total_in: 0, total_out: 0, today_in: 0, today_out: 0 })
const rows = ref([])
const showModal = ref(false)

const form = reactive({ direction: 'in', amount: 0, category: 'operasional', description: '' })

async function load() {
  const [s, list] = await Promise.all([
    client.get('/cash/summary'),
    client.get('/cash'),
  ])
  summary.value = s.data
  rows.value = list.data
}

async function submit() {
  if (form.amount <= 0) {
    ui.notify('Isi nominal', 'error')
    return
  }
  try {
    await client.post('/cash', { ...form })
    ui.notify('Transaksi kas tercatat')
    showModal.value = false
    form.amount = 0
    form.description = ''
    await load()
  } catch (e) {
    ui.notify('Gagal mencatat kas', 'error')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Kas &amp; Keuangan</h1>
        <p class="sub">Mutasi kas masuk &amp; keluar</p>
      </div>
      <button class="btn" @click="showModal = true">+ Transaksi Manual</button>
    </div>

    <div class="cards">
      <div class="stat balance"><span>Saldo Kas</span><strong>{{ rp(summary.balance) }}</strong></div>
      <div class="stat"><span>Total Masuk</span><strong class="in">{{ rp(summary.total_in) }}</strong></div>
      <div class="stat"><span>Total Keluar</span><strong class="out">{{ rp(summary.total_out) }}</strong></div>
      <div class="stat"><span>Masuk Hari Ini</span><strong class="in">{{ rp(summary.today_in) }}</strong></div>
      <div class="stat"><span>Keluar Hari Ini</span><strong class="out">{{ rp(summary.today_out) }}</strong></div>
    </div>

    <div class="card">
      <table class="tbl">
        <thead>
          <tr><th>Tanggal</th><th>Arah</th><th>Kategori</th><th>Keterangan</th><th class="num">Nominal</th><th class="num">Saldo</th></tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0"><td colspan="6" class="empty">Belum ada transaksi kas.</td></tr>
          <tr v-for="t in rows" :key="t.id">
            <td>{{ fmtDate(t.transaction_date) }}</td>
            <td><span class="tag" :class="t.direction">{{ t.direction === 'in' ? 'Masuk' : 'Keluar' }}</span></td>
            <td>{{ t.category }}</td>
            <td>{{ t.description }}</td>
            <td class="num" :class="t.direction">{{ t.direction === 'in' ? '+' : '−' }} {{ rp(t.amount) }}</td>
            <td class="num">{{ rp(t.balance_after) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal :show="showModal" title="Transaksi Kas Manual" @close="showModal = false">
      <div class="form">
        <label>Arah
          <select v-model="form.direction">
            <option value="in">Kas Masuk</option>
            <option value="out">Kas Keluar</option>
          </select>
        </label>
        <label>Kategori
          <input v-model="form.category" placeholder="operasional / lainnya" />
        </label>
        <label>Nominal (Rp)
          <CurrencyInput v-model="form.amount" />
        </label>
        <label>Keterangan
          <input v-model="form.description" />
        </label>
      </div>
      <template #footer>
        <button class="btn ghost" @click="showModal = false">Batal</button>
        <button class="btn" @click="submit">Simpan</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.85rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 18px; }
.stat { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 4px; }
.stat span { font-size: 0.78rem; color: var(--muted); }
.stat strong { font-size: 1.2rem; }
.stat.balance { background: var(--primary); color: #fff; }
.stat.balance span { color: rgba(255,255,255,0.85); }
.in { color: #166534; }
.out { color: #b91c1c; }
.stat.balance strong { color: #fff; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.tbl th, .tbl td { padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; }
.tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.num { text-align: right; }
.empty { text-align: center; color: var(--muted); padding: 26px; }
.tag { padding: 2px 9px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.tag.in { background: #dcfce7; color: #166534; }
.tag.out { background: #fee2e2; color: #991b1b; }
.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.form { display: grid; gap: 12px; }
.form label { font-size: 0.8rem; color: var(--muted); }
.form input, .form select { width: 100%; margin-top: 4px; padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; }
</style>
