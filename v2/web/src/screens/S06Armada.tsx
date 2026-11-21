import type { Ship } from '../api/case'
import { C, DotPlot } from '../charts/charts'
import { Tv } from '../components/trace'
import { Badge, DefRow, KpiStrip, Legend, Note, PH, ScreenHeader, Section, Slider, Split, Table, Tabs } from '../components/ui'
import { commodityName, isRatio, portOfRoute, routeDistance, shipTypesForForm, shortPortName, tenantName } from '../lib/case'
import { num } from '../lib/format'
import { CHAIN_DAMAI, FLEET_CANDIDATES, KPI_FLEET, feasibilityMock } from '../mock/placeholders'
import { usePlanner } from '../store'

export default function S06Armada() {
  const { caseData: c, flowId, setFlow, shipByFlow, setShip, year, setYear, showTrace, trace } = usePlanner()
  const ctx = { flow: flowId, ship: shipByFlow[flowId], year }
  const flow = c.flows.find((f) => f.id === flowId) ?? c.flows[0]
  const port = portOfRoute(c, flow.route_id)
  const ratio = c.params.berth_loa_min_ratio
  const types = shipTypesForForm(c, flow.cargo_form)
  const candidates = c.ships.filter((s) => types.includes(s.ship_type)).sort((a, b) => a.dwt_t - b.dwt_t)
  const shipId = shipByFlow[flow.id]
  const ship = c.ships.find((s) => s.id === shipId)
  const isDamai = flow.id === 'in.damai'
  const vol = flow.volume
  const feas = (s: Ship) => (port ? feasibilityMock(s, port, ratio) : { ok: null, reasons: [] })
  const nGugur = candidates.filter((s) => feas(s).ok === false).length

  return (
    <>
      <ScreenHeader step={6} kind="hasil" title="Armada & operasi" lead="Pilih kapal per flow, lihat rantai sampai jumlah kapal, lalu bandingkan dengan kandidat lain." badge={<PH>placeholder · engine tahap 4–5</PH>} />

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
              <Tv v="demand.base" ctx={ctx} className="font-mono text-abu">{isDamai && year === 10 ? '4,65 jt t' : '–'}</Tv>
              <PH />
            </DefRow>
          </>
        }
        right={
          <div className="flex flex-col gap-4">
            <span className="text-[13px] font-medium text-abu">Kapal terpilih · manual</span>
            <select aria-label="Kapal terpilih" value={shipId ?? ''} onChange={(e) => setShip(flow.id, e.target.value)} className="h-10 rounded-kontrol border border-hitam bg-white px-3 text-sm font-medium">
              {candidates.map((s) => (
                <option key={s.id} value={s.id} disabled={feas(s).ok === false}>
                  {s.name} · {num(s.dwt_t)} DWT{feas(s).ok === false ? ` (gugur: ${feas(s).reasons.join(', ')})` : ''}
                </option>
              ))}
            </select>
            {ship && (
              <span className="font-mono text-[13px] text-abu">
                <Tv v="in.ship.dwt" ctx={ctx}>{num(ship.dwt_t)} DWT</Tv> · LOA <Tv v="in.ship.loa" ctx={ctx}>{num(ship.loa_m, 2)} m</Tv> · draft <Tv v="in.ship.draft" ctx={ctx}>{num(ship.draft_m, 2)} m</Tv> · ME <Tv v="in.ship.me_kw" ctx={ctx}>{num(ship.me_kw)} kW</Tv>
              </span>
            )}
            <Slider label="Kecepatan (I2)" value={ship?.speed_kn ?? 0} min={8} max={26} step={0.1} display={`${num(ship?.speed_kn ?? 0, 1)} kn`} />
            <Slider label="Tahun tinjau" value={year} min={1} max={(c.horizon.years ?? 20)} step={1} display={`${year} / ${(c.horizon.years ?? 20)}`} onChange={setYear} input={false} dark />
            <span className="flex items-center gap-2">
              {c.plans?.[0]?.ship_by_flow[flow.id] === shipId ? <Badge kind="audit">rencana k15-excel</Badge> : <Badge kind="gugur">diubah dari rencana</Badge>}
              <span className="text-[13px] text-abu">pilihan Evolver: {c.ships.find((s) => s.id === c.plans?.[0]?.ship_by_flow[flow.id])?.name}</span>
            </span>
          </div>
        }
      />

      <Section title={`Rantai hitung · tahun ${year}`} aside={<span className="text-[13px] text-abu">klik simpul untuk menelusuri</span>}>
        {isDamai && year === 10 && shipId === 'ship.aetos' ? (
          <div className="flex w-full">
            {CHAIN_DAMAI.map((n) => (
              <button
                key={n.id}
                type="button"
                data-var={n.id}
                onClick={() => showTrace(n.id, ctx, n.value)}
                className={`flex grow basis-0 cursor-pointer flex-col gap-1.5 p-3 text-left ${n.final ? 'border-0 bg-hitam text-white' : 'border border-garis bg-white'} ${trace.id === n.id ? 'outline-2 outline-biru' : ''}`}
              >
                <span className={`h-[3px] w-4 ${n.input ? 'bg-biru' : 'bg-transparent'}`} />
                <span className={`text-[13px] ${n.final ? 'text-white' : 'text-abu'}`}>{n.label}</span>
                <span className={`font-mono text-base ${n.final ? 'text-white' : 'text-abu'}`}>{n.value}</span>
              </button>
            ))}
          </div>
        ) : (
          <Note>Contoh rantai placeholder hanya tersedia untuk in.damai · AETOS · tahun 10. Rantai lain muncul setelah engine tahap 4–5 tersambung.</Note>
        )}
        <Note>Garis biru = turunan langsung dari input K15. Semua nilai masih placeholder (estimasi kasar). Angka bergaris bawah titik-titik di layar ini bisa diklik untuk jejaknya.</Note>
      </Section>

      <KpiStrip ctx={ctx} items={isDamai && year === 10 && shipId === 'ship.aetos' ? KPI_FLEET : KPI_FLEET.map((k) => ({ ...k, value: '–' }))} />

      <Section title={`Bandingkan kandidat ${flow.cargo_form} (I1)`} aside={<span className="font-mono text-[13px] text-abu">{candidates.length} kandidat · <Tv v="vessel.feasible" ctx={ctx}>{`${nGugur} gugur`}</Tv></span>}>
        <Table<Ship>
          rowKey={(s) => s.id}
          rows={candidates}
          selected={(s) => s.id === shipId}
          muted={(s) => feas(s).ok === false}
          onRowClick={(s) => feas(s).ok !== false && setShip(flow.id, s.id)}
          columns={[
            { key: 'n', head: 'Kapal', width: 164, render: (s) => s.name },
            { key: 'dwt', head: 'DWT', width: 72, mono: true, render: (s) => <Tv v="in.ship.dwt" ctx={{ ...ctx, ship: s.id }}>{num(s.dwt_t)}</Tv> },
            { key: 'loa', head: 'LOA', width: 60, mono: true, render: (s) => <Tv v="in.ship.loa" ctx={{ ...ctx, ship: s.id }} className={feas(s).reasons.includes('LOA') ? 'text-merah' : ''}>{num(s.loa_m, 1)}</Tv> },
            { key: 'dr', head: 'Draft', width: 56, mono: true, render: (s) => <Tv v="in.ship.draft" ctx={{ ...ctx, ship: s.id }} className={feas(s).reasons.includes('draft') ? 'text-merah' : ''}>{num(s.draft_m, 2)}</Tv> },
            { key: 'kn', head: 'Kn', width: 48, mono: true, render: (s) => <Tv v="in.ship.speed" ctx={{ ...ctx, ship: s.id }}>{num(s.speed_kn, 1)}</Tv> },
            { key: 'rtd', head: 'RTD', width: 52, mono: true, render: (s) => <Tv v="voyage.rtd" ctx={{ ...ctx, ship: s.id }} className="text-abu">{isDamai && FLEET_CANDIDATES[s.id] ? num(FLEET_CANDIDATES[s.id].rtd, 1) : '–'}</Tv> },
            { key: 'k', head: 'Kapal', width: 52, mono: true, render: (s) => <Tv v="voyage.n_ship" ctx={{ ...ctx, ship: s.id }} className="text-abu">{isDamai && FLEET_CANDIDATES[s.id] ? String(FLEET_CANDIDATES[s.id].ships) : '–'}</Tv> },
            { key: 'u', head: 'Rp/t', width: 72, mono: true, render: (s) => <Tv v="shipcost.unit" ctx={{ ...ctx, ship: s.id }} className="text-abu">{isDamai && FLEET_CANDIDATES[s.id] ? `${FLEET_CANDIDATES[s.id].unitCostRb} rb` : '–'}</Tv> },
            {
              key: 'st',
              head: 'Status',
              render: (s) => {
                const f = feas(s)
                if (f.ok === false) return <Tv v="vessel.feasible" ctx={{ ...ctx, ship: s.id }} className="no-underline"><Badge kind="gugur">gugur · {f.reasons.join(', ')}</Badge></Tv>
                if (s.id === shipId) return <span className="text-[13px] font-medium">terpilih</span>
                return <span className="text-[13px] text-abu">{f.ok === null ? 'LOA ?' : 'layak'}</span>
              },
            },
          ]}
        />
        <Note>
          RTD, jumlah kapal, dan Rp/t placeholder. Kelayakan: draft ≤ draft maks pelabuhan; LOA ≤ dermaga ÷ <Tv v="in.param.berth_loa_ratio">{num(ratio, 2)}</Tv>
          {port?.longest_berth_m ? <> ({shortPortName(port.name)} <Tv v="in.port.longest_berth" ctx={ctx}>{`${num(port.longest_berth_m)} m`}</Tv> → {num(port.longest_berth_m / ratio)} m)</> : ''}. Angka merah = yang melanggar batas.
        </Note>
      </Section>

      <Section title="Unit cost terhadap ukuran kapal" aside={<span className="flex items-center gap-2"><Tv v="shipcost.unit" ctx={ctx} className="font-mono text-[13px]">ƒx Rp/t</Tv><PH /></span>}>
        {isDamai ? (
          <>
            <DotPlot
              height={200}
              points={candidates.map((s) => {
                const f = feas(s)
                const ph = FLEET_CANDIDATES[s.id]
                const y = ph ? ph.unitCostRb : 150 - s.dwt_t / 1000
                return { x: Math.log(s.dwt_t), y, color: f.ok === false ? C.merah : s.id === shipId ? C.hitam : C.biru, outline: f.ok === false, size: s.id === shipId ? 14 : 10, label: `${s.name}: ${ph ? ph.unitCostRb + ' rb/t' : 'gugur'}` }
              })}
              xLabels={[`${num(candidates[0].dwt_t / 1000, 1)}k`, `${num(candidates[candidates.length - 1].dwt_t / 1000, 1)}k DWT`]}
            />
            <Legend items={[{ color: C.biru, label: 'layak', round: true }, { color: C.hitam, label: 'terpilih', round: true }, { color: C.merah, label: 'gugur (posisi jika diizinkan)', round: true, outline: true }]} />
          </>
        ) : (
          <Note>Grafik trade-off placeholder hanya untuk in.damai.</Note>
        )}
      </Section>
    </>
  )
}
