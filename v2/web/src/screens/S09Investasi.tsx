import { C, ColumnStack } from '../charts/charts'
import { KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { num } from '../lib/format'
import { INVEST_ITEMS, INVEST_SCHEDULE, KPI_SUMMARY } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S09Investasi() {
  const c = usePlanner((s) => s.caseData)
  return (
    <>
      <ScreenHeader step={9} kind="hasil" title="Investasi & ringkasan biaya" lead="Jadwal investasi terminal dan perairan, digabung dengan biaya pelayaran menjadi unit cost dan anuitas." badge={<PH>placeholder · engine tahap 8</PH>} />

      <KpiStrip items={KPI_SUMMARY} />

      <div className="flex w-full items-center gap-8">
        <div className="w-[392px] shrink-0">
          <Slider label="Discount rate (I9)" value={c.params.discount_rate * 100} min={4} max={16} step={0.5} display={`${num(c.params.discount_rate * 100, 1)} %`} />
        </div>
        <Note>Discount rate tinggi membuat investasi bertahap lebih menarik daripada membangun penuh di awal. Nilai diedit di layar 1.</Note>
      </div>

      <Section title="Jadwal investasi per tahun, Rp miliar" aside={<Legend items={[{ color: C.hitam, label: 'infrastruktur' }, { color: C.biru, label: 'alat' }, { color: C.hijau, label: 'penyimpanan' }]} />}>
        <ColumnStack columns={INVEST_SCHEDULE} colors={[C.hitam, C.biru, C.hijau]} height={200} labels={['th 0', 'th 5', 'th 10', 'th 15', 'th 19']} />
        <Note>Lonjakan mengikuti staging di layar 8 (bangun {c.horizon.construction_lead_years} tahun sebelum dibutuhkan).</Note>
      </Section>

      <Section title="Item investasi">
        <Table
          rowKey={(r) => r.item}
          rows={INVEST_ITEMS}
          columns={[
            { key: 'i', head: 'Item', width: 260, render: (r) => r.item },
            { key: 'c', head: 'Kategori', width: 140, render: (r) => <span className="text-[13px] text-abu">{r.cat}</span> },
            { key: 'y', head: 'Tahun bangun', width: 150, mono: true, render: (r) => r.years },
            { key: 'v', head: 'Nilai', mono: true, render: (r) => <span className="text-abu">{r.value}</span> },
          ]}
        />
        <Note>Harga satuan dari {c.unit_prices.length} item sheet Investasi ({c.unit_prices[0]?.year}), dieskalasi {num(c.params.escalation_infra * 100)} %/th. Semua nilai placeholder.</Note>
      </Section>
    </>
  )
}
