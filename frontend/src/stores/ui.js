import { defineStore } from 'pinia'
import { ref } from 'vue'

// Store UI global: notifikasi toast sederhana.
export const useUiStore = defineStore('ui', () => {
  const toast = ref(null) // { type: 'success'|'error', message }

  function notify(message, type = 'success') {
    toast.value = { message, type }
    setTimeout(() => {
      toast.value = null
    }, 3000)
  }

  return { toast, notify }
})
