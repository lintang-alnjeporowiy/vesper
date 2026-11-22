import { create } from 'zustand'
import type { Case } from './api/case'
import { K15 } from './mock/case'
import type { TraceCtx, TraceRef } from './lib/registry'

export const SCREEN_COUNT = 13
export const MAP_SCREEN = 12

type Path = (string | number)[]
export type DrawerTab = 'jejak' | 'review' | 'pengaturan'

/** Pengaturan tampilan per pengguna (disimpan di localStorage browser ini). */
export interface Settings {
  /** Catatan "tidak ada temuan audit langsung" di laci jejak. */
  showNoAuditNote: boolean
  /** Catatan ≠ Excel · A# bila variabel punya temuan audit. */
  showAuditNotes: boolean
  /** Keterangan singkat variabel di laci jejak. */
  showDesc: boolean
  /** Catatan bahwa nilai turunan placeholder hanya ada untuk contoh in.damai. */
  showPlaceholderNote: boolean
}

export const DEFAULT_SETTINGS: Settings = { showNoAuditNote: false, showAuditNotes: true, showDesc: true, showPlaceholderNote: true }
const SETTINGS_KEY = 'tpt-planner.settings'

function loadSettings(): Settings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY)
    return raw ? { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<Settings>) } : DEFAULT_SETTINGS
  } catch {
    return DEFAULT_SETTINGS
  }
}

function saveSettings(s: Settings) {
  try {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  } catch {
    /* penyimpanan diblokir: pengaturan berlaku sampai halaman dimuat ulang */
  }
}

function setAt<T>(obj: T, path: Path, value: unknown): T {
  const copy = structuredClone(obj) as Record<string | number, unknown>
  let cur = copy as Record<string | number, unknown>
  for (let i = 0; i < path.length - 1; i++) cur = cur[path[i]] as Record<string | number, unknown>
  cur[path[path.length - 1]] = value
  return copy as T
}

interface PlannerState {
  caseData: Case
  baseline: Case
  /** Jalur input yang diubah sejak hitung terakhir (kunci = path digabung titik). */
  dirty: Record<string, { label: string; from: unknown; to: unknown }>
  screen: number
  year: number
  flowId: string
  shipByFlow: Record<string, string>
  traceOpen: boolean
  trace: TraceRef
  /** Riwayat jejak untuk tombol kembali di laci. */
  traceHistory: TraceRef[]
  /** Tab aktif di laci kanan. */
  drawerTab: DrawerTab
  settings: Settings
  setScreen: (n: number) => void
  setYear: (y: number) => void
  setFlow: (id: string) => void
  setShip: (flowId: string, shipId: string) => void
  setInput: (path: Path, value: unknown, label: string) => void
  recalc: () => void
  /** `open: false` = ganti variabel tanpa membuka laci yang sedang ditutup (dipakai peta variabel). */
  showTrace: (id: string, ctx?: TraceCtx, value?: string, opts?: { open?: boolean }) => void
  /** Peta variabel tanpa menu kiri (tampilan lebar). */
  mapWide: boolean
  setMapWide: (v: boolean) => void
  traceBack: () => void
  toggleTrace: () => void
  setDrawerTab: (t: DrawerTab) => void
  setSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void
  resetSettings: () => void
}

function screenFromHash(): number {
  const n = Number(window.location.hash.replace('#/', ''))
  return Number.isInteger(n) && n >= 0 && n < SCREEN_COUNT ? n : 6
}

const plan = K15.plans?.[0]

export const usePlanner = create<PlannerState>((set, get) => ({
  caseData: K15,
  baseline: K15,
  dirty: {},
  screen: screenFromHash(),
  year: 10,
  flowId: 'in.damai',
  shipByFlow: { ...(plan?.ship_by_flow ?? {}) },
  traceOpen: true,
  mapWide: false,
  trace: { id: 'voyage.rtd', ctx: { flow: 'in.damai', ship: 'ship.aetos', year: 10 } },
  traceHistory: [],
  drawerTab: 'jejak',
  settings: loadSettings(),
  setScreen: (n) => {
    window.location.hash = `#/${n}`
    set({ screen: n })
  },
  setYear: (y) => set({ year: y }),
  setFlow: (id) => set({ flowId: id }),
  setShip: (flowId, shipId) => set({ shipByFlow: { ...get().shipByFlow, [flowId]: shipId } }),
  setInput: (path, value, label) => {
    const key = path.join('.')
    const { caseData, baseline, dirty } = get()
    let from: unknown = baseline
    for (const p of path) from = (from as Record<string | number, unknown>)?.[p]
    const next = { ...dirty }
    if (from === value) delete next[key]
    else next[key] = { label, from, to: value }
    set({ caseData: setAt(caseData, path, value), dirty: next })
  },
  // Engine belum tersambung (Tahap 4+): hitung ulang hanya menandai input sebagai baseline baru.
  recalc: () => set({ baseline: get().caseData, dirty: {} }),
  showTrace: (id, ctx, value, opts) => {
    const { trace, traceHistory } = get()
    const same = trace.id === id && JSON.stringify(trace.ctx) === JSON.stringify(ctx)
    set({
      trace: { id, ctx, value },
      traceOpen: opts?.open === false ? get().traceOpen : true,
      drawerTab: 'jejak',
      traceHistory: same ? traceHistory : [...traceHistory, trace].slice(-30),
    })
  },
  traceBack: () => {
    const h = get().traceHistory
    if (h.length) set({ trace: h[h.length - 1], traceHistory: h.slice(0, -1) })
  },
  toggleTrace: () => set({ traceOpen: !get().traceOpen }),
  setMapWide: (v) => set({ mapWide: v }),
  setDrawerTab: (t) => set({ drawerTab: t, traceOpen: true }),
  setSetting: (key, value) => {
    const settings = { ...get().settings, [key]: value }
    saveSettings(settings)
    set({ settings })
  },
  resetSettings: () => {
    saveSettings(DEFAULT_SETTINGS)
    set({ settings: DEFAULT_SETTINGS })
  },
}))

window.addEventListener('hashchange', () => usePlanner.setState({ screen: screenFromHash() }))

