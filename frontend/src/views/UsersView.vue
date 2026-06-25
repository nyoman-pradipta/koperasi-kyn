<script setup>
import { ref, reactive, onMounted } from 'vue'
import client from '../api/client'
import { useUiStore } from '../stores/ui'
import { useAuthStore } from '../stores/auth'
import BaseModal from '../components/ui/BaseModal.vue'

const ui = useUiStore()
const auth = useAuthStore()

const users = ref([])
const showModal = ref(false)
const form = reactive({ username: '', password: '', full_name: '', role: 'petugas' })

async function load() {
  const { data } = await client.get('/users')
  users.value = data
}

function openAdd() {
  Object.assign(form, { username: '', password: '', full_name: '', role: 'petugas' })
  showModal.value = true
}

async function create() {
  try {
    await client.post('/users', { ...form })
    ui.notify('Pengguna ditambahkan')
    showModal.value = false
    load()
  } catch (e) {
    ui.notify(e.response?.data?.detail || 'Gagal menambah pengguna', 'error')
  }
}

async function toggleActive(u) {
  await client.put(`/users/${u.id}`, { is_active: u.is_active ? 0 : 1 })
  load()
}

async function remove(u) {
  if (!confirm(`Hapus pengguna "${u.username}"?`)) return
  try {
    await client.delete(`/users/${u.id}`)
    ui.notify('Pengguna dihapus')
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
        <h1>Pengguna (Petugas)</h1>
        <p class="sub">Kelola akun admin & petugas koperasi</p>
      </div>
      <button class="btn" @click="openAdd">+ Tambah Pengguna</button>
    </div>

    <div class="card">
      <table class="tbl">
        <thead><tr><th>Username</th><th>Nama</th><th>Peran</th><th>Status</th><th class="ta-right">Aksi</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ u.full_name }}</td>
            <td><span class="badge" :class="u.role">{{ u.role }}</span></td>
            <td>{{ u.is_active ? 'Aktif' : 'Nonaktif' }}</td>
            <td class="ta-right">
              <button class="link" @click="toggleActive(u)">{{ u.is_active ? 'Nonaktifkan' : 'Aktifkan' }}</button>
              <button v-if="u.id !== auth.user?.id" class="link danger" @click="remove(u)">Hapus</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal :show="showModal" title="Tambah Pengguna" @close="showModal = false">
      <div class="form">
        <label>Username<input v-model="form.username" /></label>
        <label>Nama Lengkap<input v-model="form.full_name" /></label>
        <label>Password<input v-model="form.password" type="password" /></label>
        <label>Peran
          <select v-model="form.role">
            <option value="petugas">Petugas</option>
            <option value="admin">Admin</option>
          </select>
        </label>
      </div>
      <template #footer>
        <button class="btn ghost" @click="showModal = false">Batal</button>
        <button class="btn" @click="create">Simpan</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 16px; }
h1 { margin: 0; font-size: 1.3rem; color: var(--primary-dark); }
.sub { margin: 2px 0 0; color: var(--muted); font-size: 0.85rem; }
.card { background: #fff; border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.tbl { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.tbl th, .tbl td { padding: 11px 14px; text-align: left; border-bottom: 1px solid var(--border); }
.tbl th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }
.ta-right { text-align: right; }
.badge { padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 600; }
.badge.admin { background: #e0e7ff; color: #3730a3; }
.badge.petugas { background: #f1f5f9; color: #475569; }
.btn { padding: 10px 16px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn:hover { background: var(--primary-dark); }
.btn.ghost { background: #fff; color: var(--text); border: 1px solid var(--border); }
.link { border: none; background: none; cursor: pointer; color: var(--primary); font-size: 0.85rem; padding: 4px 6px; }
.link.danger { color: #b91c1c; }
.form { display: grid; gap: 12px; }
.form label { font-size: 0.8rem; color: var(--muted); }
.form input, .form select { width: 100%; margin-top: 4px; padding: 9px 10px; border: 1px solid var(--border); border-radius: 8px; font-family: inherit; }
</style>
