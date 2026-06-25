<script setup>
import { ref, reactive } from 'vue'
import client from '../api/client'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()

const TYPES = [
  { key: 'loans', label: 'Laporan Pinjaman' },
  { key: 'payments', label: 'Laporan Pembayaran' },
  { key: 'savings', label: 'Laporan Simpanan' },
  { key: 'arrears', label: 'Laporan Tunggakan' },
  { key: 'shu', label: 'Laporan SHU' },
  { key: 'shu_members', label: 'Distribusi SHU per Anggota' },
  { key: 'cash', label: 'Rekap Kas' },
]

const filter = reactive({ type: 'loans', start: '', end: '' })
const report = ref(null)
const loading = ref(false)

function setPreset(p) {
  const now = new Date()
  if (p === 'month') {
    filter.start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    filter.end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  } else if (p === 'year') {
    filter.start = `${now.getFullYear()}-01-01`
    filter.end = `${now.getFullYear()}-12-31`
  } else {
    filter.start = ''
    filter.end = ''
  }
  load()
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get(`/reports/${filter.type}`, {
      params: { start: filter.start || undefined, end: filter.end || undefined },
    })
    report.value = data
  } catch (e) {
    ui.notify('Gagal memuat laporan', 'error')
  } finally {
    loading.value = false
  }
}

function fmt(v) {
  return typeof v === 'number' ? v.toLocaleString('id-ID') : v
}

async function exportExcel() {
  try {
    const res = await client.get(`/reports/${filter.type}/export`, {
      params: { start: filter.start || undefined, end: filter.end || undefined },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `laporan_${filter.type}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    ui.notify('Gagal mengekspor Excel', 'error')
  }
}

function printReport() {
  window.print()
}

load()
</script>

<template>
  <div>
    <div class="page-head no-print">
      <div>
        <h1>Laporan</h1>
        <p class="sub">Pilih jenis laporan & periode</p>
      </div>
    </div>

    <div class="toolbar no-print">
      <select v-model="filter.type" @change="load">
        <option v-for="t in TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
      </select>
      <input type="date" v-model="filter.start" @change="load" />
      <span>s/d</span>
      <input type="date" v-model="filter.end" @change="load" />
      <button class="btn ghost" @click="setPreset('month')">Bulan Ini</button>
      <button class="btn ghost" @click="setPreset('year')">Tahun Ini</button>
      <button class="btn ghost" @click="setPreset('all')">Semua</button>
      <div class="spacer"></div>
      <button class="btn ghost" @click="printReport">🖨 Print / PDF</button>
      <button class="btn" @click="exportExcel">⬇ Excel</button>
    </div>

    <div v-if="report" id="report-area" class="card">
      <div class="report-head">
        <h2>{{ report.title }}</h2>
        <p v-if="filter.start || filter.end" class="period">
          Periode: {{ filter.start || '-' }} s/d {{ filter.end || '-' }}
        </p>
      </div>

      <table class="tbl">
        <thead>
          <tr><th v-for="c in report.columns" :key="c.key" :class="{ num: false }">{{ c.label }}</th></tr>
        </thead>
        <tbody>
          <tr v-if="report.rows.length === 0"><td :colspan="report.columns.length" class="empty">Tidak ada data.</td></tr>
          <tr v-for="(row, i) in report.rows" :key="i">
            <td v-for="c in report.columns" :key="c.key" :class="{ num: typeof row[c.key] === 'number' }">
              {{ fmt(row[c.key]) }}
            </td>
          </tr>
        </tbody>
      </table>

      <div class="summary">
        <div v-for="(v, k) in report.summary" :key="k" class="sitem">
          <span>{{ k }}</span><strong>{{ fmt(v) }}</strong>
        </div>
      </div>
    </div>
    <div v-else-if="loading" class="loading">Memuat…</div>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 14px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.85rem; }
.toolbar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
.toolbar select, .toolbar input { padding: 9px 11px; border: 1px solid var(--border); border-radius: 8px; }
.spacer { flex: 1; }
.btn { padding: 9px 15px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 22px; }
.report-head { margin-bottom: 14px; }
.report-head h2 { margin: 0; color: var(--primary-dark); }
.period { margin: 4px 0 0; color: var(--muted); font-size: 0.82rem; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.tbl th, .tbl td { padding: 8px 12px; border: 1px solid var(--border); text-align: left; }
.tbl th { background: #f1f5f9; font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.empty { text-align: center; color: var(--muted); padding: 24px; }
.summary { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; justify-content: flex-end; }
.sitem { background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; display: flex; flex-direction: column; }
.sitem span { font-size: 0.75rem; color: var(--muted); }
.sitem strong { font-size: 1.05rem; color: var(--primary-dark); }
.loading { color: var(--muted); padding: 40px; text-align: center; }
</style>
