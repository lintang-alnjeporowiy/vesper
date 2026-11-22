import { useState } from 'react'
import { VAR } from '../lib/registry'
import { NOTE_TOPICS, toMarkdown, useReview, type NoteTopic, type ReviewNote } from '../review'
import { usePlanner } from '../store'
import { STEPS } from './shell'
import { Button } from './ui'

const screenTitle = (n: number) => STEPS.find((s) => s.n === n)?.title ?? `Layar ${n}`
const varLabel = (id: string) => VAR[id]?.label ?? id

/** Form catatan baru. `varId` diisi = catatan untuk variabel itu. */
export function NoteForm(props: { screen: number; varId?: string; defaultTopic?: NoteTopic; onDone?: () => void; autoFocus?: boolean }) {
  const add = useReview((s) => s.add)
  const [topic, setTopic] = useState<NoteTopic>(props.defaultTopic ?? 'lainnya')
  const [text, setText] = useState('')
  const save = () => {
    if (!text.trim()) return
    add({ screen: props.screen, varId: props.varId, topic, text: text.trim() })
    setText('')
    props.onDone?.()
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1">
        {NOTE_TOPICS.map((t) => (
          <button key={t} type="button" aria-pressed={topic === t} onClick={() => setTopic(t)} className={`h-6 cursor-pointer rounded-badge border px-1.5 text-[13px] ${topic === t ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}>
            {t}
          </button>
        ))}
      </div>
      <textarea
        aria-label="Isi catatan koreksi"
        autoFocus={props.autoFocus}
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) save()
          if (e.key === 'Escape') props.onDone?.()
        }}
        placeholder={props.varId ? 'mis. rumus seharusnya …, dependensi kurang …' : 'mis. kolom X belum ada satuannya …'}
        className="w-full rounded-kontrol border border-garis p-2 text-[13px] outline-none focus:border-biru"
      />
      <span className="flex items-center gap-2">
        <Button size="sm" variant="utama" onClick={save} disabled={!text.trim()}>Simpan catatan</Button>
        {props.onDone && <Button size="sm" variant="tipis" onClick={props.onDone}>Batal</Button>}
        <span className="text-[13px] text-abu">Ctrl+Enter</span>
      </span>
    </div>
  )
}

function NoteItem({ n, showScreen }: { n: ReviewNote; showScreen?: boolean }) {
  const { remove, toggleDone } = useReview()
  const showTrace = usePlanner((s) => s.showTrace)
  const setScreen = usePlanner((s) => s.setScreen)
  return (
    <li className={`flex gap-2 border-t border-garis py-2 ${n.done ? 'opacity-50' : ''}`}>
      <input type="checkbox" aria-label="Tandai selesai" checked={n.done} onChange={() => toggleDone(n.id)} className="mt-0.5" />
      <span className="flex min-w-0 grow flex-col gap-1">
        <span className="flex flex-wrap items-center gap-1.5 text-[13px]">
          <span className="rounded-badge bg-permukaan px-1.5 font-medium">{n.topic}</span>
          {showScreen && (
            <button type="button" onClick={() => setScreen(n.screen)} className="cursor-pointer border-0 bg-transparent p-0 font-mono text-[13px] text-abu hover:text-hitam">
              {String(n.screen).padStart(2, '0')}
            </button>
          )}
          {n.varId && (
            <button type="button" onClick={() => showTrace(n.varId!)} title={n.varId} className="cursor-pointer truncate border-0 bg-transparent p-0 text-[13px] text-biru underline decoration-dotted">
              {varLabel(n.varId)}
            </button>
          )}
        </span>
        <span className={`text-[13px] whitespace-pre-wrap ${n.done ? 'line-through' : ''}`}>{n.text}</span>
      </span>
      <button type="button" aria-label="Hapus catatan" onClick={() => remove(n.id)} className="h-5 cursor-pointer border-0 bg-transparent text-abu hover:text-merah">×</button>
    </li>
  )
}

/** Bagian kecil di tab Jejak: catatan untuk variabel yang sedang dilihat. */
export function VarNotes({ varId }: { varId: string }) {
  const screen = usePlanner((s) => s.screen)
  const notes = useReview((s) => s.notes).filter((n) => n.varId === varId)
  const [open, setOpen] = useState(false)
  return (
    <div className="flex flex-col gap-2 border-t border-garis pt-3">
      <span className="flex items-center gap-2">
        <span className="grow text-[13px] font-medium text-abu">Koreksi variabel ini{notes.length ? ` · ${notes.length}` : ''}</span>
        {!open && <Button size="sm" variant="tipis" onClick={() => setOpen(true)}>Catat koreksi</Button>}
      </span>
      {open && <NoteForm screen={screen} varId={varId} defaultTopic="rumus" autoFocus onDone={() => setOpen(false)} />}
      {notes.length > 0 && <ul className="m-0 flex list-none flex-col p-0">{notes.map((n) => <NoteItem key={n.id} n={n} />)}</ul>}
    </div>
  )
}

const SYNC_LABEL = { file: 'tersimpan di v2/review/notes.json', menyimpan: 'menyimpan …', browser: 'hanya di browser ini (dev server tidak terjangkau)' }

/** Tab Review di laci kanan. */
export function ReviewPanel() {
  const { notes, reviewed, toggleReviewed, sync, updated } = useReview()
  const { screen, setScreen, trace } = usePlanner()
  const [filter, setFilter] = useState<'layar' | 'semua' | 'terbuka'>('layar')
  const [linkVar, setLinkVar] = useState(false)
  const [copied, setCopied] = useState(false)
  const shown = notes.filter((n) => (filter === 'layar' ? n.screen === screen : filter === 'terbuka' ? !n.done : true))
  const open = notes.filter((n) => !n.done).length
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(toMarkdown({ version: 1, updated, reviewed, notes }, screenTitle, varLabel))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setCopied(false)
    }
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <span className="flex items-baseline gap-2">
          <span className="grow text-base">Milestone A</span>
          <span className="font-mono text-[13px] text-abu">{reviewed.length}/{STEPS.length} layar · {open} terbuka</span>
        </span>
        <span className="h-1 w-full bg-permukaan"><span className="block h-1 bg-hitam" style={{ width: `${(reviewed.length / STEPS.length) * 100}%` }} /></span>
        <span className="text-[13px] text-abu">{SYNC_LABEL[sync]}</span>
      </div>

      <div className="flex flex-col gap-2 border-t border-garis pt-3">
        <span className="text-[13px] font-medium">Catatan untuk layar {String(screen).padStart(2, '0')} · {screenTitle(screen)}</span>
        <label className="flex cursor-pointer items-center gap-1.5 text-[13px]">
          <input type="checkbox" checked={reviewed.includes(screen)} onChange={() => toggleReviewed(screen)} />
          layar ini sudah ditinjau
        </label>
        <label className="flex cursor-pointer items-center gap-1.5 text-[13px] text-abu">
          <input type="checkbox" checked={linkVar} onChange={(e) => setLinkVar(e.target.checked)} />
          kaitkan dengan variabel <span className="text-hitam">{varLabel(trace.id)}</span>
        </label>
        <NoteForm key={`${screen}-${linkVar}`} screen={screen} varId={linkVar ? trace.id : undefined} defaultTopic={linkVar ? 'rumus' : 'tampilan'} />
      </div>

      <div className="flex flex-col gap-1 border-t border-garis pt-3">
        <span className="flex items-center gap-1">
          {(['layar', 'terbuka', 'semua'] as const).map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)} className={`h-7 cursor-pointer rounded-badge border px-2 text-[13px] ${filter === f ? 'border-hitam' : 'border-garis bg-white'}`}>
              {f === 'layar' ? 'layar ini' : f}
            </button>
          ))}
        </span>
        {shown.length === 0 ? (
          <span className="py-2 text-[13px] text-abu">Belum ada catatan{filter === 'layar' ? ' di layar ini' : ''}.</span>
        ) : (
          <ul className="m-0 flex list-none flex-col p-0">{shown.map((n) => <NoteItem key={n.id} n={n} showScreen={filter !== 'layar'} />)}</ul>
        )}
      </div>

      <span className="flex items-center gap-2">
        <Button size="sm" variant="tipis" onClick={copy} disabled={!notes.length}>{copied ? 'Tersalin' : 'Salin semua (Markdown)'}</Button>
      </span>

      <div className="flex flex-col border-t border-garis pt-3">
        <span className="pb-1 text-[13px] font-medium text-abu">Daftar layar</span>
        {STEPS.map((s) => {
          const c = notes.filter((n) => n.screen === s.n && !n.done).length
          return (
            <span key={s.n} className="flex h-7 items-center gap-2 text-[13px]">
              <input type="checkbox" aria-label={`${s.title} sudah ditinjau`} checked={reviewed.includes(s.n)} onChange={() => toggleReviewed(s.n)} />
              <button type="button" onClick={() => setScreen(s.n)} className={`grow cursor-pointer border-0 bg-transparent p-0 text-left text-[13px] ${s.n === screen ? 'font-medium' : ''}`}>
                <span className="font-mono text-abu">{String(s.n).padStart(2, '0')}</span> {s.title}
              </button>
              {c > 0 && <span className="font-mono text-abu">{c}</span>}
            </span>
          )
        })}
      </div>
    </div>
  )
}
