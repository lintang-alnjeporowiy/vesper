import { C, ColumnStack } from '../charts/charts'
import { Tv } from '../components/trace'
import { KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { num } from '../lib/format'
import { INVEST_ITEMS, INVEST_SCHEDULE, KPI_SUMMARY, SHIPPING_BY_YEAR } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S09Investasi() {
  const c = usePlanner((s) => s.caseData)
  return (
    <>
      <ScreenHeader step={9} kind="hasil" title="Investasi & ringkasan biaya" lead="Jadwal investasi terminal dan perairan, digabung dengan biaya pelayaran menjadi unit cost dan anuitas." badge={<PH>placeholder · engine tahap 8b–8c</PH>} />

      <KpiStrip items={KPI_SUMMARY} />

      <div className="flex w-full items-center gap-8">
        <div className="w-[392px] shrink-0">
          <Slider label="Discount rate (I9)" value={c.params.discount_rate * 100} min={4} max={16} step={0.5} display={`${num(c.params.discount_rate * 100, 1)} %`} />
        </div>
        <Note><Tv v="in.param.discount_rate">Discount rate</Tv> tinggi membuat investasi bertahap lebih menarik daripada membangun penuh di awal. Nilai diedit di layar 1.</Note>
      </div>

      <Section title="Biaya per tahun: investasi + pelayaran" aside={<span className="flex items-center gap-3"><Tv v="agg.tc" className="font-mono text-[13px]">ƒx biaya total/th</Tv><Legend items={[{ color: C.abu, label: 'biaya pelayaran' }, { color: C.hitam, label: 'infrastruktur' }, { color: C.biru, label: 'alat' }, { color: C.hijau, label: 'penyimpanan' }]} /></span>}>
        <ColumnStack columns={INVEST_SCHEDULE.map((col, y) => [SHIPPING_BY_YEAR[y], ...col])} colors={[C.abu, C.hitam, C.biru, C.hijau]} height={220} labels={['th 1', 'th 5', 'th 10', 'th 15', 'th 20']} yUnit="Rp miliar" xUnit="tahun operasi" />
        <Note><Tv v="shipcost.total">Biaya pelayaran</Tv> (semua flow, layar 7) tiap tahun ditumpuk dengan <Tv v="invest.total">investasi</Tv>; jumlahnya = biaya total per tahun yang didiskon menjadi NPV. Semua nilai placeholder.</Note>
        <Note>Lonjakan mengikuti staging di layar 8 (bangun <Tv v="in.horizon.lead">{`${c.horizon.construction_lead_years} tahun`}</Tv> sebelum dibutuhkan).</Note>
      </Section>

      <Section title="Item investasi">
        <Table
          rowKey={(r) => r.item}
          rows={INVEST_ITEMS}
          columns={[
            { key: 'i', head: 'Item', width: 260, render: (r) => r.item },
            { key: 'c', head: 'Kategori', width: 140, render: (r) => <span className="text-[13px] text-abu">{r.cat}</span> },
            { key: 'y', head: 'Tahun bangun', width: 150, mono: true, render: (r) => <Tv v={r.v === 'invest.berth' ? 'terminal.n_berth' : r.v === 'invest.handling' ? 'terminal.n_equip' : r.v === 'invest.waterside' ? 'dv.waterside' : 'in.horizon.storage_lookahead'}>{r.years}</Tv> },
            { key: 'v', head: 'Nilai', mono: true, render: (r) => <Tv v={r.v} className="text-abu">{r.value}</Tv> },
          ]}
        />
        <Note><Tv v="in.price.berth">{`Harga satuan dari ${c.unit_prices.length} item sheet Investasi (${c.unit_prices[0]?.year})`}</Tv>, dieskalasi <Tv v="in.param.escalation_infra">{num(c.params.escalation_infra * 100)} %/th</Tv>. Semua nilai placeholder.</Note>
      </Section>
    </>
  )
}
