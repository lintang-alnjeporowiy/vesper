import { usePlanner, currentTrace } from '../store'
import { Badge, Button, InputMark, PH, StatusDot } from './ui'

export const STEPS: { n: number; title: string; group: 'Input' | 'Hasil'; status?: 'lengkap' | 'asumsi' | 'placeholder' }[] = [
  { n: 0, title: 'Beranda', group: 'Input' },
  { n: 1, title: 'Soal & asumsi', group: 'Input', status: 'lengkap' },
  { n: 2, title: 'Tenant & muatan', group: 'Input', status: 'lengkap' },
  { n: 3, title: 'Pelabuhan & rute', group: 'Input', status: 'asumsi' },
  { n: 4, title: 'Kapal', group: 'Input', status: 'lengkap' },
  { n: 5, title: 'Alat B/M', group: 'Input', status: 'lengkap' },
  { n: 6, title: 'Armada & operasi', group: 'Hasil', status: 'placeholder' },
  { n: 7, title: 'Biaya pelayaran', group: 'Hasil', status: 'placeholder' },
  { n: 8, title: 'Terminal KEK', group: 'Hasil', status: 'placeholder' },
  { n: 9, title: 'Investasi & biaya', group: 'Hasil', status: 'placeholder' },
  { n: 10, title: 'Optimasi', group: 'Hasil', status: 'placeholder' },
  { n: 11, title: 'Skenario & laporan', group: 'Hasil', status: 'placeholder' },
]

export function Sidebar() {
  const screen = usePlanner((s) => s.screen)
  const setScreen = usePlanner((s) => s.setScreen)
  const meta = usePlanner((s) => s.caseData.meta)
  return (
    <nav aria-label="Langkah pengerjaan" className="sticky top-14 flex h-[calc(100vh-56px)] w-60 shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-garis bg-white px-4 py-5">
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <span className="flex h-7 w-7 items-center justify-center rounded-badge bg-hitam font-mono text-[13px] font-medium text-white">TP</span>
        <span className="flex flex-col">
          <span className="text-base font-medium">TPT Planner</span>
          <span className="text-[13px] text-abu">{meta.name.replace('—', '·')}</span>
        </span>
      </div>
      {(['Input', 'Hasil'] as const).map((g) => (
        <div key={g} className="flex flex-col gap-0.5 pb-4">
          <span className="px-2 pb-1 text-[13px] font-medium text-abu">{g}</span>
          {STEPS.filter((s) => s.group === g).map((s) => {
            const on = s.n === screen
            return (
              <button
                key={s.n}
                type="button"
                aria-current={on ? 'page' : undefined}
                onClick={() => setScreen(s.n)}
                className={`flex h-9 cursor-pointer items-center gap-2 rounded-kontrol border-0 px-2 text-left ${on ? 'bg-hitam text-white' : 'bg-transparent text-hitam hover:bg-permukaan'}`}
              >
                <span className={`w-6 font-mono text-[13px] ${on ? 'text-white' : 'text-abu'}`}>{String(s.n).padStart(2, '0')}</span>
                <span className="grow text-sm">{s.title}</span>
                {s.status && <StatusDot kind={s.status} />}
              </button>
            )
          })}
        </div>
      ))}
      <span className="grow" />
      <div className="flex flex-col gap-1.5 px-2 pt-3 text-[13px] text-abu">
        <span className="flex items-center gap-2"><StatusDot kind="lengkap" />Input lengkap</span>
        <span className="flex items-center gap-2"><StatusDot kind="asumsi" />Ada asumsi atau celah</span>
        <span className="flex items-center gap-2"><StatusDot kind="placeholder" />Hasil masih placeholder</span>
      </div>
    </nav>
  )
}

export function TopBar() {
  const { caseData, year, setYear, dirty, recalc, setScreen, toggleTrace, traceOpen } = usePlanner()
  const n = Object.keys(dirty).length
  const plan = caseData.plans?.[0]
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center gap-6 border-b border-garis bg-white px-6">
      <span className="flex items-center gap-1.5">
        <span className="text-[13px] text-abu">Kasus</span>
        <span className="text-sm font-medium">{caseData.meta.name.replace('—', '·')}</span>
      </span>
      <span className="h-6 w-px bg-garis" />
      <span className="flex items-center gap-1.5">
        <span className="text-[13px] text-abu">Skenario</span>
        <span className="text-sm font-medium">{plan?.name ?? 'Manual'}</span>
      </span>
      <span className="h-6 w-px bg-garis" />
      <span className="flex items-center gap-2">
        <span className="text-[13px] text-abu">Tahun</span>
        <span className="flex items-center rounded-badge border border-garis">
          <button type="button" aria-label="Tahun sebelumnya" className="cursor-pointer border-0 bg-transparent px-2 py-1 font-mono text-[13px] text-abu" onClick={() => setYear(Math.max(1, year - 1))}>−</button>
          <span className="px-2 py-1 font-mono text-sm font-medium">{year}</span>
          <button type="button" aria-label="Tahun berikutnya" className="cursor-pointer border-0 bg-transparent px-2 py-1 font-mono text-[13px] text-abu" onClick={() => setYear(Math.min((caseData.horizon.years ?? 20), year + 1))}>+</button>
        </span>
        <span className="font-mono text-[13px] text-abu">/ {(caseData.horizon.years ?? 20)}</span>
      </span>
      <span className="grow" />
      {n > 0 ? (
        <span className="flex items-center gap-2 text-[13px] text-merah" title={Object.values(dirty).map((d) => d.label).join(', ')}>
          <span className="h-2 w-2 bg-merah" />
          {n} input berubah · perlu hitung ulang
        </span>
      ) : (
        <span className="flex items-center gap-2 text-[13px] text-abu">engine belum tersambung · semua hasil placeholder</span>
      )}
      <Button variant="utama" onClick={recalc} disabled={n === 0}>Hitung ulang</Button>
      <Button onClick={() => setScreen(10)}>Jalankan optimasi</Button>
      <Button variant="tipis" onClick={toggleTrace}>{traceOpen ? 'Tutup jejak' : 'ƒx Jejak'}</Button>
    </header>
  )
}

export function TraceDrawer() {
  const key = usePlanner((s) => s.trace)
  const open = usePlanner((s) => s.traceOpen)
  const toggle = usePlanner((s) => s.toggleTrace)
  const showTrace = usePlanner((s) => s.showTrace)
  if (!open) return null
  const t = currentTrace(key)
  return (
    <aside aria-label="Jejak variabel" className="sticky top-14 flex h-[calc(100vh-56px)] w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-garis bg-white p-6">
      <div className="flex items-center">
        <h2 className="m-0 grow text-base font-medium">Jejak variabel</h2>
        <button type="button" aria-label="Tutup jejak" onClick={toggle} className="cursor-pointer border-0 bg-transparent text-base text-abu">×</button>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[13px] text-abu">{t.context}</span>
        <span className="flex items-end gap-2">
          <span className="text-base">{t.name}</span>
          <span className="font-mono text-[28px] leading-none text-abu">{t.value}</span>
          <span className="text-sm text-abu">{t.unit}</span>
        </span>
        <span><PH /></span>
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] font-medium text-abu">Rumus · {t.spec}</span>
        <code className="block rounded-badge bg-permukaan p-3 font-mono text-[13px] whitespace-normal">{t.formula}</code>
      </div>
      <div className="flex flex-col">
        <span className="pb-1.5 text-[13px] font-medium text-abu">Masukan</span>
        {t.inputs.map((inp) => (
          <div key={inp.label} className={`flex items-center gap-1.5 py-2 ${inp.sub ? 'pl-4' : 'border-t border-garis'}`}>
            <span className={`grow text-sm ${inp.sub ? 'text-abu' : ''}`}>{inp.label}</span>
            {inp.input && <InputMark />}
            <span className={`font-mono text-sm ${inp.input ? 'text-hitam' : 'text-abu'}`}>{inp.value}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-[13px] font-medium text-abu">Dipakai oleh</span>
        <span className="flex flex-wrap gap-1.5">
          {t.usedBy.map((u) => {
            const target = u === 'Jumlah kapal' ? 'kapal' : u === 'RTD' ? 'rtd' : u === 'Frekuensi' ? 'frekuensi' : null
            return (
              <button
                key={u}
                type="button"
                disabled={!target}
                onClick={() => target && showTrace(target)}
                className="h-7 cursor-pointer rounded-badge border border-hitam bg-white px-2 text-[13px] disabled:cursor-default disabled:border-garis"
              >
                {u}
              </button>
            )
          })}
        </span>
      </div>
      <span className="grow" />
      <div className="flex gap-2 pt-3">
        <span className="w-0.5 shrink-0 bg-hitam" />
        <span className="text-[13px] text-abu">
          {'audit' in t && t.audit ? <><Badge kind="audit">≠ Excel</Badge> {t.audit}</> : 'Bila angka ini berbeda dari Excel K15, ID temuan audit (A1–A11) dan alasannya tampil di sini.'}
        </span>
      </div>
    </aside>
  )
}
