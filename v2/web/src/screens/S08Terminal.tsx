import { BathyProfile } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, InputMark, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { num, pct } from '../lib/format'
import { REQUIRED_DEPTH_PH, STAGING, STORAGE_Y13, TERMINAL_Y13, WATERSIDE_OPTIONS } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S08Terminal() {
  const { caseData: c, year, setYear } = usePlanner()
  const STORAGE_INPUT: Record<string, string> = { 'storage.gc': 'in.storage.gc', 'storage.bulk': 'in.storage.bulk', 'storage.cy': 'in.storage.cy', 'storage.liquid': 'in.storage.liquid' }
  const site = c.kek_site
  const plan = c.plans?.[0]
  const eqName = (id?: string) => c.equipment.find((e) => e.id === id)
  const phase = c.horizon.phases.find((p) => year >= p.start_year && year <= p.end_year)
  const td = site.trestle_dredge
  const req = REQUIRED_DEPTH_PH

  return (
    <>
      <ScreenHeader step={8} kind="hasil" title="Terminal KEK · Batu Ampar" lead="Tambatan, alat, penyimpanan, dan perairan yang dibutuhkan armada terpilih." badge={<PH>placeholder · engine tahap 7–8</PH>} />

      <div className="flex w-full gap-8 border-y border-garis py-4">
        <div className="flex w-[300px] shrink-0 flex-col gap-2">
          <Slider label="Tahun tinjau" value={year} min={1} max={(c.horizon.years ?? 20)} step={1} display={`${year} / ${(c.horizon.years ?? 20)}`} onChange={setYear} input={false} dark />
          <span className="flex gap-3">
            {c.horizon.phases.map((p) => (
              <span key={p.name} className={`text-[13px] ${p === phase ? 'font-medium text-hitam' : 'text-abu'}`}>{p.name} {p.start_year}–{p.end_year}</span>
            ))}
          </span>
        </div>
        <Slider label="BOR maks (I6)" value={c.params.bor_max} min={0.4} max={0.9} step={0.05} display={pct(c.params.bor_max)} />
        <Slider label="Hari kerja (I6)" value={c.params.working_days_per_year} min={250} max={365} step={5} display={`${num(c.params.working_days_per_year)} · ${num(c.params.working_hours_per_day)} j`} />
      </div>
      <Note>Edit <Tv v="in.param.bor_max">BOR maks</Tv> dan <Tv v="in.param.working_days">hari kerja</Tv> di layar 1. Kartu di bawah menunjukkan contoh tahun 13 (placeholder) apa pun tahun yang dipilih.</Note>

      <div className="flex w-full gap-8">
        {site.terminals.map((t, i) => {
          const r = TERMINAL_Y13[t.id as 'MP' | 'CC']
          const eq = eqName(plan?.equipment_by_terminal[t.id])
          const tc = { terminal: t.id, year: 13 }
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
                <div className="flex grow basis-0 flex-col gap-1 py-3"><span className="text-[13px] text-abu">Berth-days</span><Tv v="terminal.berth_days" ctx={tc} className="font-mono text-[28px] leading-none text-abu">{String(r.berthDays)}</Tv></div>
                <div className="flex grow basis-0 flex-col gap-1 bg-hitam px-3 py-3 text-white"><span className="text-[13px]">Tambatan</span><Tv v="terminal.n_berth" ctx={tc} value={String(r.berths)} className="font-mono text-[28px] leading-none">{String(r.berths)}</Tv></div>
                <div className="flex grow basis-0 flex-col gap-1 py-3 pl-3"><span className="text-[13px] text-abu">Alat {t.equipment_kind}</span><Tv v="terminal.n_equip" ctx={tc} className="font-mono text-[28px] leading-none text-abu">{String(r.equipment)}</Tv></div>
              </div>
              <div className="flex flex-col gap-2">
                <span className="flex"><span className="grow text-[13px] text-abu">BOR aktual / maks</span><span className="font-mono text-sm text-abu"><Tv v="terminal.bor" ctx={tc}>{pct(r.bor)}</Tv> / <Tv v="in.param.bor_max">{pct(c.params.bor_max)}</Tv></span></span>
                <span className="relative h-2 w-full bg-permukaan">
                  <span className="absolute inset-y-0 left-0 bg-hitam" style={{ width: `${r.bor * 100}%` }} />
                  <span className="absolute inset-y-0 w-0.5 bg-merah" style={{ left: `${c.params.bor_max * 100}%` }} />
                </span>
              </div>
              <Note>{t.id === 'MP' ? <><Tv v="in.rule.loa_bands" ctx={tc}>Alat per tambatan dari LOA</Tv>: 180–350 m → 4, <Tv v="in.rule.max_per_berth" ctx={tc}>{`batas MP ${(c.equipment_rules.max_per_berth as Record<string, number>).MP}`}</Tv>.</> : <><Tv v="in.flow.start_year" ctx={{ flow: 'in.adi' }}>Mulai tahun 13</Tv> (PT. Adi Energi). Tahun 1–12 tidak ada tambatan.</>}</Note>
            </div>
          )
        })}
      </div>

      <Section title="Staging fasilitas per tahun (I4)" aside={<span className="text-[13px] text-abu">bangun <Tv v="in.horizon.lead">{`${c.horizon.construction_lead_years} th`}</Tv> sebelum dibutuhkan · lookahead <Tv v="in.horizon.berth_lookahead">{`${c.horizon.berth_lookahead_years} th`}</Tv></span>}>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse font-mono text-sm">
            <thead>
              <tr className="border-b border-hitam text-[13px] text-abu">
                <th className="w-[136px] py-2 text-left font-sans font-medium">Tahun</th>
                {STAGING.years.map((y) => <th key={y} className={`text-left font-normal ${y === year ? 'font-medium text-hitam' : ''}`}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {([['Tambatan MP', STAGING.mpBerths, 'terminal.n_berth', 'MP'], ['Alat HMC', STAGING.mpEquipment, 'terminal.n_equip', 'MP'], ['Tambatan CC', STAGING.ccBerths, 'terminal.n_berth', 'CC']] as const).map(([label, arr, vid, term]) => (
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
        <Note>Kotak hitam = tahun bangun atau pengadaan, masuk jadwal investasi layar 9. Semua angka placeholder.</Note>
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
