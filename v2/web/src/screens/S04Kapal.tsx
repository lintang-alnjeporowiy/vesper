import { useState } from 'react'
import type { Ship } from '../api/case'
import { C, DotPlot } from '../charts/charts'
import { Badge, Button, EditNum, Note, PH, ScreenHeader, Section, Split, Table, Tabs } from '../components/ui'
import { flowsForShipType, portOfRoute, shipTypesForForm, shortPortName } from '../lib/case'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { feasibilityMock } from '../mock/placeholders'
import { usePlanner } from '../store'

const TYPE_SHORT: Record<string, string> = { tanker: 'Tanker', bulk_carrier: 'Bulk', container_ship: 'Petikemas', general_cargo_ship: 'GC', lct: 'LCT' }

function Cell(props: { path: (string | number)[]; label: string; digits?: number }) {
  const f = useField(props.path, props.label)
  return <EditNum {...f} mark={false} digits={props.digits} />
}

export default function S04Kapal() {
  const c = usePlanner((s) => s.caseData)
  const [type, setType] = useState('container_ship')
  const types = c.ship_types
  const ships = c.ships.filter((s) => s.ship_type === type).sort((a, b) => a.dwt_t - b.dwt_t)
  const st = types.find((t) => t.code === type)
  const flows = flowsForShipType(c, type)
  const ports = [...new Map(flows.map((f) => [portOfRoute(c, f.route_id)?.id, { port: portOfRoute(c, f.route_id), flow: f.id }])).values()].filter((p) => p.port)
  const assumed = new Set((c.assumptions ?? []).filter((a) => a.status === 'asumsi').map((a) => a.id))
  const pts = st?.tch_points ?? []

  return (
    <>
      <ScreenHeader step={4} kind="input" title="Kandidat kapal" lead="Database kapal per tipe, tipe mana yang boleh membawa bentuk muatan apa, dan kenapa kapal gugur di rute tertentu." badge={<Badge kind="input">input K15 · {c.ships.length} kapal</Badge>} />

      <Split
        left={
          <div className="flex flex-col gap-3">
            <h2 className="m-0 text-xl font-normal">Bentuk muatan × tipe kapal</h2>
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr className="border-b border-hitam">
                  <th className="w-12" />
                  {types.map((t) => (
                    <th key={t.code} className="py-1.5 text-left font-medium text-abu">{TYPE_SHORT[t.code] ?? t.code}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {c.cargo_forms.map((f) => (
                  <tr key={f.code} className="h-9 border-b border-garis">
                    <td className="font-mono font-medium">{f.code}</td>
                    {types.map((t) => {
                      const ok = shipTypesForForm(c, f.code).includes(t.code)
                      const asm = ok && t.code === 'lct' && assumed.has('lct')
                      return (
                        <td key={t.code}>
                          <span className={`inline-block h-4 w-4 ${asm ? 'border-2 border-merah' : ok ? 'bg-hitam' : 'border border-garis'}`} title={ok ? 'boleh' : 'tidak'} />
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <Note>Kotak hitam = boleh. Bingkai merah = asumsi (LCT untuk GC belum ada datanya di K15).</Note>
          </div>
        }
        right={
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <h2 className="m-0 grow text-xl font-normal">Titik TCH · {st?.name}</h2>
              <PH>regresi: placeholder</PH>
            </div>
            {pts.length > 0 ? (
              <>
                <DotPlot height={170} points={pts.map((p) => ({ x: p.size, y: p.usd_per_day, color: C.biru, size: 8, label: `${p.label ?? ''} ${p.size} → ${p.usd_per_day} USD/hari` }))} xLabels={[`${num(pts[0].size)} ${st?.size_basis.toUpperCase()}`, `${num(pts[pts.length - 1].size)} · ${num(pts[pts.length - 1].usd_per_day / 1000, 1)} rb USD/hari`]} />
                <Note>{pts.length} titik data TCH (input). Tarif kapal di antara titik diambil dari regresi (engine tahap 6).</Note>
              </>
            ) : (
              <Note>Tidak ada titik TCH untuk tipe ini.</Note>
            )}
          </div>
        }
      />

      <Section title="Database kapal">
        <Tabs
          items={types.map((t) => ({ id: t.code, label: <>{t.name.split(' (')[0]} <span className="font-mono text-[13px]">{c.ships.filter((s) => s.ship_type === t.code).length}</span></> }))}
          value={type}
          onChange={setType}
          right={<Button size="sm" disabled>Tambah kapal</Button>}
        />
        {ships.length === 0 ? (
          <Note>Belum ada kapal tipe ini di K15.</Note>
        ) : (
          <Table<Ship>
            rowKey={(s) => s.id}
            rows={ships}
            columns={[
              { key: 'n', head: 'Kapal', width: 150, render: (s) => s.name },
              { key: 'dwt', head: 'DWT', width: 110, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'dwt_t']} label={`DWT ${s.name}`} /> },
              { key: 'loa', head: 'LOA', width: 100, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'loa_m']} label={`LOA ${s.name}`} digits={1} /> },
              { key: 'dr', head: 'Draft', width: 100, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'draft_m']} label={`Draft ${s.name}`} digits={2} /> },
              { key: 'v', head: 'Kn', width: 90, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'speed_kn']} label={`Kecepatan ${s.name}`} digits={1} /> },
              ...ports.map(({ port, flow }) => ({
                key: port!.id,
                head: <span title={flow}>{shortPortName(port!.name)}</span>,
                width: 84,
                render: (s: Ship) => {
                  const r = feasibilityMock(s, port!, c.params.berth_loa_min_ratio)
                  if (r.ok === true) return <span className="text-[13px] text-abu">layak</span>
                  if (r.ok === null) return <span className="text-[13px] text-merah">LOA ?</span>
                  return <Badge kind="gugur">{r.reasons.join(', ')}</Badge>
                },
              })),
            ]}
          />
        )}
        <Note>Kolom pelabuhan = kelayakan per rute untuk tipe ini (aturan SPEC §5.2, dihitung sementara di UI sampai engine tahap 5). "LOA ?" = panjang dermaga pelabuhan itu kosong.</Note>
      </Section>
    </>
  )
}
