<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import { useCurrency } from '../../composables/useCurrency'
import { useDate } from '../../composables/useDate'
import { useContract } from '../../composables/useContract'
import ScheduleTable from '../../components/loans/ScheduleTable.vue'

const route  = useRoute()
const router = useRouter()
const ui     = useUiStore()
const { rp } = useCurrency()
const { fmtDate, fmtDateTime } = useDate()
const { printContract } = useContract()

// ── core loan state ──────────────────────────────────────────────────────────
const loan         = ref(null)
const schedule     = ref([])
const coop         = ref({})
const disburseDate = ref(new Date().toISOString().slice(0, 10))
const id           = route.params.id

// ── collateral-return state ──────────────────────────────────────────────────
const showReturnModal   = ref(false)
const showReturnConfirm = ref(false)
const returning         = ref(false)
const returnForm        = ref({
  return_recipient: '',
  return_date: new Date().toISOString().slice(0, 10),
  return_notes: '',
})
const returnProof   = ref(null)
const returnHistory = ref([])

function openReturnModal() {
  returnForm.value        = { return_recipient: '', return_date: new Date().toISOString().slice(0, 10), return_notes: '' }
  returnProof.value       = null
  showReturnConfirm.value = false
  showReturnModal.value   = true
}

function closeReturnModal() {
  showReturnModal.value   = false
  showReturnConfirm.value = false
}

function requestReturnConfirm() {
  if (!returnForm.value.return_recipient) { ui.notify('Nama penerima wajib diisi', 'error'); return }
  showReturnConfirm.value = true
}

// ── documents state ──────────────────────────────────────────────────────────
const colDocs     = ref([])
const showUpload  = ref(false)
const uploading   = ref(false)
const newDocType  = ref('Dokumen Jaminan')
const newDocFile  = ref(null)
const previewFile = ref(null)   // { file_name, file_path, mime_type }
const zoomLevel   = ref(1)

// ── usage history state ───────────────────────────────────────────────────────
const usageHistory = ref([])

// ── audit trail ─────────────────────────────────────────────────────────────
const auditTrail = ref([])

// ── constants ────────────────────────────────────────────────────────────────
const DOC_TYPES = [
  'Scan KTP', 'Scan KK', 'Scan BPKB', 'Scan STNK',
  'Sertifikat', 'Foto Kendaraan', 'Foto Rumah',
  'Dokumen Jaminan', 'Dokumen Pendukung Lainnya',
]

const COL_STATUS = {
  available: 'Tersedia',
  in_use: 'Sedang Digunakan',
  returned: 'Dikembalikan',
  archived: 'Diarsipkan',
}
const COL_STATUS_CLASS = {
  available: 'col-available',
  in_use: 'col-in_use',
  returned: 'col-returned',
  archived: 'col-archived',
}

// ── helpers ──────────────────────────────────────────────────────────────────
function isImageMime(mime) { return !!mime && mime.startsWith('image/') }

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

// formatDt digantikan oleh fmtDate / fmtDateTime dari useDate composable

function truncate(str, n = 32) {
  if (!str) return '—'
  return str.length > n ? str.slice(0, n - 1) + '…' : str
}

function adjustZoom(delta) {
  zoomLevel.value = Math.max(0.25, Math.min(5, zoomLevel.value + delta))
}

function fileIcon(mime) {
  if (mime && mime.startsWith('image/')) return '🖼'
  if (mime === 'application/pdf')        return '📄'
  return '📎'
}

// ── data loading ──────────────────────────────────────────────────────────────
async function load() {
  const { data } = await client.get(`/loans/${id}`)
  loan.value = data

  if (['active', 'paid_off'].includes(data.status)) {
    const res = await client.get(`/loans/${id}/schedule`)
    schedule.value = res.data
  }

  const auditRes = await client.get(`/loans/${id}/audit`)
  auditTrail.value = auditRes.data

  if (data.collateral) {
    const [histRes, docsRes, usageRes] = await Promise.all([
      client.get(`/collaterals/${data.collateral.id}/returns`),
      client.get(`/collaterals/${data.collateral.id}/documents`),
      client.get(`/collaterals/${data.collateral.id}/usage-history`),
    ])
    returnHistory.value = histRes.data
    colDocs.value = docsRes.data.documents || []
    usageHistory.value = usageRes.data
  }
}

// ── document actions ──────────────────────────────────────────────────────────
function lihatDoc(doc) {
  if (doc.mime_type && doc.mime_type.startsWith('image/')) {
    previewFile.value = doc
    zoomLevel.value   = 1
  } else {
    const url = doc.file_path.startsWith('http') ? doc.file_path : '/' + doc.file_path
    window.open(url, '_blank')
  }
}



async function uploadNewDoc() {
  if (!newDocFile.value) { ui.notify('Pilih file terlebih dahulu', 'error'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('document_type', newDocType.value)
    fd.append('file', newDocFile.value)
    await client.post(`/collaterals/${loan.value.collateral.id}/documents`, fd)
    ui.notify('Dokumen berhasil diupload')
    showUpload.value = false
    newDocFile.value = null
    newDocType.value = 'Dokumen Jaminan'
    const res = await client.get(`/collaterals/${loan.value.collateral.id}/documents`)
    colDocs.value = res.data.documents || []
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal upload dokumen', 'error')
  } finally {
    uploading.value = false
  }
}

// ── loan actions ──────────────────────────────────────────────────────────────
async function cetakKontrak() {
  if (!schedule.value.length) {
    const res = await client.get(`/loans/${id}/schedule`)
    schedule.value = res.data
  }
  const { data } = await client.get('/settings')
  coop.value = data
  printContract(loan.value, schedule.value, coop.value)
}

async function act(action, body) {
  try {
    await client.post(`/loans/${id}/${action}`, body || {})
    ui.notify('Berhasil: ' + action)
    await load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Aksi gagal', 'error')
  }
}

function approve() { act('approve', { note: prompt('Catatan persetujuan (opsional):') || '' }) }
function reject()  { act('reject',  { note: prompt('Alasan penolakan:') || '' }) }
function submit()  { act('submit') }
function disburse(){ act('disburse', { disbursement_date: disburseDate.value }) }

// ── collateral return ─────────────────────────────────────────────────────────
async function kembalikanJaminan() {
  returning.value = true
  try {
    const col = loan.value.collateral
    const fd  = new FormData()
    fd.append('return_recipient', returnForm.value.return_recipient)
    fd.append('return_date',      returnForm.value.return_date)
    if (returnForm.value.return_notes) fd.append('return_notes', returnForm.value.return_notes)
    if (returnProof.value) fd.append('proof', returnProof.value)
    await client.post(`/collaterals/${col.id}/return`, fd)
    ui.notify('Dokumen jaminan berhasil dikembalikan')
    closeReturnModal()
    await load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mengembalikan jaminan', 'error')
    showReturnConfirm.value = false
  } finally {
    returning.value = false
  }
}

const scheduleRows = computed(() =>
  schedule.value.map(r => ({
    no:        r.installment_no,
    due_date:  r.due_date,
    principal: r.principal_due,
    interest:  r.interest_due,
    total:     r.total_due,
    status:    r.status,
  }))
)

onMounted(load)
</script>

<template>
  <div v-if="loan">
    <button class="back-btn" @click="router.push('/pinjaman')">← Data Pinjaman</button>

    <!-- ── Page Head ───────────────────────────────────────────────────────── -->
    <div class="page-head">
      <div>
        <h1>{{ loan.loan_number }}</h1>
        <p class="sub">{{ loan.member_name }} · {{ loan.purpose || '-' }}</p>
      </div>
      <span class="status-badge" :class="loan.status">{{ loan.status }}</span>
    </div>

    <!-- ── 1. Rincian Pinjaman + Aksi ─────────────────────────────────────── -->
    <div class="grid-2col mb-card">
      <section class="card">
        <h2>Rincian Pinjaman</h2>
        <dl>
          <div><dt>Pokok</dt>         <dd>{{ rp(loan.principal_amount) }}</dd></div>
          <div><dt>Bunga</dt>         <dd>{{ loan.interest_type }} · {{ loan.interest_rate }}%/bln</dd></div>
          <div><dt>Tenor</dt>         <dd>{{ loan.tenor }} bulan</dd></div>
          <div><dt>Total Biaya</dt>   <dd>{{ rp(loan.total_fees) }}</dd></div>
          <div><dt>Dana Bersih</dt>   <dd>{{ rp(loan.net_received) }}</dd></div>
          <div><dt>Total Bayar</dt>   <dd>{{ rp(loan.total_payable) }}</dd></div>
          <div><dt>Tgl Pencairan</dt> <dd>{{ fmtDate(loan.disbursement_date) || '-' }}</dd></div>
        </dl>
      </section>

      <section class="card">
        <h2>Aksi</h2>
        <div class="action-stack">
          <button v-if="loan.status === 'draft'" class="btn" @click="submit">Ajukan ke Persetujuan</button>
          <template v-if="loan.status === 'pending'">
            <button class="btn" @click="approve">Setujui</button>
            <button class="btn btn-danger" @click="reject">Tolak</button>
          </template>
          <template v-if="loan.status === 'approved'">
            <label class="field-label">Tanggal Pencairan
              <input type="date" v-model="disburseDate" />
            </label>
            <button class="btn" @click="disburse">Cairkan Dana</button>
          </template>
          <button
            v-if="['approved','active','paid_off'].includes(loan.status)"
            class="btn btn-ghost"
            @click="cetakKontrak"
          >🖨 Cetak Kontrak (A4)</button>
          <button
            v-if="loan.status === 'paid_off' && loan.collateral && loan.collateral.collateral_status === 'in_use'"
            class="btn btn-return"
            @click="openReturnModal"
          >📦 Kembalikan Jaminan</button>
          <p v-if="loan.status === 'rejected'" class="text-muted">
            Pengajuan ditolak — tidak ada aksi tersedia.
          </p>
        </div>
      </section>
    </div>

    <!-- ── 2. Jadwal Angsuran ──────────────────────────────────────────────── -->
    <section v-if="scheduleRows.length" class="card mb-card">
      <h2>Jadwal Angsuran</h2>
      <ScheduleTable :rows="scheduleRows" show-due show-status />
    </section>

    <!-- ── 3. Informasi Jaminan ────────────────────────────────────────────── -->
    <section v-if="!loan.collateral && !loan.requires_collateral" class="card mb-card docs-empty">
      <span>🛡️</span>
      <p style="margin-top:8px;font-weight:600">Tanpa Jaminan</p>
      <p class="sub">Pinjaman ini diajukan tanpa menggunakan jaminan.</p>
    </section>

    <section v-else-if="loan.collateral" class="card mb-card">
      <h2>Informasi Jaminan</h2>
      <div class="col-grid">
        <dl>
          <div><dt>ID Jaminan</dt>    <dd>#{{ loan.collateral.id }}</dd></div>
          <div><dt>Jenis Jaminan</dt> <dd>{{ loan.collateral.type }}</dd></div>
          <div><dt>Nomor Dokumen</dt> <dd>{{ loan.collateral.doc_number || '-' }}</dd></div>
          <div><dt>Nama Pemilik</dt>  <dd>{{ loan.collateral.owner_name || '-' }}</dd></div>
          <div><dt>Estimasi Nilai</dt><dd>{{ rp(loan.collateral.estimated_value) }}</dd></div>
          <div><dt>Lokasi Simpan</dt> <dd style="text-transform:capitalize">{{ loan.collateral.storage_location }}</dd></div>
        </dl>
        <div class="col-right">
          <div class="col-status-block">
            <span class="col-label">Status Jaminan</span>
            <span class="col-badge" :class="COL_STATUS_CLASS[loan.collateral.collateral_status]">
              {{ COL_STATUS[loan.collateral.collateral_status] || loan.collateral.collateral_status }}
            </span>
          </div>
          <div class="col-status-block" style="margin-top:14px">
            <span class="col-label">Dokumen Asli</span>
            <span :class="['doc-status-badge', loan.collateral.doc_status === 'sudah_diterima' ? 'doc-ok' : 'doc-warn']">
              {{ loan.collateral.doc_status === 'sudah_diterima' ? 'Sudah Diterima' : 'Belum Diterima' }}
            </span>
          </div>
        </div>
      </div>

    </section>

    <!-- ── 4. Dokumen Jaminan ──────────────────────────────────────────────── -->
    <section v-if="loan.collateral" class="card mb-card">
      <div class="docs-header">
        <div>
          <h2>Dokumen Jaminan</h2>
          <p class="sub">
            {{ colDocs.length }} file tersimpan
            <span class="note-green"> · file permanen, tidak dihapus meski pinjaman lunas</span>
          </p>
        </div>
        <button class="btn btn-ghost btn-sm" @click="showUpload = !showUpload">
          {{ showUpload ? '✕ Tutup' : '+ Upload Dokumen' }}
        </button>
      </div>

      <!-- Inline upload form -->
      <div v-if="showUpload" class="upload-panel">
        <div class="upload-row">
          <label class="field-label" style="flex:1;min-width:160px">
            Jenis Dokumen
            <select v-model="newDocType">
              <option v-for="t in DOC_TYPES" :key="t" :value="t">{{ t }}</option>
            </select>
          </label>
          <label class="field-label" style="flex:2;min-width:200px">
            File (JPG/PNG/PDF · maks 10 MB)
            <input type="file" accept=".jpg,.jpeg,.png,.pdf"
              @change="e => newDocFile = e.target.files[0] || null" />
          </label>
          <div style="align-self:flex-end;padding-bottom:0">
            <button class="btn" :disabled="uploading || !newDocFile" @click="uploadNewDoc">
              {{ uploading ? 'Mengupload…' : 'Upload' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="!colDocs.length" class="docs-empty">
        <span>📂</span>
        <p>Belum ada dokumen yang diupload untuk jaminan ini.</p>
        <p class="sub">Klik "+ Upload Dokumen" untuk menambahkan file.</p>
      </div>

      <!-- Document table -->
      <div v-else class="table-scroll">
        <table class="docs-tbl">
          <thead>
            <tr>
              <th>Jenis Dokumen</th>
              <th>Nama File</th>
              <th class="col-r">Ukuran</th>
              <th>Tgl Upload</th>
              <th class="col-r">Aksi</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in colDocs" :key="doc.id">
              <td>
                <span class="doc-type-chip">{{ fileIcon(doc.mime_type) }} {{ doc.document_type }}</span>
              </td>
              <td class="filename-cell" :title="doc.file_name">{{ truncate(doc.file_name, 36) }}</td>
              <td class="col-r text-muted">{{ formatSize(doc.file_size) }}</td>
              <td class="text-muted">{{ fmtDate(doc.uploaded_at) }}</td>
              <td class="col-r">
                <div class="doc-actions">
                  <button class="doc-btn lihat-btn" @click="lihatDoc(doc)">Lihat</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── 5. Riwayat Pengembalian Dokumen ────────────────────────────────── -->
    <section v-if="loan.collateral && returnHistory.length" class="card mb-card">
      <h2>Riwayat Pengembalian Dokumen</h2>
      <div class="table-scroll">
        <table class="hist-tbl">
          <thead>
            <tr>
              <th>Tgl Kembali</th>
              <th>Diterima Oleh</th>
              <th>Petugas</th>
              <th>Catatan</th>
              <th>Bukti Serah Terima</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in returnHistory" :key="h.id">
              <td>{{ fmtDate(h.return_date) }}</td>
              <td>{{ h.return_recipient }}</td>
              <td>{{ h.returned_by }}</td>
              <td>{{ h.return_notes || '—' }}</td>
              <td>
                <div v-if="h.return_proof_path" class="doc-actions" style="justify-content:flex-start">
                  <a :href="h.return_proof_path.startsWith('http') ? h.return_proof_path : '/' + h.return_proof_path" target="_blank" class="doc-btn lihat-btn">Lihat</a>
                </div>
                <span v-else class="text-muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── 6. Riwayat Penggunaan Jaminan ─────────────────────────────────── -->
    <section v-if="loan.collateral && usageHistory.length" class="card mb-card">
      <h2>Riwayat Penggunaan Jaminan</h2>
      <div class="table-wrap">
        <table class="hist-tbl">
          <thead>
            <tr>
              <th>Tanggal</th>
              <th>Aksi</th>
              <th>No. Pinjaman</th>
              <th>Keterangan</th>
              <th>Petugas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in usageHistory" :key="u.id">
              <td>{{ fmtDate(u.created_at) }}</td>
              <td>
                <span class="usage-badge" :class="u.action === 'attached' ? 'ub-in' : 'ub-out'">
                  {{ u.action === 'attached' ? '📎 Digunakan' : '↩ Dikembalikan' }}
                </span>
              </td>
              <td>{{ u.loan_number || '—' }}</td>
              <td>{{ u.notes || '—' }}</td>
              <td>{{ u.actor }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── 7. Audit Trail ──────────────────────────────────────────────────── -->
    <section v-if="auditTrail.length" class="card mb-card">
      <h2>Riwayat Aktivitas</h2>
      <div class="timeline">
        <div v-for="(ev, i) in auditTrail" :key="ev.id" class="tl-item">
          <div class="tl-col">
            <div class="tl-dot" :class="'dot-' + ev.action"></div>
            <div v-if="i < auditTrail.length - 1" class="tl-line"></div>
          </div>
          <div class="tl-body">
            <p class="tl-desc">{{ ev.description }}</p>
            <p class="tl-actor">{{ ev.actor }}</p>
            <p class="tl-time">{{ fmtDateTime(ev.created_at) }}</p>
          </div>
        </div>
      </div>
    </section>
  </div>

  <div v-else class="page-loading">Memuat data pinjaman…</div>

  <!-- ── Return Modal ───────────────────────────────────────────────────── -->
  <Teleport to="body">
    <div v-if="showReturnModal" class="modal-overlay" @click.self="closeReturnModal">
      <div class="return-modal">
        <!-- Header -->
        <div class="modal-head">
          <div>
            <h3 class="modal-title">Pengembalian Dokumen Jaminan</h3>
            <p class="modal-sub">{{ loan?.collateral?.type }} — {{ loan?.collateral?.owner_name }}</p>
          </div>
          <button class="modal-close" @click="closeReturnModal" title="Tutup">✕</button>
        </div>

        <!-- Confirmation step -->
        <div v-if="showReturnConfirm" class="modal-confirm">
          <div class="confirm-icon">📦</div>
          <p class="confirm-text">Apakah Anda yakin dokumen jaminan telah diserahkan kepada anggota?</p>
          <p class="confirm-detail">
            Penerima: <strong>{{ returnForm.return_recipient }}</strong> ·
            Tanggal: <strong>{{ fmtDate(returnForm.return_date) }}</strong>
          </p>
          <div class="modal-foot">
            <button class="btn btn-ghost" :disabled="returning" @click="showReturnConfirm = false">
              ← Kembali ke Form
            </button>
            <button class="btn btn-return" :disabled="returning" @click="kembalikanJaminan">
              {{ returning ? 'Menyimpan…' : 'Ya, Simpan' }}
            </button>
          </div>
        </div>

        <!-- Form step -->
        <div v-else class="modal-body">
          <label class="field-label">Nama Penerima Dokumen *
            <input v-model="returnForm.return_recipient" placeholder="Nama anggota / penerima" autofocus />
          </label>
          <label class="field-label">Tanggal Pengembalian *
            <input type="date" v-model="returnForm.return_date" />
          </label>
          <label class="field-label">Catatan
            <textarea v-model="returnForm.return_notes" rows="2" placeholder="Opsional — kondisi dokumen, keterangan, dll." />
          </label>
          <label class="field-label">Upload Bukti Serah Terima
            <span class="field-hint">JPG / PNG / PDF · maks 10 MB</span>
            <input type="file" accept=".jpg,.jpeg,.png,.pdf"
              @change="e => returnProof = e.target.files[0] || null" style="margin-top:6px" />
            <span v-if="returnProof" class="file-selected">✓ {{ returnProof.name }}</span>
          </label>
          <div class="modal-foot">
            <button class="btn btn-ghost" @click="closeReturnModal">Batal</button>
            <button class="btn btn-return" @click="requestReturnConfirm">Simpan →</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ── Image Preview Modal ─────────────────────────────────────────────── -->
  <Teleport to="body">
    <div v-if="previewFile" class="img-overlay" @click.self="previewFile = null">
      <div class="img-modal">
        <div class="img-modal-head">
          <span class="img-modal-name">{{ truncate(previewFile.file_name, 44) }}</span>
          <div class="zoom-controls">
            <button class="zoom-btn" @click="adjustZoom(-0.25)" title="Perkecil">−</button>
            <span class="zoom-pct">{{ Math.round(zoomLevel * 100) }}%</span>
            <button class="zoom-btn" @click="adjustZoom(0.25)" title="Perbesar">+</button>
            <button class="zoom-btn" @click="zoomLevel = 1" title="Reset">⊙</button>
            <button class="zoom-btn close-zoom-btn" @click="previewFile = null" title="Tutup">✕</button>
          </div>
        </div>
        <div class="img-viewport">
          <img
            :src="previewFile.file_path.startsWith('http') ? previewFile.file_path : '/' + previewFile.file_path"
            :alt="previewFile.file_name"
            :style="{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }"
            class="preview-img"
          />
        </div>
        <div class="img-modal-foot">
          <button class="btn btn-ghost" @click="previewFile = null">Tutup</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* ── Base ───────────────────────────────────────────────────────────────── */
.back-btn { background: none; border: none; color: var(--primary); cursor: pointer; padding: 0; margin-bottom: 12px; font-size: 0.85rem; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 8px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
h2 { margin: 0 0 16px; font-size: 1rem; color: var(--primary-dark); }
h3 { margin: 16px 0 10px; font-size: 0.9rem; color: var(--primary-dark); padding-left: 10px; border-left: 3px solid var(--primary); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.83rem; }
.note-green { font-size: 0.78rem; color: #16a34a; }
.mb-card { margin-bottom: 20px; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
.page-loading { color: var(--muted); padding: 60px; text-align: center; font-size: 0.9rem; }
.text-muted { color: var(--muted); font-size: 0.83rem; }
.file-link { color: var(--primary); font-size: 0.84rem; text-decoration: none; }
.file-link:hover { text-decoration: underline; }

/* ── Grid ───────────────────────────────────────────────────────────────── */
.grid-2col { display: grid; grid-template-columns: 1fr 300px; gap: 20px; align-items: start; }
@media (max-width: 860px) { .grid-2col { grid-template-columns: 1fr; } }

/* ── Status badge ───────────────────────────────────────────────────────── */
.status-badge { padding: 5px 14px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; text-transform: capitalize; height: fit-content; }
.status-badge.draft    { background: #f1f5f9; color: #475569; }
.status-badge.pending  { background: #fef3c7; color: #92400e; }
.status-badge.approved { background: #dbeafe; color: #1e40af; }
.status-badge.active   { background: #dcfce7; color: #166534; }
.status-badge.rejected { background: #fee2e2; color: #991b1b; }
.status-badge.paid_off { background: #e0e7ff; color: #3730a3; }

/* ── Rincian dl ─────────────────────────────────────────────────────────── */
dl { margin: 0; display: grid; gap: 8px; }
dl div { display: flex; justify-content: space-between; padding-bottom: 7px; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
dl div:last-child { border-bottom: none; padding-bottom: 0; }
dt { color: var(--muted); }
dd { margin: 0; font-weight: 600; text-align: right; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; transition: background 0.15s; }
.btn:hover:not(:disabled) { background: var(--primary-dark); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { background: #b91c1c; }
.btn-danger:hover:not(:disabled) { background: #991b1b; }
.btn-ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.btn-ghost:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.btn-return { background: #7c3aed; }
.btn-return:hover:not(:disabled) { background: #6d28d9; }
.btn-sm { padding: 7px 14px; font-size: 0.82rem; }

/* ── Aksi ───────────────────────────────────────────────────────────────── */
.action-stack { display: flex; flex-direction: column; gap: 10px; }
.field-label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 10px; }
.field-label input, .field-label select, .field-label textarea {
  display: block; width: 100%; margin-top: 4px; padding: 9px 10px;
  border: 1px solid var(--border); border-radius: 8px; font-size: 0.9rem;
  font-family: inherit; box-sizing: border-box;
}
.field-label input:focus, .field-label select:focus, .field-label textarea:focus {
  outline: none; border-color: var(--primary);
}

/* ── Informasi Jaminan ──────────────────────────────────────────────────── */
.col-grid { display: grid; grid-template-columns: 1fr 200px; gap: 24px; }
@media (max-width: 620px) { .col-grid { grid-template-columns: 1fr; } }
.col-right { display: flex; flex-direction: column; }
.col-status-block { display: flex; flex-direction: column; gap: 6px; }
.col-label { font-size: 0.75rem; color: var(--muted); }
.col-badge { display: inline-block; padding: 5px 14px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; width: fit-content; }
.col-available  { background: #dcfce7; color: #166534; }
.col-in_use     { background: #fef3c7; color: #92400e; }
.col-returned   { background: #dbeafe; color: #1e40af; }
.col-archived   { background: #f1f5f9; color: #475569; }
.doc-status-badge { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }
.doc-ok   { background: #dcfce7; color: #166534; }
.doc-warn { background: #fef3c7; color: #92400e; }

/* ── Return Modal ───────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 9998; padding: 20px;
}
.return-modal {
  background: #fff; border-radius: 16px; width: 100%; max-width: 480px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2); display: flex; flex-direction: column;
  animation: modal-in 0.18s ease;
}
@keyframes modal-in { from { opacity: 0; transform: scale(0.96) translateY(8px); } to { opacity: 1; transform: none; } }
.modal-head {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 20px 20px 16px; border-bottom: 1px solid var(--border);
}
.modal-title { margin: 0; font-size: 1rem; font-weight: 700; color: var(--primary-dark); }
.modal-sub { margin: 3px 0 0; font-size: 0.8rem; color: var(--muted); }
.modal-close {
  background: #f1f5f9; border: none; width: 28px; height: 28px; border-radius: 50%;
  cursor: pointer; font-size: 0.85rem; color: var(--muted); flex-shrink: 0; margin-top: 2px;
}
.modal-close:hover { background: #e2e8f0; }
.modal-body { padding: 20px; display: flex; flex-direction: column; gap: 4px; }
.field-hint { font-size: 0.74rem; color: var(--muted); margin-left: 4px; font-weight: 400; }
.file-selected { display: block; margin-top: 4px; font-size: 0.78rem; color: #16a34a; }
.modal-foot { display: flex; gap: 8px; justify-content: flex-end; padding-top: 16px; }
.modal-confirm {
  padding: 28px 24px 24px; display: flex; flex-direction: column; align-items: center; text-align: center; gap: 10px;
}
.confirm-icon { font-size: 2.4rem; }
.confirm-text { margin: 0; font-size: 0.95rem; font-weight: 600; color: var(--text); }
.confirm-detail { margin: 0; font-size: 0.84rem; color: var(--muted); }
.modal-confirm .modal-foot { width: 100%; justify-content: center; gap: 10px; }

/* ── Dokumen Jaminan ────────────────────────────────────────────────────── */
.docs-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; gap: 12px; }
.docs-header h2 { margin: 0; }
.upload-panel { background: #f8fafc; border: 1px dashed var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.upload-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.upload-row .field-label { margin-bottom: 0; }
.docs-empty { display: flex; flex-direction: column; align-items: center; padding: 36px 16px; gap: 6px; }
.docs-empty span { font-size: 2.4rem; }
.docs-empty p { margin: 0; color: var(--muted); font-size: 0.88rem; }
.table-scroll { overflow-x: auto; }
.docs-tbl { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.docs-tbl th, .docs-tbl td { padding: 10px 14px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.docs-tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; }
.docs-tbl tbody tr:last-child td { border-bottom: none; }
.docs-tbl tbody tr:hover td { background: #fafafa; }
.col-r { text-align: right; }
.filename-cell { max-width: 260px; word-break: break-all; font-size: 0.85rem; }
.doc-type-chip { display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; background: #eff6ff; color: #1e40af; border-radius: 6px; font-size: 0.8rem; font-weight: 500; white-space: nowrap; }
.doc-actions { display: flex; gap: 6px; justify-content: flex-end; }
.doc-btn { padding: 5px 12px; border: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.12s; text-decoration: none; display: inline-block; }
.lihat-btn { background: #dbeafe; color: #1e40af; }
.lihat-btn:hover { background: #bfdbfe; }
.dl-btn { background: #dcfce7; color: #166534; }
.dl-btn:hover { background: #bbf7d0; }

/* ── Riwayat Pengembalian ───────────────────────────────────────────────── */
.hist-tbl { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.hist-tbl th, .hist-tbl td { padding: 9px 12px; border: 1px solid var(--border); text-align: left; }
.hist-tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.75rem; text-transform: uppercase; }
.usage-badge { padding: 3px 10px; border-radius: 999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.ub-in  { background: #fef3c7; color: #92400e; }
.ub-out { background: #dcfce7; color: #166534; }

/* ── Audit timeline ─────────────────────────────────────────────────────── */
.timeline { display: flex; flex-direction: column; }
.tl-item  { display: flex; gap: 12px; }
.tl-col   { display: flex; flex-direction: column; align-items: center; width: 16px; flex-shrink: 0; }
.tl-dot   { width: 12px; height: 12px; border-radius: 50%; background: var(--primary); margin-top: 3px; flex-shrink: 0; }
.tl-line  { width: 2px; background: var(--border); flex: 1; margin: 3px 0; min-height: 14px; }
.tl-body  { padding-bottom: 18px; flex: 1; }
.tl-desc  { margin: 0; font-size: 0.88rem; color: var(--text); font-weight: 500; }
.tl-actor { margin: 4px 0 0; font-size: 0.8rem; color: var(--text); font-weight: 600; }
.tl-time  { margin: 1px 0 0; font-size: 0.74rem; color: var(--muted); }
.dot-loan_created .tl-dot { background: #64748b; }
.dot-loan_submitted .tl-dot { background: #0891b2; }
.dot-loan_approved .tl-dot, .dot-collateral_returned .tl-dot { background: #16a34a; }
.dot-loan_rejected .tl-dot { background: #b91c1c; }
.dot-loan_disbursed .tl-dot { background: #1e40af; }
.dot-payment_recorded .tl-dot { background: #7c3aed; }
.dot-loan_settled .tl-dot { background: #059669; }
.dot-collateral_attached .tl-dot { background: #d97706; }
.dot-document_uploaded .tl-dot { background: #0284c7; }
.dot-member_status_changed .tl-dot { background: #be185d; }

/* ── Image Preview Modal ────────────────────────────────────────────────── */
.img-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.84);
  display: flex; align-items: flex-start; justify-content: center;
  z-index: 9999; padding: 20px; overflow-y: auto;
}
.img-modal {
  background: #fff; border-radius: 14px; width: 100%; max-width: 940px;
  display: flex; flex-direction: column;
}
.img-modal-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; border-bottom: 1px solid var(--border); gap: 12px; flex-shrink: 0;
}
.img-modal-name { font-size: 0.86rem; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.zoom-controls { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.zoom-btn { padding: 4px 10px; background: #f1f5f9; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; font-size: 0.9rem; }
.zoom-btn:hover { background: #e2e8f0; }
.close-zoom-btn { background: #fee2e2; border-color: #fca5a5; color: #b91c1c; }
.close-zoom-btn:hover { background: #fecaca; }
.zoom-pct { font-size: 0.82rem; color: var(--muted); min-width: 40px; text-align: center; }
.img-viewport { overflow: auto; max-height: 75vh; padding: 20px; display: flex; justify-content: center; }
.preview-img { max-width: 100%; transition: transform 0.14s ease; display: block; }
.img-modal-foot {
  display: flex; gap: 8px; justify-content: flex-end;
  padding: 12px 16px; border-top: 1px solid var(--border); flex-shrink: 0;
}
.img-modal-foot .btn { padding: 8px 14px; font-size: 0.85rem; }
</style>
