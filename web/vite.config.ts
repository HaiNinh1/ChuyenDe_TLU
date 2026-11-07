import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Khi chạy `npm run dev`, mọi request /api được chuyển sang server Python (server.py, cổng 8000).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  build: { chunkSizeWarningLimit: 1500 }, // app chạy cục bộ, không cần tách nhỏ file JS
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
