import type { ReactNode } from 'react'
import { usePlanner } from '../store'
import { VAR, sameCtx, type TraceCtx } from '../lib/registry'

function textOf(node: ReactNode): string | undefined {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).filter(Boolean).join('')
  return undefined
}

/**
 * Angka yang bisa ditelusuri: klik → laci jejak menampilkan rumus, masukan, dan turunan variabel `v`
 * dari registry. Garis bawah titik-titik = bisa diklik.
 */
export function Tv(props: { v: string; ctx?: TraceCtx; value?: string; children: ReactNode; className?: string; block?: boolean }) {
  const show = usePlanner((s) => s.showTrace)
  const active = usePlanner((s) => s.traceOpen && s.trace.id === props.v && sameCtx(s.trace.ctx, props.ctx))
  const def = VAR[props.v]
  if (!def && import.meta.env.DEV) console.warn(`Tv: variabel '${props.v}' tidak ada di registry`)
  return (
    <button
      type="button"
      data-var={props.v}
      title={def ? `ƒx ${def.label}: ${def.desc}` : props.v}
      onClick={(e) => {
        e.stopPropagation()
        show(props.v, props.ctx, props.value ?? textOf(props.children))
      }}
      className={`cursor-pointer border-0 bg-transparent p-0 text-left [color:inherit] [font:inherit] underline decoration-[#9a9a9a] decoration-dotted underline-offset-4 hover:decoration-current ${props.block ? 'flex w-full flex-col items-start no-underline' : 'inline'} ${active ? 'outline-2 outline-offset-2 outline-biru' : ''} ${props.className ?? ''}`}
    >
      {props.children}
    </button>
  )
}
