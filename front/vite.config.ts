import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:5435',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // La cache de dependencias fuera de node_modules: dentro, Vite necesita
  // escribir en `.vite/deps_temp_*` y en entornos con node_modules de solo
  // lectura (contenedores, montajes de red) el arranque falla con EACCES.
  cacheDir: process.env.VITE_CACHE_DIR || 'node_modules/.vite',
})
