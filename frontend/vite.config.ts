import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  optimizeDeps: { include: ['dagre'] },
  server: {
    host: '127.0.0.1',
    port: Number(process.env.FRONTEND_PORT || 5177),
    allowedHosts: ['ontology.ojlab.com'],
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
