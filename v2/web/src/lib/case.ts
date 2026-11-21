import type { Case, CargoFlow, ExternalPort, Volume, VolumeRatio } from '../api/case'

export function portOfRoute(c: Case, routeId: string): ExternalPort | undefined {
  const r = c.routes.find((x) => x.id === routeId)
  const leg = r?.legs.find((l) => l.origin !== 'KEK') ?? r?.legs[0]
  const id = leg ? (leg.origin === 'KEK' ? leg.destination : leg.origin) : undefined
  return c.ports.find((p) => p.id === id)
}

export function routeDistance(c: Case, routeId: string): number {
  return c.routes.find((x) => x.id === routeId)?.legs[0]?.distance_nm ?? 0
}

export function commodityName(c: Case, id: string): string {
  return c.commodities.find((x) => x.id === id)?.name ?? id
}

export function tenantName(c: Case, id: string): string {
  return c.tenants.find((x) => x.id === id)?.name ?? id
}

export function shipName(c: Case, id: string | undefined): string {
  return c.ships.find((s) => s.id === id)?.name ?? '–'
}

/** Flow yang bentuk muatannya boleh dibawa tipe kapal ini. */
export function flowsForShipType(c: Case, shipType: string): CargoFlow[] {
  const compat = c.compatibility as unknown as Record<string, string[]>
  return c.flows.filter((f) => (compat[f.cargo_form] ?? []).includes(shipType))
}

export function shipTypesForForm(c: Case, form: string): string[] {
  const compat = c.compatibility as unknown as Record<string, string[]>
  return compat[form] ?? []
}

/** Tahun mulai flow; outbound mengikuti inbound acuannya. */
export function startYearOf(c: Case, flowId: string): number | undefined {
  const f = c.flows.find((x) => x.id === flowId)
  if (!f) return undefined
  return isRatio(f.volume) ? startYearOf(c, f.volume.basis_flow_id) : f.volume.start_year
}

export function isRatio(v: Volume): v is VolumeRatio {
  return 'basis_flow_id' in v
}

export const FORM_LABEL: Record<string, string> = { CC: 'Curah cair', CK: 'Curah kering', PK: 'Petikemas', GC: 'General cargo' }

export function shortPortName(name: string): string {
  return name.replace(/^(Pelabuhan|Port of|Port Of)\s+/i, '').replace(/^\w/, (m) => m.toUpperCase())
}
