import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Tahap 2b: UI membaca ../cases/*.json langsung sebagai mock (belum ada backend).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { fs: { allow: ['..'] } },
})
