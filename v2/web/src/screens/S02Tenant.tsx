import { useState } from 'react'
import type { CargoFlow } from '../api/case'
import { C, ColumnStack } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, Button, DefRow, EditNum, InputMark, Legend, Note, PH, ScreenHeader, Section, Slider, Split, Table } from '../components/ui'
import { commodityName, portOfRoute, shortPortName, tenantName } from '../lib/case'
import { fmtValue, series, useCalc } from '../lib/engine'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { PROJECTION } from '../mock/placeholders'
import { usePlanner } from '../store'

const COLORS = [C.biru, C.hitam, C.hijau, C.abu, C.merah]

function Cell(props: { path: (string | number)[]; label: string; digits?: number; scale?: number; unit?: string }) {
  const f = useField(props.path, props.label)
  if (f.value === undefined || f.value === null) return <span className="font-mono text-abu">–</span>
  return <EditNum {...f} mark={false} digits={props.digits} scale={props.scale} unit={props.unit} />
}

/** Badge status angka hasil di layar ini: dihitung engine, sedang dihitung, atau placeholder (API mati). */
function CalcBadge({ ok, loading }: { ok: boolean; loading?: boolean }) {
  return ok ? <Badge kind="dihitung">{loading ? 'menghitung…' : 'dihitung · engine'}</Badge> : <PH>placeholder · API tidak aktif</PH>
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
        <Note>Proyeksi dan TEU di layar ini langsung dihitung ulang engine. Setelah engine tahap 5–7: tahun volume menyentuh maks, kapan kapal ditambah (layar 6), kapan tambatan dan alat ditambah (layar 8).</Note>
      </div>
    </div>
  )
}

export default function S02Tenant() {
  const c = usePlanner((s) => s.caseData)
  const flowId = usePlanner((s) => s.flowId)
  const setFlow = usePlanner((s) => s.setFlow)
  const year = usePlanner((s) => s.year)
  const shipByFlow = usePlanner((s) => s.shipByFlow)
  const calc = useCalc()
  const res = calc.ok ? calc.result : undefined
  const loading = calc.status === 'loading'
  const [unit, setUnit] = useState<'ton' | 'TEU'>('ton')

  // Kalkulator ton ↔ TEU: komoditas yang diangkut dalam petikemas, dipetakan ke flow-nya (NetMax bergantung kapal flow itu).
  const teuForms = new Set(c.cargo_forms.filter((f) => f.default_unit === 'TEU').map((f) => f.code))
  const teuFlows = c.flows.filter((f) => teuForms.has(f.cargo_form))
  const [calcFlowId, setCalcFlowId] = useState(teuFlows.find((f) => f.unit === 'ton')?.id ?? teuFlows[0]?.id ?? '')
  const calcFlow = teuFlows.find((f) => f.id === calcFlowId) ?? teuFlows[0]
  const com = c.commodities.find((x) => x.id === calcFlow?.commodity_id)
  const calcShip = calcFlow ? (res?.ship_by_flow[calcFlow.id] ?? shipByFlow[calcFlow.id]) : undefined
  const calcShipName = c.ships.find((s) => s.id === calcShip)?.name ?? '–'
  const sc = (id: string) => (calcFlow && res ? (res.values[id]?.[calcFlow.id] as number | undefined) : undefined)

  const rows = c.tenants.flatMap((t) => c.flows.filter((f) => f.tenant_id === t.id))
  const inbound = c.flows.filter((f) => f.direction === 'inbound')
  const selIn = inbound.find((f) => f.id === flowId) ?? inbound[0]
  const selIdx = c.flows.indexOf(selIn)
  const outIdx = c.flows.findIndex((f) => f.volume.mode === 'ratio' && (f.volume as { basis_flow_id: string }).basis_flow_id === selIn.id)

  // Grafik: inbound per satuan kapal (ton: juta t, TEU: ribu TEU).
  const shipUnit = (f: CargoFlow) => (res ? res.units[f.id] : teuForms.has(f.cargo_form) ? 'TEU' : 'ton')
  const chartFlows = inbound.filter((f) => (shipUnit(f) === 'TEU') === (unit === 'TEU'))
  const div = unit === 'ton' ? 1e6 : 1e3
  const seriesOf = (f: CargoFlow) => series(res, 'cargo.demand_unit', f.id)?.map((v) => v / div) ?? PROJECTION[f.id] ?? []
  const columns = Array.from({ length: c.horizon.years }, (_, y) => chartFlows.map((f) => seriesOf(f)[y] ?? 0))
  const labels = [1, 5, 10, 15, 20].filter((y) => y <= c.horizon.years).map((y) => `th ${y}`)

  const dYear = (f: CargoFlow) => series(res, 'cargo.demand_unit', f.id)?.[year - 1]
  const unitLabel = (f: CargoFlow) => (shipUnit(f) === 'TEU' ? 'TEU' : 't')

  return (
    <>
      <ScreenHeader step={2} kind="input" title="Tenant & muatan" lead="Inbound punya volume sendiri. Outbound mengikuti inbound lewat rasio konversi." badge={<Badge kind="input">input K15 · {c.tenants.length} tenant · {c.flows.length} flow</Badge>} />

      <Section title="Tenant dan aliran muatan" aside={<><CalcBadge ok={!!res} loading={loading} /><Button size="sm" disabled>Tambah tenant</Button></>}>
        <Table<CargoFlow>
          rowKey={(f) => f.id}
          rows={rows}
          selected={(f) => f.id === selIn.id}
          groupStart={(f, i) => i === 0 || rows[i - 1].tenant_id !== f.tenant_id}
          onRowClick={(f) => f.direction === 'inbound' && setFlow(f.id)}
          columns={[
            { key: 't', head: 'Tenant', width: 120, render: (f) => (f.direction === 'inbound' ? <span className="font-medium">{tenantName(c, f.tenant_id).replace('PT. ', '')}</span> : '') },
            { key: 'a', head: 'Arah', width: 40, mono: true, render: (f) => (f.direction === 'inbound' ? 'in' : 'out') },
            { key: 'k', head: 'Komoditas', width: 150, render: (f) => commodityName(c, f.commodity_id) },
            { key: 'b', head: 'Bentuk', width: 56, render: (f) => <Badge kind="kode">{f.cargo_form}</Badge> },
            { key: 's', head: 'Sat.', width: 40, render: (f) => <span className="text-[13px] text-abu">{f.unit}</span> },
            { key: 'm', head: 'Th', width: 56, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'start_year']} label={`Tahun mulai ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            { key: 'v0', head: 'Awal', width: 110, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'initial']} label={`Volume awal ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            { key: 'vm', head: 'Maks', width: 110, input: true, render: (f) => (f.volume.mode === 'independent' ? <Cell path={['flows', c.flows.indexOf(f), 'volume', 'maximum']} label={`Volume maks ${f.id}`} /> : <span className="font-mono text-abu">–</span>) },
            {
              key: 'g',
              head: 'Laju / rasio',
              width: 100,
              input: true,
              render: (f) =>
                f.volume.mode === 'independent' ? (
                  <Cell path={['flows', c.flows.indexOf(f), 'volume', 'growth_rate']} label={`Laju ${f.id}`} scale={100} digits={1} unit="%" />
                ) : (
                  <Cell path={['flows', c.flows.indexOf(f), 'volume', 'ratio']} label={`Rasio ${f.id}`} digits={2} unit="×" />
                ),
            },
            {
              key: 'd',
              head: `D th ${year}`,
              width: 120,
              render: (f) => {
                const v = dYear(f)
                return v === undefined ? (
                  <span className="font-mono text-abu">–</span>
                ) : (
                  <Tv v="cargo.demand_unit" ctx={{ flow: f.id, year }} className="font-mono">
                    {fmtValue(v)} <span className="text-[13px] text-abu">{unitLabel(f)}</span>
                  </Tv>
                )
              },
            },
            { key: 'p', head: 'Asal/tujuan', render: (f) => shortPortName(portOfRoute(c, f.route_id)?.name ?? '–') },
          ]}
        />
        <Note>Klik angka bertanda biru untuk mengedit (I4, I5); kolom D = demand tahun {year} dalam satuan kapal (ton, atau TEU untuk petikemas), dihitung engine — ganti tahun di bar atas. Klik baris inbound untuk memilihnya di what-if. Rasio fantasi dalam TEU: 1 TEU aluminium menjadi 2 TEU baja ringan.</Note>
      </Section>

      <Split
        left={
          <>
            <h2 className="m-0 flex items-center gap-2 pb-4 text-xl font-normal">Kalkulator ton ↔ TEU (I5) <CalcBadge ok={!!res} loading={loading} /></h2>
            <select aria-label="Flow petikemas" value={calcFlow?.id ?? ''} onChange={(e) => setCalcFlowId(e.target.value)} className="h-10 rounded-kontrol border border-hitam bg-white px-3 text-sm font-medium">
              {teuFlows.map((f) => (
                <option key={f.id} value={f.id}>{commodityName(c, f.commodity_id)} · {f.id}</option>
              ))}
            </select>
            <div className="h-3" />
            {com?.packaging ? (
              <DefRow label="Kemasan" labelWidth={150}>
                <InputMark />
                <span className="font-mono">{num(com.packaging.length_m, 2)}×{num(com.packaging.width_m, 2)}×{num(com.packaging.height_m, 3)} m · {num(com.packaging.weight_kg, 2)} kg</span>
              </DefRow>
            ) : (
              <DefRow label="Stowage factor" labelWidth={150}><InputMark /><span className="font-mono">{com?.stowage_factor_m3_t ? `${num(com.stowage_factor_m3_t, 2)} m³/t` : com?.density_t_m3 ? `ρ ${num(com.density_t_m3, 2)} t/m³` : '–'}</span></DefRow>
            )}
            <DefRow label="Kontainer 20 ft" labelWidth={150}><InputMark /><span className="font-mono">{num(c.params.container.inner_length_m, 3)}×{num(c.params.container.inner_width_m, 2)}×{num(c.params.container.inner_height_m, 2)} m</span></DefRow>
            <DefRow label={`NetMax · ${calcShipName}`} labelWidth={150}>
              {sc('cargo.netmax') === undefined ? <span className="font-mono text-abu">–</span> : <Tv v="cargo.netmax" ctx={{ flow: calcFlow?.id, ship: calcShip }} className="font-mono">{num(sc('cargo.netmax'), 3)} t/TEU</Tv>}
            </DefRow>
            <DefRow label="Kemasan per TEU" labelWidth={150}>
              {sc('cargo.box_per_teu') === undefined ? <span className="font-mono text-abu">{com?.packaging ? '–' : 'tanpa data kemasan'}</span> : <Tv v="cargo.box_per_teu" ctx={{ flow: calcFlow?.id, ship: calcShip }} className="font-mono">{num(sc('cargo.box_per_teu'))}</Tv>}
            </DefRow>
            <DefRow label="Muatan per TEU" labelWidth={150}>
              {sc('cargo.ton_per_teu') === undefined ? <span className="font-mono text-abu">–</span> : <Tv v="cargo.ton_per_teu" ctx={{ flow: calcFlow?.id, ship: calcShip }} className="font-mono">{num(sc('cargo.ton_per_teu'), 3)} t</Tv>}
            </DefRow>
            <DefRow label={`D_TEU, tahun ${year}`} labelWidth={150} last>
              {calcFlow && dYear(calcFlow) !== undefined ? <Tv v="cargo.demand_unit" ctx={{ flow: calcFlow.id, year }} className="font-mono">{fmtValue(dYear(calcFlow) ?? 0)} TEU</Tv> : <span className="font-mono text-abu">–</span>}
            </DefRow>
            <Note>NetMax = min(berat bersih maks kontainer, α·DWT/TEU − tare) bergantung kapal terpilih flow ini (A8). {calcFlow?.unit === 'TEU' ? 'Flow ini sudah didefinisikan dalam TEU; ton/TEU dipakai untuk cek payload (tahap 5).' : 'D_TEU = ⌈D ton / muatan per TEU⌉, dibulatkan sekali per tahun (A12).'}</Note>
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
            <CalcBadge ok={!!res} loading={loading} />
          </>
        }
      >
        <ColumnStack columns={columns} colors={COLORS} height={240} labels={labels} yUnit={unit === 'ton' ? 'juta t/th' : 'ribu TEU/th'} xUnit="tahun ke-" />
        <Legend items={chartFlows.map((f, i) => ({ color: COLORS[i % COLORS.length], label: `${tenantName(c, f.tenant_id).replace('PT. ', '').split(' ')[0]} · ${commodityName(c, f.commodity_id).toLowerCase()}` }))} />
        <Note>
          {res
            ? 'Dihitung engine dari input aktif (termasuk editan): D[t] = 0 sebelum tahun mulai, V₀ di tahun mulai, lalu min(Dmax, D[t−1]·(1+g)) — batas dicek ke tahun sebelumnya (A4).'
            : `Engine tidak terjangkau (${calc.error ?? 'API belum dijalankan'}); grafik menampilkan placeholder dan belum mengikuti editan. Jalankan konfigurasi "api" (uvicorn :8000).`}
        </Note>
      </Section>
    </>
  )
}
