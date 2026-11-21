// Registry variabel (SPEC §9.3) — dibaca dari mock JSON hasil tools/dump_registry.py
// sampai endpoint /registry ada. Hanya definisi: rumus, dependensi, sumber Excel.
import type { Case } from '../api/case'
import registryJson from '../mock/registry.json'
import { num } from './format'
import { portOfRoute } from './case'

export type VarKind = 'input' | 'decision' | 'derived' | 'metric' | 'objective'

export interface VarDef {
  id: string
  label: string
  unit: string
  scope: string
  kind: VarKind
  formula: string
  deps: string[]
  dependents: string[]
  excel_ref?: string
  section: string
  audit?: string[]
  case_path?: string
  screens?: number[]
  note?: string
  symbol?: string
  lane: number
  depth: number
  topo: number
  group?: string
}

interface RegistryFile {
  lanes: string[]
  input_groups: Record<string, string>
  audit: Record<string, string>
  interactions: { id: string; label: string; start: string }[]
  variables: VarDef[]
}

const REG = registryJson as unknown as RegistryFile

export const VARS: VarDef[] = REG.variables
export const LANES = REG.lanes
export const INPUT_GROUPS = REG.input_groups
export const INTERACTIONS = REG.interactions
export const AUDIT = REG.audit
export const VAR: Record<string, VarDef> = Object.fromEntries(VARS.map((v) => [v.id, v]))

export function getVar(id: string): VarDef {
  const v = VAR[id]
  if (!v) throw new Error(`variabel '${id}' tidak ada di registry`)
  return v
}

function closure(id: string, key: 'deps' | 'dependents'): Set<string> {
  const out = new Set<string>()
  const stack = [...(VAR[id]?.[key] ?? [])]
  while (stack.length) {
    const n = stack.pop()!
    if (out.has(n)) continue
    out.add(n)
    stack.push(...(VAR[n]?.[key] ?? []))
  }
  return out
}

const upCache = new Map<string, Set<string>>()
const downCache = new Map<string, Set<string>>()
export const upstream = (id: string) => upCache.get(id) ?? upCache.set(id, closure(id, 'deps')).get(id)!
export const downstream = (id: string) => downCache.get(id) ?? downCache.set(id, closure(id, 'dependents')).get(id)!

export const KIND_LABEL: Record<VarKind, string> = {
  input: 'input kasus',
  decision: 'variabel keputusan',
  derived: 'turunan',
  metric: 'metrik laporan',
  objective: 'objektif',
}

// ── Konteks jejak: instance mana dari variabel yang sedang dilihat ─────────────────────────────
export interface TraceCtx {
  flow?: string
  ship?: string
  year?: number
  terminal?: string
}

export interface TraceRef {
  id: string
  ctx?: TraceCtx
  /** Nilai seperti tampil di layar (placeholder). */
  value?: string
}

export function sameCtx(a?: TraceCtx, b?: TraceCtx): boolean {
  return (a?.flow ?? '') === (b?.flow ?? '') && (a?.ship ?? '') === (b?.ship ?? '') && (a?.year ?? 0) === (b?.year ?? 0) && (a?.terminal ?? '') === (b?.terminal ?? '')
}

export function contextLabel(c: Case, v: VarDef, ctx: TraceCtx | undefined, shipByFlow: Record<string, string>): string {
  const parts: string[] = []
  const s = v.scope
  if (ctx?.flow && /flow|commodity|cargo_form/.test(s)) parts.push(ctx.flow)
  const shipId = ctx?.ship ?? (ctx?.flow ? shipByFlow[ctx.flow] : undefined)
  if (shipId && /ship|flow/.test(s)) parts.push(c.ships.find((x) => x.id === shipId)?.name ?? shipId)
  if (ctx?.terminal && /terminal/.test(s)) parts.push(`terminal ${ctx.terminal}`)
  if (ctx?.year && /year/.test(s)) parts.push(`tahun ${ctx.year}`)
  return parts.length ? parts.join(' · ') : `definisi · lingkup ${s}`
}

// ── Nilai input dari kasus aktif (path `nama[kunci]` dipilih lewat konteks) ────────────────────
type Obj = Record<string, unknown>

function pickKey(c: Case, key: string, ctx: TraceCtx, shipByFlow: Record<string, string>): string | undefined {
  const flow = c.flows.find((f) => f.id === ctx.flow)
  const shipId = ctx.ship ?? (ctx.flow ? shipByFlow[ctx.flow] : undefined)
  const ship = c.ships.find((s) => s.id === shipId)
  const terminal = ctx.terminal ?? c.kek_site.terminals.find((t) => flow && t.cargo_forms.includes(flow.cargo_form))?.id
  switch (key) {
    case 'flow': return flow?.id
    case 'ship': return ship?.id
    case 'route': return flow?.route_id
    case 'port': return flow ? portOfRoute(c, flow.route_id)?.id : undefined
    case 'commodity': return flow?.commodity_id
    case 'ship_type': return ship?.ship_type
    case 'terminal': return terminal
    case 'equip': return terminal ? c.plans?.[0]?.equipment_by_terminal[terminal] : undefined
    case 'fuel': return c.params.me_fuel
    case 'tariff_class': return flow ? portOfRoute(c, flow.route_id)?.tariff_class : undefined
  }
  return undefined
}

function resolvePath(c: Case, path: string, ctx: TraceCtx, shipByFlow: Record<string, string>): unknown {
  let cur: unknown = c
  for (const seg of path.split('.')) {
    const m = /^(\w+)(?:\[(\w+)\])?$/.exec(seg)
    if (!m || cur == null) return undefined
    cur = (cur as Obj)[m[1]]
    if (m[2]) {
      const key = pickKey(c, m[2], ctx, shipByFlow)
      if (key === undefined || !Array.isArray(cur)) return undefined
      cur = (cur as Obj[]).find((x) => x.id === key || x.code === key || x.tariff_class === key)
    }
  }
  return cur
}

const SPECIAL: Record<string, (c: Case, ctx: TraceCtx, sbf: Record<string, string>) => unknown> = {
  'in.route.distance': (c, ctx, sbf) => {
    const legs = resolvePath(c, 'routes[route].legs', ctx, sbf) as { distance_nm: number; laden: boolean }[] | undefined
    return legs ? `${legs.map((l) => num(l.distance_nm, 1)).join(' + ')} NM` : undefined
  },
  'in.route.laden': (c, ctx, sbf) => {
    const legs = resolvePath(c, 'routes[route].legs', ctx, sbf) as { laden: boolean }[] | undefined
    return legs?.map((l) => (l.laden ? 'muat' : 'ballast')).join(' · ')
  },
  'in.container.dims': (c) => `${num(c.params.container.inner_length_m, 2)} × ${num(c.params.container.inner_width_m, 2)} × ${num(c.params.container.inner_height_m, 2)} m`,
  'in.param.fuel_choice': (c) => `ME ${c.params.me_fuel} · AE ${c.params.ae_fuel}`,
  'in.param.fuel_share_me': (c) => `${num(c.params.fuel_share_me_sea, 2)} · ${num(c.params.fuel_share_me_port, 2)}`,
  'in.param.fuel_share_ae': (c) => `${num(c.params.fuel_share_ae_sea, 2)} · ${num(c.params.fuel_share_ae_port, 2)}`,
  'in.port.productivity': (c, ctx, sbf) => {
    const p = resolvePath(c, 'ports[port].productivity', ctx, sbf) as { mode: string; value: number; unit: string; equipment_count?: number | null } | undefined
    return p ? `${num(p.value)} ${p.unit}${p.mode === 'per_equipment' ? ` × ${p.equipment_count}` : ''}` : undefined
  },
  'in.equip.productivity': (c, ctx, sbf) => {
    const e = resolvePath(c, 'equipment[equip]', ctx, sbf) as { name: string; productivity: Record<string, { unload: number; unit: string }> } | undefined
    const flow = c.flows.find((f) => f.id === ctx.flow)
    const p = e && flow ? e.productivity[flow.cargo_form] : undefined
    return p ? `${num(p.unload)} ${p.unit} (${e!.name})` : e ? `${Object.keys(e.productivity).length} bentuk muatan` : undefined
  },
  'in.equip.price': (c, ctx, sbf) => {
    const e = resolvePath(c, 'equipment[equip]', ctx, sbf) as { price_usd: number; name: string } | undefined
    return e ? `USD ${num(e.price_usd)}` : undefined
  },
}

/** Nilai input sebagai teks siap tampil, atau undefined bila konteks tidak cukup. */
export function inputValue(c: Case, v: VarDef, ctx: TraceCtx, shipByFlow: Record<string, string>): string | undefined {
  if (v.kind !== 'input' || !v.case_path) return undefined
  const special = SPECIAL[v.id]
  const raw = special ? special(c, ctx, shipByFlow) : resolvePath(c, v.case_path, ctx, shipByFlow)
  if (raw === undefined || raw === null) return undefined
  if (typeof raw === 'string') return raw
  if (typeof raw === 'number') {
    const digits = Number.isInteger(raw) || Math.abs(raw) >= 100 ? 0 : 2
    const unit = v.unit === '–' || v.unit.includes('|') ? '' : ` ${v.unit}`
    return `${num(raw, digits)}${unit}`
  }
  if (typeof raw === 'boolean') return raw ? 'ya' : 'tidak'
  if (Array.isArray(raw)) return `tabel · ${raw.length} baris`
  if (typeof raw === 'object') return `${Object.keys(raw as Obj).length} parameter`
  return String(raw)
}
