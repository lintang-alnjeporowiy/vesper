import { BathyProfile } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, InputMark, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { series, useCalc } from '../lib/engine'
import { num, pct } from '../lib/format'
import { useField } from '../lib/useField'
import { REQUIRED_DEPTH_PH, STORAGE_Y13, TERMINAL_Y13, WATERSIDE_OPTIONS } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S08Terminal() {
  const { caseData: c, year, setYear, shipByFlow } = usePlanner()
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
  const STORAGE_INPUT: Record<string, string> = { 'storage.gc': 'in.storage.gc', 'storage.bulk': 'in.storage.bulk', 'storage.cy': 'in.storage.cy', 'storage.liquid': 'in.storage.liquid' }
  const site = c.kek_site
  const plan = c.plans?.[0]
  const eqName = (id?: string) => c.equipment.find((e) => e.id === id)
  const phase = c.horizon.phases.find((p) => year >= p.start_year && year <= p.end_year)
  const td = site.trestle_dredge
  const req = REQUIRED_DEPTH_PH

  return (
    <>
      <ScreenHeader step={8} kind="hasil" title="Terminal KEK · Batu Ampar" lead="Tambatan, alat, penyimpanan, dan perairan yang dibutuhkan armada terpilih." badge={res ? <Badge kind="dihitung">tambatan & alat dihitung · penyimpanan & perairan placeholder</Badge> : <PH>placeholder · API tidak aktif</PH>} />

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
              {site.terminals.flatMap((t) => [
                { label: `Tambatan ${t.id}`, vid: 'terminal.n_berth', term: t.id },
                { label: `Alat ${t.equipment_kind}`, vid: 'terminal.n_equip', term: t.id },
              ]).map(({ label, vid, term }) => ({ label, vid, term, arr: termSeries(vid, term) ?? Array<number>(nYears).fill(0) })).map(({ label, arr, vid, term }) => (
                <tr key={label} className="border-b border-garis">
                  <td className="py-2 font-sans">{label}</td>
                  {arr.map((v, i) => {
                    const step = i > 0 && v > arr[i - 1]
                    return <td key={i}><Tv v={vid} ctx={{ terminal: term, year: i + 1 }} value={String(v)} className="no-underline">{step ? <span className="bg-hitam px-1 text-white">{v}</span> : <span className="text-abu">{v}</span>}</Tv></td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>
          Kotak hitam = tahun jumlahnya bertambah (tambatan yang sudah dibangun tidak berkurang). Ini kebutuhan per tahun; jadwal bangun dengan
          masa konstruksi <Tv v="in.horizon.lead">{`${c.horizon.construction_lead_years} th`}</Tv> dan lookahead <Tv v="in.horizon.berth_lookahead">{`${c.horizon.berth_lookahead_years} th`}</Tv> menyusul di tahap 8 (investasi).
          {res ? '' : ' API tidak aktif: semua angka 0.'}
        </Note>
      </Section>

      <Section title="Penyimpanan per komoditas" aside={<span className="text-[13px] text-abu">dwell dari lama konsumsi · tahun 13</span>}>
        <Table
          rowKey={(r) => r.facility}
          rows={STORAGE_Y13}
          columns={[
            { key: 'k', head: 'Komoditas', width: 200, render: (r) => r.commodity },
            { key: 'f', head: 'Fasilitas', width: 140, render: (r) => r.facility },
            { key: 'p', head: 'Parameter', width: 230, input: true, mono: true, render: (r) => <Tv v={STORAGE_INPUT[r.v]} className="text-[13px]">{r.param}</Tv> },
            { key: 'n', head: 'Kebutuhan', width: 110, mono: true, render: (r) => <Tv v={r.v} ctx={{ year: 13 }} className="text-abu">{r.need}</Tv> },
            { key: 'c', head: 'Biaya', mono: true, render: (r) => <Tv v="invest.storage" ctx={{ year: 13 }} className="text-abu">{r.cost}</Tv> },
          ]}
        />
      </Section>

      <Section title="Trestle atau keruk (I8)" aside={site.bathymetry_source === 'dummy' ? <Badge kind="asumsi">asumsi · batimetri dummy</Badge> : undefined}>
        <BathyProfile
          points={site.bathymetry}
          required={{ depth: req, label: `kedalaman perlu ${num(req, 1)} m · placeholder` }}
          marks={[{ at: td?.trestle_length_m ?? 250, label: `${num(td?.trestle_length_m ?? 250)} m` }, { at: site.trestle?.max_length_m ?? 500, label: `${num(site.trestle?.max_length_m ?? 500)} m` }]}
          width={860}
        />
        <div className="flex w-full justify-between font-mono text-[13px] text-abu">
          <span>0 m</span>
          <Tv v="in.site.trestle_dredge" className="font-medium text-hitam">{`${num(td?.trestle_length_m ?? 0)} m · ${num(td?.existing_depth_m ?? 0, 1)}`}</Tv>
          <span className="font-medium text-hitam"><Tv v="in.site.trestle">{`${num(site.trestle?.max_length_m ?? 0)} m`}</Tv> · <Tv v="waterside.depth_req">{num(req, 1)}</Tv></span>
          <Tv v="in.site.bathymetry">{`${num(site.bathymetry[site.bathymetry.length - 1].distance_m)} m · ${num(site.bathymetry[site.bathymetry.length - 1].depth_m, 1)}`}</Tv>
        </div>
        <Note>Profil diedit di layar 3. Garis hitam: ujung trestle {num(td?.trestle_length_m ?? 0)} m dan {num(site.trestle?.max_length_m ?? 0)} m. <Tv v="waterside.depth_req">Kedalaman perlu {num(req, 1)} m</Tv> = <Tv v="in.site.depth_factor">1,5</Tv> × draft <Tv v="waterside.governing">kapal penentu</Tv> (placeholder).</Note>
        <div className="flex w-full border-y border-garis">
          {WATERSIDE_OPTIONS.map((o, i) => {
            const on = plan?.waterside_mode === o.id
            return (
              <div key={o.id} className={`flex grow basis-0 flex-col gap-1.5 py-4 ${i === 0 ? 'pr-4' : 'border-l border-garis pl-4'}`} style={on ? { boxShadow: 'inset 0 3px 0 var(--color-biru)' } : undefined}>
                <span className="flex items-center gap-2">
                  <span className="grow text-base font-medium">{o.name}</span>
                  {on && <span className="text-[13px] font-medium">terpilih</span>}
                  {o.delta && <Tv v="invest.waterside" className="no-underline"><Badge kind="buruk">{o.delta}</Badge></Tv>}
                </span>
                <Tv v={o.id === 'trestle' ? 'waterside.trestle_len' : 'waterside.dredge_vol'} className="font-mono text-[13px]">{o.spec}</Tv>
                <Tv v="invest.waterside" className="font-mono text-base text-abu">{o.cost}</Tv>
              </div>
            )
          })}
        </div>
        <Note>Biaya placeholder. Alur 2 jalur dan kolam putar ikut LOA kapal terbesar; ganti kapal di layar 6 dan pilihan bisa berpindah.</Note>
      </Section>
    </>
  )
}
