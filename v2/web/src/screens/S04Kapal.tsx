import { useState } from 'react'
import type { Ship, TchPoint } from '../api/case'
import { C, DotPlot } from '../charts/charts'
import { Badge, Button, EditNum, EditText, InputMark, Note, PH, ScreenHeader, Section, Split, Table, Tabs } from '../components/ui'
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

/** Cek digit IMO: 7 angka, digit ke-7 = Σ(digit_i × (7−i)) mod 10. */
function imoValid(s: string | null | undefined): boolean {
  if (!s || !/^\d{7}$/.test(s)) return false
  const sum = [...s.slice(0, 6)].reduce((a, d, i) => a + Number(d) * (7 - i), 0)
  return sum % 10 === Number(s[6])
}

function ImoCell({ ship, idx }: { ship: Ship; idx: number }) {
  const setInput = usePlanner((s) => s.setInput)
  const v = ship.imo ?? ''
  const ok = imoValid(v)
  return (
    <span className="inline-flex items-center gap-1.5">
      <EditText
        mono
        width="8ch"
        value={ship.imo}
        placeholder="–"
        invalid={!!v && !ok}
        title={v && !ok ? 'Digit periksa IMO tidak cocok' : undefined}
        label={`IMO ${ship.name}`}
        onChange={(x) => setInput(['ships', idx, 'imo'], x?.replace(/^IMO\s*/i, '') ?? null, `IMO ${ship.name}`)}
      />
      {ok && (
        <a href={`https://www.marinetraffic.com/en/ais/details/ships/imo:${v}`} target="_blank" rel="noreferrer" title="Buka di MarineTraffic untuk verifikasi" className="text-[13px] text-abu no-underline hover:text-biru">↗</a>
      )}
    </span>
  )
}

/** Tabel titik TCH pasar per tipe kapal (ship_types[i].tch_points). */
function TchEditor({ typeIdx }: { typeIdx: number }) {
  const st = usePlanner((s) => s.caseData.ship_types[typeIdx])
  const changed = usePlanner((s) => Object.keys(s.dirty).some((k) => k.startsWith(`ship_types.${typeIdx}.tch_points`)))
  const setInput = usePlanner((s) => s.setInput)
  if (!st) return null
  const pts: TchPoint[] = st.tch_points ?? []
  const basis = st.size_basis === 'teu' ? 'TEU' : 'DWT'
  const setPts = (next: TchPoint[], label: string) => setInput(['ship_types', typeIdx, 'tch_points'], next, label)
  const setAt = (i: number, patch: Partial<TchPoint>, label: string) => setPts(pts.map((p, j) => (j === i ? { ...p, ...patch, refs: {} } : p)), label)
  const add = () => {
    const last = pts[pts.length - 1]
    setPts([...pts, { refs: {}, label: null, size: last ? last.size * 1.5 : st.size_basis === 'teu' ? 1000 : 10000, usd_per_day: last?.usd_per_day ?? 10000 }], `TCH ${st.name}: tambah titik`)
  }
  return (
    <div className="flex flex-col gap-2">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-hitam text-[13px] text-abu">
            <th className="py-1.5 text-left font-medium"><span className="inline-flex items-center gap-1"><InputMark />Kelas pasar</span></th>
            <th className="py-1.5 text-right font-medium"><span className="inline-flex items-center gap-1"><InputMark />Ukuran, {basis}</span></th>
            <th className="py-1.5 text-right font-medium"><span className="inline-flex items-center gap-1"><InputMark />TCH, USD/hari</span></th>
            <th className="w-6" />
          </tr>
        </thead>
        <tbody>
          {pts.map((p, i) => (
            <tr key={i} className="border-t border-garis">
              <td className="py-1"><EditText value={p.label} placeholder="(tanpa nama)" width="16ch" label={`Kelas TCH ${i + 1}`} onChange={(v) => setAt(i, { label: v }, `TCH ${st.name}: kelas ${i + 1}`)} /></td>
              <td className="py-1 text-right"><EditNum value={p.size} mark={false} label={`Ukuran TCH ${i + 1}`} onChange={(v) => v > 0 && setAt(i, { size: v }, `TCH ${st.name}: ukuran ${i + 1}`)} /></td>
              <td className="py-1 text-right"><EditNum value={p.usd_per_day} mark={false} label={`TCH ${i + 1}`} onChange={(v) => v > 0 && setAt(i, { usd_per_day: v }, `TCH ${st.name}: tarif ${i + 1}`)} /></td>
              <td className="text-right">
                <button type="button" aria-label={`Hapus titik TCH ${i + 1}`} onClick={() => setPts(pts.filter((_, j) => j !== i), `TCH ${st.name}: hapus titik ${i + 1}`)} className="cursor-pointer border-0 bg-transparent text-abu hover:text-merah">×</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <span className="flex items-center gap-2">
        <Button size="sm" variant="tipis" onClick={add}>+ Titik TCH</Button>
        {changed && <Badge kind="gugur">diubah</Badge>}
        {pts.length < 2 && <span className="text-[13px] text-merah">Regresi butuh minimal 2 titik.</span>}
      </span>
    </div>
  )
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
            {pts.length > 0 && (
              <DotPlot height={140} points={pts.map((p) => ({ x: p.size, y: p.usd_per_day, color: C.biru, size: 8, label: `${p.label ?? ''} ${num(p.size)} → ${num(p.usd_per_day)} USD/hari` }))} xLabels={[`${num(Math.min(...pts.map((p) => p.size)))} ${st?.size_basis.toUpperCase()}`, `${num(Math.max(...pts.map((p) => p.size)))} ${st?.size_basis.toUpperCase()}`]} />
            )}
            <TchEditor typeIdx={types.findIndex((t) => t.code === type)} />
            <Note>Tarif charter pasar per tipe kapal (sumber K15: sheet TCH). TCH tiap kapal = regresi linier titik-titik ini terhadap {st?.size_basis === 'teu' ? 'kapasitas TEU' : 'DWT'} kapal (engine tahap 6). Ganti tipe lewat tab Database kapal di bawah.</Note>
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
              { key: 'imo', head: 'IMO', width: 110, input: true, render: (s) => <ImoCell ship={s} idx={c.ships.indexOf(s)} /> },
              { key: 'dwt', head: 'DWT, t', width: 110, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'dwt_t']} label={`DWT ${s.name}`} /> },
              { key: 'loa', head: 'LOA, m', width: 100, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'loa_m']} label={`LOA ${s.name}`} digits={1} /> },
              { key: 'dr', head: 'Draft, m', width: 100, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'draft_m']} label={`Draft ${s.name}`} digits={2} /> },
              { key: 'v', head: 'Kecepatan, knot', width: 120, input: true, render: (s) => <Cell path={['ships', c.ships.indexOf(s), 'speed_kn']} label={`Kecepatan ${s.name}`} digits={1} /> },
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
        <Note>IMO number tidak dipakai dalam hitungan; gunanya agar kapal bisa diverifikasi sebagai kapal riil (merah = digit periksa tidak cocok, ↗ = buka di MarineTraffic). Kolom pelabuhan = kelayakan per rute untuk tipe ini (aturan SPEC §5.2, dihitung sementara di UI sampai engine tahap 5). "LOA ?" = panjang dermaga pelabuhan itu kosong.</Note>
      </Section>
    </>
  )
}
