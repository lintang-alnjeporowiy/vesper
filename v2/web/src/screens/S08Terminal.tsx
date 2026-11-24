import { BathyProfile } from '../charts/charts'
import { Tv } from '../components/trace'
import type { WatersideOption } from '../api/case'
import { Badge, Button, DefRow, InputMark, Note, PH, ScreenHeader, Section, Slider, Split, Table } from '../components/ui'
import { SITE, bathyLines, designValue, series, useCalc, withWaterside } from '../lib/engine'
import { num, pct } from '../lib/format'
import { useField } from '../lib/useField'
import { TERMINAL_Y13 } from '../mock/placeholders'
import { usePlanner } from '../store'

const OPTION_LABEL: Record<WatersideOption['mode'], string> = { trestle: 'Trestle penuh', mixed: 'Trestle + keruk', dredge: 'Keruk penuh' }
const OPTION_DESC: Record<WatersideOption['mode'], string> = {
  trestle: 'trestle sampai x*, tanpa keruk',
  mixed: 'trestle sebagian, kolam tambat dikeruk',
  dredge: 'tambatan di garis pantai, kolam tambat dikeruk',
}

/** Rupiah ringkas: miliar (M) atau triliun (T). */
const rp = (x: number | undefined) => (x === undefined ? '–' : Math.abs(x) >= 1e12 ? `Rp ${num(x / 1e12, 2)} T` : `Rp ${num(x / 1e9, 1)} M`)

/** Kartu opsi kosong saat API mati (placeholder). */
const emptyOption = (mode: WatersideOption['mode'], selected: boolean): WatersideOption => ({
  mode, selected, feasible: true, reasons: [], trestle_len: {}, theta: {}, tip_depth: {}, trestle_area: {}, dredge_vol: {}, cost_trestle: {}, cost_dredge: {}, cost: 0,
})

export default function S08Terminal() {
  const { caseData: c, year, setYear, shipByFlow, setInput } = usePlanner()
  const calc = useCalc()
  const res = calc.ok && calc.result?.modules.includes('terminal') ? calc.result : undefined
  const bor = useField(['params', 'bor_max'], 'BOR maks')
  const wd = useField(['params', 'working_days_per_year'], 'Hari kerja per tahun')
  const nYears = c.horizon.years ?? 20
  const y0 = year - 1
  const termSeries = (vid: string, t: string) => series(res, vid, t)
  const termOf = (form: string) => c.kek_site.terminals.find((t) => t.cargo_forms.includes(form))?.id
  const flowsOf = (t: string) => c.flows.filter((f) => termOf(f.cargo_form) === t)
  const sumFlows = (vid: string, t: string, y: number) => flowsOf(t).reduce((a, f) => a + (series(res, vid, f.id)?.[y] ?? 0), 0)
  const shipOf = (fid: string) => c.ships.find((s) => s.id === (res?.ship_by_flow[fid] ?? shipByFlow[fid]))
  const at = (vid: string, fid: string) => series(res, vid, fid)?.[y0] ?? 0
  const sres = calc.ok && calc.result?.modules.includes('storage') ? calc.result : undefined
  const st = (vid: string, key: string) => series(sres, vid, key)?.[y0] ?? 0
  const sat = st
  const sp = c.storage
  const teuForms = c.cargo_forms.filter((f) => f.default_unit === 'TEU').map((f) => f.code)
  const cmdOf = (forms: string[]) => [...new Set(c.flows.filter((f) => forms.includes(f.cargo_form)).map((f) => c.commodities.find((x) => x.id === f.commodity_id)?.name ?? f.commodity_id))].join(', ')
  type Facility = { id: string; name: string; forms: string[]; pv: string; param: string; need: { vid: string; unit: string }[]; flowNeed: { vid: string; unit: string } }
  const facilities: (Facility & { commodities: string })[] = ([
    { id: 'cy', name: 'Container yard', forms: teuForms, pv: 'in.storage.cy', param: `${num(sp.container_yard.area_per_teu_m2)} m²/TEU · ${sp.container_yard.max_tiers} tier · YOR ${pct(sp.container_yard.yor_max)} · kosong ${pct(sp.container_yard.empty_share)}`, need: [{ vid: 'storage.cy', unit: 'm²' }, { vid: 'storage.cy_slots', unit: 'slot' }], flowNeed: { vid: 'storage.cy', unit: 'm²' } },
    { id: 'gc', name: 'Gudang / lapangan GC', forms: ['GC'], pv: 'in.storage.gc', param: `f ${num(sp.general_cargo.f_area, 1)} × ${num(sp.general_cargo.f_bulk, 1)} · ${num(sp.general_cargo.stack_height_m)} m · SOR ${pct(sp.general_cargo.sor_max)}`, need: [{ vid: 'storage.gc', unit: 'm²' }], flowNeed: { vid: 'storage.gc', unit: 'm²' } },
    { id: 'bulk', name: 'Silo curah kering', forms: ['CK'], pv: 'in.storage.bulk', param: `${num(sp.dry_bulk.silo_capacity_m3 ?? 0)} m³ · isi ${pct(sp.dry_bulk.silo_fill_ratio ?? 0.8)} · Rc ${num(sp.dry_bulk.capacity_ratio, 1)}`, need: [{ vid: 'storage.silos', unit: 'silo' }, { vid: 'storage.bulk', unit: 'm³' }], flowNeed: { vid: 'storage.bulk', unit: 'm³' } },
    { id: 'liquid', name: 'Tangki timbun', forms: ['CC'], pv: 'in.storage.liquid', param: `${num(sp.liquid.tank_capacity_m3)} m³ · okupansi ${pct(sp.liquid.occupancy)}`, need: [{ vid: 'storage.tanks', unit: 'tangki' }, { vid: 'storage.liquid', unit: 'm³' }], flowNeed: { vid: 'storage.liquid', unit: 'm³' } },
  ] as Facility[]).map((x) => ({ ...x, commodities: cmdOf(x.forms) }))
  const yardEq = (forms: string[]) => (sp.yard_equipment ?? []).filter((e) => (e.role ?? 'yard') === 'yard' && forms.includes(e.cargo_form))
  const truckEq = (forms: string[]) => (sp.yard_equipment ?? []).filter((e) => e.role === 'transport' && forms.includes(e.cargo_form))
  const TOTAL = 'total'
  const site = c.kek_site
  const plan = c.plans?.[0]
  const eqName = (id?: string) => c.equipment.find((e) => e.id === id)
  const phase = c.horizon.phases.find((p) => year >= p.start_year && year <= p.end_year)
  const td = site.trestle_dredge
  // perairan (Tahap 8a): desain = kebutuhan akhir horizon
  const wres = withWaterside(calc.ok ? calc.result : undefined)
  const wv = (vid: string, key: string) => designValue(wres, vid, key)
  const dctx = (key: string) => ({ terminal: key, year: nYears })
  const lines = bathyLines(site, wres)
  const opts = wres?.waterside_options.length
    ? wres.waterside_options
    : (['trestle', 'mixed', 'dredge'] as const).map((m) => emptyOption(m, (plan?.waterside_mode ?? 'trestle') === m))
  const chosen = opts.find((o) => o.selected)
  const cheapest = wres ? [...opts].filter((o) => o.feasible).sort((a, b) => a.cost - b.cost)[0] : undefined
  const shipName = (id?: string) => c.ships.find((s) => s.id === id)?.name ?? '–'
  const firstYear = (t: string) => {
    const i = termSeries('terminal.n_berth', t)?.findIndex((v) => v > 0) ?? -1
    return i >= 0 ? i + 1 : undefined
  }
  const govRows: { key: string; name: string; since?: number }[] = [
    ...site.terminals.map((t) => ({ key: t.id, name: t.name, since: firstYear(t.id) })),
    { key: SITE, name: 'Tapak · alur & kolam putar' },
  ]
  const govShip = (key: string) => {
    const g = wres?.governing_ships[key]
    if (!g) return '–'
    return g.loa === g.draft && g.beam === g.draft ? shipName(g.draft) : `LOA/B ${shipName(g.loa)} · T ${shipName(g.draft)}`
  }
  const part = (k: string) => wres?.channel_parts[k]?.[nYears - 1]
  const w = site.waterside

  return (
    <>
      <ScreenHeader step={8} kind="hasil" title="Terminal KEK · Batu Ampar" lead="Tambatan, alat, penyimpanan, dan perairan yang dibutuhkan armada terpilih." badge={res ? <Badge kind="dihitung">tambatan, alat, penyimpanan & perairan dihitung · investasi placeholder</Badge> : <PH>placeholder · API tidak aktif</PH>} />

      <div className="flex w-full gap-8 border-y border-garis py-4">
        <div className="flex w-[300px] shrink-0 flex-col gap-2">
          <Slider label="Tahun tinjau" value={year} min={1} max={(c.horizon.years ?? 20)} step={1} display={`${year} / ${(c.horizon.years ?? 20)}`} onChange={setYear} input={false} dark />
          <span className="flex gap-3">
            {c.horizon.phases.map((p) => (
              <span key={p.name} className={`text-[13px] ${p === phase ? 'font-medium text-hitam' : 'text-abu'}`}>{p.name} {p.start_year}–{p.end_year}</span>
            ))}
          </span>
        </div>
        <Slider label={`BOR maks (I6)${bor.changed ? ' · diubah' : ''}`} value={bor.value} min={0.4} max={0.9} step={0.05} display={pct(bor.value)} onChange={bor.onChange} />
        <Slider label={`Hari kerja (I6)${wd.changed ? ' · diubah' : ''}`} value={wd.value} min={250} max={365} step={5} display={`${num(wd.value)} hr/th`} onChange={wd.onChange} />
      </div>
      <Note>Slider <Tv v="in.param.bor_max">BOR maks</Tv> dan <Tv v="in.param.working_days">hari kerja</Tv> langsung mengubah input kasus (juga terlihat di layar 1). {res ? `Kartu di bawah = tahun ${year}.` : 'API tidak aktif: kartu menampilkan contoh tahun 13 (placeholder).'}</Note>

      <div className="flex w-full gap-8">
        {site.terminals.map((t, i) => {
          const ph = TERMINAL_Y13[t.id as 'MP' | 'CC']
          const r = res
            ? { berthDays: sumFlows('terminal.berth_days', t.id, y0), berths: termSeries('terminal.n_berth', t.id)?.[y0] ?? 0, equipment: termSeries('terminal.n_equip', t.id)?.[y0] ?? 0, bor: termSeries('terminal.bor', t.id)?.[y0] ?? 0, length: termSeries('terminal.berth_length', t.id)?.[y0] ?? 0 }
            : { ...ph, length: ph.berths * t.berth_unit_length_m }
          const eq = eqName(res?.equipment_by_terminal[t.id] ?? plan?.equipment_by_terminal[t.id])
          const tc = { terminal: t.id, year: res ? year : 13 }
          const dim = res ? '' : 'text-abu'
          const longest = flowsOf(t.id).filter((f) => at('voyage.freq', f.id) > 0).map((f) => shipOf(f.id)).filter((x) => x !== undefined).sort((a, b) => b.loa_m - a.loa_m)[0]
          return (
            <div key={t.id} className={`flex grow basis-0 flex-col gap-4 ${i > 0 ? 'border-l border-garis pl-8' : ''}`}>
              <div className="flex items-center gap-1.5">
                <span className="grow text-base font-medium">{t.name}</span>
                {t.cargo_forms.map((f) => <Badge key={f} kind="kode">{f}</Badge>)}
              </div>
              <span className="flex items-center gap-1.5 text-[13px] text-abu">
                <InputMark />
                <Tv v="in.term.berth_length" ctx={tc}>{num(t.berth_unit_length_m)}</Tv> × <Tv v="in.term.berth_width" ctx={tc}>{num(t.berth_width_m)}</Tv> m per tambatan · {eq?.name.replace("''", '″')} · <Tv v="in.equip.price" ctx={tc}>USD {num((eq?.price_usd ?? 0) / 1000)} rb</Tv>
              </span>
              <div className="flex border-y border-garis">
                <div className="flex grow basis-0 flex-col gap-1 py-3"><span className="text-[13px] text-abu">Berth-days</span><Tv v="terminal.berth_days" ctx={tc} className={`font-mono text-[28px] leading-none ${dim}`}>{num(r.berthDays)}</Tv></div>
                <div className="flex grow basis-0 flex-col gap-1 bg-hitam px-3 py-3 text-white"><span className="text-[13px]">Tambatan</span><Tv v="terminal.n_berth" ctx={tc} value={String(r.berths)} className="font-mono text-[28px] leading-none">{String(r.berths)}</Tv></div>
                <div className="flex grow basis-0 flex-col gap-1 py-3 pl-3"><span className="text-[13px] text-abu">Alat {t.equipment_kind}</span><Tv v="terminal.n_equip" ctx={tc} className={`font-mono text-[28px] leading-none ${dim}`}>{num(r.equipment)}</Tv></div>
              </div>
              <div className="flex flex-col gap-2">
                <span className="flex"><span className="grow text-[13px] text-abu">BOR aktual / maks</span><span className={`font-mono text-sm ${dim}`}><Tv v="terminal.bor" ctx={tc}>{pct(r.bor)}</Tv> / <Tv v="in.param.bor_max">{pct(c.params.bor_max)}</Tv></span></span>
                <span className="relative h-2 w-full bg-permukaan">
                  <span className="absolute inset-y-0 left-0 bg-hitam" style={{ width: `${Math.min(1, r.bor) * 100}%` }} />
                  <span className="absolute inset-y-0 w-0.5 bg-merah" style={{ left: `${c.params.bor_max * 100}%` }} />
                </span>
              </div>
              <span className="flex text-[13px]"><span className="grow text-abu">Panjang {t.berth_layout === 'jetty' ? 'jetty' : 'dermaga'}</span><Tv v="terminal.berth_length" ctx={tc} className={`font-mono ${dim}`}>{`${num(r.length)} m`}</Tv></span>
              <Note>
                {t.berth_layout === 'jetty'
                  ? <><Tv v="in.term.layout" ctx={tc}>Jetty</Tv>: satu kapal satu jetty, berth-days = ship-days (A16). </>
                  : <><Tv v="in.term.layout" ctx={tc}>Dermaga menerus</Tv>: berth-days = ship-days × LOA / {num(t.berth_unit_length_m)} m. </>}
                <Tv v="in.rule.loa_bands" ctx={tc}>Alat per tambatan dari LOA</Tv>{longest ? <> kapal terpanjang {longest.name} ({num(longest.loa_m, 1)} m)</> : null}, <Tv v="in.rule.max_per_berth" ctx={tc}>{`batas ${(c.equipment_rules.max_per_berth as Record<string, number>)[t.id] ?? '–'}`}</Tv>.
                {res && r.berths === 0 ? ' Belum ada muatan di terminal ini pada tahun ini.' : ''}
              </Note>
            </div>
          )
        })}
      </div>

      <Section title="Pemakaian tambatan per flow" aside={res ? <Badge kind="dihitung">dihitung · tahun {year}</Badge> : <PH />}>
        <Table
          rowKey={(f) => f.id}
          rows={c.flows}
          columns={[
            { key: 'f', head: 'Flow', width: 110, mono: true, render: (f) => f.id },
            { key: 't', head: 'Terminal', width: 70, render: (f) => termOf(f.cargo_form) ?? '–' },
            { key: 's', head: 'Kapal', width: 160, render: (f) => shipOf(f.id)?.name ?? '–' },
            { key: 'l', head: 'LOA m', width: 70, mono: true, render: (f) => <Tv v="in.ship.loa" ctx={{ flow: f.id, ship: shipOf(f.id)?.id }}>{num(shipOf(f.id)?.loa_m ?? 0, 1)}</Tv> },
            { key: 'F', head: 'Call/th', width: 70, mono: true, render: (f) => <Tv v="voyage.freq" ctx={{ flow: f.id, year }}>{res ? num(at('voyage.freq', f.id)) : '–'}</Tv> },
            { key: 'k', head: 'B/M KEK hr/call', width: 110, mono: true, render: (f) => <Tv v="voyage.t_port_kek" ctx={{ flow: f.id, year }}>{res ? num(at('voyage.t_port_kek', f.id), 2) : '–'}</Tv> },
            { key: 'sd', head: 'Ship-days', width: 90, mono: true, render: (f) => <Tv v="terminal.ship_days" ctx={{ flow: f.id, year }}>{res ? num(at('terminal.ship_days', f.id), 1) : '–'}</Tv> },
            { key: 'bd', head: 'Berth-days', mono: true, render: (f) => <Tv v="terminal.berth_days" ctx={{ flow: f.id, year }}>{res ? num(at('terminal.berth_days', f.id)) : '–'}</Tv> },
          ]}
        />
        <Note>
          <Tv v="terminal.ship_days">Ship-days</Tv> = call/th × (waktu B/M di KEK + <Tv v="in.param.it">IT {num(c.params.it_hours)} jam</Tv>); AT dan WT tidak menempati tambatan (A17).
          Selisih terhadap Excel K15: A2 (waktu muat outbound non-PK dikali jumlah alat), A10 (alat per tambatan dari LOA), A16, A17. Rinciannya: <span className="font-mono">tools/diff_k15.py</span>.
        </Note>
      </Section>

      <Section title="Kebutuhan fasilitas per tahun (I4)" aside={res ? <Badge kind="dihitung">dihitung</Badge> : <PH />}>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse font-mono text-sm">
            <thead>
              <tr className="border-b border-hitam text-[13px] text-abu">
                <th className="w-[136px] py-2 text-left font-sans font-medium">Tahun</th>
                {Array.from({ length: nYears }, (_, i) => i + 1).map((y) => <th key={y} className={`text-left font-normal ${y === year ? 'font-medium text-hitam' : ''}`}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {[
                ...site.terminals.flatMap((t) => [
                  { label: `Tambatan ${t.id}`, vid: 'terminal.n_berth', ctx: (y: number) => ({ terminal: t.id, year: y }), arr: termSeries('terminal.n_berth', t.id), k: 1 },
                  { label: `Alat ${t.equipment_kind}`, vid: 'terminal.n_equip', ctx: (y: number) => ({ terminal: t.id, year: y }), arr: termSeries('terminal.n_equip', t.id), k: 1 },
                ]),
                ...[
                  { label: 'CY (rb m²)', vid: 'storage.cy', k: 1000 },
                  { label: 'Gudang GC (rb m²)', vid: 'storage.gc', k: 1000 },
                  { label: 'Silo', vid: 'storage.silos', k: 1 },
                  { label: 'Tangki', vid: 'storage.tanks', k: 1 },
                ].map((r) => ({ ...r, ctx: (y: number) => ({ flow: TOTAL, year: y }), arr: series(sres, r.vid, TOTAL) })),
                ...yardEq(c.cargo_forms.map((f) => f.code)).map((e) => ({ label: e.name.replace(/ \(.*\)$/, ''), vid: 'storage.yard_equipment', ctx: (y: number) => ({ flow: e.id, year: y }), arr: series(sres, 'storage.yard_equipment', e.id), k: 1 })),
                ...truckEq(c.cargo_forms.map((f) => f.code)).map((e) => ({ label: e.name, vid: 'storage.trucks', ctx: (y: number) => ({ flow: e.id, year: y }), arr: series(wres, 'storage.trucks', e.id), k: 1 })),
              ].map(({ label, vid, ctx, arr: a, k }) => ({ label, vid, ctx, k, arr: a ?? Array<number>(nYears).fill(0) })).map(({ label, arr, vid, ctx, k }) => (
                <tr key={label} className="border-b border-garis">
                  <td className="py-2 font-sans">{label}</td>
                  {arr.map((v, i) => {
                    const step = i > 0 && Math.round(v / k) > Math.round(arr[i - 1] / k)
                    const txt = num(v / k)
                    return <td key={i}><Tv v={vid} ctx={ctx(i + 1)} value={txt} className="no-underline">{step ? <span className="bg-hitam px-1 text-white">{txt}</span> : <span className="text-abu">{txt}</span>}</Tv></td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>
          Kotak hitam = tahun jumlahnya bertambah (tambatan, penyimpanan, dan alat yang sudah ada tidak berkurang). Ini kebutuhan per tahun; jadwal bangun dengan
          masa konstruksi <Tv v="in.horizon.lead">{`${c.horizon.construction_lead_years} th`}</Tv> dan lookahead <Tv v="in.horizon.berth_lookahead">{`${c.horizon.berth_lookahead_years} th`}</Tv> menyusul di tahap 8b (investasi).
          {res ? '' : ' API tidak aktif: semua angka 0.'}
        </Note>
      </Section>

      <Section title="Penyimpanan per fasilitas" aside={sres ? <Badge kind="dihitung">dihitung · tahun {year} · kapasitas terpasang</Badge> : <PH>placeholder · API tidak aktif</PH>}>
        <Table
          rowKey={(r) => r.id}
          rows={facilities}
          columns={[
            { key: 'f', head: 'Fasilitas', width: 150, render: (r) => r.name },
            { key: 'k', head: 'Komoditas', width: 190, render: (r) => r.commodities || '–' },
            { key: 'p', head: 'Parameter', width: 250, input: true, mono: true, render: (r) => <Tv v={r.pv} className="text-[13px]">{r.param}</Tv> },
            { key: 'n', head: 'Kebutuhan', width: 170, mono: true, render: (r) => (
              <span className="flex flex-col">
                {r.need.map((n) => <Tv key={n.vid} v={n.vid} ctx={{ flow: TOTAL, year }} className={sres ? '' : 'text-abu'}>{sres ? `${num(st(n.vid, TOTAL))} ${n.unit}` : '–'}</Tv>)}
              </span>
            ) },
            { key: 'a', head: 'Alat lapangan · truk', width: 150, mono: true, render: (r) => (
              <span className="flex flex-col">
                {yardEq(r.forms).map((e) => <Tv key={e.id} v="storage.yard_equipment" ctx={{ flow: e.id, year }} className={sres ? '' : 'text-abu'}>{`${sres ? num(st('storage.yard_equipment', e.id)) : '–'} ${e.name.replace(/ \(.*\)$/, '')}`}</Tv>)}
                {truckEq(r.forms).map((e) => <Tv key={e.id} v="storage.trucks" ctx={{ flow: e.id, year }} className={wres ? '' : 'text-abu'}>{`${wres ? num(series(wres, 'storage.trucks', e.id)?.[y0] ?? 0) : '–'} truk`}</Tv>)}
                {yardEq(r.forms).length + truckEq(r.forms).length === 0 ? '–' : null}
              </span>
            ) },
            { key: 'c', head: 'Biaya', render: () => <Tv v="invest.storage" ctx={{ year }} className="no-underline"><PH>placeholder · Tahap 8b</PH></Tv> },
          ]}
        />
        <Note>
          <Tv v="storage.dwell">Dwell time</Tv> = <Tv v="voyage.consumption">lama konsumsi</Tv> tahun itu (selang antar-pengapalan), sehingga stok = satu muatan per call: luas mengikuti ukuran kapal, bukan langsung demand (I1).
          Excel K15 merata-rata lama konsumsi 20 tahun termasuk tahun tanpa muatan (A18). <Tv v="storage.yard_equipment">Alat lapangan</Tv> = satu armada per bentuk muatan; Excel menghitung RTG per tenant dengan produktivitas berbeda (A19).
          Tangki memakai densitas komoditas, Excel 0,9 tetap (A20). Kapasitas terpasang tidak pernah turun.
          {' '}<Tv v="storage.trucks">Truk dermaga–lapangan</Tv> = ⌈siklus ÷ waktu muat⌉ per alat B/M × alat B/M aktif, jarak = panjang trestle desain; Excel membagi produktivitas box/jam dengan 60 lalu memakainya sebagai menit (A25). Biaya menyusul di tahap 8b.
        </Note>
      </Section>

      <Section title="Penyimpanan per flow" aside={sres ? <Badge kind="dihitung">dihitung · tahun {year}</Badge> : <PH />}>
        <Table
          rowKey={(f) => f.id}
          rows={c.flows}
          muted={(f) => sres !== undefined && sat('storage.throughput', f.id) === 0}
          columns={[
            { key: 'f', head: 'Flow', width: 110, mono: true, render: (f) => f.id },
            { key: 'k', head: 'Komoditas', width: 170, render: (f) => c.commodities.find((x) => x.id === f.commodity_id)?.name ?? f.commodity_id },
            { key: 'fa', head: 'Fasilitas', width: 120, render: (f) => facilities.find((x) => x.forms.includes(f.cargo_form))?.name ?? '–' },
            { key: 'q', head: 'Arus/th', width: 110, mono: true, render: (f) => <Tv v="storage.throughput" ctx={{ flow: f.id, year }}>{sres ? `${num(sat('storage.throughput', f.id))} ${res?.units[f.id] === 'TEU' ? 'TEU' : 't'}` : '–'}</Tv> },
            { key: 'c', head: 'Muatan/call', width: 110, mono: true, render: (f) => <Tv v="voyage.q" ctx={{ flow: f.id, year }}>{sres ? num(at('voyage.q', f.id)) : '–'}</Tv> },
            { key: 'd', head: 'Dwell hr', width: 80, mono: true, render: (f) => <Tv v="storage.dwell" ctx={{ flow: f.id, year }}>{sres ? num(sat('storage.dwell', f.id), 2) : '–'}</Tv> },
            { key: 'n', head: 'Kebutuhan', mono: true, render: (f) => {
              const fac = facilities.find((x) => x.forms.includes(f.cargo_form))
              const n = fac?.flowNeed
              return n ? <Tv v={n.vid} ctx={{ flow: f.id, year }}>{sres ? `${num(sat(n.vid, f.id))} ${n.unit}` : '–'}</Tv> : '–'
            } },
          ]}
        />
      </Section>

      <Section title="Kapal penentu & kedalaman perlu" aside={wres ? <Badge kind="dihitung">dihitung · desain akhir horizon (th {nYears})</Badge> : <PH>placeholder · API tidak aktif</PH>}>
        <Table
          rowKey={(r) => r.key}
          rows={govRows}
          groupStart={(r) => r.key === SITE}
          columns={[
            { key: 'n', head: 'Lingkup', width: 200, render: (r) => r.name },
            { key: 's', head: 'Kapal penentu', width: 210, render: (r) => govShip(r.key) },
            { key: 'l', head: 'LOA m', width: 75, mono: true, render: (r) => <Tv v="waterside.gov_loa" ctx={dctx(r.key)}>{num(wv('waterside.gov_loa', r.key), 2)}</Tv> },
            { key: 'b', head: 'B m', width: 60, mono: true, render: (r) => <Tv v="waterside.gov_beam" ctx={dctx(r.key)}>{num(wv('waterside.gov_beam', r.key), 1)}</Tv> },
            { key: 't', head: 'T m', width: 70, mono: true, render: (r) => <Tv v="waterside.gov_draft" ctx={dctx(r.key)}>{num(wv('waterside.gov_draft', r.key), 2)}</Tv> },
            { key: 'd', head: 'Kedalaman perlu m', width: 135, mono: true, render: (r) => <Tv v="waterside.depth_req" ctx={dctx(r.key)}>{num(wv('waterside.depth_req', r.key), 2)}</Tv> },
            { key: 'x', head: 'x* m', width: 70, mono: true, render: (r) => (r.key === SITE ? '–' : <Tv v="waterside.x_star" ctx={dctx(r.key)}>{num(wv('waterside.x_star', r.key))}</Tv>) },
            { key: 'y', head: 'Sejak', mono: true, render: (r) => (r.since ? `th ${r.since}` : '–') },
          ]}
        />
        <Note>
          Kapal penentu per terminal = kapal rencana yang melayani terminal itu (LOA, B, dan T masing-masing maksimum kumulatif sampai tahun itu); baris tapak = semua terminal, dipakai alur
          dan kolam putar. <Tv v="waterside.depth_req">Kedalaman perlu</Tv> = <Tv v="in.site.depth_factor">{num(w.depth_factor_of_draft, 1)}</Tv> × T per terminal. Excel memakai satu kapal
          (ALS CERES) untuk semua terminal, padahal tanker di jetty CC lebih dalam (A21). Desain perairan = kebutuhan akhir horizon, ada sejak tahun pertama terminal punya tambatan.
        </Note>
      </Section>

      <Section title="Alur & kolam (PIANC)" aside={wres ? <Badge kind="dihitung">dihitung · tapak · th {nYears}</Badge> : <PH>placeholder · API tidak aktif</PH>}>
        <Split
          left={
            <>
              <DefRow label={<Tv v="waterside.channel_width" ctx={dctx(SITE)}>Lebar alur</Tv>} justify><span className="font-mono">{`${num(wv('waterside.channel_width', SITE), 1)} m`}</span></DefRow>
              <DefRow label={w.lanes === 2 ? '2 jalur = 2(Wm + Wa) + 2Wb + Ws' : '1 jalur = Wm + Wa + 2Wb'} justify>
                <span className="font-mono text-[13px]">{`${num(part('wm'), 1)} · ${num(part('wa'), 1)} · ${num(part('wb'), 1)} · ${num(part('ws'), 1)} m`}</span>
              </DefRow>
              <DefRow label="Wa = angin · arus · gelombang · SBNP" justify>
                <span className="font-mono text-[13px]">{`${num(part('wa_wind'), 1)} · ${num((part('wa_cross_current') ?? 0) + (part('wa_long_current') ?? 0), 1)} · ${num(part('wa_wave'), 1)} · ${num(part('wa_nav_aids'), 1)} m`}</span>
              </DefRow>
              <DefRow label={<Tv v="waterside.channel_length" ctx={dctx(SITE)}>Panjang alur</Tv>} justify last><span className="font-mono">{`${num(wv('waterside.channel_length', SITE), 1)} m`}</span></DefRow>
            </>
          }
          right={
            <>
              <DefRow label={<Tv v="waterside.entrance_width" ctx={dctx(SITE)}>Lebar pintu masuk</Tv>} justify><span className="font-mono">{`${num(wv('waterside.entrance_width', SITE), 1)} m`}</span></DefRow>
              <DefRow label={<Tv v="waterside.stopping_distance" ctx={dctx(SITE)}>Jarak henti</Tv>} justify><span className="font-mono">{`${num(wv('waterside.stopping_distance', SITE))} m`}</span></DefRow>
              <DefRow label={<Tv v="waterside.turning_basin" ctx={dctx(SITE)}>Kolam putar</Tv>} justify>
                <span className="font-mono">{`Ø ${num(wv('waterside.turning_basin', SITE))} m · `}<Tv v="waterside.turning_area" ctx={dctx(SITE)}>{`${num((wv('waterside.turning_area', SITE) ?? 0) / 1e4, 1)} ha`}</Tv></span>
              </DefRow>
              <DefRow label={<Tv v="waterside.anchorage_radius" ctx={dctx(SITE)}>Radius area labuh</Tv>} justify last><span className="font-mono">{`${num(wv('waterside.anchorage_radius', SITE), 1)} m`}</span></DefRow>
            </>
          }
        />
        <Note>
          Komponen lebar dalam kelipatan B kapal penentu tapak (tabel PIANC di engine): manuver {w.maneuverability}, kecepatan {w.ship_speed_class}, angin {num(w.wind_kn)} kn, arus, gelombang
          {' '}{num(w.wave_height_m, 2)} m, SBNP {w.nav_aids}. Excel mengambil Wa kecepatan 0,1 · Vs dari baris "cepat" dan Wa dasar laut 0,1 B walau h = 1,5 T (A22), serta menghitung luas kolam putar dari diameter 1,5 LOA walau kapal dibantu tunda (2 LOA, A23).
          Alur dan kolam putar hanya dimensi; biayanya di luar cakupan (keruk hanya kolam tambat, sama seperti Excel).
        </Note>
      </Section>

      <Section title="Trestle atau keruk (I8)" aside={site.bathymetry_source === 'dummy' ? <Badge kind="asumsi">asumsi · batimetri dummy</Badge> : undefined}>
        <BathyProfile
          points={site.bathymetry}
          required={lines.required}
          marks={[...lines.marks, ...(td?.trestle_length_m && !plan?.trestle_fraction ? [{ at: td.trestle_length_m, label: `trestle + keruk ${num(td.trestle_length_m)} m` }] : [])]}
          width={860}
        />
        <Note>
          Profil diedit di layar 3. Garis merah = <Tv v="waterside.depth_req">kedalaman perlu</Tv> per terminal{lines.computed ? '' : ' (placeholder)'}; titik potongnya = <Tv v="waterside.x_star">x*</Tv>, panjang trestle penuh.
          Opsi trestle + keruk memakai trestle <Tv v="in.site.trestle_dredge">{`${num(td?.trestle_length_m ?? 0)} m`}</Tv>{plan?.trestle_fraction ? ` (diganti θ ${num(plan.trestle_fraction, 2)} × x* dari rencana)` : ''} lalu
          mengeruk kolam tambat dari kedalaman di ujung trestle sampai kedalaman perlu. Excel memakai kedalaman ujung tetap 10 m dan lebar trestle 50 m untuk semua terminal (A24).
        </Note>
        <div className="flex w-full border-y border-garis">
          {opts.map((o, i) => {
            const on = o.selected
            const delta = wres && chosen && !on && chosen.cost > 0 ? o.cost / chosen.cost - 1 : undefined
            return (
              <div key={o.mode} className={`flex grow basis-0 flex-col gap-1.5 py-4 ${i === 0 ? 'pr-4' : 'border-l border-garis pl-4'}`} style={on ? { boxShadow: 'inset 0 3px 0 var(--color-biru)' } : undefined}>
                <span className="flex items-center gap-2">
                  <span className="grow text-base font-medium">{OPTION_LABEL[o.mode]}</span>
                  {on && <Tv v="dv.waterside" className="text-[13px] font-medium">rencana</Tv>}
                  {o === cheapest && <Badge kind="baik">termurah</Badge>}
                  {wres && !o.feasible && <Badge kind="gugur">tidak layak</Badge>}
                  {delta !== undefined && <Badge kind={delta > 0 ? 'buruk' : 'baik'}>{`${delta > 0 ? '+' : '−'}${num(Math.abs(delta) * 100, 0)} %`}</Badge>}
                </span>
                <span className="text-[13px] text-abu">{OPTION_DESC[o.mode]}</span>
                {wres ? Object.keys(o.trestle_len).map((t) => {
                  const tw = num(site.terminals.find((x) => x.id === t)?.trestle_width_m, 1)
                  const cost = rp((o.cost_trestle[t] ?? 0) + (o.cost_dredge[t] ?? 0))
                  // hanya opsi rencana yang bisa ditelusuri (variabel waterside.* mengikuti rencana)
                  const T = (v: string, txt: string) => (on ? <Tv v={v} ctx={dctx(t)}>{txt}</Tv> : txt)
                  return (
                    <span key={t} className="flex gap-2 font-mono text-[13px]">
                      <span className="w-6 shrink-0 font-medium">{t}</span>
                      <span className="flex flex-col">
                        <span>trestle {T('waterside.trestle_len', num(o.trestle_len[t]))} × {tw} m</span>
                        <span>ujung {T('waterside.tip_depth', num(o.tip_depth[t], 1))} m · keruk {T('waterside.dredge_vol', num(o.dredge_vol[t]))} m³</span>
                        <span>{T('waterside.cost', cost)}</span>
                      </span>
                    </span>
                  )
                }) : <span className="font-mono text-[13px] text-abu">–</span>}
                {o.reasons.map((r) => <span key={r} className="text-[13px] text-merah">{r}</span>)}
                <span className="flex items-center gap-2 pt-1">
                  {wres ? <span className="font-mono text-base">{rp(o.cost)}</span> : <PH>placeholder · API tidak aktif</PH>}
                  <span className="grow text-[13px] text-abu">biaya dasar</span>
                  <Tv v="invest.waterside" className="no-underline"><PH>PV · Tahap 8b</PH></Tv>
                </span>
                {!on && (
                  <span className="pt-1">
                    <Button size="sm" variant="garis" disabled={!o.feasible} onClick={() => setInput(['plans', 0, 'waterside_mode'], o.mode, `Mode perairan: ${OPTION_LABEL[o.mode]}`)}>Pakai di rencana</Button>
                  </span>
                )}
              </div>
            )
          })}
        </div>
        <Note>
          Biaya dasar = luas trestle × harga trestle + volume keruk × harga keruk, harga tahun dasar tanpa eskalasi dan diskonto (jadwal bangun dan PV di tahap 8b). Persentase = selisih terhadap opsi rencana.
          Setelah koreksi A24, trestle + keruk dan keruk penuh lebih murah daripada trestle penuh pada batimetri dummy, sedangkan Excel K15 memilih trestle penuh. Mengganti opsi rencana juga mengubah jarak truk dermaga–lapangan.
        </Note>
      </Section>
    </>
  )
}
