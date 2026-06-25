<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useUiStore } from '../stores/ui'
import { useAuthStore } from '../stores/auth'

const ui = useUiStore()
const router = useRouter()
const auth = useAuthStore()
const { toast } = storeToRefs(ui)

const menu = computed(() => {
  const items = [
    { to: '/', label: 'Dashboard', icon: '📊' },
    { to: '/anggota', label: 'Data Anggota', icon: '👥' },
    { to: '/simulasi', label: 'Simulasi Kredit', icon: '🧮' },
    { to: '/pengajuan', label: 'Pengajuan', icon: '📝' },
    { to: '/persetujuan', label: 'Persetujuan', icon: '✅' },
    { to: '/pinjaman', label: 'Data Pinjaman', icon: '💳' },
    { to: '/pengingat', label: 'Pengingat', icon: '📱' },
    { to: '/pembayaran', label: 'Pembayaran', icon: '🧾' },
    { to: '/simpanan', label: 'Simpanan', icon: '🏦' },
    { to: '/kas', label: 'Kas & Keuangan', icon: '💰' },
    { to: '/laporan', label: 'Laporan', icon: '📑' },
  ]
  if (auth.isAdmin) items.push({ to: '/pengguna', label: 'Pengguna', icon: '🧑‍💼' })
  items.push({ to: '/pengaturan', label: 'Pengaturan', icon: '⚙️' })
  return items
})

async function doLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">KOP</span>
        <span class="brand-text">Koperasi</span>
      </div>
      <nav>
        <RouterLink
          v-for="m in menu"
          :key="m.to"
          :to="m.to"
          class="nav-item"
          exact-active-class="active"
        >
          <span class="icon">{{ m.icon }}</span>{{ m.label }}
        </RouterLink>
      </nav>
      <div class="sidebar-foot">Mode Lokal · Offline</div>
    </aside>

    <div class="main">
      <header class="topbar">
        <strong>Sistem Koperasi Simpan Pinjam</strong>
        <div class="user-area">
          <span class="user">👤 {{ auth.user?.full_name || '-' }}
            <em>({{ auth.user?.role }})</em></span>
          <button class="logout" @click="doLogout">Keluar</button>
        </div>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>

    <!-- Toast global -->
    <transition name="fade">
      <div v-if="toast" class="toast" :class="toast.type">
        {{ toast.message }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 230px;
  background: var(--primary-dark);
  color: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.logo {
  background: #fff;
  color: var(--primary-dark);
  font-weight: 800;
  border-radius: 8px;
  padding: 6px 9px;
  font-size: 0.85rem;
}

.brand-text {
  font-weight: 700;
}

nav {
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 0.9rem;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.nav-item.active {
  background: var(--primary);
  color: #fff;
  font-weight: 600;
}

.icon {
  font-size: 1rem;
}

.sidebar-foot {
  margin-top: auto;
  padding: 14px 18px;
  font-size: 0.72rem;
  opacity: 0.7;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topbar {
  background: #fff;
  border-bottom: 1px solid var(--border);
  padding: 14px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user {
  font-size: 0.85rem;
  color: var(--muted);
}

.user em {
  font-style: normal;
  color: var(--primary);
  text-transform: capitalize;
}

.logout {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.82rem;
  cursor: pointer;
  color: var(--text);
}

.logout:hover {
  border-color: #b91c1c;
  color: #b91c1c;
}

.content {
  padding: 24px;
  flex: 1;
}

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 18px;
  border-radius: 10px;
  color: #fff;
  font-size: 0.9rem;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
}

.toast.success {
  background: var(--primary);
}

.toast.error {
  background: #b91c1c;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
