import { BarRows, C } from '../charts/charts'
import { Badge, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { startYearOf } from '../lib/case'
import { num } from '../lib/format'
import { SHIPPING_DETAIL_DAMAI, SHIPPING_Y10 } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S07Biaya() {
  const c = usePlanner((s) => s.caseData)
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
      <Note>Slider menampilkan input saat ini (edit nilainya di layar 1). Efek ke biaya muncul setelah engine tahap 6.</Note>

      <KpiStrip
        items={[
          { label: 'Total shipping cost th 10', value: `Rp ${num(total / 1000, 2)} T` },
          { label: 'Porsi BBM', value: `${num((bbm / total) * 100)} %` },
          { label: 'Flow termahal per ton', value: 'in.baru' },
        ]}
      />

      <Section title="Komposisi per flow · tahun 10, Rp miliar" aside={<Legend items={[{ color: C.hitam, label: 'TCH' }, { color: C.biru, label: 'BBM' }, { color: C.hijau, label: 'pelabuhan' }]} />}>
        <BarRows
          colors={[C.hitam, C.biru, C.hijau]}
          rows={c.flows.map((f) => {
            const p = SHIPPING_Y10[f.id] ?? null
            return { label: f.id, parts: p, total: p ? num(p[0] + p[1] + p[2]) : undefined, emptyText: `mulai tahun ${startYearOf(c, f.id) ?? '?'}` }
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
            { key: 's', head: 'Kapal', width: 80, mono: true, render: (r) => <span className="text-abu">{r.ships}</span> },
            { key: 'c', head: 'Call/th', width: 90, mono: true, render: (r) => <span className="text-abu">{r.calls}</span> },
            { key: 't', head: 'TCH', width: 110, mono: true, render: (r) => <span className="text-abu">{r.tch} M</span> },
            { key: 'b', head: 'BBM', width: 110, mono: true, render: (r) => <span className="text-abu">{r.bbm} M</span> },
            { key: 'p', head: 'Pelabuhan', width: 110, mono: true, render: (r) => <span className="text-abu">{r.port} M</span> },
            { key: 'tot', head: 'Total', width: 110, mono: true, render: (r) => <span className="text-abu">{r.tch + r.bbm + r.port} M</span> },
            { key: 'u', head: 'Rp/t', mono: true, render: (r) => <span className="text-abu">{r.rpPerT} rb</span> },
          ]}
        />
        <Note>Semua angka placeholder. Biaya pelabuhan = tarif × frekuensi aktual (A11), bukan nilai statis Excel.</Note>
      </Section>
    </>
  )
}
