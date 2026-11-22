// Sambungan ke engine lewat API (Tahap 4): kasus aktif (termasuk editan) dikirim otomatis ke /calculate
// (debounce), hasil disimpan di store. Bila API mati, layar kembali ke placeholder dengan catatan.
import { useEffect, useState } from 'react'
import { ApiError, postCalculate, postCompare } from '../api/client'
import type { CalcRequest, CalcResult, Case, CompareResult } from '../api/case'
import { usePlanner, type CalcState } from '../store'
import { num } from './format'
import { VAR, type TraceCtx } from './registry'

const DEBOUNCE_MS = 300
/** Selang coba lagi selama API tidak terjangkau. */
const RETRY_MS = 5000
/** Modul engine yang sudah tersedia. */
export const ENGINE_MODULES: NonNullable<CalcRequest['modules']> = ['demand', 'voyage']

/** Pasang sekali di App: hitung ulang setiap kali kasus aktif atau kapal terpilih berubah. */
export function useEngineSync() {
  const caseData = usePlanner((s) => s.caseData)
  const shipByFlow = usePlanner((s) => s.shipByFlow)
  const setCalc = usePlanner((s) => s.setCalc)
  const nonce = usePlanner((s) => s.calcNonce)
  const offline = usePlanner((s) => s.calc.status === 'offline')
  const retryCalc = usePlanner((s) => s.retryCalc)
  useEffect(() => {
    if (!offline) return
    const t = window.setInterval(retryCalc, RETRY_MS)
    return () => window.clearInterval(t)
  }, [offline, retryCalc])
  useEffect(() => {
    const ctl = new AbortController()
    const timer = window.setTimeout(() => {
      // selama API mati status tetap 'offline' (tanpa kedip) sampai percobaan berhasil
      if (usePlanner.getState().calc.status !== 'offline') setCalc({ status: 'loading' })
      postCalculate({ case: caseData, modules: ENGINE_MODULES, plan_id: null, ship_by_flow: shipByFlow }, ctl.signal)
        .then((result) => setCalc({ status: 'ok', result, error: undefined, at: Date.now() }))
        .catch((e: unknown) => {
          if (ctl.signal.aborted) return
          const offline = !(e instanceof ApiError) || e.status >= 500
          setCalc({ status: offline ? 'offline' : 'error', result: undefined, error: e instanceof Error ? e.message : String(e) })
        })
    }, DEBOUNCE_MS)
    return () => {
      window.clearTimeout(timer)
      ctl.abort()
    }
  }, [caseData, shipByFlow, nonce, setCalc])
}

/** Hasil engine yang berlaku (undefined bila belum ada / API mati). Hasil lama tetap dipakai selama memuat ulang. */
export function useCalc(): CalcState & { ok: boolean } {
  const calc = usePlanner((s) => s.calc)
  return { ...calc, ok: calc.result !== undefined && (calc.status === 'ok' || calc.status === 'loading') }
}

export function isComputed(calc: CalcState, id: string): boolean {
  return calc.result !== undefined && calc.status !== 'offline' && calc.status !== 'error' && calc.result.computed.includes(id)
}

/** Seri tahunan sebuah variabel per flow (indeks 0 = tahun ke-1). */
export function series(result: CalcResult | undefined, id: string, key: string): number[] | undefined {
  const v = result?.values[id]?.[key]
  return Array.isArray(v) ? v : undefined
}

/** Nilai skalar (atau seri pada tahun `year`) untuk konteks jejak. */
export function computedNumber(result: CalcResult | undefined, id: string, ctx: TraceCtx | undefined, year: number): number | undefined {
  const byKey = result?.values[id]
  if (!byKey) return undefined
  const key = VAR[id]?.scope === 'ship' ? ctx?.ship : ctx?.flow
  const v = key ? byKey[key] : undefined
  if (v === undefined) return undefined
  return Array.isArray(v) ? v[(ctx?.year ?? year) - 1] : v
}

/** Satuan tampilan: demand dalam satuan flow / satuan kapal, lainnya dari registry. */
export function unitOf(caseData: Case, result: CalcResult | undefined, id: string, flow?: string): string {
  if ((id === 'cargo.demand_unit' || id === 'vessel.payload' || id === 'voyage.q') && flow) return result?.units[flow] === 'TEU' ? 'TEU' : 't'
  if ((id === 'demand.base' || id === 'demand.ratio') && flow) {
    return caseData.flows.find((f) => f.id === flow)?.unit === 'TEU' ? 'TEU' : 't'
  }
  return VAR[id]?.unit ?? ''
}

export function fmtValue(v: number): string {
  if (Number.isInteger(v) || Math.abs(v) >= 1000) return num(v, 0)
  return num(v, Math.abs(v) < 100 ? 3 : 1)
}

/** Teks nilai hasil engine untuk laci jejak ("358.021 TEU"), undefined bila variabel/konteks belum dihitung. */
export function computedText(caseData: Case, calc: CalcState, id: string, ctx: TraceCtx | undefined, year: number): string | undefined {
  if (!isComputed(calc, id)) return undefined
  const v = computedNumber(calc.result, id, ctx, year)
  if (v === undefined) return undefined
  const u = unitOf(caseData, calc.result, id, ctx?.flow)
  return u ? `${fmtValue(v)} ${u}` : fmtValue(v)
}

/** Bandingkan semua kapal kandidat untuk satu flow lewat /compare (layar 4 & 6); dihitung ulang saat kasus berubah. */
export function useCompare(flowId: string | undefined): { data?: CompareResult; status: 'idle' | 'loading' | 'ok' | 'offline' | 'error'; error?: string } {
  const caseData = usePlanner((s) => s.caseData)
  const shipByFlow = usePlanner((s) => s.shipByFlow)
  const nonce = usePlanner((s) => s.calcNonce)
  const [state, setState] = useState<{ data?: CompareResult; status: 'idle' | 'loading' | 'ok' | 'offline' | 'error'; error?: string; key?: string }>({ status: 'idle' })
  useEffect(() => {
    if (!flowId) return
    const ctl = new AbortController()
    const timer = window.setTimeout(() => {
      setState((s) => ({ ...s, status: 'loading' }))
      postCompare({ case: caseData, flow_id: flowId, plan_id: null, ship_by_flow: shipByFlow, equipment_by_terminal: null }, ctl.signal)
        .then((data) => setState({ data, status: 'ok', key: flowId }))
        .catch((e: unknown) => {
          if (ctl.signal.aborted) return
          const offline = !(e instanceof ApiError) || e.status >= 500
          setState({ status: offline ? 'offline' : 'error', error: e instanceof Error ? e.message : String(e) })
        })
    }, DEBOUNCE_MS)
    return () => {
      window.clearTimeout(timer)
      ctl.abort()
    }
  }, [flowId, caseData, shipByFlow, nonce])
  // hasil flow lain (sebelum respons flow baru tiba) tidak ditampilkan
  return state.data && state.data.flow_id !== flowId ? { status: 'loading' } : state
}

/** Nilai skalar atau seri pada tahun `year` dari sebuah baris kandidat. */
export function rowNumber(values: Record<string, number | number[]> | undefined, id: string, year: number): number | undefined {
  const v = values?.[id]
  if (v === undefined) return undefined
  return Array.isArray(v) ? v[year - 1] : v
}
