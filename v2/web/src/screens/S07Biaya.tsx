import { BarRows, C } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { startYearOf } from '../lib/case'
import { num } from '../lib/format'
import { SHIPPING_DETAIL_DAMAI, SHIPPING_Y10 } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S07Biaya() {
  const c = usePlanner((s) => s.caseData)
  const shipByFlow = usePlanner((s) => s.shipByFlow)
  const showTrace = usePlanner((s) => s.showTrace)
  const PART_VARS = ['shipcost.tch', 'shipcost.voyage', 'shipcost.port']
  const PART_LABEL = ['TCH', 'BBM', 'pelabuhan']
  const ctxOf = (flow: string, year = 10) => ({ flow, ship: shipByFlow[flow], year })
  const hsd = c.params.fuels.find((f) => f.code === 'HSD')
  const total = Object.values(SHIPPING_Y10).reduce((a, p) => a + (p ? p[0] + p[1] + p[2] : 0), 0)
  const bbm = Object.values(SHIPPING_Y10).reduce((a, p) => a + (p ? p[1] : 0), 0)

  return (
    <>
      <ScreenHeader step={7} kind="hasil" title="Biaya pelayaran" lead="TCH, BBM, dan biaya pelabuhan per flow per tahun, dari armada yang dipilih di layar 6." badge={<PH>placeholder · engine tahap 6</PH>} />

      <div className="flex w-full gap-8 border-y border-garis py-4">
        <Slider label="Harga HSD (I7)" value={hsd?.price_rp_per_l ?? 0} min={10000} max={40000} step={500} display={`Rp ${num(hsd?.price_rp_per_l ?? 0)} / l`} />
        <Slider label="Kurs (I7)" value={c.params.usd_rate} min={12000} max={20000} step={50} display={num(c.params.usd_rate)} />
        <Slider label="Pengali tarif (I7)" value={1} min={0.5} max={2} step={0.05} display="× 1,00" />
      </div>
      <Note>
        Slider menampilkan input saat ini: <Tv v="in.param.fuel_price">harga BBM</Tv>, <Tv v="in.param.usd_rate">kurs</Tv>, <Tv v="in.tariff.labuh">tarif pelabuhan</Tv> (edit nilainya di layar 1). Efek ke biaya muncul setelah engine tahap 6.
      </Note>

      <KpiStrip
        ctx={{ year: 10 }}
        items={[
          { label: 'Total shipping cost th 10', value: `Rp ${num(total / 1000, 2)} T`, v: 'shipcost.total' },
          { label: 'Porsi BBM', value: `${num((bbm / total) * 100)} %`, v: 'shipcost.voyage' },
          { label: 'Flow termahal per ton', value: 'in.baru', v: 'shipcost.unit' },
        ]}
      />

      <Section title="Komposisi per flow · tahun 10, Rp miliar" aside={<Legend items={[{ color: C.hitam, label: 'TCH' }, { color: C.biru, label: 'BBM' }, { color: C.hijau, label: 'pelabuhan' }]} />}>
        <BarRows
          colors={[C.hitam, C.biru, C.hijau]}
          onSegment={(flow, j, v) => showTrace(PART_VARS[j], ctxOf(flow), `Rp ${num(v)} M`)}
          segmentTitle={(flow, j, v) => `${flow} · ${PART_LABEL[j]} Rp ${num(v)} M — klik untuk jejak`}
          rows={c.flows.map((f) => {
            const p = SHIPPING_Y10[f.id] ?? null
            return { label: f.id, parts: p, total: p ? <Tv v="shipcost.total" ctx={ctxOf(f.id)}>{num(p[0] + p[1] + p[2])}</Tv> : undefined, emptyText: `mulai tahun ${startYearOf(c, f.id) ?? '?'}` }
          })}
        />
      </Section>

      <Section title="Rincian in.damai per tahun" aside={<Badge kind="audit">≠ Excel · A11</Badge>}>
        <Table
          rowKey={(r) => String(r.year)}
          rows={SHIPPING_DETAIL_DAMAI}
          selected={(r) => r.year === 10}
          columns={[
            { key: 'y', head: 'Tahun', width: 70, mono: true, render: (r) => r.year },
            { key: 's', head: 'Kapal', width: 80, mono: true, render: (r) => <Tv v="voyage.n_ship" ctx={ctxOf('in.damai', r.year)} className="text-abu">{String(r.ships)}</Tv> },
            { key: 'c', head: 'Call/th', width: 90, mono: true, render: (r) => <Tv v="voyage.freq" ctx={ctxOf('in.damai', r.year)} className="text-abu">{String(r.calls)}</Tv> },
            { key: 't', head: 'TCH', width: 110, mono: true, render: (r) => <Tv v="shipcost.tch" ctx={ctxOf('in.damai', r.year)} className="text-abu">{`${r.tch} M`}</Tv> },
            { key: 'b', head: 'BBM', width: 110, mono: true, render: (r) => <Tv v="shipcost.voyage" ctx={ctxOf('in.damai', r.year)} className="text-abu">{`${r.bbm} M`}</Tv> },
            { key: 'p', head: 'Pelabuhan', width: 110, mono: true, render: (r) => <Tv v="shipcost.port" ctx={ctxOf('in.damai', r.year)} className="text-abu">{`${r.port} M`}</Tv> },
            { key: 'tot', head: 'Total', width: 110, mono: true, render: (r) => <Tv v="shipcost.total" ctx={ctxOf('in.damai', r.year)} className="text-abu">{`${r.tch + r.bbm + r.port} M`}</Tv> },
            { key: 'u', head: 'Rp/t', mono: true, render: (r) => <Tv v="shipcost.unit" ctx={ctxOf('in.damai', r.year)} className="text-abu">{`${r.rpPerT} rb`}</Tv> },
          ]}
        />
        <Note>Semua angka placeholder; klik angka atau segmen batang untuk jejaknya. Biaya pelabuhan = tarif × frekuensi aktual (A11), bukan nilai statis Excel.</Note>
      </Section>
    </>
  )
}
