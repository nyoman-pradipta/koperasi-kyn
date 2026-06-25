import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// createWebHashHistory dipakai agar aman saat disajikan langsung dari
// static files FastAPI (tanpa konfigurasi rewrite server tambahan).
const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Masuk', public: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { title: 'Dashboard' },
  },
  {
    path: '/anggota',
    name: 'members',
    component: () => import('../views/members/MemberListView.vue'),
    meta: { title: 'Data Anggota' },
  },
  {
    path: '/anggota/:id',
    name: 'member-detail',
    component: () => import('../views/members/MemberDetailView.vue'),
    meta: { title: 'Detail Anggota' },
  },
  {
    path: '/simulasi',
    name: 'simulation',
    component: () => import('../views/SimulationView.vue'),
    meta: { title: 'Simulasi Kredit' },
  },
  {
    path: '/pengajuan',
    name: 'loan-application',
    component: () => import('../views/loans/LoanApplicationView.vue'),
    meta: { title: 'Pengajuan Pinjaman' },
  },
  {
    path: '/persetujuan',
    name: 'approval',
    component: () => import('../views/ApprovalView.vue'),
    meta: { title: 'Persetujuan Kredit' },
  },
  {
    path: '/pinjaman',
    name: 'loans',
    component: () => import('../views/loans/LoanListView.vue'),
    meta: { title: 'Data Pinjaman' },
  },
  {
    path: '/pinjaman/:id',
    name: 'loan-detail',
    component: () => import('../views/loans/LoanDetailView.vue'),
    meta: { title: 'Detail Pinjaman' },
  },
  {
    path: '/pembayaran',
    name: 'payments',
    component: () => import('../views/payments/PaymentView.vue'),
    meta: { title: 'Pembayaran Angsuran' },
  },
  {
    path: '/simpanan',
    name: 'savings',
    component: () => import('../views/savings/SavingsView.vue'),
    meta: { title: 'Simpanan' },
  },
  {
    path: '/kas',
    name: 'cash',
    component: () => import('../views/CashView.vue'),
    meta: { title: 'Kas & Keuangan' },
  },
  {
    path: '/laporan',
    name: 'reports',
    component: () => import('../views/ReportsView.vue'),
    meta: { title: 'Laporan' },
  },
  {
    path: '/pengguna',
    name: 'users',
    component: () => import('../views/UsersView.vue'),
    meta: { title: 'Pengguna', admin: true },
  },
  {
    path: '/pengaturan',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { title: 'Pengaturan' },
  },
  {
    path: '/pengingat',
    name: 'reminders',
    component: () => import('../views/reminders/ReminderView.vue'),
    meta: { title: 'Pengingat Jatuh Tempo' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// Guard: wajib login kecuali route public; halaman admin hanya untuk admin.
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    return auth.isAuthenticated ? { path: '/' } : true
  }
  if (!auth.isAuthenticated) {
    return { path: '/login' }
  }
  if (!auth.user) {
    await auth.fetchMe()
  }
  if (to.meta.admin && !auth.isAdmin) {
    return { path: '/' }
  }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title || 'Koperasi'} — Koperasi`
})

export default router
