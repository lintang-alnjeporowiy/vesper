import { useState } from 'react'
import { BarRows, C, ColumnStack } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { portOfRoute, shortPortName, startYearOf } from '../lib/case'
import { series, useCalc } from '../lib/engine'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { usePlanner } from '../store'

const PART_VARS = ['shipcost.tch', 'shipcost.voyage', 'shipcost.port']
const PART_LABEL = ['TCH', 'BBM', 'pelabuhan']
const COLORS = [C.hitam, C.biru, C.hijau]

/** Rupiah ringkas: miliar (M) atau triliun (T). */
function rp(v: number | undefined): string {
  if (v === undefined) return '–'
  const a = Math.abs(v)
  if (a >= 1e12) return `${num(v / 1e12, 2)} T`
  if (a >= 1e9) return `${num(v / 1e9, 1)} M`
  if (a >= 1e6) return `${num(v / 1e6, 1)} jt`
  return num(v)
}

const PORT_ROWS: { key: string; comp: string; basis: string }[] = [
  { key: 'labuh', comp: 'Jasa labuh', basis: 'tarif/GT per kunjungan × GT' },
  { key: 'pandu', comp: 'Jasa pandu', basis: '(tetap + variabel × GT) × 2 gerakan' },
  { key: 'tambat', comp: 'Jasa tambat', basis: 'tarif/GT/etmal × GT × ⌈port time asal/tujuan⌉ etmal' },
  { key: 'tunda', comp: 'Jasa tunda', basis: '(tetap + variabel × GT, rentang GT) × 2 gerakan' },
  { key: 'bm', comp: 'Bongkar muat', basis: 'muatan per call × tarif per ton atau per TEU' },
]

export default function S07Biaya() {
  const c = usePlanner((s) => s.caseData)
  const shipByFlow = usePlanner((s) => s.shipByFlow)
  const showTrace = usePlanner((s) => s.showTrace)
  const year = usePlanner((s) => s.year)
  const calc = useCalc()
  const res = calc.ok ? calc.result : undefined
  const hsdIdx = c.params.fuels.findIndex((f) => f.code === 'HSD')
  const hsd = useField(['params', 'fuels', hsdIdx, 'price_rp_per_l'], 'Harga HSD')
  const usd = useField(['params', 'usd_rate'], 'Kurs USD')
  const ctxOf = (flow: string, y = year) => ({ flow, ship: shipByFlow[flow], year: y })
  const at = (id: string, flow: string, y = year) => series(res, id, flow)?.[y - 1]
  const parts = (flow: string, y = year): number[] | null => {
    const p = PART_VARS.map((id) => at(id, flow, y) ?? 0)
    return p.some((v) => v > 0) ? p : null
  }

  const flowsActive = c.flows.filter((f) => (at('shipcost.total', f.id) ?? 0) > 0)
  const total = flowsActive.reduce((a, f) => a + (at('shipcost.total', f.id) ?? 0), 0)
  const bbm = flowsActive.reduce((a, f) => a + (at('shipcost.voyage', f.id) ?? 0), 0)
  const unitOfFlow = (fid: string) => (c.flows.find((f) => f.id === fid)?.unit === 'TEU' ? 'TEU' : 't')
  const tonFlows = flowsActive.filter((f) => unitOfFlow(f.id) === 't')
  const worst = tonFlows.reduce<string | undefined>((w, f) => (w === undefined || (at('shipcost.unit', f.id) ?? 0) > (at('shipcost.unit', w) ?? 0) ? f.id : w), undefined)

  const [flow, setFlow] = useState('in.damai')
  const flowObj = c.flows.find((f) => f.id === flow)
  const portName = flowObj ? shortPortName(portOfRoute(c, flowObj.route_id)?.name ?? '') : ''
  const port = flowObj ? portOfRoute(c, flowObj.route_id) : undefined
  const shipName = c.ships.find((s) => s.id === (res?.ship_by_flow[flow] ?? shipByFlow[flow]))?.name ?? '–'
  const years = Array.from({ length: c.horizon.years }, (_, i) => i + 1)
  const rows = years.filter((y) => (at('voyage.freq', flow, y) ?? 0) > 0)
  const breakdown = res?.port_breakdown[flow]
  const callTotal = at('shipcost.port_call', flow)
  const byYear = years.map((y) => PART_VARS.map((id) => c.flows.reduce((a, f) => a + (at(id, f.id, y) ?? 0), 0) / 1e9))
  const badge = res ? <Badge kind="dihitung">dihitung · engine</Badge> : <PH>placeholder · API tidak aktif</PH>

  return (
    <>
      <ScreenHeader step={7} kind="hasil" title="Biaya pelayaran" lead="TCH, BBM, dan biaya pelabuhan per flow per tahun, dari armada yang dipilih di layar 6." badge={badge} />

      <div className="flex w-full gap-8 border-y border-garis py-4">
        <Slider label="Harga HSD (I7)" value={hsd.value} min={10000} max={40000} step={500} display={`Rp ${num(hsd.value)} / l`} onChange={hsd.onChange} />
        <Slider label="Kurs (I7)" value={usd.value} min={12000} max={20000} step={50} display={num(usd.value)} onChange={usd.onChange} />
      </div>
      <Note>
        Geser untuk melihat efek <Tv v="in.param.fuel_price">harga BBM</Tv> dan <Tv v="in.param.usd_rate">kurs</Tv> (TCH dan tarif pelabuhan luar negeri dalam USD); engine menghitung ulang langsung. Tarif pelabuhan per kelas diedit di layar 3. Jenis BBM ME & AE = HSD (A6).
      </Note>

      <KpiStrip
        ctx={{ year }}
        items={[
          { label: `Total shipping cost th ${year}`, value: res ? `Rp ${rp(total)}` : '–', v: 'shipcost.total' },
          { label: 'Porsi BBM', value: res && total ? `${num((bbm / total) * 100)} %` : '–', v: 'shipcost.voyage' },
          { label: 'Flow termahal per ton', value: res && worst ? `${worst} · Rp ${num((at('shipcost.unit', worst) ?? 0) / 1000)} rb/t` : '–', v: 'shipcost.unit' },
        ]}
      />

      <Section title={`Komposisi per flow · tahun ${year}`} aside={<span className="flex items-center gap-3"><Legend items={[{ color: C.hitam, label: 'TCH' }, { color: C.biru, label: 'BBM' }, { color: C.hijau, label: 'pelabuhan' }]} />{badge}</span>}>
        <BarRows
          colors={COLORS}
          xUnit="Rp miliar/th"
          onSegment={(f, j, v) => showTrace(PART_VARS[j], ctxOf(f), `Rp ${num(v, 1)} M`)}
          segmentTitle={(f, j, v) => `${f} · ${PART_LABEL[j]} Rp ${num(v, 1)} M — klik untuk jejak`}
          rows={c.flows.map((f) => {
            const p = parts(f.id)
            return {
              label: f.id,
              parts: p ? p.map((v) => v / 1e9) : null,
              total: p ? <Tv v="shipcost.total" ctx={ctxOf(f.id)}>{rp(at('shipcost.total', f.id))}</Tv> : undefined,
              emptyText: res ? `mulai tahun ${startYearOf(c, f.id) ?? '?'}` : 'API tidak aktif',
            }
          })}
        />
      </Section>

      <Section title="Biaya pelayaran per tahun · semua flow" aside={badge}>
        {res ? (
          <>
            <ColumnStack columns={byYear} colors={COLORS} height={220} labels={['th 1', 'th 5', 'th 10', 'th 15', 'th 20']} yUnit="Rp miliar/th" xUnit="tahun ke-" />
            <Legend items={[{ color: C.hitam, label: 'TCH' }, { color: C.biru, label: 'BBM' }, { color: C.hijau, label: 'pelabuhan' }]} />
          </>
        ) : (
          <Note>Grafik muncul setelah engine menjawab.</Note>
        )}
      </Section>

      <Section
        title="Rincian per tahun"
        aside={
          <span className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-[13px] text-abu">
              Flow (tenant · arah)
              <select aria-label="Flow yang dirinci" value={flow} onChange={(e) => setFlow(e.target.value)} className="h-8 rounded-kontrol border border-hitam bg-white px-2 text-[13px] text-hitam">
                {c.flows.map((f) => <option key={f.id} value={f.id}>{f.id}</option>)}
              </select>
            </label>
            <span className="text-[13px] text-abu">{shipName}</span>
            <Badge kind="audit">≠ Excel · A9, A11, A14, A15</Badge>
          </span>
        }
      >
        {rows.length === 0 ? (
          <Note>{res ? `Flow ${flow} belum punya pelayaran (atau kapal/tarif belum lengkap).` : 'API tidak aktif.'}</Note>
        ) : (
          <Table
            rowKey={(y) => String(y)}
            rows={rows}
            selected={(y) => y === year}
            columns={[
              { key: 'y', head: 'Tahun', width: 64, mono: true, render: (y) => y },
              { key: 's', head: 'Kapal', width: 64, mono: true, render: (y) => <Tv v="voyage.n_ship" ctx={ctxOf(flow, y)}>{num(at('voyage.n_ship', flow, y))}</Tv> },
              { key: 'c', head: 'Call/th', width: 72, mono: true, render: (y) => <Tv v="voyage.freq" ctx={ctxOf(flow, y)}>{num(at('voyage.freq', flow, y))}</Tv> },
              { key: 't', head: 'TCH, Rp', width: 100, mono: true, render: (y) => <Tv v="shipcost.tch" ctx={ctxOf(flow, y)}>{rp(at('shipcost.tch', flow, y))}</Tv> },
              { key: 'b', head: 'BBM, Rp', width: 100, mono: true, render: (y) => <Tv v="shipcost.voyage" ctx={ctxOf(flow, y)}>{rp(at('shipcost.voyage', flow, y))}</Tv> },
              { key: 'p', head: 'Pelabuhan, Rp', width: 110, mono: true, render: (y) => <Tv v="shipcost.port" ctx={ctxOf(flow, y)}>{rp(at('shipcost.port', flow, y))}</Tv> },
              { key: 'tot', head: 'Total, Rp', width: 100, mono: true, render: (y) => <Tv v="shipcost.total" ctx={ctxOf(flow, y)} className="font-medium">{rp(at('shipcost.total', flow, y))}</Tv> },
              { key: 'u', head: `Per satuan, Rp/${unitOfFlow(flow)}`, mono: true, render: (y) => <Tv v="shipcost.unit" ctx={ctxOf(flow, y)}>{num(at('shipcost.unit', flow, y))}</Tv> },
            ]}
          />
        )}
        <Note>M = miliar, T = triliun. Klik angka untuk jejaknya. BBM dari frekuensi aktual (A9); biaya pelabuhan = biaya per call × frekuensi aktual (A11) dengan tarif luar negeri untuk pelabuhan luar negeri (A14). Per satuan = shipping cost ÷ demand dalam satuan flow (A7).</Note>
      </Section>

      <Section title={`Biaya pelabuhan per call · ${flow} di ${portName} · tahun ${year}`} aside={badge}>
        {breakdown && callTotal ? (
          <Table
            rowKey={(r) => r.key}
            rows={PORT_ROWS}
            columns={[
              { key: 'c', head: 'Komponen', width: 150, render: (r) => r.comp },
              { key: 'b', head: 'Dasar perhitungan', render: (r) => <span className="text-[13px] text-abu">{r.basis}</span> },
              { key: 'v', head: 'Per call, Rp juta', width: 140, mono: true, render: (r) => <Tv v="shipcost.port_call" ctx={ctxOf(flow)}>{num((breakdown[r.key]?.[year - 1] ?? 0) / 1e6, 1)}</Tv> },
            ]}
          />
        ) : (
          <Note>{res ? `Tidak ada call di tahun ${year} untuk ${flow}.` : 'API tidak aktif.'}</Note>
        )}
        <Note>
          {callTotal ? `Total per call Rp ${num(callTotal / 1e6, 1)} juta. ` : ''}
          {port ? `${portName}: kelas tarif ${port.tariff_class}, ${port.kind === 'foreign' ? 'luar negeri (USD × kurs)' : 'dalam negeri'}, tambatan ${port.berth_type}. ` : ''}
          GT dan muatan per call dari kapal terpilih ({shipName}); lama tambat = port time di pelabuhan itu, dibulatkan ke etmal (A15). Di KEK (TERSUS) {c.kek_site.port_charges === 'none' ? 'tidak ada tarif pelabuhan' : `dikenai tarif kelas ${c.kek_site.tariff_class}`}.
        </Note>
      </Section>
    </>
  )
}
