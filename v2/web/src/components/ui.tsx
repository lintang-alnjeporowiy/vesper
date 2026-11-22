import { useState, type ReactNode } from 'react'
import { num, parseNum } from '../lib/format'
import type { TraceCtx } from '../lib/registry'
import { Tv } from './trace'

// ── Badge status (SPEC §8) ──────────────────────────────────────────────────
export type BadgeKind = 'placeholder' | 'dihitung' | 'input' | 'asumsi' | 'gugur' | 'audit' | 'baik' | 'buruk' | 'tetap' | 'kode' | 'aktif'

const BADGE: Record<BadgeKind, string> = {
  placeholder: 'bg-permukaan text-abu',
  dihitung: 'bg-hijau text-hitam',
  input: 'bg-biru text-hitam',
  asumsi: 'border border-merah text-merah',
  gugur: 'bg-merah text-white',
  audit: 'border border-hitam text-hitam',
  baik: 'bg-hijau text-hitam font-mono',
  buruk: 'bg-merah text-white font-mono',
  tetap: 'bg-permukaan text-abu font-mono',
  kode: 'border border-hitam text-hitam font-mono',
  aktif: 'bg-hitam text-white',
}

export function Badge({ kind, children }: { kind: BadgeKind; children: ReactNode }) {
  return (
    <span className={`inline-flex h-5 shrink-0 items-center whitespace-nowrap rounded-badge px-1.5 text-[13px] font-medium ${BADGE[kind]}`}>
      {children}
    </span>
  )
}

export const PH = ({ children = 'placeholder' }: { children?: ReactNode }) => <Badge kind="placeholder">{children}</Badge>

/** Penanda kotak biru = nilai input kasus yang bisa diedit. */
export const InputMark = () => <span aria-hidden className="inline-block h-1.5 w-1.5 shrink-0 bg-biru" />

export function StatusDot({ kind }: { kind: 'lengkap' | 'asumsi' | 'placeholder' }) {
  const cls = kind === 'lengkap' ? 'bg-hijau' : kind === 'asumsi' ? 'bg-merah' : 'border border-abu'
  return <span aria-hidden className={`inline-block h-2 w-2 shrink-0 ${cls}`} />
}

// ── Kepala layar & bagian ───────────────────────────────────────────────────
export function ScreenHeader(props: { step: number; kind: 'input' | 'hasil' | 'beranda' | 'telusur'; title: string; lead: string; badge?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="flex flex-col gap-2">
      <span className="font-mono text-[13px] text-abu">
        {String(props.step).padStart(2, '0')} · {props.kind}
      </span>
      <div className="flex items-center gap-3">
        <h1 className="m-0 grow text-[32px] font-normal leading-tight">{props.title}</h1>
        {props.badge}
        {props.actions}
      </div>
      <p className="m-0 max-w-[680px] text-base">{props.lead}</p>
    </header>
  )
}

export function Section(props: { title: string; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`flex flex-col gap-4 ${props.className ?? ''}`}>
      <div className="flex items-center gap-3">
        <h2 className="m-0 grow text-xl font-normal">{props.title}</h2>
        {props.aside}
      </div>
      {props.children}
    </section>
  )
}

export const Note = ({ children }: { children: ReactNode }) => <p className="m-0 text-[13px] text-abu">{children}</p>

export const Label = ({ children }: { children: ReactNode }) => <span className="text-[13px] font-medium text-abu">{children}</span>

// ── Tombol ──────────────────────────────────────────────────────────────────
export function Button(props: { variant?: 'utama' | 'garis' | 'tipis'; size?: 'md' | 'sm'; onClick?: () => void; children: ReactNode; disabled?: boolean }) {
  const v = props.variant ?? 'garis'
  const cls =
    v === 'utama' ? 'bg-hitam text-white' : v === 'garis' ? 'border border-hitam text-hitam bg-white' : 'border border-garis text-hitam bg-white'
  const size = props.size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-9 px-4 text-sm'
  return (
    <button
      type="button"
      disabled={props.disabled}
      onClick={props.onClick}
      className={`inline-flex shrink-0 cursor-pointer items-center justify-center rounded-kontrol font-medium disabled:cursor-not-allowed disabled:opacity-40 ${size} ${cls}`}
    >
      {props.children}
    </button>
  )
}

// ── Tabel ───────────────────────────────────────────────────────────────────
export interface Column<T> {
  key: string
  head: ReactNode
  width?: number
  mono?: boolean
  input?: boolean
  render: (row: T, i: number) => ReactNode
}

export function Table<T>(props: { columns: Column<T>[]; rows: T[]; rowKey: (row: T, i: number) => string; selected?: (row: T) => boolean; muted?: (row: T) => boolean; onRowClick?: (row: T) => void; groupStart?: (row: T, i: number) => boolean }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-hitam">
            {props.columns.map((c) => (
              <th key={c.key} style={{ width: c.width }} className="py-2 pr-2 text-left text-[13px] font-medium text-abu">
                <span className="inline-flex items-center gap-1">
                  {c.input && <InputMark />}
                  {c.head}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {props.rows.map((row, i) => {
            const sel = props.selected?.(row)
            const mut = props.muted?.(row)
            return (
              <tr
                key={props.rowKey(row, i)}
                onClick={props.onRowClick ? () => props.onRowClick!(row) : undefined}
                className={`${props.groupStart && !props.groupStart(row, i) ? '' : 'border-t border-garis'} ${sel ? 'bg-permukaan shadow-[inset_3px_0_0_var(--color-biru)]' : ''} ${mut ? 'text-abu' : ''} ${props.onRowClick ? 'cursor-pointer hover:bg-permukaan/60' : ''}`}
              >
                {props.columns.map((c) => (
                  <td key={c.key} className={`py-2 pr-2 align-middle ${c.mono ? 'font-mono' : ''} ${sel && c.key === props.columns[0].key ? 'pl-2 font-medium' : ''}`}>
                    {c.render(row, i)}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Baris definisi (label kiri, nilai kanan) ────────────────────────────────
export function DefRow(props: { label: ReactNode; children: ReactNode; last?: boolean; labelWidth?: number; justify?: boolean }) {
  return (
    <div className={`flex items-center gap-2 border-t border-garis py-2 ${props.last ? 'border-b' : ''}`}>
      <span className="shrink-0 text-[13px] text-abu" style={props.justify ? { flexGrow: 1 } : { width: props.labelWidth ?? 120 }}>
        {props.label}
      </span>
      <span className="flex items-center gap-2 text-sm">{props.children}</span>
    </div>
  )
}

// ── Angka yang bisa diedit (input layar 1–5) ────────────────────────────────
export function EditNum(props: { value: number; onChange: (v: number) => void; digits?: number; unit?: string; scale?: number; changed?: boolean; label: string; mark?: boolean }) {
  const scale = props.scale ?? 1
  const [draft, setDraft] = useState<string | null>(null)
  const shown = num(props.value * scale, props.digits ?? 0)
  const commit = () => {
    if (draft !== null) {
      const v = parseNum(draft)
      if (v !== null) props.onChange(v / scale)
    }
    setDraft(null)
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      {props.changed && <Badge kind="gugur">diubah</Badge>}
      {props.mark !== false && <InputMark />}
      <input
        aria-label={props.label}
        className="w-[11ch] border-0 border-b border-transparent bg-transparent text-right font-mono text-sm outline-none hover:border-garis focus:border-biru"
        value={draft ?? shown}
        onFocus={() => setDraft(shown)}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
          if (e.key === 'Escape') setDraft(null)
        }}
      />
      {props.unit && <span className="font-mono text-sm">{props.unit}</span>}
    </span>
  )
}

/** Isian teks satu baris (mis. IMO number, nama kelas TCH). Disimpan saat blur/Enter. */
export function EditText(props: { value: string | null | undefined; onChange: (v: string | null) => void; label: string; placeholder?: string; mono?: boolean; width?: string; invalid?: boolean; title?: string }) {
  const [draft, setDraft] = useState<string | null>(null)
  const commit = () => {
    if (draft !== null && draft.trim() !== (props.value ?? '')) props.onChange(draft.trim() || null)
    setDraft(null)
  }
  return (
    <input
      aria-label={props.label}
      title={props.title}
      placeholder={props.placeholder}
      className={`border-0 border-b bg-transparent text-sm outline-none hover:border-garis focus:border-biru ${props.mono ? 'font-mono' : ''} ${props.invalid ? 'border-merah text-merah' : 'border-transparent'}`}
      style={{ width: props.width ?? '12ch' }}
      value={draft ?? props.value ?? ''}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
        if (e.key === 'Escape') setDraft(null)
      }}
    />
  )
}

// ── Slider what-if ──────────────────────────────────────────────────────────
export function Slider(props: { label: string; value: number; min: number; max: number; step: number; display: string; onChange?: (v: number) => void; input?: boolean; dark?: boolean }) {
  return (
    <label className="flex w-full flex-col gap-2">
      <span className="flex items-center gap-1.5">
        <span className="grow text-[13px] text-abu">{props.label}</span>
        {props.input !== false && <InputMark />}
        <span className="font-mono text-sm">{props.display}</span>
      </span>
      <input
        type="range"
        min={props.min}
        max={props.max}
        step={props.step}
        value={props.value}
        onChange={(e) => props.onChange?.(Number(e.target.value))}
        className={`w-full ${props.dark ? '[accent-color:#000]' : ''}`}
      />
    </label>
  )
}

// ── KPI strip ───────────────────────────────────────────────────────────────
export function KpiStrip(props: { items: { label: string; value: string; final?: boolean; delta?: ReactNode; v?: string }[]; ctx?: TraceCtx }) {
  return (
    <div className="flex w-full border-y border-garis">
      {props.items.map((k, i) => (
        <div
          key={k.label}
          className={`flex grow basis-0 flex-col gap-1.5 py-4 ${i === 0 ? 'pr-4' : 'px-4'} ${i > 0 && !k.final ? 'border-l border-garis' : ''} ${k.final ? 'bg-hitam px-4 text-white' : ''}`}
        >
          <span className={`text-[13px] ${k.final ? 'text-white' : 'text-abu'}`}>{k.label}</span>
          <span className="flex items-center gap-2">
            <span className={`font-mono text-[28px] leading-none ${k.final ? 'text-white' : 'text-abu'}`}>
              {k.v && k.value !== '–' ? <Tv v={k.v} ctx={props.ctx}>{k.value}</Tv> : k.value}
            </span>
            {k.delta}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Tab garis bawah ─────────────────────────────────────────────────────────
export function Tabs<T extends string>(props: { items: { id: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; mono?: boolean; right?: ReactNode }) {
  return (
    <div role="tablist" className="flex w-full items-center border-b border-garis">
      {props.items.map((t) => {
        const on = t.id === props.value
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={on}
            type="button"
            onClick={() => props.onChange(t.id)}
            className={`-mb-px flex h-10 cursor-pointer items-center gap-1.5 border-0 bg-transparent px-2.5 ${props.mono ? 'font-mono text-[13px]' : 'text-sm'} ${on ? 'border-b-2 border-solid border-hitam font-medium text-hitam' : 'text-abu'}`}
          >
            {t.label}
          </button>
        )
      })}
      <span className="grow" />
      {props.right}
    </div>
  )
}

// ── Dua kolom dipisah garis ─────────────────────────────────────────────────
export function Split(props: { left: ReactNode; right: ReactNode; leftWidth?: number }) {
  return (
    <div className="flex w-full gap-8">
      <div className="flex shrink-0 flex-col" style={{ width: props.leftWidth ?? 392 }}>
        {props.left}
      </div>
      <div className="flex min-w-0 grow flex-col border-l border-garis pl-8">{props.right}</div>
    </div>
  )
}

export function Legend(props: { items: { color: string; label: string; round?: boolean; outline?: boolean }[] }) {
  return (
    <span className="flex flex-wrap items-center gap-3">
      {props.items.map((l) => (
        <span key={l.label} className="inline-flex items-center gap-1.5 text-[13px] text-abu">
          <span
            className={`inline-block h-2.5 w-2.5 ${l.round ? 'rounded-full' : ''}`}
            style={l.outline ? { border: `1px solid ${l.color}` } : { background: l.color }}
          />
          {l.label}
        </span>
      ))}
    </span>
  )
}
