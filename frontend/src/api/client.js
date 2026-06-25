import axios from 'axios'

// baseURL '/api' → same-origin di produksi; saat dev di-proxy Vite ke :8001.
const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Sisipkan token login (jika ada) ke setiap request.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('koperasi_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Jika sesi tidak valid (401), bersihkan token & arahkan ke halaman login.
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('koperasi_token')
      if (!location.hash.startsWith('#/login')) location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

export default client
