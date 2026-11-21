import { create } from 'zustand'
import type { Case } from './api/case'
import { K15 } from './mock/case'
import type { TraceCtx, TraceRef } from './lib/registry'

export const SCREEN_COUNT = 13
export const MAP_SCREEN = 12

type Path = (string | number)[]

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
  setScreen: (n: number) => void
  setYear: (y: number) => void
  setFlow: (id: string) => void
  setShip: (flowId: string, shipId: string) => void
  setInput: (path: Path, value: unknown, label: string) => void
  recalc: () => void
  showTrace: (id: string, ctx?: TraceCtx, value?: string) => void
  traceBack: () => void
  toggleTrace: () => void
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
  trace: { id: 'voyage.rtd', ctx: { flow: 'in.damai', ship: 'ship.aetos', year: 10 } },
  traceHistory: [],
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
  showTrace: (id, ctx, value) => {
    const { trace, traceHistory } = get()
    const same = trace.id === id && JSON.stringify(trace.ctx) === JSON.stringify(ctx)
    set({
      trace: { id, ctx, value },
      traceOpen: true,
      traceHistory: same ? traceHistory : [...traceHistory, trace].slice(-30),
    })
  },
  traceBack: () => {
    const h = get().traceHistory
    if (h.length) set({ trace: h[h.length - 1], traceHistory: h.slice(0, -1) })
  },
  toggleTrace: () => set({ traceOpen: !get().traceOpen }),
}))

window.addEventListener('hashchange', () => usePlanner.setState({ screen: screenFromHash() }))

