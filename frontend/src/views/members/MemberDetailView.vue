<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import { useCurrency } from '../../composables/useCurrency'
import { useDate } from '../../composables/useDate'

const route  = useRoute()
const router = useRouter()
const ui     = useUiStore()
const { rp } = useCurrency()
const { fmtDate, fmtDateTime } = useDate()

const id     = route.params.id
const member = ref(null)
const loans  = ref([])
const payments = ref([])
const collaterals = ref([])
const audit  = ref([])
const tab    = ref('loans')

const STATUS_COLOR = {
  aktif: '#16a34a', nonaktif: '#64748b', diblokir: '#b91c1c', diarsipkan: '#92400e',
}
const LOAN_STATUS_COLOR = {
  draft: '#64748b', pending: '#0891b2', approved: '#16a34a',
  active: '#1e40af', settled: '#059669', rejected: '#b91c1c',
}
const LOAN_STATUS_LABEL = {
  draft: 'Draft', pending: 'Menunggu', approved: 'Disetujui',
  active: 'Aktif', settled: 'Lunas', rejected: 'Ditolak',
}

async function load() {
  try {
    const [m, l, p, c, a] = await Promise.all([
      client.get(`/members/${id}`),
      client.get(`/members/${id}/loans`),
      client.get(`/members/${id}/payments`),
      client.get(`/members/${id}/collaterals`),
      client.get(`/members/${id}/audit`),
    ])
    member.value     = m.data
    loans.value      = l.data
    payments.value   = p.data
    collaterals.value = c.data
    audit.value      = a.data
  } catch {
    ui.notify('Gagal memuat data anggota', 'error')
    router.push('/anggota')
  }
}

async function setStatus(status) {
  try {
    await client.post(`/members/${id}/set-status`, null, { params: { status } })
    ui.notify('Status anggota diperbarui')
    await load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mengubah status', 'error')
  }
}

async function archive() {
  if (!confirm('Arsipkan anggota ini? Status akan berubah menjadi "Diarsipkan".')) return
  try {
    await client.post(`/members/${id}/archive`)
    ui.notify('Anggota diarsipkan')
    await load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mengarsipkan', 'error')
  }
}

const AUDIT_ACTION_ICON = {
  loan_created: '📄', loan_submitted: '📤', loan_approved: '✅',
  loan_rejected: '❌', loan_disbursed: '💸', payment_recorded: '💳',
  loan_settled: '🏁', collateral_attached: '📎', collateral_returned: '↩️',
  document_uploaded: '📎', member_status_changed: '🔄',
}

function auditIcon(action) {
  return AUDIT_ACTION_ICON[action] || '●'
}

onMounted(load)
</script>

<template>
  <div v-if="member">
    <!-- Header -->
    <div class="page-head">
      <button class="back-btn" @click="router.push('/anggota')">← Kembali</button>
      <div class="head-info">
        <h1>{{ member.full_name }}</h1>
        <span class="member-no">{{ member.member_number }}</span>
        <span class="status-chip" :style="{ background: STATUS_COLOR[member.status] + '20', color: STATUS_COLOR[member.status], border: '1px solid ' + STATUS_COLOR[member.status] + '40' }">
          {{ member.status }}
        </span>
      </div>
    </div>

    <div class="layout">
      <!-- Sidebar: Info Anggota -->
      <aside>
        <section class="card">
          <h2>Informasi Anggota</h2>
          <dl class="info-dl">
            <div><dt>NIK</dt><dd>{{ member.nik || '—' }}</dd></div>
            <div><dt>Telepon</dt><dd>{{ member.phone || '—' }}</dd></div>
            <div><dt>Email</dt><dd>{{ member.email || '—' }}</dd></div>
            <div><dt>Alamat</dt><dd>{{ member.address || '—' }}</dd></div>
            <div><dt>Tgl Bergabung</dt><dd>{{ fmtDate(member.join_date) }}</dd></div>
            <div><dt>Terdaftar</dt><dd>{{ fmtDateTime(member.created_at) }}</dd></div>
          </dl>

          <div v-if="member.ktp_photo_path" class="ktp-wrap">
            <p class="ktp-label">Foto KTP</p>
            <a :href="'/' + member.ktp_photo_path" target="_blank">
              <img :src="'/' + member.ktp_photo_path" class="ktp-img" alt="Foto KTP" />
            </a>
          </div>
        </section>

        <section class="card stat-card">
          <h2>Ringkasan</h2>
          <div class="mini-stat">
            <div class="ms-item"><span class="ms-val">{{ member.total_loans_count }}</span><span class="ms-label">Total Pinjaman</span></div>
            <div class="ms-item"><span class="ms-val">{{ member.active_loans_count }}</span><span class="ms-label">Pinjaman Aktif</span></div>
            <div class="ms-item"><span class="ms-val">{{ collaterals.length }}</span><span class="ms-label">Jaminan</span></div>
          </div>
        </section>

        <!-- Aksi -->
        <section class="card" v-if="member.status !== 'diarsipkan'">
          <h2>Aksi</h2>
          <div class="action-stack">
            <button v-if="member.status === 'aktif'" class="btn btn-warn" @click="setStatus('nonaktif')" :disabled="member.active_loans_count > 0">
              Nonaktifkan
            </button>
            <button v-if="member.status === 'nonaktif'" class="btn" @click="setStatus('aktif')">
              Aktifkan Kembali
            </button>
            <button v-if="member.status !== 'diblokir'" class="btn btn-danger" @click="setStatus('diblokir')" :disabled="member.active_loans_count > 0">
              Blokir
            </button>
            <button v-if="member.status === 'diblokir'" class="btn" @click="setStatus('aktif')">
              Buka Blokir
            </button>
            <button v-if="member.has_any_data" class="btn btn-muted" @click="archive" :disabled="member.active_loans_count > 0">
              Arsipkan
            </button>
            <p v-if="member.active_loans_count > 0" class="hint-warn">
              ⚠️ Anggota memiliki pinjaman aktif — aksi nonaktifkan/blokir/arsipkan dinonaktifkan.
            </p>
          </div>
        </section>
      </aside>

      <!-- Main: Tabs -->
      <main>
        <div class="tab-bar">
          <button :class="['tab-btn', tab === 'loans' && 'active']" @click="tab = 'loans'">
            Pinjaman ({{ loans.length }})
          </button>
          <button :class="['tab-btn', tab === 'payments' && 'active']" @click="tab = 'payments'">
            Pembayaran ({{ payments.length }})
          </button>
          <button :class="['tab-btn', tab === 'collaterals' && 'active']" @click="tab = 'collaterals'">
            Jaminan ({{ collaterals.length }})
          </button>
          <button :class="['tab-btn', tab === 'audit' && 'active']" @click="tab = 'audit'">
            Riwayat Aktivitas ({{ audit.length }})
          </button>
        </div>

        <!-- Tab: Pinjaman -->
        <section v-if="tab === 'loans'" class="card">
          <div v-if="loans.length" class="table-wrap">
            <table class="tbl">
              <thead>
                <tr>
                  <th>No. Pinjaman</th>
                  <th class="num">Pokok</th>
                  <th>Bunga</th>
                  <th>Tenor</th>
                  <th>Status</th>
                  <th>Tgl Pencairan</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="l in loans" :key="l.id">
                  <td class="mono">{{ l.loan_number }}</td>
                  <td class="num">{{ rp(l.principal_amount) }}</td>
                  <td>{{ l.interest_rate }}%/bln</td>
                  <td>{{ l.tenor }} bln</td>
                  <td>
                    <span class="status-chip small" :style="{ background: (LOAN_STATUS_COLOR[l.status] || '#64748b') + '20', color: LOAN_STATUS_COLOR[l.status] || '#64748b' }">
                      {{ LOAN_STATUS_LABEL[l.status] || l.status }}
                    </span>
                  </td>
                  <td>{{ fmtDate(l.disbursement_date) }}</td>
                  <td><button class="link-btn" @click="router.push('/pinjaman/' + l.id)">Detail →</button></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty">Belum ada riwayat pinjaman.</p>
        </section>

        <!-- Tab: Pembayaran -->
        <section v-if="tab === 'payments'" class="card">
          <div v-if="payments.length" class="table-wrap">
            <table class="tbl">
              <thead>
                <tr>
                  <th>No. Kwitansi</th>
                  <th class="num">Nominal</th>
                  <th>Tanggal</th>
                  <th>Catatan</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in payments" :key="p.id">
                  <td class="mono">{{ p.payment_number }}</td>
                  <td class="num">{{ rp(p.amount_paid) }}</td>
                  <td>{{ fmtDate(p.payment_date) }}</td>
                  <td class="text-muted">{{ p.note || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty">Belum ada riwayat pembayaran.</p>
        </section>

        <!-- Tab: Jaminan -->
        <section v-if="tab === 'collaterals'" class="card">
          <div v-if="collaterals.length" class="table-wrap">
            <table class="tbl">
              <thead>
                <tr>
                  <th>Jenis</th>
                  <th>No. Dokumen</th>
                  <th>Pemilik</th>
                  <th class="num">Est. Nilai</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in collaterals" :key="c.id">
                  <td>{{ c.type }}</td>
                  <td class="mono">{{ c.doc_number || '—' }}</td>
                  <td>{{ c.owner_name || '—' }}</td>
                  <td class="num">{{ c.estimated_value ? rp(c.estimated_value) : '—' }}</td>
                  <td>
                    <span class="col-status" :class="c.collateral_status">{{ c.collateral_status }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="empty">Belum ada data jaminan.</p>
        </section>

        <!-- Tab: Audit Trail -->
        <section v-if="tab === 'audit'" class="card">
          <div v-if="audit.length" class="timeline">
            <div v-for="(ev, i) in audit" :key="ev.id" class="tl-item">
              <div class="tl-col">
                <div class="tl-dot">{{ auditIcon(ev.action) }}</div>
                <div v-if="i < audit.length - 1" class="tl-line"></div>
              </div>
              <div class="tl-body">
                <p class="tl-desc">{{ ev.description }}</p>
                <p class="tl-actor">{{ ev.actor }}</p>
                <p class="tl-time">{{ fmtDateTime(ev.created_at) }}</p>
              </div>
            </div>
          </div>
          <p v-else class="empty">Belum ada riwayat aktivitas.</p>
        </section>
      </main>
    </div>
  </div>
  <div v-else class="loading">Memuat data anggota…</div>
</template>

<style scoped>
/* Page header */
.page-head { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.back-btn { padding: 8px 14px; background: #fff; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.85rem; color: var(--muted); }
.back-btn:hover { border-color: var(--primary); color: var(--primary); }
.head-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.head-info h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.member-no { font-size: 0.8rem; color: var(--muted); background: #f1f5f9; padding: 3px 8px; border-radius: 6px; font-family: monospace; }
.status-chip { font-size: 0.74rem; font-weight: 700; padding: 3px 10px; border-radius: 20px; text-transform: capitalize; }
.status-chip.small { font-size: 0.7rem; padding: 2px 7px; }

/* Layout */
.layout { display: grid; grid-template-columns: 280px 1fr; gap: 16px; align-items: start; }
@media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }

/* Card */
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 14px; }
.card h2 { margin: 0 0 14px; font-size: 0.95rem; color: var(--primary-dark); }

/* Info DL */
.info-dl { margin: 0; display: flex; flex-direction: column; gap: 8px; }
.info-dl div { display: flex; flex-direction: column; gap: 2px; }
.info-dl dt { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.info-dl dd { margin: 0; font-size: 0.88rem; color: var(--text); word-break: break-word; }

/* KTP */
.ktp-wrap { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
.ktp-label { font-size: 0.72rem; color: var(--muted); margin: 0 0 6px; }
.ktp-img { width: 100%; border-radius: 8px; border: 1px solid var(--border); }

/* Mini stat */
.stat-card { }
.mini-stat { display: flex; gap: 0; }
.ms-item { flex: 1; text-align: center; padding: 8px 4px; border-right: 1px solid var(--border); }
.ms-item:last-child { border-right: none; }
.ms-val { display: block; font-size: 1.4rem; font-weight: 700; color: var(--primary-dark); }
.ms-label { display: block; font-size: 0.68rem; color: var(--muted); margin-top: 2px; }

/* Action buttons */
.action-stack { display: flex; flex-direction: column; gap: 8px; }
.btn { padding: 9px 16px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: none; background: var(--primary); color: #fff; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn:not(:disabled):hover { opacity: 0.88; }
.btn-warn { background: #f59e0b; }
.btn-danger { background: #ef4444; }
.btn-muted { background: #64748b; }
.hint-warn { font-size: 0.75rem; color: #92400e; background: #fef3c7; padding: 6px 10px; border-radius: 6px; margin: 4px 0 0; }

/* Tabs */
.tab-bar { display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap; }
.tab-btn { padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; background: #fff; cursor: pointer; font-size: 0.83rem; color: var(--muted); }
.tab-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); font-weight: 600; }

/* Table */
.table-wrap { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.tbl th { text-align: left; padding: 8px 10px; background: #f8faf9; border-bottom: 2px solid var(--border); font-size: 0.78rem; color: var(--muted); }
.tbl td { padding: 10px 10px; border-bottom: 1px solid var(--border); }
.tbl tr:last-child td { border-bottom: none; }
.num { text-align: right; }
.mono { font-family: monospace; font-size: 0.82rem; }
.text-muted { color: var(--muted); }

/* Collateral status */
.col-status { font-size: 0.74rem; font-weight: 700; padding: 2px 8px; border-radius: 12px; text-transform: capitalize; background: #f1f5f9; color: #475569; }
.col-status.in_use { background: #dbeafe; color: #1e40af; }
.col-status.available { background: #dcfce7; color: #166534; }
.col-status.returned { background: #f0fdf4; color: #15803d; }
.col-status.archived { background: #fef9c3; color: #92400e; }

/* Link button */
.link-btn { background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.82rem; padding: 0; font-weight: 600; }
.link-btn:hover { text-decoration: underline; }

/* Audit timeline */
.timeline { display: flex; flex-direction: column; }
.tl-item { display: flex; gap: 12px; }
.tl-col { display: flex; flex-direction: column; align-items: center; width: 28px; flex-shrink: 0; }
.tl-dot { width: 28px; height: 28px; border-radius: 50%; background: #f1f5f9; border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 0.82rem; flex-shrink: 0; }
.tl-line { width: 2px; background: var(--border); flex: 1; margin: 3px 0; min-height: 14px; }
.tl-body { padding-bottom: 18px; flex: 1; }
.tl-desc { margin: 2px 0 0; font-size: 0.88rem; color: var(--text); font-weight: 500; }
.tl-actor { margin: 4px 0 0; font-size: 0.8rem; color: var(--text); font-weight: 600; }
.tl-time { margin: 1px 0 0; font-size: 0.74rem; color: var(--muted); }

.empty { color: var(--muted); font-size: 0.86rem; text-align: center; padding: 24px 0; }
.loading { color: var(--muted); padding: 40px; text-align: center; }
</style>
