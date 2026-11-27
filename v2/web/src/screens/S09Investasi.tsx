import { C, ColumnStack } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, DefRow, EditNum, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Split, Table, Tabs } from '../components/ui'
import { TOTAL, buildYears, rp, series, sum, useCalc, withInvest } from '../lib/engine'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { INVEST_ITEMS, INVEST_SCHEDULE, KPI_SUMMARY, SHIPPING_BY_YEAR } from '../mock/placeholders'
import { usePlanner } from '../store'

type Cat = 'infrastruktur' | 'alat' | 'penyimpanan'
const CATS: Cat[] = ['infrastruktur', 'alat', 'penyimpanan']
const CAT_COLOR: Record<Cat, string> = { infrastruktur: C.hitam, alat: C.biru, penyimpanan: C.hijau }
/** variabel investasi → kategori tumpukan grafik */
const CAT_OF: Record<string, Cat> = {
  'invest.berth': 'infrastruktur', 'invest.waterside': 'infrastruktur', 'invest.handling': 'alat', 'invest.yard_equipment': 'alat',
  'invest.storage': 'penyimpanan', 'invest.pipeline': 'penyimpanan',
}
const FACILITY: Record<string, string> = { cy: 'Lapangan petikemas (CY)', gc: 'Lapangan / gudang GC', bulk: 'Silo curah kering', liquid: 'Tangki timbun' }

export default function S09Investasi() {
  const { caseData: c, setInput } = usePlanner()
  const calc = useCalc()
  const ires = withInvest(calc.ok ? calc.result : undefined)
  const shipRes = calc.ok && calc.result?.modules.includes('shipcost') ? calc.result : undefined
  const plan = c.plans?.[0]
  const nYears = c.horizon.years ?? 20
  const y0 = ires?.invest_start_year ?? 1 - c.horizon.construction_lead_years
  const years = Array.from({ length: nYears + 1 - y0 }, (_, i) => i + y0)
  const disc = useField(['params', 'discount_rate'], 'Discount rate')
  const lead = useField(['horizon', 'construction_lead_years'], 'Masa konstruksi')
  const lookB = useField(['horizon', 'berth_lookahead_years'], 'Lookahead tambatan')
  const lookS = useField(['horizon', 'storage_lookahead_years'], 'Lookahead penyimpanan')
  const staging = plan?.staging ?? 'phase'
  const esc = c.params.apply_escalation ?? false

  // baris item investasi dari engine (variabel × kunci)
  const termName = (id: string) => c.kek_site.terminals.find((t) => t.id === id)?.name ?? id
  const eqName = (id: string) => c.storage.yard_equipment?.find((e) => e.id === id)?.name.replace(/ \(.*\)$/, '') ?? id
  const label = (vid: string, key: string) => {
    switch (vid) {
      case 'invest.berth': return `${termName(key)} · tambatan`
      case 'invest.handling': return `Alat B/M ${key}`
      case 'invest.waterside': return `Trestle & keruk ${key}`
      case 'invest.storage': return FACILITY[key] ?? key
      case 'invest.pipeline': return `Pipa ${key}`
      default: return eqName(key)
    }
  }
  const items = ires
    ? Object.keys(CAT_OF).flatMap((vid) => Object.entries(ires.values[vid] ?? {}).flatMap(([key, s]) => {
        const arr = Array.isArray(s) ? s : []
        return sum(arr) ? [{ vid, key, label: label(vid, key), cat: CAT_OF[vid], arr, years: buildYears(ires, arr), total: sum(arr) ?? 0 }] : []
      }))
    : []
  const totalSeries = series(ires, 'invest.total', TOTAL)
  const grand = sum(totalSeries)
  const shipping = (y: number) => (shipRes ? c.flows.reduce((a, f) => a + (series(shipRes, 'shipcost.total', f.id)?.[y - 1] ?? 0), 0) : 0)
  const columns = ires
    ? years.map((y) => [shipping(y) / 1e9, ...CATS.map((cat) => items.filter((it) => it.cat === cat).reduce((a, it) => a + (it.arr[y - y0] ?? 0), 0) / 1e9)])
    : INVEST_SCHEDULE.map((col, y) => [SHIPPING_BY_YEAR[y], ...col])
  const xLabels = ires ? [years[0], 5, 10, 15, nYears].map((y) => `th ${y}`) : ['th 1', 'th 5', 'th 10', 'th 15', 'th 20']
  const first = totalSeries?.[0] ?? 0
  const kpis = ires
    ? KPI_SUMMARY.map((k) => (k.v === 'invest.total' ? { ...k, label: `Investasi Σ th ${y0}–${nYears} (nominal)`, value: rp(grand) } : k))
    : KPI_SUMMARY

  return (
    <>
      <ScreenHeader step={9} kind="hasil" title="Investasi & ringkasan biaya" lead="Jadwal investasi terminal dan perairan, digabung dengan biaya pelayaran menjadi unit cost dan anuitas."
        badge={ires ? <Badge kind="dihitung">jadwal investasi dihitung · total cost, unit cost, NPV placeholder (tahap 8c)</Badge> : <PH>placeholder · API tidak aktif</PH>} />

      <KpiStrip items={kpis} ctx={{ flow: TOTAL, year: y0 }} />
      <Note>Total biaya, anuitas, dan NPV menunggu agregasi (tahap 8c); investasi Σ = jumlah nominal jadwal di bawah{ires ? `, ${rp(first)} di th ${y0}` : ''}.</Note>

      <Section title="Pola bangun & harga">
        <Split
          left={
            <>
              <DefRow label={<Tv v="dv.staging">Pola bangun</Tv>} justify>
                <span className="w-[260px]"><Tabs items={[{ id: 'phase', label: 'Per tahap' }, { id: 'incremental', label: 'Saat dibutuhkan' }]} value={staging} onChange={(v) => setInput(['plans', 0, 'staging'], v, 'Pola bangun investasi')} /></span>
              </DefRow>
              <DefRow label={<Tv v="in.horizon.lead">Masa konstruksi</Tv>} justify><EditNum {...lead} unit="th" digits={0} /></DefRow>
              <DefRow label={<Tv v="in.horizon.berth_lookahead">Lookahead tambatan, alat B/M, perairan</Tv>} justify><EditNum {...lookB} unit="th" digits={0} /></DefRow>
              <DefRow label={<Tv v="in.horizon.storage_lookahead">Lookahead penyimpanan, alat lapangan, truk, pipa</Tv>} justify last><EditNum {...lookS} unit="th" digits={0} /></DefRow>
            </>
          }
          right={
            <>
              <DefRow label={<Tv v="in.param.apply_escalation">Eskalasi harga</Tv>} justify>
                <span className="w-[200px]"><Tabs items={[{ id: 'off', label: 'Mati' }, { id: 'on', label: 'Hidup' }]} value={esc ? 'on' : 'off'} onChange={(v) => setInput(['params', 'apply_escalation'], v === 'on', 'Terapkan eskalasi')} /></span>
              </DefRow>
              <DefRow label={<Tv v="in.param.escalation_infra">Eskalasi infrastruktur</Tv>} justify><span className="font-mono">{num(c.params.escalation_infra * 100, 1)} %/th</span></DefRow>
              <DefRow label={<Tv v="in.param.escalation_equipment">Eskalasi alat</Tv>} justify><span className="font-mono">{num(c.params.escalation_equipment * 100, 1)} %/th</span></DefRow>
              <DefRow label={<Tv v="in.price.berth">Harga satuan</Tv>} justify last><span className="text-[13px] text-abu">{`${c.unit_prices.length} item · tahun ${c.unit_prices[0]?.year ?? '–'}`}</span></DefRow>
            </>
          }
        />
        <Note>
          {staging === 'incremental'
            ? <>Saat dibutuhkan: bila kebutuhan tahun t melampaui kapasitas terpasang, dibangun di tahun t − masa konstruksi untuk kebutuhan terbesar N tahun ke depan (lookahead).</>
            : <>Per tahap: tiap <Tv v="in.horizon.phases">tahap</Tv> ({c.horizon.phases.map((p) => `${p.name} ${p.start_year}–${p.end_year}`).join(', ')}) dibangun di awal tahap − masa konstruksi untuk kebutuhan terbesar tahap itu; lookahead tidak dipakai.</>}
          {' '}Eskalasi {esc ? 'hidup' : 'mati'}: harga di tahun bangun t = harga dasar × (1 + e)^t, th 0 = tahun harga satuan; Excel K15 tidak menerapkannya (A27) dan menaruh dermaga & trestle di th −1 walau masa konstruksi 1 th (A26).
        </Note>
      </Section>

      <div className="flex w-full items-center gap-8">
        <div className="w-[392px] shrink-0">
          <Slider label={`Discount rate (I9)${disc.changed ? ' · diubah' : ''}`} value={disc.value * 100} min={4} max={16} step={0.5} display={`${num(disc.value * 100, 1)} %`} onChange={(v) => disc.onChange(v / 100)} />
        </div>
        <Note><Tv v="in.param.discount_rate">Discount rate</Tv> mengubah PV opsi perairan di layar 8 (keruk bertahap lebih diuntungkan daripada trestle penuh di awal); NPV biaya total menyusul di tahap 8c.</Note>
      </div>

      <Section title="Biaya per tahun: investasi + pelayaran" aside={<span className="flex items-center gap-3"><Tv v="invest.total" ctx={{ flow: TOTAL, year: y0 }} className="font-mono text-[13px]">ƒx investasi/th</Tv><Legend items={[{ color: C.abu, label: 'biaya pelayaran' }, ...CATS.map((cat) => ({ color: CAT_COLOR[cat], label: cat }))]} /></span>}>
        <ColumnStack columns={columns} colors={[C.abu, ...CATS.map((cat) => CAT_COLOR[cat])]} height={220} labels={xLabels} yUnit="Rp miliar" xUnit="tahun (bangun / operasi)" />
        <Note>
          <Tv v="shipcost.total">Biaya pelayaran</Tv> (semua flow, layar 7) ditumpuk dengan <Tv v="invest.total">investasi</Tv> di tahun bangunnya{ires ? '' : ' (placeholder)'}; th {y0} = investasi awal sebelum operasi. Belum didiskon dan belum dialokasikan per satuan (tahap 8c).
        </Note>
      </Section>

      <Section title="Jadwal investasi" aside={ires ? <Badge kind="dihitung">dihitung · Rp miliar per tahun bangun</Badge> : <PH />}>
        {ires ? (
          <div className="w-full overflow-x-auto">
            <table className="w-full table-fixed border-collapse font-mono text-sm">
              <thead>
                <tr className="border-b border-hitam text-[13px] text-abu">
                  <th className="w-[200px] py-2 text-left font-sans font-medium">Item</th>
                  {years.map((y) => <th key={y} className="text-right font-normal">{y}</th>)}
                </tr>
              </thead>
              <tbody>
                {[...items, { vid: 'invest.total', key: TOTAL, label: 'Total', arr: totalSeries ?? [] }].map((it) => (
                  <tr key={`${it.vid}:${it.key}`} className={`border-b ${it.vid === 'invest.total' ? 'border-hitam font-medium' : 'border-garis'}`}>
                    <td className="py-2 font-sans">{it.label}</td>
                    {it.arr.map((v, i) => (
                      <td key={i} className="text-right">
                        {Math.abs(v) > 1e-6
                          ? <Tv v={it.vid} ctx={{ flow: it.key, terminal: it.key, year: i + y0 }} value={num(v / 1e9, 1)} className="no-underline">{num(v / 1e9, 1)}</Tv>
                          : <span className="text-garis">·</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <PH>placeholder · API tidak aktif</PH>}
        <Note>
          Tambatan & <Tv v="invest.handling">alat B/M</Tv> mengikuti <Tv v="terminal.n_berth">kebutuhan tambatan</Tv>; <Tv v="invest.waterside">trestle</Tv> dibangun penuh bersama tambatan pertama tiap terminal, keruk kolam tambat per tambatan yang ditambahkan.
          <Tv v="invest.storage"> Penyimpanan</Tv> dari kapasitas terpasang (Excel memakai baris penambahan untuk GC, A28), <Tv v="invest.yard_equipment">alat lapangan & truk</Tv> (truk tidak diinvestasikan Excel, A25), <Tv v="invest.pipeline">pipa CC</Tv> dengan trestle desain (A30).
        </Note>
      </Section>

      <Section title="Item investasi">
        <Table
          rowKey={(r) => `${r.v}:${r.item}`}
          rows={ires ? items.map((it) => ({ v: it.vid, key: it.key, item: it.label, cat: it.cat, years: it.years.join(', '), value: rp(it.total), y: it.years[0] ?? y0 })) : INVEST_ITEMS.map((r) => ({ ...r, key: '', y: 0 }))}
          columns={[
            { key: 'i', head: 'Item', width: 260, render: (r) => r.item },
            { key: 'c', head: 'Kategori', width: 140, render: (r) => <span className="text-[13px] text-abu">{r.cat}</span> },
            { key: 'y', head: 'Tahun bangun', width: 150, mono: true, render: (r) => <Tv v="dv.staging">{r.years}</Tv> },
            { key: 'v', head: 'Nilai Σ nominal', mono: true, render: (r) => <Tv v={r.v} ctx={{ flow: r.key, terminal: r.key, year: r.y }} className={ires ? '' : 'text-abu'}>{r.value}</Tv> },
          ]}
        />
        <Note>
          <Tv v="in.price.berth">{`Harga satuan dari ${c.unit_prices.length} item sheet Investasi (${c.unit_prices[0]?.year})`}</Tv>; kunci harga per terminal dan <Tv v="in.storage.price_keys">per fasilitas penyimpanan</Tv> bisa diganti di kasus (mis. silo memakai harga tangki seperti Excel, atau harga silo spesifikasi Fasilitas Daratan).
          {ires ? ` Σ semua item ${rp(grand)}.` : ' Semua nilai placeholder.'}
        </Note>
      </Section>
    </>
  )
}
