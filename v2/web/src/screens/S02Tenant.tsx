import { useState } from 'react'
import type { CargoFlow } from '../api/case'
import { C, ColumnStack } from '../charts/charts'
import { Badge, Button, DefRow, EditNum, InputMark, Legend, Note, PH, ScreenHeader, Section, Slider, Split, Table } from '../components/ui'
import { commodityName, portOfRoute, shortPortName, tenantName } from '../lib/case'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { PROJECTION, TEU_CALC } from '../mock/placeholders'
import { usePlanner } from '../store'

function Cell(props: { path: (string | number)[]; label: string; digits?: number; scale?: number; unit?: string }) {
  const f = useField(props.path, props.label)
  if (f.value === undefined || f.value === null) return <span className="font-mono text-abu">–</span>
  return <EditNum {...f} mark={false} digits={props.digits} scale={props.scale} unit={props.unit} />
}

function WhatIf({ flow, idx, outIdx }: { flow: CargoFlow; idx: number; outIdx: number }) {
  const g = useField(['flows', idx, 'volume', 'growth_rate'], `Laju ${flow.id}`)
  const m = useField(['flows', idx, 'volume', 'maximum'], `Volume maks ${flow.id}`)
  const s = useField(['flows', idx, 'volume', 'start_year'], `Tahun mulai ${flow.id}`)
  const r = useField(['flows', outIdx, 'volume', 'ratio'], `Rasio outbound ${flow.tenant_id}`)
  const unit = flow.unit === 'TEU' ? 'rb TEU' : 'jt t'
  const div = flow.unit === 'TEU' ? 1e3 : 1e6
  return (
    <div className="flex flex-col gap-5">
      <h2 className="m-0 text-xl font-normal">What-if volume {flow.id} (I4, I5)</h2>
      <Slider label="Laju pertumbuhan" value={g.value * 100} min={0} max={10} step={0.5} display={`${num(g.value * 100, 1)} %/th`} onChange={(v) => g.onChange(v / 100)} />
      <Slider label="Volume maksimum" value={m.value / div} min={0} max={(m.value / div) * 2} step={0.1} display={`${num(m.value / div, 1)} ${unit}`} onChange={(v) => m.onChange(v * div)} />
      <Slider label="Tahun mulai" value={s.value} min={1} max={20} step={1} display={String(s.value)} onChange={(v) => s.onChange(v)} />
      {outIdx >= 0 && <Slider label="Rasio outbound" value={r.value} min={0} max={3} step={0.05} display={num(r.value, 2)} onChange={(v) => r.onChange(v)} />}
      <div className="flex gap-2">
        <span className="w-0.5 shrink-0 bg-hitam" />
        <Note>Setelah dihitung: tahun volume menyentuh maks, kapan kapal ditambah (layar 6), kapan tambatan dan alat ditambah (layar 8).</Note>
      </div>
    </div>
  )
}

export default function S02Tenant() {
  const c = usePlanner((s) => s.caseData)
  const flowId = usePlanner((s) => s.flowId)
  const setFlow = usePlanner((s) => s.setFlow)
  const [unit, setUnit] = useState<'ton' | 'TEU'>('ton')
  const pkCommodities = c.commodities.filter((x) => x.cargo_form === 'PK' && x.packaging)
  const [comId, setComId] = useState(pkCommodities[0]?.id ?? '')
  const com = c.commodities.find((x) => x.id === comId)

  const rows = c.tenants.flatMap((t) => c.flows.filter((f) => f.tenant_id === t.id))
  const inbound = c.flows.filter((f) => f.direction === 'inbound')
  const selIn = inbound.find((f) => f.id === flowId) ?? inbound[0]
  const selIdx = c.flows.indexOf(selIn)
  const outIdx = c.flows.findIndex((f) => f.volume.mode === 'ratio' && (f.volume as { basis_flow_id: string }).basis_flow_id === selIn.id)

  const tonFlows = ['in.damai', 'in.esa', 'in.baru', 'in.adi']
  const colors = [C.biru, C.hitam, C.hijau, C.abu]
  const columns = Array.from({ length: 20 }, (_, y) => (unit === 'ton' ? tonFlows.map((f) => PROJECTION[f][y]) : [PROJECTION['in.fantasi'][y]]))

  return (
    <>
      <ScreenHeader step={2} kind="input" title="Tenant & muatan" lead="Inbound punya volume sendiri. Outbound mengikuti inbound lewat rasio konversi." badge={<Badge kind="input">input K15 · {c.tenants.length} tenant · {c.flows.length} flow</Badge>} />

      <Section title="Tenant dan aliran muatan" aside={<Button size="sm" disabled>Tambah tenant</Button>}>
        <Table<CargoFlow>
          rowKey={(f) => f.id}
          rows={rows}
          selected={(f) => f.id === selIn.id}
          groupStart={(f, i) => i === 0 || rows[i - 1].tenant_id !== f.tenant_id}
          onRowClick={(f) => f.direction === 'inbound' && setFlow(f.id)}
          columns={[
            { key: 't', head: 'Tenant', width: 130, render: (f) => (f.direction === 'inbound' ? <span className="font-medium">{tenantName(c, f.tenant_id).replace('PT. ', '')}</span> : '') },
            { key: 'a', head: 'Arah', width: 40, mono: true, render: (f) => (f.direction === 'inbound' ? 'in' : 'out') },
            { key: 'k', head: 'Komoditas', width: 170, render: (f) => commodityName(c, f.commodity_id) },
            { key: 'b', head: 'Bentuk', width: 56, render: (f) => <Badge kind="kode">{f.cargo_form}</Badge> },
            { key: 's', head: 'Sat.', width: 40, render: (f) => <span className="text-[13px] text-abu">{f.unit}</span> },
            { key: 'm', head: 'Th', width: 70, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'start_year']} label={`Tahun mulai ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            { key: 'v0', head: 'Awal', width: 120, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'initial']} label={`Volume awal ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            { key: 'vm', head: 'Maks', width: 120, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'maximum']} label={`Volume maks ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            {
              key: 'g',
              head: 'Laju / rasio',
              width: 120,
              input: true,
              render: (f) =>
                f.volume.mode === 'independent' ? (
                  <Cell path={['flows', c.flows.indexOf(f), 'volume', 'growth_rate']} label={`Laju ${f.id}`} scale={100} digits={1} unit="%" />
                ) : (
                  <Cell path={['flows', c.flows.indexOf(f), 'volume', 'ratio']} label={`Rasio ${f.id}`} digits={2} unit="×" />
                ),
            },
            { key: 'p', head: 'Asal/tujuan', render: (f) => shortPortName(portOfRoute(c, f.route_id)?.name ?? '–') },
          ]}
        />
        <Note>Klik angka bertanda biru untuk mengedit (I4, I5). Klik baris inbound untuk memilihnya di what-if. Rasio fantasi dalam TEU: 1 TEU aluminium menjadi 2 TEU baja ringan.</Note>
      </Section>

      <Split
        left={
          <>
            <h2 className="m-0 pb-4 text-xl font-normal">Kalkulator ton ↔ TEU (I5)</h2>
            <select aria-label="Komoditas petikemas" value={comId} onChange={(e) => setComId(e.target.value)} className="h-10 rounded-kontrol border border-hitam bg-white px-3 text-sm font-medium">
              {pkCommodities.map((x) => (
                <option key={x.id} value={x.id}>{x.name}</option>
              ))}
            </select>
            <div className="h-3" />
            {com?.packaging && (
              <DefRow label="Kemasan" labelWidth={140}>
                <InputMark />
                <span className="font-mono">{num(com.packaging.length_m, 2)}×{num(com.packaging.width_m, 2)}×{num(com.packaging.height_m, 2)} m · {num(com.packaging.weight_kg, 1)} kg</span>
              </DefRow>
            )}
            <DefRow label="Kontainer 20 ft" labelWidth={140}><InputMark /><span className="font-mono">{num(c.params.container.inner_length_m, 3)}×{num(c.params.container.inner_width_m, 2)}×{num(c.params.container.inner_height_m, 2)} m</span></DefRow>
            <DefRow label="Berat bersih maks" labelWidth={140}><InputMark /><span className="font-mono">{num(c.params.container.max_net_t, 1)} t/TEU</span></DefRow>
            <DefRow label="Kemasan per TEU" labelWidth={140}><span className="font-mono text-abu">{comId === 'tepung_jagung' ? TEU_CALC.cartonsPerTeu : '–'}</span></DefRow>
            <DefRow label="Muatan per TEU" labelWidth={140}><span className="font-mono text-abu">{comId === 'tepung_jagung' ? `${num(TEU_CALC.tonPerTeu, 1)} t` : '–'}</span></DefRow>
            <DefRow label="TEU/th, tahun 10" labelWidth={140} last><span className="font-mono text-abu">{comId === 'tepung_jagung' ? TEU_CALC.teuYear10 : '–'}</span><PH /></DefRow>
          </>
        }
        right={<WhatIf flow={selIn} idx={selIdx} outIdx={outIdx} />}
      />

      <Section
        title={unit === 'ton' ? 'Proyeksi inbound 20 tahun, juta ton' : 'Proyeksi inbound 20 tahun, ribu TEU'}
        aside={
          <>
            <span className="flex overflow-hidden rounded-badge border border-hitam">
              {(['ton', 'TEU'] as const).map((u) => (
                <button key={u} type="button" onClick={() => setUnit(u)} className={`h-6 cursor-pointer border-0 px-2 text-[13px] ${unit === u ? 'bg-hitam font-medium text-white' : 'bg-white'}`}>{u}</button>
              ))}
            </span>
            <PH>placeholder · engine tahap 4</PH>
          </>
        }
      >
        <ColumnStack columns={columns} colors={unit === 'ton' ? colors : [C.biru]} height={240} labels={['th 1', 'th 5', 'th 10', 'th 15', 'th 20']} />
        <Legend
          items={
            unit === 'ton'
              ? [
                  { color: C.biru, label: 'Damai · jagung' },
                  { color: C.hitam, label: 'Esa · pelat baja' },
                  { color: C.hijau, label: 'Baru · gandum' },
                  { color: C.abu, label: 'Adi · CPO' },
                ]
              : [{ color: C.biru, label: 'Fantasi · aluminium' }]
          }
        />
        <Note>Proyeksi belum mengikuti input yang diedit — dihitung engine tahap 4.</Note>
      </Section>
    </>
  )
}
