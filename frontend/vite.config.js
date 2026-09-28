import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // En dev, les appels /api sont envoyés au backend FastAPI
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
