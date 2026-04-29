import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/xpost/',
  server: {
    proxy: {
      '/xpost/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/xpost\/api/, '')
      }
    }
  }
})
