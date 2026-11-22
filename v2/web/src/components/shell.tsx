import { MAP_SCREEN, usePlanner, type Settings } from '../store'
import { AUDIT, KIND_LABEL, VAR, contextLabel, sameCtx, downstream, getVar, inputValue, upstream, type VarDef } from '../lib/registry'
import { PH_SAMPLE, PH_SAMPLE_CTX } from '../mock/placeholders'
import { computedText, isComputed } from '../lib/engine'
import { useReview } from '../review'
import { ReviewPanel, VarNotes } from './ReviewPanel'
import { Badge, Button, InputMark, PH, StatusDot } from './ui'

export const STEPS: { n: number; title: string; group: 'Input' | 'Hasil' | 'Telusur'; status?: 'lengkap' | 'asumsi' | 'placeholder' }[] = [
  { n: 0, title: 'Beranda', group: 'Input' },
  { n: 1, title: 'Soal & parameter', group: 'Input', status: 'lengkap' },
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
  { n: 12, title: 'Peta variabel', group: 'Telusur' },
]

export function Sidebar() {
  const screen = usePlanner((s) => s.screen)
  const setScreen = usePlanner((s) => s.setScreen)
  const meta = usePlanner((s) => s.caseData.meta)
  const reviewed = useReview((s) => s.reviewed)
  const openNotes = useReview((s) => s.notes).filter((n) => !n.done)
  return (
    <nav aria-label="Langkah pengerjaan" className="sticky top-14 flex h-[calc(100vh-56px)] w-60 shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-garis bg-white px-4 py-5">
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <span className="flex h-7 w-7 items-center justify-center rounded-badge bg-hitam font-mono text-[13px] font-medium text-white">TP</span>
        <span className="flex flex-col">
          <span className="text-base font-medium">TPT Planner</span>
          <span className="text-[13px] text-abu">{meta.name.replace('—', '·')}</span>
        </span>
      </div>
      {(['Input', 'Hasil', 'Telusur'] as const).map((g) => (
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
                {openNotes.some((n) => n.screen === s.n) && (
                  <span title="catatan review terbuka" className={`font-mono text-[13px] ${on ? 'text-white' : 'text-abu'}`}>{openNotes.filter((n) => n.screen === s.n).length}</span>
                )}
                {reviewed.includes(s.n) && <span title="sudah ditinjau (Milestone A)" className={`text-[13px] ${on ? 'text-white' : 'text-hijau'}`}>✓</span>}
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
  const { caseData, year, setYear, dirty, recalc, setScreen, toggleTrace, traceOpen, calc } = usePlanner()
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
        <span className="flex items-center gap-2 text-[13px] text-abu" title={calc.error}>
          {calc.status === 'offline' ? (
            <><span className="h-2 w-2 bg-merah" />API tidak aktif · semua hasil placeholder</>
          ) : calc.status === 'error' ? (
            <><span className="h-2 w-2 bg-merah" />engine menolak kasus · lihat laci</>
          ) : calc.result ? (
            <><span className="h-2 w-2 bg-hijau" />{calc.status === 'loading' ? 'menghitung…' : 'demand & operasi kapal dihitung engine'} · biaya & terminal placeholder</>
          ) : (
            'menghubungi engine…'
          )}
        </span>
      )}
      <Button variant="utama" onClick={recalc} disabled={n === 0 && calc.status !== 'offline'}>Hitung ulang</Button>
      <Button onClick={() => setScreen(10)}>Jalankan optimasi</Button>
      <Button variant="tipis" onClick={toggleTrace}>{traceOpen ? 'Tutup laci' : 'ƒx Jejak'}</Button>
    </header>
  )
}

/** Nilai placeholder sebuah variabel turunan pada konteks contoh (in.damai · AETOS · th 10), selain itu undefined. */
function phValue(id: string, ctx?: { flow?: string; ship?: string; year?: number }): string | undefined {
  if (!(id in PH_SAMPLE)) return undefined
  const s = VAR[id]?.scope ?? ''
  if (/flow/.test(s) && ctx?.flow !== PH_SAMPLE_CTX.flow) return undefined
  if (/flow|ship/.test(s) && ctx?.ship && ctx.ship !== PH_SAMPLE_CTX.ship) return undefined
  if (/year/.test(s) && ctx?.year !== PH_SAMPLE_CTX.year) return undefined
  return PH_SAMPLE[id]
}

function KindBadge({ v }: { v: VarDef }) {
  if (v.kind === 'input') return <Badge kind="input">input</Badge>
  if (v.kind === 'decision') return <Badge kind="kode">keputusan</Badge>
  return <PH />
}

const SETTING_ROWS: { key: keyof Settings; label: string; hint: string }[] = [
  { key: 'showDesc', label: 'Keterangan variabel', hint: 'Satu-dua kalimat "variabel ini apa" di bawah nama variabel.' },
  { key: 'showAuditNotes', label: 'Catatan selisih Excel (≠ Excel · A#)', hint: 'Penjelasan temuan audit bila variabel ini berbeda dari Excel K15.' },
  { key: 'showNoAuditNote', label: 'Catatan "tidak ada temuan audit"', hint: 'Kalimat pengingat saat variabel tidak punya temuan audit langsung.' },
  { key: 'showDevNotes', label: 'Catatan development (asumsi data)', hint: 'Tabel asumsi & celah data kasus di layar 1. Panduan pengembangan, bukan bagian tampilan akhir.' },
  { key: 'showPlaceholderNote', label: 'Catatan nilai placeholder', hint: 'Pengingat bahwa nilai turunan hanya tersedia untuk contoh in.damai · AETOS · tahun 10.' },
]

function SettingsPanel() {
  const { settings, setSetting, resetSettings } = usePlanner()
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col">
        <span className="pb-1.5 text-[13px] font-medium text-abu">Laci jejak</span>
        {SETTING_ROWS.map((r) => (
          <label key={r.key} className="flex cursor-pointer items-start gap-2.5 border-t border-garis py-2.5">
            <input type="checkbox" className="mt-0.5 [accent-color:#000]" checked={settings[r.key]} onChange={(e) => setSetting(r.key, e.target.checked)} />
            <span className="flex flex-col gap-0.5">
              <span className="text-sm">{r.label}</span>
              <span className="text-[13px] text-abu">{r.hint}</span>
            </span>
          </label>
        ))}
      </div>
      <Button size="sm" variant="tipis" onClick={resetSettings}>Kembalikan bawaan</Button>
      <p className="m-0 text-[13px] text-abu">Pengaturan disimpan di browser ini saja. Pengaturan lain menyusul di tab ini.</p>
    </div>
  )
}

export function TraceDrawer() {
  const { trace, traceOpen, toggleTrace, showTrace, traceBack, traceHistory, caseData, shipByFlow, setScreen, screen, drawerTab, setDrawerTab, settings, calc, year } = usePlanner()
  if (!traceOpen) return null
  const tabs = (
    <div className="flex items-center gap-2">
      {drawerTab === 'jejak' && traceHistory.length > 0 && (
        <button type="button" aria-label="Jejak sebelumnya" onClick={traceBack} className="cursor-pointer border-0 bg-transparent p-0 font-mono text-base text-abu hover:text-hitam">←</button>
      )}
      <div role="tablist" className="flex grow items-center border-b border-garis">
        {(['jejak', 'review', 'pengaturan'] as const).map((t) => (
          <button
            key={t}
            role="tab"
            type="button"
            aria-selected={drawerTab === t}
            onClick={() => setDrawerTab(t)}
            className={`-mb-px h-9 cursor-pointer border-0 bg-transparent px-2 text-sm ${drawerTab === t ? 'border-b-2 border-solid border-hitam font-medium text-hitam' : 'text-abu'}`}
          >
            {t === 'jejak' ? 'Jejak' : t === 'review' ? 'Review' : 'Pengaturan'}
          </button>
        ))}
      </div>
      <button type="button" aria-label="Tutup laci" onClick={toggleTrace} className="cursor-pointer border-0 bg-transparent text-base text-abu">×</button>
    </div>
  )
  if (drawerTab === 'review') {
    return (
      <aside aria-label="Review" className="sticky top-14 flex h-[calc(100vh-56px)] w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-garis bg-white p-6">
        {tabs}
        <ReviewPanel />
      </aside>
    )
  }
  if (drawerTab === 'pengaturan') {
    return (
      <aside aria-label="Pengaturan" className="sticky top-14 flex h-[calc(100vh-56px)] w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-garis bg-white p-6">
        {tabs}
        <SettingsPanel />
      </aside>
    )
  }
  const v = VAR[trace.id] ?? getVar('voyage.rtd')
  const ctx = trace.ctx ?? {}
  const shipCtx = { ...ctx, ship: ctx.ship ?? (ctx.flow ? shipByFlow[ctx.flow] : undefined) }
  const live = v.kind === 'input' ? undefined : computedText(caseData, calc, v.id, shipCtx, year)
  const value = v.kind === 'input' ? (inputValue(caseData, v, shipCtx, shipByFlow) ?? trace.value) : (live ?? (isComputed(calc, v.id) ? trace.value : (trace.value ?? phValue(v.id, shipCtx))))
  const depLive = (d: VarDef) => computedText(caseData, calc, d.id, shipCtx, year)
  const depValue = (d: VarDef) => (d.kind === 'input' ? inputValue(caseData, d, shipCtx, shipByFlow) : (depLive(d) ?? phValue(d.id, shipCtx))) ?? '–'
  return (
    <aside aria-label="Jejak variabel" className="sticky top-14 flex h-[calc(100vh-56px)] w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-garis bg-white p-6">
      {tabs}
      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] text-abu">{contextLabel(caseData, v, ctx, shipByFlow)}</span>
        <span className="text-base">{v.label}</span>
        <span className="flex items-end gap-2">
          <span className={`font-mono text-[28px] leading-none ${v.kind === 'input' || live ? 'text-hitam' : 'text-abu'}`}>{value ?? '–'}</span>
          {value === undefined && <span className="text-sm text-abu">{v.unit}</span>}
        </span>
        <span className="flex flex-wrap items-center gap-1.5">
          {isComputed(calc, v.id) ? <Badge kind="dihitung">dihitung</Badge> : <KindBadge v={v} />}
          {v.symbol && <span className="font-mono text-[13px]">{v.symbol}</span>}
          <span className="font-mono text-[13px] text-abu">{v.id}</span>
        </span>
        {settings.showDesc && <p className="m-0 pt-1 text-sm leading-5">{v.desc}</p>}
      </div>
      {v.screens && v.screens.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-abu">{v.kind === 'input' ? 'Diisi / tampil di layar' : 'Tampil di layar'}</span>
          <span className="flex flex-wrap gap-1.5">
            {v.screens.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setScreen(n)}
                className={`h-7 cursor-pointer rounded-badge border px-2 text-[13px] ${n === screen ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}
              >
                <span className="font-mono">{String(n).padStart(2, '0')}</span> {STEPS[n]?.title}
              </button>
            ))}
          </span>
        </div>
      )}
      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] font-medium text-abu">
          {v.kind === 'input' ? 'Sumber' : 'Rumus'} · SPEC §{v.section}
        </span>
        <code className="block rounded-badge bg-permukaan p-3 font-mono text-[13px] whitespace-normal">{v.kind === 'input' ? v.case_path : v.formula}</code>
        <span className="font-mono text-[13px] text-abu">Excel {v.excel_ref ?? '–'} · {KIND_LABEL[v.kind]} · {v.unit}</span>
      </div>
      {v.deps.length > 0 && (
        <div className="flex flex-col">
          <span className="pb-1.5 text-[13px] font-medium text-abu">Dihitung dari · {v.deps.length}</span>
          {v.deps.map((id) => {
            const d = getVar(id)
            return (
              <button
                key={id}
                type="button"
                title={d.desc}
                onClick={() => showTrace(id, trace.ctx)}
                className="flex cursor-pointer items-center gap-1.5 border-0 border-t border-solid border-garis bg-transparent px-0 py-2 text-left hover:bg-permukaan"
              >
                <span className="grow text-sm">{d.label}</span>
                {d.kind === 'input' && <InputMark />}
                <span className={`max-w-[120px] truncate font-mono text-[13px] ${d.kind === 'input' || depLive(d) ? 'text-hitam' : 'text-abu'}`}>{depValue(d)}</span>
              </button>
            )
          })}
        </div>
      )}
      <div className="flex flex-col gap-2">
        <span className="text-[13px] font-medium text-abu">Dipakai untuk menghitung · {v.dependents.length}</span>
        <span className="flex flex-wrap gap-1.5">
          {v.dependents.length === 0 && <span className="text-[13px] text-abu">ujung rantai ({KIND_LABEL[v.kind]})</span>}
          {v.dependents.map((id) => (
            <button key={id} type="button" title={getVar(id).desc} onClick={() => showTrace(id, trace.ctx)} className="h-7 cursor-pointer rounded-badge border border-hitam bg-white px-2 text-[13px] hover:bg-permukaan">
              {getVar(id).label}
            </button>
          ))}
        </span>
      </div>
      <div className="flex items-center gap-2 border-t border-garis pt-3">
        <span className="grow font-mono text-[13px] text-abu">hulu {upstream(v.id).size} · hilir {downstream(v.id).size}</span>
        {screen !== MAP_SCREEN && <Button size="sm" variant="tipis" onClick={() => setScreen(MAP_SCREEN)}>Buka di peta</Button>}
      </div>
      {v.note && <p className="m-0 text-[13px] text-abu">{v.note}</p>}
      <VarNotes varId={v.id} />
      {settings.showPlaceholderNote && v.kind !== 'input' && !isComputed(calc, v.id) && !sameCtx(shipCtx, PH_SAMPLE_CTX) && <p className="m-0 text-[13px] text-abu">Nilai turunan placeholder hanya tersedia untuk contoh in.damai · AETOS · tahun 10.</p>}
      <span className="grow" />
      {(v.audit?.length ? settings.showAuditNotes : settings.showNoAuditNote) && (
        <div className="flex gap-2 pt-3">
          <span className="w-0.5 shrink-0 bg-hitam" />
          <span className="flex flex-col gap-1.5 text-[13px] text-abu">
            {v.audit?.length
              ? v.audit.map((a) => (
                  <span key={a}>
                    <Badge kind="audit">≠ Excel · {a}</Badge> {AUDIT[a]}
                  </span>
                ))
              : 'Tidak ada temuan audit langsung pada variabel ini. Selisih vs Excel K15 bisa diwarisi dari masukannya (lihat hulu).'}
          </span>
        </div>
      )}
    </aside>
  )
}
