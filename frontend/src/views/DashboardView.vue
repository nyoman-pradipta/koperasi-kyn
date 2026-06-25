<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../api/client'
import { useCurrency } from '../composables/useCurrency'
import { useDate } from '../composables/useDate'
import BarChart from '../components/dashboard/BarChart.vue'

const router = useRouter()
const { rp } = useCurrency()
const { fmtDate } = useDate()

const summary = ref(null)
const chart = ref({ labels: [], masuk: [], keluar: [] })
const reminders = ref([])
const activities = ref([])

async function load() {
  const [s, c, r, a] = await Promise.all([
    client.get('/dashboard/summary'),
    client.get('/dashboard/chart'),
    client.get('/dashboard/reminders', { params: { days_ahead: 30 } }),
    client.get('/dashboard/activities'),
  ])
  summary.value = s.data
  chart.value = c.data
  reminders.value = r.data
  activities.value = a.data
}

const stats = () => [
  { label: 'Total Anggota', value: summary.value.total_members, icon: '👥', fmt: false },
  { label: 'Pinjaman Aktif', value: summary.value.active_loans_count, icon: '💳', fmt: false },
  { label: 'Outstanding', value: summary.value.active_loans_outstanding, icon: '📄', fmt: true },
  { label: 'Total Simpanan', value: summary.value.total_savings, icon: '🏦', fmt: true },
  { label: 'Saldo Kas', value: summary.value.cash_balance, icon: '💰', fmt: true },
  { label: 'Tunggakan', value: summary.value.arrears, icon: '⚠️', fmt: true, warn: true },
  { label: 'Pencairan Bln Ini', value: summary.value.disbursed_this_month, icon: '📤', fmt: true },
  { label: 'Angsuran Masuk Bln Ini', value: summary.value.payments_this_month, icon: '📥', fmt: true },
]

const actions = [
  { label: '+ Anggota', to: '/anggota' },
  { label: '+ Pengajuan', to: '/pengajuan' },
  { label: 'Input Pembayaran', to: '/pembayaran' },
  { label: 'Cetak Laporan', to: '/laporan' },
]

onMounted(load)
</script>

<template>
  <div v-if="summary">
    <h1>Dashboard</h1>
    <p class="sub">Ringkasan operasional koperasi</p>

    <div class="stats">
      <div v-for="s in stats()" :key="s.label" class="stat" :class="{ warn: s.warn && s.value > 0 }">
        <div class="stat-icon">{{ s.icon }}</div>
        <div>
          <div class="stat-value">{{ s.fmt ? rp(s.value) : s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="quick">
      <button v-for="a in actions" :key="a.to" class="quick-btn" @click="router.push(a.to)">
        {{ a.label }}
      </button>
    </div>

    <div class="grid">
      <section class="card">
        <h2>Grafik Transaksi Kas (6 Bulan)</h2>
        <BarChart :labels="chart.labels" :masuk="chart.masuk" :keluar="chart.keluar" />
      </section>

      <section class="card">
        <h2>Reminder Jatuh Tempo (30 hari)</h2>
        <ul v-if="reminders.length" class="list">
          <li v-for="(r, i) in reminders" :key="i" :class="{ overdue: r.overdue }">
            <div>
              <strong>{{ r.member_name }}</strong> · {{ r.loan_number }}
              <div class="meta">Angsuran ke-{{ r.installment_no }} · {{ fmtDate(r.due_date) }}
                <span v-if="r.overdue" class="tag-late">TELAT</span>
              </div>
            </div>
            <strong>{{ rp(r.amount) }}</strong>
          </li>
        </ul>
        <p v-else class="muted">Tidak ada jatuh tempo dalam 30 hari.</p>
      </section>
    </div>

    <section class="card">
      <h2>Aktivitas Terbaru</h2>
      <ul v-if="activities.length" class="list">
        <li v-for="(a, i) in activities" :key="i">
          <div>
            <span class="dot" :class="a.direction"></span>{{ a.description }}
            <div class="meta">{{ fmtDate(a.date) }} · {{ a.category }}</div>
          </div>
          <strong :class="a.direction">{{ a.direction === 'in' ? '+' : '−' }} {{ rp(a.amount) }}</strong>
        </li>
      </ul>
      <p v-else class="muted">Belum ada aktivitas.</p>
    </section>
  </div>
  <div v-else class="loading">Memuat dashboard…</div>
</template>

<style scoped>
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 20px; color: var(--muted); font-size: 0.85rem; }
h2 { font-size: 1rem; color: var(--primary-dark); margin: 0 0 14px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.stat { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 12px; }
.stat.warn { border-color: #fca5a5; background: #fef2f2; }
.stat-icon { font-size: 1.6rem; background: #eef6f0; border-radius: 10px; padding: 7px 9px; }
.stat-value { font-size: 1.25rem; font-weight: 700; }
.stat-label { font-size: 0.8rem; color: var(--muted); }
.quick { display: flex; gap: 10px; flex-wrap: wrap; margin: 18px 0; }
.quick-btn { padding: 10px 16px; background: #fff; border: 1px solid var(--border); border-radius: 10px; font-weight: 600; cursor: pointer; color: var(--primary-dark); }
.quick-btn:hover { border-color: var(--primary); background: #f8faf9; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
@media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.list li { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-size: 0.88rem; }
.list li.overdue { color: #b91c1c; }
.meta { font-size: 0.76rem; color: var(--muted); margin-top: 2px; }
.tag-late { background: #fee2e2; color: #991b1b; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: 0.68rem; }
.muted { color: var(--muted); font-size: 0.85rem; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.dot.in { background: #16a34a; }
.dot.out { background: #d97706; }
.in { color: #166534; }
.out { color: #b91c1c; }
.loading { color: var(--muted); padding: 40px; text-align: center; }
</style>
