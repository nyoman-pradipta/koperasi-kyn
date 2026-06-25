<script setup>
import { ref, computed, onMounted } from 'vue'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()

const items      = ref([])
const coopName   = ref('')
const loading    = ref(false)
const daysAhead  = ref(30)
const sentSet    = ref(new Set())

const DAYS_OPTIONS = [
  { label: '7 hari ke depan',  value: 7 },
  { label: '14 hari ke depan', value: 14 },
  { label: '30 hari ke depan', value: 30 },
  { label: '60 hari ke depan', value: 60 },
  { label: '90 hari ke depan', value: 90 },
  { label: '120 hari ke depan', value: 120 },
]

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/reminders/due', {
      params: { days_ahead: daysAhead.value, include_overdue: true },
    })
    coopName.value = data.coop_name
    items.value    = data.items
    const today = new Date().toISOString().slice(0, 10)
    const fresh = new Set()
    for (const it of data.items) {
      if (it.last_sent_at && it.last_sent_at.startsWith(today)) {
        fresh.add(it.schedule_id)
      }
    }
    sentSet.value = fresh
  } catch {
    ui.notify('Gagal memuat data pengingat', 'error')
  } finally {
    loading.value = false
  }
}

async function send(item) {
  if (!item.has_phone) {
    ui.notify(`${item.member_name} tidak memiliki nomor HP terdaftar.`, 'error')
    return
  }
  const url = `https://wa.me/${item.wa_phone}?text=${encodeURIComponent(item.wa_message)}`
  window.open(url, '_blank')
  sentSet.value = new Set([...sentSet.value, item.schedule_id])
  try {
    await client.post(
      `/reminders/log?schedule_id=${item.schedule_id}&member_id=${item.member_id}&loan_id=${item.loan_id}&phone=${encodeURIComponent(item.wa_phone)}`
    )
  } catch { /* log failure is non-critical */ }
}


function copyMsg(item) {
  navigator.clipboard.writeText(item.wa_message).then(() => ui.notify('Pesan disalin'))
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d + 'T00:00:00').toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatDt(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function rp(n) { return 'Rp ' + Number(n).toLocaleString('id-ID') }

const overdueCount = computed(() => items.value.filter(it => it.is_overdue).length)
const noPhoneCount = computed(() => items.value.filter(it => !it.has_phone).length)

onMounted(load)
</script>

<template>
  <div>
    <!-- Header -->
    <div class="page-head">
      <div>
        <h1>📱 Pengingat Jatuh Tempo</h1>
        <p class="sub">Kirim notifikasi WhatsApp ke anggota yang memiliki tagihan aktif</p>
      </div>
      <div class="head-actions">
        <select v-model="daysAhead" @change="load" class="days-sel">
          <option v-for="o in DAYS_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <button class="btn ghost" @click="load" :disabled="loading">🔄 Refresh</button>
      </div>
    </div>

    <!-- Summary cards -->
    <div class="summary-row">
      <div class="sum-card">
        <div class="sum-num">{{ items.length }}</div>
        <div class="sum-lbl">Total Tagihan</div>
      </div>
      <div class="sum-card warn">
        <div class="sum-num">{{ overdueCount }}</div>
        <div class="sum-lbl">Sudah Lewat Jatuh Tempo</div>
      </div>
      <div class="sum-card ok">
        <div class="sum-num">{{ sentSet.size }}</div>
        <div class="sum-lbl">Sudah Dikirim Hari Ini</div>
      </div>
      <div class="sum-card muted">
        <div class="sum-num">{{ noPhoneCount }}</div>
        <div class="sum-lbl">Tidak Ada No HP</div>
      </div>
    </div>

    <!-- Table -->
    <div class="card">
      <div v-if="loading" class="empty">Memuat data…</div>
      <div v-else-if="items.length === 0" class="empty">
        Tidak ada tagihan dalam rentang {{ daysAhead }} hari ke depan.
      </div>
      <div v-else class="tbl-wrap">
        <table class="tbl">
          <thead>
            <tr>
              <th>Anggota</th>
              <th>No HP</th>
              <th>No. Pinjaman</th>
              <th class="ta-c">Angsuran ke</th>
              <th>Jatuh Tempo</th>
              <th class="ta-r">Sisa Tagihan</th>
              <th>Status</th>
              <th>Terakhir Dikirim</th>
              <th class="ta-r">Aksi</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="it in items"
              :key="it.schedule_id"
              :class="{ 'row-overdue': it.is_overdue, 'row-sent': sentSet.has(it.schedule_id) }"
            >
              <td class="td-name">{{ it.member_name }}</td>
              <td>
                <span v-if="it.phone" class="phone-txt">{{ it.phone }}</span>
                <span v-else class="no-phone">Tidak ada</span>
              </td>
              <td>{{ it.loan_number }}</td>
              <td class="ta-c">{{ it.installment_no }}</td>
              <td>
                <span :class="it.is_overdue ? 'badge-overdue' : 'badge-upcoming'">
                  {{ formatDate(it.due_date) }}
                </span>
              </td>
              <td class="ta-r fw-6">{{ rp(it.remaining) }}</td>
              <td>
                <span class="status-badge" :class="it.status">
                  {{ it.status === 'partial' ? 'Sebagian' : 'Belum Bayar' }}
                </span>
              </td>
              <td class="td-sent">
                <span v-if="sentSet.has(it.schedule_id)" class="sent-tag">✓ Hari ini</span>
                <span v-else-if="it.last_sent_at" class="old-sent">{{ formatDt(it.last_sent_at) }}</span>
                <span v-else class="muted-txt">—</span>
              </td>
              <td class="ta-r">
                <div class="act-group">
                  <!-- Preview pesan -->
                  <details class="msg-details">
                    <summary class="preview-btn" title="Lihat pesan">👁</summary>
                    <div class="msg-popover">
                      <pre class="msg-text">{{ it.wa_message }}</pre>
                      <button class="copy-btn" @click.stop="copyMsg(it)">📋 Salin Pesan</button>
                    </div>
                  </details>

                  <!-- Kirim WA -->
                  <button
                    class="wa-btn"
                    :class="{ sent: sentSet.has(it.schedule_id), 'no-hp': !it.has_phone }"
                    :disabled="!it.has_phone"
                    :title="it.has_phone ? `Kirim ke ${it.phone}` : 'Tidak ada nomor HP'"
                    @click="send(it)"
                  >
                    {{ sentSet.has(it.schedule_id) ? '✓ Terkirim' : '📱 Kirim WA' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="info-box">
      <strong>ℹ️ Cara kerja:</strong>
      Tombol "Kirim WA" membuka WhatsApp dengan pesan yang sudah terisi otomatis.
      Pesan dikirim secara manual oleh petugas — klik <em>Send</em> di WhatsApp untuk mengirim.
      Log pengiriman disimpan di sistem untuk keperluan audit.
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 20px; gap: 12px; flex-wrap: wrap;
}
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 3px 0 0; color: var(--muted); font-size: 0.85rem; }
.head-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

.days-sel { padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.88rem; background: #fff; }
.btn { padding: 9px 16px; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.88rem; }
.btn.ghost { background: #fff; border: 1px solid var(--border); color: var(--text); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }

.summary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.sum-card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; text-align: center; }
.sum-card.warn { border-color: #fca5a5; background: #fff7f7; }
.sum-card.ok   { border-color: #86efac; background: #f0fdf4; }
.sum-num { font-size: 1.8rem; font-weight: 700; color: var(--primary-dark); }
.sum-card.warn .sum-num { color: #b91c1c; }
.sum-card.ok   .sum-num { color: #166534; }
.sum-lbl { font-size: 0.78rem; color: var(--muted); margin-top: 4px; }

.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tbl-wrap { overflow-x: auto; }
.empty { text-align: center; color: var(--muted); padding: 32px; }

.tbl { width: 100%; border-collapse: collapse; font-size: 0.87rem; }
.tbl th, .tbl td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
.tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; white-space: nowrap; }
.tbl tr:last-child td { border-bottom: none; }
.ta-r { text-align: right; }
.ta-c { text-align: center; }
.fw-6 { font-weight: 600; }

.row-overdue { background: #fff7f7; }
.row-sent    { background: #f0fdf4; }

.td-name  { font-weight: 600; white-space: nowrap; }
.phone-txt { font-family: monospace; font-size: 0.85rem; }
.no-phone  { color: var(--muted); font-style: italic; font-size: 0.82rem; }

.badge-overdue  { background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; white-space: nowrap; }
.badge-upcoming { background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; white-space: nowrap; }

.status-badge { padding: 2px 8px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; }
.status-badge.unpaid  { background: #fef3c7; color: #92400e; }
.status-badge.partial { background: #dbeafe; color: #1e40af; }

.sent-tag  { font-size: 0.78rem; color: #166534; font-weight: 600; }
.old-sent  { font-size: 0.78rem; color: var(--muted); }
.muted-txt { color: var(--muted); font-size: 0.8rem; }
.td-sent   { white-space: nowrap; }

.act-group { display: flex; gap: 6px; justify-content: flex-end; align-items: flex-start; }

.wa-btn {
  padding: 6px 12px; border: none; border-radius: 7px;
  font-size: 0.82rem; font-weight: 600; cursor: pointer;
  background: #25d366; color: #fff; white-space: nowrap;
}
.wa-btn:hover:not(:disabled) { background: #1ebe5a; }
.wa-btn.sent  { background: #dcfce7; color: #166534; }
.wa-btn.no-hp { background: #f1f5f9; color: #94a3b8; }
.wa-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.msg-details { position: relative; }
.preview-btn {
  list-style: none; padding: 6px 9px; background: #f1f5f9;
  border-radius: 7px; cursor: pointer; font-size: 0.85rem; color: var(--text);
}
.preview-btn::-webkit-details-marker { display: none; }
.msg-popover {
  position: absolute; right: 0; top: calc(100% + 6px);
  width: 340px; background: #fff; border: 1px solid var(--border);
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  z-index: 50; padding: 14px;
}
.msg-text {
  white-space: pre-wrap; font-size: 0.8rem; line-height: 1.6;
  margin: 0 0 10px; color: var(--text); font-family: inherit;
}
.copy-btn {
  width: 100%; padding: 6px 12px; background: var(--primary); color: #fff;
  border: none; border-radius: 6px; font-size: 0.78rem; cursor: pointer;
}

.info-box {
  margin-top: 14px; background: #f0f9ff; border: 1px solid #bae6fd;
  border-radius: 10px; padding: 12px 16px; font-size: 0.84rem;
  color: #0369a1; line-height: 1.6;
}
</style>
