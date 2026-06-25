<script setup>
import { ref, reactive, onMounted } from 'vue'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import { useCurrency } from '../../composables/useCurrency'
import { useDate } from '../../composables/useDate'
import CurrencyInput from '../../components/ui/CurrencyInput.vue'

const ui = useUiStore()
const { rp } = useCurrency()
const { fmtDate } = useDate()

const members = ref([])
const balance = ref({ pokok: 0, wajib: 0, sukarela: 0, total: 0 })
const transactions = ref([])

const form = reactive({
  member_id: '',
  savings_type: 'wajib',
  transaction_type: 'setor',
  amount: 0,
})

async function loadMembers() {
  const { data } = await client.get('/members', { params: { page_size: 100 } })
  members.value = data.items
}

async function refresh() {
  if (!form.member_id) return
  const [bal, list] = await Promise.all([
    client.get('/savings/balance', { params: { member_id: form.member_id } }),
    client.get('/savings', { params: { member_id: form.member_id } }),
  ])
  balance.value = bal.data
  transactions.value = list.data
}

async function submit() {
  if (!form.member_id || form.amount <= 0) {
    ui.notify('Pilih anggota & isi nominal', 'error')
    return
  }
  try {
    await client.post('/savings', { ...form })
    ui.notify('Transaksi simpanan tercatat')
    form.amount = 0
    await refresh()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mencatat simpanan', 'error')
  }
}

onMounted(loadMembers)
</script>

<template>
  <div>
    <h1>Simpanan</h1>
    <p class="sub">Simpanan Pokok, Wajib, dan Sukarela</p>

    <div class="grid">
      <section class="card">
        <h2>Transaksi Simpanan</h2>
        <label>Anggota
          <select v-model="form.member_id" @change="refresh">
            <option value="" disabled>— pilih anggota —</option>
            <option v-for="m in members" :key="m.id" :value="m.id">
              {{ m.member_number }} — {{ m.full_name }}
            </option>
          </select>
        </label>
        <div class="row">
          <label>Jenis
            <select v-model="form.savings_type">
              <option value="pokok">Pokok</option>
              <option value="wajib">Wajib</option>
              <option value="sukarela">Sukarela</option>
            </select>
          </label>
          <label>Transaksi
            <select v-model="form.transaction_type">
              <option value="setor">Setor</option>
              <option value="tarik">Tarik</option>
            </select>
          </label>
        </div>
        <label>Nominal (Rp)
          <CurrencyInput v-model="form.amount" />
        </label>
        <button class="btn" @click="submit">Catat Transaksi</button>
      </section>

      <section class="card">
        <h2>Saldo Simpanan</h2>
        <div v-if="form.member_id" class="balances">
          <div class="bal"><span>Pokok</span><strong>{{ rp(balance.pokok) }}</strong></div>
          <div class="bal"><span>Wajib</span><strong>{{ rp(balance.wajib) }}</strong></div>
          <div class="bal"><span>Sukarela</span><strong>{{ rp(balance.sukarela) }}</strong></div>
          <div class="bal total"><span>Total</span><strong>{{ rp(balance.total) }}</strong></div>
        </div>
        <p v-else class="muted">Pilih anggota untuk melihat saldo.</p>

        <h3 v-if="transactions.length">Mutasi Terakhir</h3>
        <table v-if="transactions.length" class="tbl">
          <thead><tr><th>Tgl</th><th>Jenis</th><th>Tipe</th><th class="num">Nominal</th><th class="num">Saldo</th></tr></thead>
          <tbody>
            <tr v-for="t in transactions" :key="t.id">
              <td>{{ fmtDate(t.transaction_date) }}</td>
              <td>{{ t.savings_type }}</td>
              <td><span class="tag" :class="t.transaction_type">{{ t.transaction_type }}</span></td>
              <td class="num">{{ rp(t.amount) }}</td>
              <td class="num">{{ rp(t.balance_after) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 20px; color: var(--muted); font-size: 0.85rem; }
.grid { display: grid; grid-template-columns: 360px 1fr; gap: 20px; align-items: start; }
@media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
h2 { margin: 0 0 14px; font-size: 1rem; color: var(--primary-dark); }
h3 { font-size: 0.85rem; color: var(--muted); margin: 18px 0 8px; }
label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 12px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
input, select { width: 100%; margin-top: 4px; padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.92rem; font-family: inherit; }
input:focus, select:focus { outline: none; border-color: var(--primary); }
.btn { padding: 11px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; width: 100%; }
.btn:hover { background: var(--primary-dark); }
.balances { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 12px; }
.bal { background: #f8fafc; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; }
.bal span { font-size: 0.75rem; color: var(--muted); }
.bal strong { font-size: 1.05rem; }
.bal.total { background: var(--primary); color: #fff; grid-column: 1 / -1; }
.bal.total span { color: rgba(255,255,255,0.85); }
.muted { color: var(--muted); font-size: 0.85rem; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.tbl th, .tbl td { padding: 8px 10px; border: 1px solid var(--border); text-align: left; }
.tbl th { background: #f1f5f9; font-weight: 600; }
.num { text-align: right; }
.tag { padding: 2px 8px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; }
.tag.setor { background: #dcfce7; color: #166534; }
.tag.tarik { background: #fee2e2; color: #991b1b; }
</style>
