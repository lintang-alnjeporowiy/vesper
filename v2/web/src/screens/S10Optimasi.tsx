import { useState } from 'react'
import { Badge, Button, Note, PH, ScreenHeader, Section, Split, Table } from '../components/ui'
import { ConvergenceChart } from '../charts/charts'
import { CONVERGENCE, OPTIM_RESULT } from '../mock/placeholders'

const VARS = [
  { id: 'ship', label: 'Kapal per flow', sym: 'y[f,k]', on: true },
  { id: 'equip', label: 'Alat per terminal', sym: 'z[τ,e]', on: true },
  { id: 'water', label: 'Mode perairan', sym: 'w[m]', on: true },
  { id: 'speed', label: 'Level kecepatan · opsional', sym: 's[f,v]', on: false },
  { id: 'mixed', label: 'Armada campuran · nanti', sym: '', on: false, disabled: true },
]
const CONSTRAINTS = [
  { id: 'port', label: 'Draft dan LOA pelabuhan', on: true },
  { id: 'bor', label: 'BOR ≤ maks', on: true },
  { id: 'depth', label: 'Kedalaman perlu ≥ 1,5 × draft', on: true },
  { id: 'reach', label: 'Jangkauan alat ≥ kebutuhan', on: true },
  { id: 'interval', label: 'Interval layanan ≤ lama konsumsi', on: false },
]

function Toggle({ on, onClick, label }: { on: boolean; onClick: () => void; label: string }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={onClick} className={`flex h-[18px] w-8 cursor-pointer items-center rounded-full border-0 px-0.5 ${on ? 'justify-end bg-hitam' : 'justify-start bg-garis'}`}>
      <span className="h-3.5 w-3.5 rounded-full bg-white" />
    </button>
  )
}

export default function S10Optimasi() {
  const [objective, setObjective] = useState<'npv' | 'unit'>('npv')
  const [vars, setVars] = useState(() => Object.fromEntries(VARS.map((v) => [v.id, v.on])))
  const [cons, setCons] = useState(() => Object.fromEntries(CONSTRAINTS.map((c) => [c.id, c.on])))
  const [ran, setRan] = useState(false)

  return (
    <>
      <ScreenHeader step={10} kind="hasil" title="Optimasi" lead="Pilih objektif dan batasan, jalankan MILP, lalu bandingkan hasilnya dengan pilihan manual per flow." badge={<PH>placeholder · optimizer tahap 9</PH>} />

      <Split
        left={
          <div className="flex flex-col gap-5">
            <fieldset className="m-0 flex flex-col gap-2.5 border-0 p-0">
              <legend className="pb-2.5 text-xl">Objektif</legend>
              {([['npv', 'Minimalkan NPV biaya total', 'bawaan'], ['unit', 'Minimalkan unit cost', 'perlu aturan agregasi']] as const).map(([id, label, note]) => (
                <label key={id} className="flex cursor-pointer items-center gap-2.5">
                  <input type="radio" name="objektif" checked={objective === id} onChange={() => setObjective(id)} className="h-4 w-4 accent-hitam" />
                  <span className="grow text-sm">{label}</span>
                  <span className="text-[13px] text-abu">{note}</span>
                </label>
              ))}
            </fieldset>
            <fieldset className="m-0 flex flex-col gap-2.5 border-0 p-0">
              <legend className="pb-2.5 text-xl">Yang dioptimasi</legend>
              {VARS.map((v) => (
                <label key={v.id} className={`flex items-center gap-2.5 ${v.disabled ? 'text-abu' : 'cursor-pointer'}`}>
                  <input type="checkbox" disabled={v.disabled} checked={vars[v.id]} onChange={() => setVars({ ...vars, [v.id]: !vars[v.id] })} className="h-4 w-4 accent-hitam" />
                  <span className="grow text-sm">{v.label}</span>
                  <span className="font-mono text-[13px] text-abu">{v.sym}</span>
                </label>
              ))}
              <Note>Yang tidak dicentang dipakai tetap dari pilihan manual (layar 5, 6, 8).</Note>
            </fieldset>
          </div>
        }
        right={
          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-2.5">
              <h2 className="m-0 pb-0 text-xl font-normal">Batasan</h2>
              {CONSTRAINTS.map((c) => (
                <span key={c.id} className="flex items-center gap-2.5">
                  <span className="grow text-sm">{c.label}</span>
                  <Toggle label={c.label} on={cons[c.id]} onClick={() => setCons({ ...cons, [c.id]: !cons[c.id] })} />
                </span>
              ))}
            </div>
            <div className="flex flex-col gap-2 rounded-kontrol bg-permukaan p-4">
              <span className="flex"><span className="grow text-[13px] text-abu">Solver</span><span className="font-mono text-[13px]">HiGHS (MILP)</span></span>
              <span className="flex"><span className="grow text-[13px] text-abu">Kombinasi diprakalkulasi</span><span className="font-mono text-[13px] text-abu">≈ 1.400</span></span>
              <Button variant="utama" onClick={() => setRan(true)}>Jalankan optimasi</Button>
              {ran && <Note>Optimizer belum tersambung (tahap 9). Hasil di bawah adalah contoh bentuk tabel.</Note>}
            </div>
          </div>
        }
      />

      <Section title="Konvergensi solver" aside={<span className="flex items-center gap-3"><span className="flex items-center gap-1.5 text-[13px] text-abu"><span className="inline-block h-0.5 w-4 bg-hitam" />solusi terbaik (incumbent)</span><span className="flex items-center gap-1.5 text-[13px] text-abu"><span className="inline-block h-0.5 w-4 bg-biru" />batas bawah (dual bound)</span><PH /></span>}>
        <ConvergenceChart points={CONVERGENCE} yUnit="NPV biaya total, Rp triliun" xUnit="waktu solver, detik" />
        <Note>
          Bukti optimasi: HiGHS (branch-and-bound) merekam setiap solusi layak yang lebih baik (garis hitam, turun) dan batas bawah yang bisa dicapai (garis biru, naik). Saat keduanya bertemu, gap = 0 % dan solusi terbukti optimal, bukan sekadar "tidak membaik lagi" seperti iterasi Evolver. Data direkam lewat callback solver di Tahap 9; kurva ini placeholder.
        </Note>
      </Section>

      <Section title="Hasil optimasi vs pilihan manual" aside={<span className="flex items-center gap-2"><span className="text-[13px] text-abu">NPV biaya total</span><span className="font-mono text-sm text-abu">{OPTIM_RESULT.npvDelta}</span><Badge kind="dihitung">lebih murah</Badge></span>}>
        <Table
          rowKey={(r) => r.what}
          rows={OPTIM_RESULT.rows}
          columns={[
            { key: 'w', head: 'Keputusan', width: 110, mono: true, render: (r) => <span className="text-[13px]">{r.what}</span> },
            { key: 'm', head: 'Manual (Evolver)', width: 160, render: (r) => r.manual },
            { key: 'o', head: 'Optimum', width: 170, render: (r) => <span className="text-abu">{r.optimum}</span> },
            { key: 'd', head: 'Selisih', width: 90, render: (r) => (r.delta ? <Badge kind="baik">{r.delta}</Badge> : <span className="font-mono text-abu">±0</span>) },
            { key: 'b', head: 'Batasan aktif', render: (r) => <span className="text-[13px] text-abu">{r.binding}</span> },
          ]}
        />
        <Note>Semua hasil placeholder; contoh ini hanya menunjukkan bentuk tabel.</Note>
      </Section>

      <Section title="Kenapa in.damai tetap AETOS">
        <div className="flex w-full border-y border-garis">
          {OPTIM_RESULT.top3.map((t, i) => (
            <div key={t.name} className={`flex grow basis-0 flex-col gap-1.5 py-4 ${i === 0 ? 'pr-4' : 'border-l border-garis px-4'}`} style={i === 0 ? { boxShadow: 'inset 0 3px 0 var(--color-biru)' } : undefined}>
              <span className="text-[13px] text-abu">{t.rank}</span>
              <span className="text-base font-medium">{t.name}</span>
              <span className={`text-[13px] ${'bad' in t && t.bad ? 'text-merah' : 'font-mono text-abu'}`}>{t.note}</span>
            </div>
          ))}
        </div>
      </Section>
    </>
  )
}
