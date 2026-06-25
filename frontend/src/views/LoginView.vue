<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Gagal masuk'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="wrap">
    <form class="box" @submit.prevent="submit">
      <div class="brand">
        <span class="logo">KOP</span>
        <h1>Koperasi Simpan Pinjam</h1>
        <p>Masuk untuk melanjutkan</p>
      </div>

      <label>Username
        <input v-model="username" autofocus autocomplete="username" />
      </label>
      <label>Password
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>

      <p v-if="error" class="error">{{ error }}</p>

      <button class="btn" :disabled="loading">{{ loading ? 'Memproses…' : 'Masuk' }}</button>
    </form>
  </div>
</template>

<style scoped>
.wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--bg); padding: 20px; }
.box { background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 30px; width: 100%; max-width: 360px; box-shadow: 0 6px 24px rgba(0,0,0,0.06); display: flex; flex-direction: column; gap: 14px; }
.brand { text-align: center; margin-bottom: 6px; }
.logo { display: inline-block; background: var(--primary); color: #fff; font-weight: 800; border-radius: 10px; padding: 8px 12px; letter-spacing: 1px; }
.brand h1 { font-size: 1.1rem; margin: 12px 0 2px; color: var(--primary-dark); }
.brand p { margin: 0; color: var(--muted); font-size: 0.85rem; }
label { font-size: 0.82rem; color: var(--muted); }
input { width: 100%; margin-top: 4px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; font-size: 0.95rem; }
input:focus { outline: none; border-color: var(--primary); }
.btn { padding: 11px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-weight: 700; cursor: pointer; }
.btn:hover:not(:disabled) { background: var(--primary-dark); }
.btn:disabled { opacity: 0.6; }
.error { color: #b91c1c; font-size: 0.85rem; margin: 0; }
.hint { text-align: center; color: var(--muted); font-size: 0.78rem; margin: 0; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }
</style>
