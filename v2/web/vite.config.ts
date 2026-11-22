import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

// Milestone A: catatan review dari UI disimpan ke v2/review/notes.json (hanya dev server).
const REVIEW_FILE = fileURLToPath(new URL('../review/notes.json', import.meta.url))

function reviewNotes(): Plugin {
  return {
    name: 'tpt-review-notes',
    configureServer(server) {
      server.middlewares.use('/__review', (req, res) => {
        if (req.method === 'GET') {
          res.setHeader('Content-Type', 'application/json')
          res.end(existsSync(REVIEW_FILE) ? readFileSync(REVIEW_FILE, 'utf8') : 'null')
          return
        }
        if (req.method === 'POST') {
          let body = ''
          req.on('data', (c: Buffer) => (body += c.toString('utf8')))
          req.on('end', () => {
            try {
              const data = JSON.parse(body) as { version?: number; notes?: unknown }
              if (data.version !== 1 || !Array.isArray(data.notes)) throw new Error('format')
              mkdirSync(dirname(REVIEW_FILE), { recursive: true })
              writeFileSync(REVIEW_FILE, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
              res.statusCode = 204
            } catch {
              res.statusCode = 400
            }
            res.end()
          })
          return
        }
        res.statusCode = 405
        res.end()
      })
    },
  }
}

// Tahap 4: /api diteruskan ke FastAPI (uvicorn :8000, konfigurasi "api" di .claude/launch.json).
// Kasus awal tetap dibundel dari ../cases/*.json agar UI terbuka walau API mati (angka hasil → placeholder).
const API_TARGET = process.env.TPT_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss(), reviewNotes()],
  server: {
    fs: { allow: ['..'] },
    watch: { ignored: ['**/review/notes.json'] },
    proxy: { '/api': { target: API_TARGET, changeOrigin: false } },
  },
})
