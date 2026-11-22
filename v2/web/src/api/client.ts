// Klien API FastAPI (Tahap 4). Dev: Vite mem-proxy /api → http://127.0.0.1:8000 (vite.config.ts).
import type { CalcRequest, CalcResult, CaseSummary, CompareRequest, CompareResult } from './case'

export const API_BASE = '/api'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* respons bukan JSON (mis. proxy gagal karena API mati) */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

export const fetchCases = () => call<CaseSummary[]>('/cases')

export const postCalculate = (req: CalcRequest, signal?: AbortSignal) =>
  call<CalcResult>('/calculate', { method: 'POST', body: JSON.stringify(req), signal })

export const postCompare = (req: CompareRequest, signal?: AbortSignal) =>
  call<CompareResult>('/compare', { method: 'POST', body: JSON.stringify(req), signal })
