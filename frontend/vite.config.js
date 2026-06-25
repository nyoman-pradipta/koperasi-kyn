import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],

  // Output build masuk ke folder yang disajikan FastAPI.
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },

  // Path relatif agar berfungsi saat disajikan dari root server FastAPI.
  base: './',

  // Saat `npm run dev`, teruskan panggilan /api ke server FastAPI (:8000),
  // sehingga kode frontend memakai URL yang sama persis dengan produksi.
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8001',
    },
  },
})
