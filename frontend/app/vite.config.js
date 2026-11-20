import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  server: {
    proxy: {
      '/api/': {
        target: process.env.MECHGUARD_BACKEND_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: path => path.slice(4),
      },
    },
  },
  plugins: [react(), tailwindcss()],
})