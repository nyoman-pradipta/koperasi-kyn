<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import { useCurrency } from '../../composables/useCurrency'
import ScheduleTable from '../../components/loans/ScheduleTable.vue'
import CurrencyInput from '../../components/ui/CurrencyInput.vue'

const router = useRouter()
const ui = useUiStore()
const { rp } = useCurrency()

const members = ref([])
const sim = ref(null)
const saving = ref(false)

const maxLoanWithoutCollateral = ref(5000000)

async function loadSettings() {
  try {
    const { data } = await client.get('/settings')
    if (data.max_loan_without_collateral) {
      maxLoanWithoutCollateral.value = Number(data.max_loan_without_collateral)
    }
  } catch (e) {}
}

const form = reactive({
  member_id: '',
  principal_amount: 10000000,
  interest_rate: 2.5,
  interest_type: 'flat',
  tenor: 6,
  admin_pct: 4,
  provisi_pct: 1,
  form_fee: 200000,
  purpose: '',
})

// ---- Data Jaminan ----
const colMode = ref('existing')
const savedCollaterals = ref([])
const selectedColId = ref('')
const selectedCol = computed(() =>
  savedCollaterals.value.find(c => c.id === selectedColId.value) || null
)

const requiresCollateral = computed(() => form.principal_amount > maxLoanWithoutCollateral.value)
const useCollateral = ref(false)

watch(requiresCollateral, (req) => {
  if (req) useCollateral.value = true
}, { immediate: true })

const newCol = reactive({
  type: 'BPKB Motor',
  doc_number: '',
  owner_name: '',
  estimated_value: 0,
  doc_status: 'belum_diterima',
  doc_received_date: '',
  receiver_officer: '',
  storage_location: 'brankas',
  notes: '',
})
const colFiles = ref([])
const COL_TYPES = ['Sertifikat Tanah', 'BPKB Motor', 'BPKB Mobil', 'Lainnya']

async function loadMembers() {
  const { data } = await client.get('/members', { params: { status: 'aktif', page_size: 100 } })
  members.value = data.items
}

watch(() => form.member_id, async (mid) => {
  selectedColId.value = ''
  savedCollaterals.value = []
  if (!mid) return
  try {
    const { data } = await client.get('/collaterals/available', { params: { member_id: mid } })
    savedCollaterals.value = data
  } catch (_) {}
})

function onColFiles(e) {
  colFiles.value = Array.from(e.target.files || [])
}
function removeColFile(i) { colFiles.value.splice(i, 1) }

const STATUS_LABEL = {
  available: 'Tersedia',
  in_use: 'Sedang Digunakan',
  returned: 'Dikembalikan',
  archived: 'Diarsipkan',
}

async function simulate() {
  try {
    const { data } = await client.post('/simulate', {
      loan_amount: form.principal_amount,
      monthly_rate_pct: form.interest_rate,
      tenor: form.tenor,
      interest_type: form.interest_type,
      admin_pct: form.admin_pct,
      provisi_pct: form.provisi_pct,
      form_fee: form.form_fee,
    })
    sim.value = data
  } catch (e) {
    ui.notify('Gagal menghitung simulasi', 'error')
  }
}

async function save(submitAfter) {
  if (!form.member_id) { ui.notify('Pilih anggota terlebih dahulu', 'error'); return }
  if (useCollateral.value && colMode.value === 'new' && colFiles.value.length === 0) {
    ui.notify('Upload minimal 1 dokumen jaminan', 'error'); return
  }
  if (requiresCollateral.value && !useCollateral.value) {
    ui.notify('Jaminan wajib untuk nominal pinjaman ini', 'error'); return
  }

  saving.value = true
  try {
    const { data: loan } = await client.post('/loans', { ...form, requires_collateral: useCollateral.value })

    if (useCollateral.value) {
      if (colMode.value === 'existing' && selectedColId.value) {
        await client.post(`/collaterals/${selectedColId.value}/attach/${loan.id}`)
      } else if (colMode.value === 'new') {
        const payload = { ...newCol, member_id: Number(form.member_id), estimated_value: Number(newCol.estimated_value) || 0 }
        if (!payload.doc_received_date) delete payload.doc_received_date
        const { data: col } = await client.post('/collaterals', payload)

        for (const f of colFiles.value) {
          const fd = new FormData()
          fd.append('file', f)
          await client.post(`/collaterals/${col.id}/upload`, fd, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        }
        await client.post(`/collaterals/${col.id}/attach/${loan.id}`)
      }
    }

    if (submitAfter) {
      await client.post(`/loans/${loan.id}/submit`)
      ui.notify('Pengajuan dibuat & diajukan untuk persetujuan')
    } else {
      ui.notify('Pengajuan tersimpan sebagai draft')
    }
    router.push(`/pinjaman/${loan.id}`)
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal menyimpan pengajuan', 'error')
  } finally {
    saving.value = false
  }
}

const simRows = () =>
  (sim.value?.schedule || []).map(r => ({ no: r.month, principal: r.principal, interest: r.interest, total: r.total }))

onMounted(() => {
  loadMembers()
  loadSettings()
})
</script>

<template>
  <div>
    <h1>Pengajuan Pinjaman</h1>
    <p class="sub">Isi data pengajuan, tambahkan jaminan, lalu ajukan</p>

    <div class="grid">
      <div class="left-col">
        <!-- Form Pengajuan -->
        <section class="card">
          <h2>Form Pengajuan</h2>
          <label>
            Anggota *
            <select v-model="form.member_id">
              <option value="" disabled>— pilih anggota —</option>
              <option v-for="m in members" :key="m.id" :value="m.id">
                {{ m.member_number }} — {{ m.full_name }}
              </option>
            </select>
          </label>
          <div class="row">
            <label>Nominal Pinjaman (Rp)
              <CurrencyInput v-model="form.principal_amount" />
            </label>
            <label>Jenis Bunga
              <select v-model="form.interest_type">
                <option value="flat">Flat</option>
                <option value="menurun">Menurun</option>
              </select>
            </label>
          </div>
          <div class="row">
            <label>Bunga / Bulan (%)
              <input type="number" v-model.number="form.interest_rate" step="0.1" />
            </label>
            <label>Tenor (bulan)
              <input type="number" v-model.number="form.tenor" step="1" />
            </label>
          </div>
          <div class="row">
            <label>Biaya Admin (%)
              <input type="number" v-model.number="form.admin_pct" step="0.1" />
            </label>
            <label>Provisi (%)
              <input type="number" v-model.number="form.provisi_pct" step="0.1" />
            </label>
          </div>
          <label>Biaya Form &amp; Pemeriksaan (Rp)
            <CurrencyInput v-model="form.form_fee" />
          </label>
          <label>Tujuan / Keperluan
            <input v-model="form.purpose" placeholder="mis. Modal usaha" />
          </label>
        </section>

        <!-- Data Jaminan -->
        <section class="card" style="margin-top:16px">
          <h2>Data Jaminan</h2>

          <div v-if="requiresCollateral" class="banner banner-warn">
            ⚠ Jaminan wajib untuk nominal pinjaman ini.
          </div>
          <div v-else class="banner banner-ok">
            ✓ Pinjaman ini dapat diajukan tanpa jaminan.
            <label class="cb-label">
              <input type="checkbox" v-model="useCollateral" />
              Tetap gunakan jaminan
            </label>
          </div>

          <template v-if="useCollateral">
            <div class="radio-group">
            <label class="radio-opt">
              <input type="radio" v-model="colMode" value="existing" />
              Gunakan Jaminan Tersimpan
            </label>
            <label class="radio-opt">
              <input type="radio" v-model="colMode" value="new" />
              Tambah Jaminan Baru
            </label>
          </div>

          <!-- Mode: jaminan tersimpan -->
          <template v-if="colMode === 'existing'">
            <p v-if="!form.member_id" class="hint">Pilih anggota terlebih dahulu.</p>
            <template v-else>
              <label>Pilih Jaminan
                <select v-model="selectedColId">
                  <option value="" disabled>— pilih jaminan —</option>
                  <option
                    v-for="c in savedCollaterals"
                    :key="c.id"
                    :value="c.id"
                    :disabled="c.collateral_status !== 'available'"
                  >
                    {{ c.type }}{{ c.doc_number ? ' · ' + c.doc_number : '' }}
                  </option>
                </select>
              </label>
              <div v-if="selectedCol" class="col-preview">
                <div><span>Jenis Jaminan</span><strong>{{ selectedCol.type }}</strong></div>
                <div><span>Nomor Dokumen</span><strong>{{ selectedCol.doc_number || '-' }}</strong></div>
                <div><span>Nama Pemilik</span><strong>{{ selectedCol.owner_name || '-' }}</strong></div>
                <div>
                  <span>Status Dok. Asli</span>
                  <strong :class="selectedCol.doc_status === 'sudah_diterima' ? 'ok' : 'warn'">
                    {{ selectedCol.doc_status === 'sudah_diterima' ? 'Sudah diterima' : 'Belum diterima' }}
                  </strong>
                </div>
                <div v-if="JSON.parse(selectedCol.file_paths || '[]').length">
                  <span>Foto Dokumen</span>
                  <div class="file-chips">
                    <a v-for="(p, i) in JSON.parse(selectedCol.file_paths)" :key="i"
                       :href="'/' + p" target="_blank" class="chip">📎 File {{ i + 1 }}</a>
                  </div>
                </div>
              </div>
              <p v-else-if="savedCollaterals.length === 0" class="hint">Anggota belum punya jaminan tersimpan.</p>
            </template>
          </template>

          <!-- Mode: jaminan baru -->
          <template v-else>
            <div class="row">
              <label>Jenis Jaminan *
                <select v-model="newCol.type">
                  <option v-for="t in COL_TYPES" :key="t" :value="t">{{ t }}</option>
                </select>
              </label>
              <label>Nomor Dokumen
                <input v-model="newCol.doc_number" placeholder="No. Sertifikat / BPKB" />
              </label>
            </div>
            <div class="row">
              <label>Nama Pemilik
                <input v-model="newCol.owner_name" placeholder="Sesuai dokumen" />
              </label>
              <label>Estimasi Nilai (Rp)
                <CurrencyInput v-model="newCol.estimated_value" />
              </label>
            </div>
            <label>
              Upload Foto / Dokumen * <span class="hint-sm">(JPG/PNG/PDF, maks 10 MB, multi-file)</span>
              <input type="file" accept=".jpg,.jpeg,.png,.pdf" multiple @change="onColFiles" style="margin-top:6px" />
            </label>
            <div v-if="colFiles.length" class="file-chips" style="margin-bottom:10px">
              <span v-for="(f, i) in colFiles" :key="i" class="chip">
                {{ f.name }}
                <button @click="removeColFile(i)" class="chip-del">×</button>
              </span>
            </div>
            <div class="row">
              <label>Status Dokumen Asli
                <select v-model="newCol.doc_status">
                  <option value="belum_diterima">Belum diterima</option>
                  <option value="sudah_diterima">Sudah diterima</option>
                </select>
              </label>
              <label>Tanggal Serah Dokumen
                <input type="date" v-model="newCol.doc_received_date" />
              </label>
            </div>
            <div class="row">
              <label>Petugas Penerima
                <input v-model="newCol.receiver_officer" placeholder="Nama petugas" />
              </label>
              <label>Lokasi Penyimpanan
                <select v-model="newCol.storage_location">
                  <option value="brankas">Brankas</option>
                  <option value="lemari">Lemari</option>
                </select>
              </label>
            </div>
            <label>Catatan
              <textarea v-model="newCol.notes" rows="2" placeholder="Opsional" />
            </label>
          </template>
          </template>
        </section>

        <div class="actions-bar">
          <button class="btn ghost" @click="simulate">Lihat Simulasi</button>
          <button class="btn ghost" :disabled="saving" @click="save(false)">Simpan Draft</button>
          <button class="btn" :disabled="saving" @click="save(true)">Ajukan</button>
        </div>
      </div>

      <!-- Simulasi -->
      <section v-if="sim" class="card">
        <h2>Simulasi ({{ sim.input.interest_type }})</h2>
        <div class="summary">
          <div><span>Total Bunga</span><strong>{{ rp(sim.total_interest) }}</strong></div>
          <div><span>Total Pembayaran</span><strong>{{ rp(sim.total_payable) }}</strong></div>
          <div><span>Total Potongan</span><strong>{{ rp(sim.fees.total_fees) }}</strong></div>
          <div class="net"><span>Dana Bersih Diterima</span><strong>{{ rp(sim.disbursement.net_received) }}</strong></div>
        </div>
        <ScheduleTable :rows="simRows()" />
      </section>
      <section v-else class="card placeholder">
        Klik <strong>Lihat Simulasi</strong> untuk menampilkan rincian angsuran.
      </section>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 20px; color: var(--muted); font-size: 0.85rem; }
.grid { display: grid; grid-template-columns: 420px 1fr; gap: 20px; align-items: start; }
@media (max-width: 960px) { .grid { grid-template-columns: 1fr; } }
.left-col { display: flex; flex-direction: column; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
h2 { margin: 0 0 14px; font-size: 1rem; color: var(--primary-dark); }
label { display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 10px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
input, select, textarea { width: 100%; margin-top: 4px; padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.92rem; font-family: inherit; box-sizing: border-box; }
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--primary); }
.actions-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.radio-group { display: flex; gap: 20px; margin-bottom: 14px; }
.radio-opt { display: flex; align-items: center; gap: 6px; font-size: 0.88rem; color: var(--text); margin: 0; cursor: pointer; }
.radio-opt input { width: auto; margin: 0; }
.col-preview { background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.col-preview > div { display: flex; justify-content: space-between; align-items: flex-start; font-size: 0.85rem; }
.col-preview span { color: var(--muted); }
.ok { color: #166534; }
.warn { color: #92400e; }
.file-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.chip { background: #f1f5f9; padding: 4px 10px; border-radius: 999px; font-size: 0.8rem; }
.chip.btn { cursor: pointer; border: none; }
.chip.btn:hover { background: #fee2e2; color: #991b1b; }

.banner {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 0.92rem;
}
.banner-warn {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fef3c7;
}
.banner-ok {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #dcfce7;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.cb-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: inherit;
  margin: 0;
}
.chip-del { background: none; border: none; cursor: pointer; color: #b91c1c; font-size: 1rem; padding: 0; line-height: 1; }
.hint { color: var(--muted); font-size: 0.82rem; margin: 4px 0 10px; }
.hint-sm { font-size: 0.74rem; font-weight: normal; }
.summary { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
.summary div { background: #f8fafc; border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; }
.summary span { font-size: 0.75rem; color: var(--muted); }
.summary strong { font-size: 1.05rem; }
.summary .net { background: var(--primary); color: #fff; grid-column: 1 / -1; }
.summary .net span { color: rgba(255,255,255,0.85); }
.placeholder { color: var(--muted); display: flex; align-items: center; justify-content: center; min-height: 180px; }
</style>
