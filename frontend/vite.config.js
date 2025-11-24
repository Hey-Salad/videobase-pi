import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    allowedHosts: [
      '782172c4807b.ngrok-free.app',
    ],
    proxy: {
      '/ws': {
        target: 'ws://127.0.0.1:9200',
        ws: true,
        rewrite: (path) => path,
      },
      '/api': {
        target: 'http://127.0.0.1:9200',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/health': {
        target: 'http://127.0.0.1:9200',
        changeOrigin: true,
      },
      '/device-info': {
        target: 'http://127.0.0.1:9200',
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
})
