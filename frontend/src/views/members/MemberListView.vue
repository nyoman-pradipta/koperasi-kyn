<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import client from '../../api/client'
import { useUiStore } from '../../stores/ui'
import BaseModal from '../../components/ui/BaseModal.vue'
import MemberForm from '../../components/members/MemberForm.vue'

const router = useRouter()
const ui = useUiStore()

const members  = ref([])
const total    = ref(0)
const search   = ref('')
const statusFilter = ref('')
const loading  = ref(false)

const showModal = ref(false)
const editing   = ref({})

const STATUS_OPTIONS = ['', 'aktif', 'nonaktif', 'diblokir', 'diarsipkan']
const STATUS_LABEL   = { aktif: 'Aktif', nonaktif: 'Nonaktif', diblokir: 'Diblokir', diarsipkan: 'Diarsipkan' }

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/members', {
      params: { search: search.value || undefined, status: statusFilter.value || undefined, page_size: 50 },
    })
    members.value = data.items
    total.value   = data.total
  } catch {
    ui.notify('Gagal memuat data anggota', 'error')
  } finally {
    loading.value = false
  }
}

function openAdd()   { editing.value = {}; showModal.value = true }
function openEdit(m) { editing.value = { ...m }; showModal.value = true }
function goDetail(m) { router.push(`/anggota/${m.id}`) }

async function handleSubmit(payload) {
  try {
    if (editing.value.id) {
      await client.put(`/members/${editing.value.id}`, payload)
      ui.notify('Data anggota diperbarui')
    } else {
      await client.post('/members', payload)
      ui.notify('Anggota baru ditambahkan')
    }
    showModal.value = false
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal menyimpan', 'error')
  }
}

async function setStatus(m, status) {
  const label = { nonaktif: 'Nonaktifkan', diblokir: 'Blokir', diarsipkan: 'Arsipkan', aktif: 'Aktifkan kembali' }
  if (!confirm(`${label[status] || status} anggota "${m.full_name}"?`)) return
  try {
    await client.post(`/members/${m.id}/set-status?status=${status}`)
    ui.notify('Status anggota diperbarui')
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mengubah status', 'error')
  }
}

async function archive(m) {
  if (!confirm(`Arsipkan anggota "${m.full_name}"?\nData historis akan tetap tersimpan.`)) return
  try {
    await client.post(`/members/${m.id}/archive`)
    ui.notify('Anggota diarsipkan')
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal mengarsipkan', 'error')
  }
}

async function remove(m) {
  if (!confirm(`Hapus permanen anggota "${m.full_name}"?\nTindakan ini tidak bisa dibatalkan.`)) return
  try {
    await client.delete(`/members/${m.id}`)
    ui.notify('Anggota dihapus')
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal menghapus', 'error')
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h1>Data Anggota</h1>
        <p class="sub">{{ total }} anggota terdaftar</p>
      </div>
      <button class="btn" @click="openAdd">+ Tambah Anggota</button>
    </div>

    <div class="toolbar">
      <input v-model="search" class="search" placeholder="Cari nama / no anggota / NIK…" @keyup.enter="load" />
      <select v-model="statusFilter" @change="load">
        <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ s ? STATUS_LABEL[s] : 'Semua status' }}</option>
      </select>
      <button class="btn ghost" @click="load">Cari</button>
    </div>

    <div class="card">
      <table class="tbl">
        <thead>
          <tr>
            <th>No. Anggota</th>
            <th>Nama</th>
            <th>NIK</th>
            <th>No. HP</th>
            <th>Pinjaman Aktif</th>
            <th>Status Anggota</th>
            <th class="ta-right">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="empty">Memuat…</td></tr>
          <tr v-else-if="members.length === 0"><td colspan="7" class="empty">Belum ada data anggota.</td></tr>
          <tr v-for="m in members" :key="m.id">
            <td>{{ m.member_number }}</td>
            <td>
              <button class="name-link" @click="goDetail(m)">{{ m.full_name }}</button>
            </td>
            <td>{{ m.nik || '—' }}</td>
            <td>{{ m.phone || '—' }}</td>
            <td>
              <span v-if="m.active_loans_count > 0" class="loan-badge active-loan">
                {{ m.active_loans_count }} Pinjaman Aktif
              </span>
              <span v-else class="loan-badge no-loan">Tidak Ada Pinjaman</span>
            </td>
            <td>
              <span class="badge" :class="'st-' + m.status">{{ STATUS_LABEL[m.status] || m.status }}</span>
            </td>
            <td class="ta-right">
              <div class="action-row">
                <button class="link" @click="goDetail(m)">Detail</button>
                <button class="link" @click="openEdit(m)">Edit</button>

                <!-- Nonaktifkan / Aktifkan -->
                <span v-if="m.status === 'aktif'" class="tooltip-wrap">
                  <button
                    class="link warn"
                    :disabled="m.active_loans_count > 0"
                    @click="setStatus(m, 'nonaktif')"
                  >Nonaktifkan</button>
                  <span v-if="m.active_loans_count > 0" class="tooltip-text">Masih memiliki pinjaman atau pengajuan aktif.</span>
                </span>
                <button v-else-if="m.status === 'nonaktif' || m.status === 'diblokir'" class="link ok" @click="setStatus(m, 'aktif')">Aktifkan</button>

                <!-- Arsipkan vs Hapus -->
                <button v-if="m.has_any_data" class="link danger" @click="archive(m)">Arsipkan</button>
                <button v-else class="link danger" @click="remove(m)">Hapus</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal :show="showModal" :title="editing.id ? 'Edit Anggota' : 'Tambah Anggota'" @close="showModal = false">
      <MemberForm :model-value="editing" @submit="handleSubmit" @cancel="showModal = false" />
    </BaseModal>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.85rem; }
.toolbar { display: flex; gap: 10px; margin-bottom: 14px; }
.search { flex: 1; max-width: 360px; padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; }
select { padding: 9px 12px; border: 1px solid var(--border); border-radius: 8px; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.tbl th, .tbl td { padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }
.tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.ta-right { text-align: right; }
.empty { text-align: center; color: var(--muted); padding: 28px; }

.name-link { background: none; border: none; cursor: pointer; color: var(--primary); font-weight: 600; font-size: 0.9rem; padding: 0; }
.name-link:hover { text-decoration: underline; }

.badge { padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; }
.st-aktif      { background: #dcfce7; color: #166534; }
.st-nonaktif   { background: #fee2e2; color: #991b1b; }
.st-diblokir   { background: #fef3c7; color: #92400e; }
.st-diarsipkan { background: #f1f5f9; color: #475569; }

.loan-badge  { padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; }
.active-loan { background: #fef3c7; color: #92400e; }
.no-loan     { background: #f1f5f9; color: #64748b; }

.action-row { display: flex; gap: 4px; justify-content: flex-end; align-items: center; flex-wrap: wrap; }
.link { border: none; background: none; cursor: pointer; color: var(--primary); font-size: 0.82rem; padding: 3px 6px; border-radius: 4px; }
.link:hover:not(:disabled) { background: #f0f4ff; }
.link.warn   { color: #92400e; }
.link.ok     { color: #166534; }
.link.danger { color: #b91c1c; }
.link:disabled { opacity: 0.4; cursor: not-allowed; }

.tooltip-wrap { position: relative; display: inline-block; }
.tooltip-text { display: none; position: absolute; bottom: calc(100% + 4px); right: 0; background: #1e293b; color: #fff; font-size: 0.72rem; padding: 5px 9px; border-radius: 6px; white-space: nowrap; z-index: 20; pointer-events: none; }
.tooltip-wrap:hover .tooltip-text { display: block; }

.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
</style>
