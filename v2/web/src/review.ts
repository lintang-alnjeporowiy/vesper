import { useEffect } from 'react'
import { create } from 'zustand'

// Milestone A: catatan koreksi pengguna per layar/variabel. Disimpan di localStorage dan, saat
// dev server berjalan, disinkronkan ke v2/review/notes.json (plugin Vite /__review) agar agen
// bisa membaca dan menerapkannya ke registry & SPEC.

export const NOTE_TOPICS = ['nama', 'keterangan', 'rumus', 'dependensi', 'satuan', 'data', 'tampilan', 'lainnya'] as const
export type NoteTopic = (typeof NOTE_TOPICS)[number]

export interface ReviewNote {
  id: string
  screen: number
  varId?: string
  topic: NoteTopic
  text: string
  at: string
  done: boolean
}

export interface ReviewFile {
  version: 1
  updated: string
  reviewed: number[]
  notes: ReviewNote[]
}

const KEY = 'tpt-planner.review'
const EMPTY: ReviewFile = { version: 1, updated: '', reviewed: [], notes: [] }

function loadLocal(): ReviewFile {
  try {
    const raw = window.localStorage.getItem(KEY)
    return raw ? { ...EMPTY, ...(JSON.parse(raw) as Partial<ReviewFile>) } : EMPTY
  } catch {
    return EMPTY
  }
}

type Sync = 'file' | 'browser' | 'menyimpan'

interface ReviewState extends ReviewFile {
  sync: Sync
  add: (n: Omit<ReviewNote, 'id' | 'at' | 'done'>) => void
  remove: (id: string) => void
  toggleDone: (id: string) => void
  toggleReviewed: (screen: number) => void
  hydrate: () => Promise<void>
}

let timer: ReturnType<typeof setTimeout> | undefined

export const useReview = create<ReviewState>((set, get) => {
  const persist = (patch: Partial<ReviewFile>) => {
    const s = get()
    const data: ReviewFile = { version: 1, updated: new Date().toISOString(), reviewed: s.reviewed, notes: s.notes, ...patch }
    set({ ...data, sync: 'menyimpan' })
    try {
      window.localStorage.setItem(KEY, JSON.stringify(data))
    } catch {
      /* penyimpanan browser diblokir */
    }
    clearTimeout(timer)
    timer = setTimeout(() => {
      fetch('/__review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(snapshot()) })
        .then((r) => set({ sync: r.ok ? 'file' : 'browser' }))
        .catch(() => set({ sync: 'browser' }))
    }, 400)
  }
  return {
    ...loadLocal(),
    sync: 'browser',
    add: (n) =>
      persist({ notes: [...get().notes, { ...n, id: `n${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`, at: new Date().toISOString(), done: false }] }),
    remove: (id) => persist({ notes: get().notes.filter((n) => n.id !== id) }),
    toggleDone: (id) => persist({ notes: get().notes.map((n) => (n.id === id ? { ...n, done: !n.done } : n)) }),
    toggleReviewed: (screen) => {
      const r = get().reviewed
      persist({ reviewed: r.includes(screen) ? r.filter((x) => x !== screen) : [...r, screen].sort((a, b) => a - b) })
    },
    hydrate: async () => {
      try {
        const r = await fetch('/__review')
        if (!r.ok) return
        const f = (await r.json()) as ReviewFile | null
        const local = get()
        if (f && f.updated > local.updated) {
          set({ ...f, sync: 'file' })
          window.localStorage.setItem(KEY, JSON.stringify(f))
        } else if (local.updated) {
          persist({}) // browser lebih baru → tulis ke file
        } else {
          set({ sync: 'file' })
        }
      } catch {
        set({ sync: 'browser' })
      }
    },
  }
})

/** Isi file catatan (tanpa status sinkron). */
function snapshot(): ReviewFile {
  const s = useReview.getState()
  return { version: 1, updated: s.updated, reviewed: s.reviewed, notes: s.notes }
}

/** Ekspor Markdown untuk ditempel ke chat. */
export function toMarkdown(f: ReviewFile, screenTitle: (n: number) => string, varLabel: (id: string) => string): string {
  const out = ['# Catatan review Milestone A', '', `Layar ditinjau: ${f.reviewed.length ? f.reviewed.join(', ') : '-'}`, '']
  const screens = [...new Set(f.notes.map((n) => n.screen))].sort((a, b) => a - b)
  for (const sc of screens) {
    out.push(`## Layar ${sc} · ${screenTitle(sc)}`)
    for (const n of f.notes.filter((x) => x.screen === sc)) {
      const v = n.varId ? ` \`${n.varId}\` (${varLabel(n.varId)})` : ''
      out.push(`- [${n.done ? 'x' : ' '}] **${n.topic}**${v}: ${n.text.replace(/\s*\n\s*/g, ' ')}`)
    }
    out.push('')
  }
  return out.join('\n')
}

/** Muat catatan dari file dev server sekali saat aplikasi dibuka. */
export function useReviewHydrate() {
  const hydrate = useReview((s) => s.hydrate)
  useEffect(() => {
    void hydrate()
  }, [hydrate])
}
