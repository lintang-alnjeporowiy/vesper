import type { CandidateRow } from '../api/case'
import { C, DotPlot } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, DefRow, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Split, Table, Tabs } from '../components/ui'
import { commodityName, isRatio, portOfRoute, routeDistance, shipTypesForForm, shortPortName, tenantName } from '../lib/case'
import { computedNumber, fmtValue, rowNumber, useCalc, useCompare } from '../lib/engine'
import { num } from '../lib/format'
import { usePlanner } from '../store'

/** Simpul rantai hitung layar 6: id registry, label, satuan tampilan. */
const CHAIN: { id: string; label: string; unit: (u: string) => string; digits?: number; final?: boolean }[] = [
  { id: 'cargo.demand_unit', label: 'Demand', unit: (u) => `${u}/th` },
  { id: 'vessel.payload', label: 'Payload', unit: (u) => u },
  { id: 'voyage.freq', label: 'Frekuensi', unit: () => 'call/th' },
  { id: 'voyage.q', label: 'Muatan per call', unit: (u) => u },
  { id: 'voyage.t_port_kek', label: 'Port time KEK', unit: () => 'hr', digits: 2 },
  { id: 'voyage.t_port_ext', label: 'Port time asal/tujuan', unit: () => 'hr', digits: 2 },
  { id: 'voyage.t_fix', label: 'Waktu tetap', unit: () => 'hr', digits: 2 },
  { id: 'voyage.t_sea', label: 'Sea time', unit: () => 'hr', digits: 2 },
  { id: 'voyage.rtd', label: 'RTD', unit: () => 'hr', digits: 2 },
  { id: 'voyage.f_max', label: 'Voyage maks/kapal', unit: () => 'call' },
  { id: 'voyage.n_ship', label: 'Jumlah kapal', unit: () => 'unit', final: true },
]

function fmt(v: number | undefined, digits?: number): string {
  if (v === undefined) return '–'
  return digits !== undefined ? num(v, digits) : fmtValue(v)
}

export default function S06Armada() {
  const { caseData: c, flowId, setFlow, shipByFlow, setShip, year, setYear, showTrace, trace } = usePlanner()
  const calc = useCalc()
  const res = calc.ok ? calc.result : undefined
  const flow = c.flows.find((f) => f.id === flowId) ?? c.flows[0]
  const cmp = useCompare(flow.id)
  const port = portOfRoute(c, flow.route_id)
  const ratio = c.params.berth_loa_min_ratio
  const types = shipTypesForForm(c, flow.cargo_form)
  const shipId = shipByFlow[flow.id]
  const ship = c.ships.find((s) => s.id === shipId)
  const ctx = { flow: flow.id, ship: shipId, year }
  const vol = flow.volume
  const unit = res?.units[flow.id] === 'TEU' ? 'TEU' : 't'
  const v = (id: string) => computedNumber(res, id, ctx, year)
  const reasons = res?.reasons[flow.id] ?? []
  const term = c.kek_site.terminals.find((t) => t.cargo_forms.includes(flow.cargo_form))

  const shipsById = Object.fromEntries(c.ships.map((s) => [s.id, s]))
  const rows: CandidateRow[] = cmp.data
    ? cmp.data.rows.filter((r) => r.compatible).sort((a, b) => shipsById[a.ship_id].dwt_t - shipsById[b.ship_id].dwt_t)
    : c.ships.filter((s) => types.includes(s.ship_type)).sort((a, b) => a.dwt_t - b.dwt_t).map((s) => ({ ship_id: s.id, compatible: true, feasible: true, reasons: [], notes: [], selected: s.id === shipId, values: {}, error: null }))
  const cmpOk = cmp.status === 'ok' && !!cmp.data
  const nGugur = cmpOk ? rows.filter((r) => !r.feasible).length : undefined
  const bad = (r: CandidateRow, word: string) => r.reasons.some((x) => x.includes(word))
  const engineBadge = res ? <Badge kind="dihitung">dihitung · engine</Badge> : <PH>placeholder · API tidak aktif</PH>
  const fUnit = flow.unit === 'TEU' ? 'TEU' : 't'
  const rpShort = (x: number | undefined) => (x === undefined ? '–' : x >= 1e12 ? `Rp ${num(x / 1e12, 2)} T` : `Rp ${num(x / 1e9, 1)} M`)

  return (
    <>
      <ScreenHeader step={6} kind="hasil" title="Armada & operasi" lead="Pilih kapal per flow, lihat rantai sampai jumlah kapal, lalu bandingkan dengan kandidat lain." badge={engineBadge} />

      <Tabs mono items={c.flows.map((f) => ({ id: f.id, label: f.id }))} value={flow.id} onChange={setFlow} />

      <Split
        left={
          <>
            <div className="flex items-center gap-2 pb-3">
              <span className="text-base font-medium">{tenantName(c, flow.tenant_id).replace('PT. ', '')} · {flow.direction}</span>
              <Badge kind="kode">{flow.cargo_form}</Badge>
            </div>
            <DefRow label="Komoditas">{commodityName(c, flow.commodity_id)}</DefRow>
            <DefRow label="Rute">{shortPortName(port?.name ?? '')} ⇄ Batu Ampar · <Tv v="in.route.distance" ctx={ctx} className="font-mono">{num(routeDistance(c, flow.route_id), 1)} nm</Tv></DefRow>
            <DefRow label="Pelabuhan">
              <span className="font-mono">draft <Tv v="in.port.max_draft" ctx={ctx}>{num(port?.max_draft_m ?? 0, 1)} m</Tv> · dermaga <Tv v="in.port.longest_berth" ctx={ctx}>{port?.longest_berth_m ? `${num(port.longest_berth_m)} m` : '?'}</Tv></span>
            </DefRow>
            <DefRow label="Volume">
              {isRatio(vol) ? (
                <span className="font-mono">× <Tv v="in.flow.ratio" ctx={ctx}>{num(vol.ratio, 2)}</Tv> dari {vol.basis_flow_id}</span>
              ) : (
                <span className="font-mono"><Tv v="in.flow.initial" ctx={ctx}>{num(vol.initial)}</Tv> → maks <Tv v="in.flow.maximum" ctx={ctx}>{num(vol.maximum)}</Tv> {flow.unit} · <Tv v="in.flow.growth" ctx={ctx}>{num(vol.growth_rate * 100, 1)} %/th</Tv></span>
              )}
            </DefRow>
            <DefRow label={`Demand th-${year}`} last>
              {v('cargo.demand_unit') === undefined ? <span className="font-mono text-abu">–</span> : <Tv v="cargo.demand_unit" ctx={ctx} className="font-mono">{fmtValue(v('cargo.demand_unit') ?? 0)} {unit}</Tv>}
            </DefRow>
          </>
        }
        right={
          <div className="flex flex-col gap-4">
            <span className="text-[13px] font-medium text-abu">Kapal terpilih · manual</span>
            <select aria-label="Kapal terpilih" value={shipId ?? ''} onChange={(e) => setShip(flow.id, e.target.value)} className="h-10 rounded-kontrol border border-hitam bg-white px-3 text-sm font-medium">
              {rows.map((r) => {
                const s = shipsById[r.ship_id]
                return (
                  <option key={s.id} value={s.id} disabled={cmpOk && !r.feasible && s.id !== shipId}>
                    {s.name} · {num(s.dwt_t)} DWT{cmpOk && !r.feasible ? ' (gugur)' : ''}
                  </option>
                )
              })}
            </select>
            {ship && (
              <span className="font-mono text-[13px] text-abu">
                <Tv v="in.ship.dwt" ctx={ctx}>{num(ship.dwt_t)} DWT</Tv> · LOA <Tv v="in.ship.loa" ctx={ctx}>{num(ship.loa_m, 2)} m</Tv> · draft <Tv v="in.ship.draft" ctx={ctx}>{num(ship.draft_m, 2)} m</Tv> · Vs <Tv v="in.ship.speed" ctx={ctx}>{num(ship.speed_kn, 1)} kn</Tv> · V ballast <Tv v="vessel.ballast_speed" ctx={ctx}>{fmt(v('vessel.ballast_speed'), 1)} kn</Tv>
              </span>
            )}
            {reasons.length > 0 && <Badge kind="gugur">kapal terpilih gugur · {reasons.join('; ')}</Badge>}
            <span className="font-mono text-[13px] text-abu">
              alat {c.equipment.find((e) => e.id === (term ? res?.equipment_by_terminal[term.id] : undefined))?.name ?? '–'} ({term?.id ?? '–'}) · <Tv v="vessel.neq" ctx={ctx}>{fmt(v('vessel.neq'))} per tambatan</Tv>
            </span>
            <Slider label="Tahun tinjau" value={year} min={1} max={(c.horizon.years ?? 20)} step={1} display={`${year} / ${(c.horizon.years ?? 20)}`} onChange={setYear} input={false} dark />
            <span className="flex items-center gap-2">
              {c.plans?.[0]?.ship_by_flow[flow.id] === shipId ? <Badge kind="audit">rencana k15-excel</Badge> : <Badge kind="gugur">diubah dari rencana</Badge>}
              <span className="text-[13px] text-abu">pilihan Evolver: {c.ships.find((s) => s.id === c.plans?.[0]?.ship_by_flow[flow.id])?.name}</span>
            </span>
            <Note>Kecepatan = Vs kapal (keputusan kecepatan, I2, menyusul).</Note>
          </div>
        }
      />

      <Section title={`Rantai hitung · tahun ${year}`} aside={<span className="flex items-center gap-2 text-[13px] text-abu">klik simpul untuk menelusuri {res ? <Badge kind="dihitung">dihitung</Badge> : <PH />}</span>}>
        <div className="grid w-full grid-cols-6 gap-px border border-garis bg-garis">
          {CHAIN.map((n) => {
            const val = v(n.id)
            const text = val === undefined ? '–' : `${fmt(val, n.digits)} ${n.unit(unit)}`
            return (
              <button
                key={n.id}
                type="button"
                data-var={n.id}
                onClick={() => showTrace(n.id, ctx, text)}
                className={`flex cursor-pointer flex-col gap-1.5 border-0 p-3 text-left ${n.final ? 'bg-hitam text-white' : 'bg-white'} ${trace.id === n.id ? 'outline-2 outline-biru' : ''}`}
              >
                <span className={`text-[13px] ${n.final ? 'text-white' : 'text-abu'}`}>{n.label}</span>
                <span className={`font-mono text-base ${n.final ? 'text-white' : val === undefined ? 'text-abu' : ''}`}>{text}</span>
              </button>
            )
          })}
        </div>
        <Note>RTD = sea time + port time KEK + port time asal/tujuan + waktu tetap; F_max = ⌊{num(c.params.commission_days)} / RTD⌋ (A1); jumlah kapal = ⌈F / F_max⌉. Port time KEK dibagi jumlah alat (A2) dari rentang LOA (A10); pelabuhan asal/tujuan memakai produktivitas total per kapal (A3); V ballast = rasio × Vs (A5).</Note>
      </Section>

      <KpiStrip
        ctx={ctx}
        items={[
          { label: 'Utilisasi kapal', value: v('voyage.utilization') === undefined ? '–' : `${num((v('voyage.utilization') ?? 0) * 100)} %`, v: 'voyage.utilization' },
          { label: 'Lama konsumsi / pengapalan', value: v('voyage.consumption') === undefined ? '–' : `${num(v('voyage.consumption'), 1)} hr`, v: 'voyage.consumption' },
          { label: `Shipping cost th ${year}`, value: rpShort(v('shipcost.total')), v: 'shipcost.total' },
          { label: `Biaya pelayaran per ${fUnit}`, value: v('shipcost.unit') === undefined ? '–' : `Rp ${num(v('shipcost.unit'))}`, v: 'shipcost.unit', final: true },
        ]}
      />

      <Section
        title={`Bandingkan kandidat ${flow.cargo_form} · tahun ${year} (I1)`}
        aside={<span className="flex items-center gap-2 font-mono text-[13px] text-abu">{rows.length} kandidat · <Tv v="vessel.feasible" ctx={ctx}>{nGugur === undefined ? '– gugur' : `${nGugur} gugur`}</Tv> {cmpOk ? <Badge kind="dihitung">dihitung</Badge> : <PH>{cmp.status === 'loading' ? 'menghitung…' : 'API tidak aktif'}</PH>}</span>}
      >
        <Table<CandidateRow>
          rowKey={(r) => r.ship_id}
          rows={rows}
          selected={(r) => r.ship_id === shipId}
          muted={(r) => cmpOk && !r.feasible}
          onRowClick={(r) => (!cmpOk || r.feasible) && setShip(flow.id, r.ship_id)}
          columns={[
            { key: 'n', head: 'Kapal', width: 150, render: (r) => shipsById[r.ship_id].name },
            { key: 'dwt', head: 'DWT', width: 72, mono: true, render: (r) => <Tv v="in.ship.dwt" ctx={{ ...ctx, ship: r.ship_id }}>{num(shipsById[r.ship_id].dwt_t)}</Tv> },
            { key: 'loa', head: 'LOA', width: 56, mono: true, render: (r) => <Tv v="in.ship.loa" ctx={{ ...ctx, ship: r.ship_id }} className={bad(r, 'dermaga') || bad(r, 'LOA') ? 'text-merah' : ''}>{num(shipsById[r.ship_id].loa_m, 1)}</Tv> },
            { key: 'dr', head: 'Draft', width: 52, mono: true, render: (r) => <Tv v="in.ship.draft" ctx={{ ...ctx, ship: r.ship_id }} className={bad(r, 'draft') ? 'text-merah' : ''}>{num(shipsById[r.ship_id].draft_m, 2)}</Tv> },
            { key: 'pay', head: `Payload, ${unit}`, width: 84, mono: true, render: (r) => fmt(rowNumber(r.values, 'vessel.payload', year)) },
            { key: 'f', head: 'F', width: 48, mono: true, render: (r) => fmt(rowNumber(r.values, 'voyage.freq', year)) },
            { key: 'rtd', head: 'RTD', width: 52, mono: true, render: (r) => fmt(rowNumber(r.values, 'voyage.rtd', year), 1) },
            { key: 'fm', head: 'F_max', width: 52, mono: true, render: (r) => fmt(rowNumber(r.values, 'voyage.f_max', year)) },
            { key: 'k', head: 'Kapal', width: 48, mono: true, render: (r) => <span className={r.ship_id === shipId ? 'font-medium' : ''}>{fmt(rowNumber(r.values, 'voyage.n_ship', year))}</span> },
            { key: 'u', head: `Rp/${fUnit}`, width: 80, mono: true, render: (r) => <Tv v="shipcost.unit" ctx={{ ...ctx, ship: r.ship_id }} value={fmt(rowNumber(r.values, 'shipcost.unit', year))}>{fmt(rowNumber(r.values, 'shipcost.unit', year))}</Tv> },
            {
              key: 'st',
              head: 'Status',
              render: (r) => {
                if (!cmpOk) return <span className="text-[13px] text-abu">–</span>
                if (r.error) return <span className="text-[13px] text-merah" title={r.error}>galat data</span>
                if (!r.feasible) return <span title={r.reasons.join('\n')}><Badge kind="gugur">gugur · {r.reasons.map((x) => x.split(' ')[0]).join(', ')}</Badge></span>
                if (r.ship_id === shipId) return <span className="text-[13px] font-medium">terpilih</span>
                return <span className="text-[13px] text-abu" title={r.notes.join('\n')}>{r.notes.length ? 'layak · LOA ?' : 'layak'}</span>
              },
            },
          ]}
        />
        <Note>
          Kelayakan (engine): tipe kapal boleh membawa {flow.cargo_form}; draft ≤ draft maks pelabuhan; dermaga terpanjang ≥ <Tv v="in.param.berth_loa_ratio">{num(ratio, 2)}</Tv> × LOA
          {port?.longest_berth_m ? <> ({shortPortName(port.name)} <Tv v="in.port.longest_berth" ctx={ctx}>{`${num(port.longest_berth_m)} m`}</Tv> → LOA ≤ {num(port.longest_berth_m / ratio)} m)</> : ' (panjang dermaga belum ada → LOA tidak dicek)'}. Angka merah = yang melanggar; arahkan kursor ke badge gugur untuk alasan lengkap. Kandidat gugur tetap dihitung agar terlihat posisinya. Rp/{fUnit} = shipping cost (TCH + BBM + pelabuhan) ÷ demand.
        </Note>
      </Section>

      <Section title={`Biaya pelayaran per ${fUnit} terhadap ukuran kapal · tahun ${year}`} aside={cmpOk ? <Badge kind="dihitung">dihitung</Badge> : <PH />}>
        {cmpOk ? (
          <>
            <DotPlot
              height={200}
              points={rows
                .filter((r) => (rowNumber(r.values, 'shipcost.unit', year) ?? 0) > 0)
                .map((r) => {
                  const s = shipsById[r.ship_id]
                  const u = rowNumber(r.values, 'shipcost.unit', year) ?? 0
                  return { x: Math.log(s.dwt_t), y: u, color: !r.feasible ? C.merah : r.ship_id === shipId ? C.hitam : C.biru, outline: !r.feasible, size: r.ship_id === shipId ? 14 : 10, label: `${s.name}: Rp ${num(u)}/${fUnit} · ${fmt(rowNumber(r.values, 'voyage.n_ship', year))} kapal` }
                })}
              xLabels={rows.length ? [`${num(shipsById[rows[0].ship_id].dwt_t / 1000, 1)}k`, `${num(shipsById[rows[rows.length - 1].ship_id].dwt_t / 1000, 1)}k DWT`] : []}
            />
            <Legend items={[{ color: C.biru, label: 'layak', round: true }, { color: C.hitam, label: 'terpilih', round: true }, { color: C.merah, label: 'gugur (posisi jika diizinkan)', round: true, outline: true }]} />
            <Note>Sumbu X = DWT (skala log), sumbu Y = biaya pelayaran per {fUnit} pada tahun {year} (makin rendah makin baik). Kapal besar: TCH per unit lebih mahal tapi butuh lebih sedikit unit dan call; titik terendah yang layak = kandidat terbaik untuk biaya pelayaran saja (biaya terminal & perairan menyusul tahap 7–8).</Note>
          </>
        ) : (
          <Note>Grafik muncul setelah engine (/api/compare) menjawab.</Note>
        )}
      </Section>
    </>
  )
}
