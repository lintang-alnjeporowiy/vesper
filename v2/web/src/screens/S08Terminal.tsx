import { Bathymetry } from '../charts/charts'
import { Badge, InputMark, Note, PH, ScreenHeader, Section, Slider, Table } from '../components/ui'
import { num, pct } from '../lib/format'
import { STAGING, STORAGE_Y13, TERMINAL_Y13, WATERSIDE_OPTIONS } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S08Terminal() {
  const { caseData: c, year, setYear, showTrace } = usePlanner()
  const site = c.kek_site
  const plan = c.plans?.[0]
  const eqName = (id?: string) => c.equipment.find((e) => e.id === id)
  const phase = c.horizon.phases.find((p) => year >= p.start_year && year <= p.end_year)
  const td = site.trestle_dredge
  const req = 21.3

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
      <Note>Edit BOR maks dan hari kerja di layar 1. Kartu di bawah menunjukkan contoh tahun 13 (placeholder) apa pun tahun yang dipilih.</Note>

      <div className="flex w-full gap-8">
        {site.terminals.map((t, i) => {
          const r = TERMINAL_Y13[t.id as 'MP' | 'CC']
          const eq = eqName(plan?.equipment_by_terminal[t.id])
          return (
            <div key={t.id} className={`flex grow basis-0 flex-col gap-4 ${i > 0 ? 'border-l border-garis pl-8' : ''}`}>
              <div className="flex items-center gap-1.5">
                <span className="grow text-base font-medium">{t.name}</span>
                {t.cargo_forms.map((f) => <Badge key={f} kind="kode">{f}</Badge>)}
              </div>
              <span className="flex items-center gap-1.5 text-[13px] text-abu">
                <InputMark />
                {num(t.berth_unit_length_m)} × {num(t.berth_width_m)} m per tambatan · {eq?.name.replace("''", '″')} · USD {num((eq?.price_usd ?? 0) / 1000)} rb
              </span>
              <div className="flex border-y border-garis">
                <div className="flex grow basis-0 flex-col gap-1 py-3"><span className="text-[13px] text-abu">Berth-days</span><span className="font-mono text-[28px] leading-none text-abu">{r.berthDays}</span></div>
                <button type="button" onClick={() => t.id === 'MP' && showTrace('berth')} className="flex grow basis-0 cursor-pointer flex-col gap-1 border-0 bg-hitam px-3 py-3 text-left text-white"><span className="text-[13px]">Tambatan</span><span className="font-mono text-[28px] leading-none">{r.berths}</span></button>
                <div className="flex grow basis-0 flex-col gap-1 py-3 pl-3"><span className="text-[13px] text-abu">Alat {t.equipment_kind}</span><span className="font-mono text-[28px] leading-none text-abu">{r.equipment}</span></div>
              </div>
              <div className="flex flex-col gap-2">
                <span className="flex"><span className="grow text-[13px] text-abu">BOR aktual / maks</span><span className="font-mono text-sm text-abu">{pct(r.bor)} / {pct(c.params.bor_max)}</span></span>
                <span className="relative h-2 w-full bg-permukaan">
                  <span className="absolute inset-y-0 left-0 bg-hitam" style={{ width: `${r.bor * 100}%` }} />
                  <span className="absolute inset-y-0 w-0.5 bg-merah" style={{ left: `${c.params.bor_max * 100}%` }} />
                </span>
              </div>
              <Note>{t.id === 'MP' ? `Alat per tambatan dari LOA: 180–350 m → 4, batas MP ${(c.equipment_rules.max_per_berth as Record<string, number>).MP}.` : 'Mulai tahun 13 (PT. Adi Energi). Tahun 1–12 tidak ada tambatan.'}</Note>
            </div>
          )
        })}
      </div>

      <Section title="Staging fasilitas per tahun (I4)" aside={<span className="text-[13px] text-abu">bangun {c.horizon.construction_lead_years} th sebelum dibutuhkan · lookahead {c.horizon.berth_lookahead_years} th</span>}>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse font-mono text-sm">
            <thead>
              <tr className="border-b border-hitam text-[13px] text-abu">
                <th className="w-[136px] py-2 text-left font-sans font-medium">Tahun</th>
                {STAGING.years.map((y) => <th key={y} className={`text-left font-normal ${y === year ? 'font-medium text-hitam' : ''}`}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              {([['Tambatan MP', STAGING.mpBerths], ['Alat HMC', STAGING.mpEquipment], ['Tambatan CC', STAGING.ccBerths]] as const).map(([label, arr]) => (
                <tr key={label} className="border-b border-garis">
                  <td className="py-2 font-sans">{label}</td>
                  {arr.map((v, i) => {
                    const step = i > 0 && v > arr[i - 1]
                    return <td key={i}>{step ? <span className="bg-hitam px-1 text-white">{v}</span> : <span className="text-abu">{v}</span>}</td>
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
            { key: 'p', head: 'Parameter', width: 230, input: true, mono: true, render: (r) => <span className="text-[13px]">{r.param}</span> },
            { key: 'n', head: 'Kebutuhan', width: 110, mono: true, render: (r) => <span className="text-abu">{r.need}</span> },
            { key: 'c', head: 'Biaya', mono: true, render: (r) => <span className="text-abu">{r.cost}</span> },
          ]}
        />
      </Section>

      <Section title="Trestle atau keruk (I8)" aside={site.bathymetry_source === 'dummy' ? <Badge kind="asumsi">asumsi · batimetri dummy</Badge> : undefined}>
        <Bathymetry points={site.bathymetry} marks={[td?.trestle_length_m ?? 250, site.trestle?.max_length_m ?? 500]} required={req} />
        <div className="flex w-full justify-between font-mono text-[13px] text-abu">
          <span>0 m</span>
          <span className="font-medium text-hitam">{num(td?.trestle_length_m ?? 0)} m · {num(td?.existing_depth_m ?? 0, 1)}</span>
          <span className="font-medium text-hitam">{num(site.trestle?.max_length_m ?? 0)} m · {num(req, 1)}</span>
          <span>{num(site.bathymetry[site.bathymetry.length - 1].distance_m)} m · {num(site.bathymetry[site.bathymetry.length - 1].depth_m, 1)}</span>
        </div>
        <Note>Kedalaman ke bawah. Batang hitam: ujung trestle {num(td?.trestle_length_m ?? 0)} m dan {num(site.trestle?.max_length_m ?? 0)} m. Kedalaman perlu {num(req, 1)} m = 1,5 × draft terbesar (placeholder).</Note>
        <div className="flex w-full border-y border-garis">
          {WATERSIDE_OPTIONS.map((o, i) => {
            const on = plan?.waterside_mode === o.id
            return (
              <div key={o.id} className={`flex grow basis-0 flex-col gap-1.5 py-4 ${i === 0 ? 'pr-4' : 'border-l border-garis pl-4'}`} style={on ? { boxShadow: 'inset 0 3px 0 var(--color-biru)' } : undefined}>
                <span className="flex items-center gap-2">
                  <span className="grow text-base font-medium">{o.name}</span>
                  {on && <span className="text-[13px] font-medium">terpilih</span>}
                  {o.delta && <Badge kind="buruk">{o.delta}</Badge>}
                </span>
                <span className="font-mono text-[13px]">{o.spec}</span>
                <span className="font-mono text-base text-abu">{o.cost}</span>
              </div>
            )
          })}
        </div>
        <Note>Biaya placeholder. Alur 2 jalur dan kolam putar ikut LOA kapal terbesar; ganti kapal di layar 6 dan pilihan bisa berpindah.</Note>
      </Section>
    </>
  )
}
