import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '../api/client'

const TOKEN_KEY = 'koperasi_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setToken(t) {
    token.value = t
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  }

  async function login(username, password) {
    const { data } = await client.post('/auth/login', { username, password })
    setToken(data.token)
    user.value = data.user
    return data.user
  }

  async function fetchMe() {
    if (!token.value) return null
    try {
      const { data } = await client.get('/auth/me')
      user.value = data
      return data
    } catch (e) {
      logout()
      return null
    }
  }

  async function logout() {
    try {
      if (token.value) await client.post('/auth/logout')
    } catch (e) {
      /* abaikan */
    }
    setToken('')
    user.value = null
  }

  return { token, user, isAuthenticated, isAdmin, login, fetchMe, logout, setToken }
})
