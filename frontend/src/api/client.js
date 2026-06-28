import axios from 'axios'

// baseURL mengambil dari ENV, jika kosong (local dev) pakai '/api'
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
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
