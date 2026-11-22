import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as RPointerEvent } from 'react'
import { Button, InputMark, Legend, Note, ScreenHeader } from '../components/ui'
import { INPUT_GROUPS, INTERACTIONS, KIND_LABEL, LANES, VAR, VARS, downstream, upstream, type VarDef } from '../lib/registry'
import { usePlanner } from '../store'

// Tata letak: kolom kiri = input kasus; di kanannya lajur per modul (baris) dengan posisi horizontal
// = tingkat dependensi, jadi setiap panah mengalir kiri → kanan.
const W = 164
const W_IN = 200
const H = 46
const H_IN = 30
const GAP_Y = 8
const GAP_X = 36
const LANE_HEAD = 26
const LANE_PAD = 14

type Mode = 'ringkas' | 'rinci'
type View = { x: number; y: number; z: number }
const Z_MIN = 0.2
const Z_MAX = 2
const clampZ = (z: number) => Math.min(Z_MAX, Math.max(Z_MIN, z))

interface GNode {
  id: string
  label: string
  sub: string
  desc: string
  kind: VarDef['kind'] | 'group'
  members: string[]
  x: number
  y: number
  w: number
  h: number
}

const groupId = (g: string) => `grp.${g}`

function buildLayout(mode: Mode, visible: Set<string> | null) {
  const show = (id: string) => !visible || visible.has(id)
  // input → simpul (atribut atau kelompok)
  const inputs = VARS.filter((v) => v.kind === 'input' && show(v.id))
  const inNodes: GNode[] = []
  const nodeOf: Record<string, string> = {}
  if (mode === 'rinci') {
    for (const v of inputs) {
      inNodes.push({ id: v.id, label: v.label, sub: v.id, kind: 'input', desc: v.desc, members: [v.id], x: 0, y: 0, w: W_IN, h: H_IN })
      nodeOf[v.id] = v.id
    }
  } else {
    const groups = new Map<string, string[]>()
    for (const v of inputs) groups.set(v.group!, [...(groups.get(v.group!) ?? []), v.id])
    for (const g of Object.keys(INPUT_GROUPS)) {
      const m = groups.get(g)
      if (!m) continue
      inNodes.push({ id: groupId(g), label: INPUT_GROUPS[g], sub: `${m.length} input`, kind: 'group', desc: `${m.length} input: ${m.map((id) => VAR[id].label).join(', ')}`, members: m, x: 0, y: 0, w: W_IN, h: H_IN })
      for (const id of m) nodeOf[id] = groupId(g)
    }
  }
  // non-input: lajur × tingkat
  const rest = VARS.filter((v) => v.kind !== 'input' && show(v.id))
  const depthsUsed = [...new Set(rest.map((v) => v.depth))].sort((a, b) => a - b)
  const xIndex = Object.fromEntries(depthsUsed.map((d, i) => [d, i]))
  const lanesUsed = [...new Set(rest.map((v) => v.lane))].sort((a, b) => a - b)
  const x0 = W_IN + GAP_X * 1.5
  const lanes: { name: string; y: number; h: number }[] = []
  const nodes: GNode[] = [...inNodes]
  let y = 0
  for (const lane of lanesUsed) {
    const inLane = rest.filter((v) => v.lane === lane)
    const cells = new Map<number, VarDef[]>()
    for (const v of inLane) cells.set(v.depth, [...(cells.get(v.depth) ?? []), v])
    const rows = Math.max(...[...cells.values()].map((c) => c.length))
    const laneH = LANE_HEAD + rows * (H + GAP_Y) + LANE_PAD
    for (const [d, list] of cells) {
      list.forEach((v, i) => {
        nodes.push({ id: v.id, label: v.label, sub: v.symbol ?? v.id, kind: v.kind, desc: v.desc, members: [v.id], x: x0 + xIndex[d] * (W + GAP_X), y: y + LANE_HEAD + i * (H + GAP_Y), w: W, h: H })
        nodeOf[v.id] = v.id
      })
    }
    lanes.push({ name: LANES[lane], y, h: laneH })
    y += laneH
  }
  // kolom input, dirapatkan ke tengah tinggi lajur bila lebih pendek
  const inH = inNodes.length * (H_IN + GAP_Y)
  const inTop = LANE_HEAD + Math.max(0, (y - inH - LANE_HEAD) / 2)
  inNodes.forEach((n, i) => (n.y = inTop + i * (H_IN + GAP_Y)))
  const width = x0 + depthsUsed.length * (W + GAP_X)
  const height = Math.max(y, inTop + inH) + 8
  // sisi (dedupe untuk kelompok input)
  const edgeSet = new Set<string>()
  const edges: { from: string; to: string; fromVars: string[]; toVar: string }[] = []
  for (const v of rest) {
    for (const d of v.deps) {
      if (!show(d) || !nodeOf[d]) continue
      const key = `${nodeOf[d]}>${v.id}`
      if (edgeSet.has(key)) {
        edges.find((e) => e.from === nodeOf[d] && e.to === v.id)!.fromVars.push(d)
        continue
      }
      edgeSet.add(key)
      edges.push({ from: nodeOf[d], to: v.id, fromVars: [d], toVar: v.id })
    }
  }
  return { nodes, edges, lanes, width, height, x0 }
}

export default function S12PetaVariabel() {
  const { trace, showTrace, traceOpen, toggleTrace, mapWide, setMapWide } = usePlanner()
  const [mode, setMode] = useState<Mode>('ringkas')
  const [onlyChain, setOnlyChain] = useState(false)
  const [view, setView] = useState<View>({ x: 16, y: 16, z: 0.8 })
  const [grabbing, setGrabbing] = useState(false)
  const vpRef = useRef<HTMLDivElement>(null)
  const drag = useRef<{ id: number; sx: number; sy: number; vx: number; vy: number; moved: boolean } | null>(null)
  const suppressClick = useRef(false)
  const [query, setQuery] = useState('')
  const sel = VAR[trace.id] ? trace.id : null
  const up = useMemo(() => (sel ? upstream(sel) : new Set<string>()), [sel])
  const down = useMemo(() => (sel ? downstream(sel) : new Set<string>()), [sel])
  const visible = useMemo(() => (onlyChain && sel ? new Set([sel, ...up, ...down]) : null), [onlyChain, sel, up, down])
  const layout = useMemo(() => buildLayout(mode, visible), [mode, visible])
  const byId = useMemo(() => Object.fromEntries(layout.nodes.map((n) => [n.id, n])), [layout])

  // ── pan & zoom ────────────────────────────────────────────────
  const zoomAt = useCallback((factor: number, cx?: number, cy?: number) => {
    const el = vpRef.current
    if (!el) return
    const px = cx ?? el.clientWidth / 2
    const py = cy ?? el.clientHeight / 2
    setView((v) => {
      const z = clampZ(v.z * factor)
      const k = z / v.z
      return { z, x: px - (px - v.x) * k, y: py - (py - v.y) * k }
    })
  }, [])
  const fit = useCallback(() => {
    const el = vpRef.current
    if (!el) return
    const z = clampZ(Math.min((el.clientWidth - 32) / layout.width, (el.clientHeight - 32) / layout.height))
    setView({ z, x: (el.clientWidth - layout.width * z) / 2, y: 16 })
  }, [layout])
  useEffect(() => {
    const el = vpRef.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const r = el.getBoundingClientRect()
      if (e.ctrlKey || e.metaKey || Math.abs(e.deltaY) >= Math.abs(e.deltaX)) zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top)
      else setView((v) => ({ ...v, x: v.x - e.deltaX }))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [zoomAt])
  // "hanya rantai terpilih" mengubah ukuran graf -> paskan ulang
  useEffect(() => {
    if (onlyChain) fit()
  }, [onlyChain, fit])
  // simpul terpilih di luar layar -> geser ke tengah
  useEffect(() => {
    const el = vpRef.current
    const n = sel ? byId[sel] : undefined
    if (!el || !n) return
    setView((v) => {
      const sx = v.x + n.x * v.z
      const sy = v.y + n.y * v.z
      const inside = sx >= 0 && sy >= 0 && sx + n.w * v.z <= el.clientWidth && sy + n.h * v.z <= el.clientHeight
      if (inside) return v
      return { ...v, x: el.clientWidth / 2 - (n.x + n.w / 2) * v.z, y: el.clientHeight / 2 - (n.y + n.h / 2) * v.z }
    })
  }, [sel, byId])
  const onPointerDown = (e: RPointerEvent) => {
    if (e.button !== 0) return
    drag.current = { id: e.pointerId, sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y, moved: false }
  }
  const onPointerMove = (e: RPointerEvent) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    const dx = e.clientX - d.sx
    const dy = e.clientY - d.sy
    if (!d.moved && Math.hypot(dx, dy) < 4) return
    if (!d.moved) {
      d.moved = true
      setGrabbing(true)
      vpRef.current?.setPointerCapture(e.pointerId)
    }
    setView((v) => ({ ...v, x: d.vx + dx, y: d.vy + dy }))
  }
  const onPointerUp = (e: RPointerEvent) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    suppressClick.current = d.moved
    drag.current = null
    setGrabbing(false)
  }

  // laci yang sudah ditutup tetap tertutup saat memilih simpul; rincian tampil lagi bila laci dibuka
  const select = (id: string) => showTrace(id, trace.ctx, undefined, { open: false })
  const q = query.trim().toLowerCase()
  const matches = q ? VARS.filter((v) => v.label.toLowerCase().includes(q) || v.id.includes(q) || (v.symbol ?? '').toLowerCase().includes(q)).slice(0, 8) : []

  const role = (n: GNode): 'sel' | 'up' | 'down' | 'dim' | 'none' => {
    if (!sel) return 'none'
    if (n.members.includes(sel)) return 'sel'
    if (n.members.some((m) => up.has(m))) return 'up'
    if (n.members.some((m) => down.has(m))) return 'down'
    return 'dim'
  }

  const nCount = { input: 0, derived: 0, other: 0 }
  for (const v of VARS) {
    if (v.kind === 'input') nCount.input++
    else if (v.kind === 'derived') nCount.derived++
    else nCount.other++
  }

  return (
    <>
      <ScreenHeader
        step={12}
        kind="telusur"
        title="Peta variabel"
        lead={`${VARS.length} variabel registry (${nCount.input} input, ${nCount.derived} turunan, ${nCount.other} keputusan/metrik/objektif). Klik simpul untuk menyorot hulu dan hilirnya; rincian tampil di laci jejak.`}
      />

      <div className="flex flex-col gap-3 border-y border-garis py-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="w-24 text-[13px] font-medium text-abu">Interaksi</span>
          {INTERACTIONS.map((it) => (
            <button
              key={it.id}
              type="button"
              title={it.label}
              onClick={() => select(it.start)}
              className={`h-7 cursor-pointer rounded-badge border px-2 text-[13px] ${sel === it.start ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}
            >
              <span className="font-mono">{it.id}</span> {it.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="w-24 text-[13px] font-medium text-abu">Tampilan</span>
          <span className="flex rounded-kontrol border border-garis">
            {(['ringkas', 'rinci'] as const).map((m) => (
              <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)} className={`h-8 cursor-pointer border-0 px-3 text-[13px] ${mode === m ? 'bg-hitam text-white' : 'bg-white'}`}>
                input {m}
              </button>
            ))}
          </span>
          <label className="flex cursor-pointer items-center gap-1.5 text-[13px]">
            <input type="checkbox" checked={onlyChain} onChange={(e) => setOnlyChain(e.target.checked)} disabled={!sel} />
            hanya rantai terpilih
          </label>
          <span className="flex items-center gap-1">
            <span className="text-[13px] text-abu">Zoom</span>
            <button type="button" aria-label="Perkecil" onClick={() => zoomAt(1 / 1.25)} className="h-8 w-8 cursor-pointer rounded-kontrol border border-garis bg-white font-mono text-[13px] hover:border-hitam">−</button>
            <button type="button" title="Kembali ke 100 %" onClick={() => zoomAt(1 / view.z)} className="h-8 w-14 cursor-pointer rounded-kontrol border border-garis bg-white font-mono text-[13px] hover:border-hitam">{Math.round(view.z * 100)}%</button>
            <button type="button" aria-label="Perbesar" onClick={() => zoomAt(1.25)} className="h-8 w-8 cursor-pointer rounded-kontrol border border-garis bg-white font-mono text-[13px] hover:border-hitam">+</button>
            <button type="button" onClick={fit} className="h-8 cursor-pointer rounded-kontrol border border-garis bg-white px-2 text-[13px] hover:border-hitam">Paskan</button>
          </span>
          <span className="flex items-center gap-1">
            <span className="text-[13px] text-abu">Ruang</span>
            <button type="button" aria-pressed={mapWide} title="Sembunyikan/tampilkan menu langkah di kiri (hanya di layar ini)" onClick={() => setMapWide(!mapWide)} className={`h-8 cursor-pointer rounded-kontrol border px-2 text-[13px] ${mapWide ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}>
              {mapWide ? '⇥ Menu' : '⇤ Menu'}
            </button>
            <button type="button" aria-pressed={!traceOpen} title="Tutup/buka laci jejak di kanan; memilih simpul tidak membuka laci yang sudah ditutup" onClick={toggleTrace} className={`h-8 cursor-pointer rounded-kontrol border px-2 text-[13px] ${!traceOpen ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}>
              {traceOpen ? 'Laci ⇥' : 'Laci ⇤'}
            </button>
          </span>
          <span className="relative grow">
            <input
              aria-label="Cari variabel"
              placeholder="cari variabel: RTD, payload, voyage.freq …"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && matches[0]) {
                  select(matches[0].id)
                  setQuery('')
                }
                if (e.key === 'Escape') setQuery('')
              }}
              className="h-8 w-full rounded-kontrol border border-garis px-2 text-[13px] outline-none focus:border-biru"
            />
            {matches.length > 0 && (
              <span className="absolute top-9 right-0 left-0 z-20 flex flex-col border border-hitam bg-white">
                {matches.map((m) => (
                  <button key={m.id} type="button" onClick={() => { select(m.id); setQuery('') }} className="flex cursor-pointer items-center gap-2 border-0 bg-white px-2 py-1.5 text-left text-[13px] hover:bg-permukaan">
                    <span className="grow">{m.label}</span>
                    <span className="font-mono text-abu">{m.id}</span>
                  </button>
                ))}
              </span>
            )}
          </span>
          {sel && <Button size="sm" variant="tipis" onClick={() => { select('obj.npv'); setOnlyChain(false) }}>Ke objektif</Button>}
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <span className="w-24 text-[13px] font-medium text-abu">Legenda</span>
          <span className="flex items-center gap-1.5 text-[13px] text-abu"><InputMark />input kasus</span>
          <span className="flex items-center gap-1.5 text-[13px] text-abu"><span className="inline-block h-2.5 w-3.5 border border-dashed border-hitam" />keputusan</span>
          <span className="flex items-center gap-1.5 text-[13px] text-abu"><span className="inline-block h-2.5 w-3.5 border border-garis" />turunan · metrik</span>
          <span className="flex items-center gap-1.5 text-[13px] text-abu"><span className="inline-block h-2.5 w-3.5 bg-hitam" />objektif</span>
          <Legend items={[{ color: '#56BDCC', label: 'hulu (mempengaruhi)' }, { color: '#000000', label: 'hilir (dipengaruhi)', outline: true }]} />
          <span className="text-[13px] text-abu">bingkai biru = terpilih</span>
        </div>
      </div>

      <div
        ref={vpRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onClickCapture={(e) => {
          if (suppressClick.current) {
            e.stopPropagation()
            e.preventDefault()
            suppressClick.current = false
          }
        }}
        onDoubleClick={(e) => {
          if ((e.target as HTMLElement).closest('button')) return
          const r = vpRef.current!.getBoundingClientRect()
          zoomAt(1.5, e.clientX - r.left, e.clientY - r.top)
        }}
        className={`relative w-full touch-none overflow-hidden border-y border-garis select-none ${grabbing ? 'cursor-grabbing' : 'cursor-grab'}`}
        style={{ height: 'calc(100vh - 160px)', minHeight: 420, backgroundImage: 'radial-gradient(#DEDEDE 1px, transparent 1px)', backgroundSize: `${24 * view.z}px ${24 * view.z}px`, backgroundPosition: `${view.x}px ${view.y}px` }}
      >
        <span className="pointer-events-none absolute right-2 bottom-2 z-30 bg-white/90 px-1.5 text-[13px] text-abu">seret = geser · roda = zoom · klik ganda = perbesar</span>
        <div className="absolute top-0 left-0 origin-top-left" style={{ transform: `translate(${view.x}px, ${view.y}px) scale(${view.z})` }}>
          <div className="relative" style={{ width: layout.width, height: layout.height }}>
            {layout.lanes.map((l, i) => (
              <div key={l.name} className={`absolute right-0 ${i > 0 ? 'border-t border-garis' : ''}`} style={{ left: layout.x0 - GAP_X / 2, top: l.y, height: l.h }}>
                <span className="absolute top-1 left-2 z-10 bg-white pr-1 text-[13px] font-medium text-abu">{l.name}</span>
              </div>
            ))}
            <span className="absolute top-1 left-0 text-[13px] font-medium text-abu">Input kasus</span>
            <svg className="pointer-events-none absolute inset-0" width={layout.width} height={layout.height} aria-hidden>
              {layout.edges.map((e) => {
                const a = byId[e.from]
                const b = byId[e.to]
                if (!a || !b) return null
                const x1 = a.x + a.w
                const y1 = a.y + a.h / 2
                const x2 = b.x
                const y2 = b.y + b.h / 2
                const mx = (x1 + x2) / 2
                let stroke = '#DEDEDE'
                let width = 1
                let opacity = sel ? 0.35 : 1
                if (sel) {
                  const fromIn = e.fromVars.some((f) => f === sel || up.has(f))
                  const toIn = e.toVar === sel || up.has(e.toVar)
                  const fromDown = e.fromVars.some((f) => f === sel || down.has(f))
                  const toDown = down.has(e.toVar)
                  if (fromIn && toIn) { stroke = '#56BDCC'; width = 2; opacity = 1 }
                  else if (fromDown && toDown) { stroke = '#000000'; width = 1.5; opacity = 1 }
                }
                return <path key={`${e.from}>${e.to}`} d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} fill="none" stroke={stroke} strokeWidth={width} opacity={opacity} />
              })}
            </svg>
            {layout.nodes.map((n) => {
              const r = role(n)
              const base = n.kind === 'objective' ? 'bg-hitam text-white border-hitam' : n.kind === 'decision' ? 'bg-white border-dashed border-hitam' : 'bg-white border-garis'
              const hl = r === 'up' ? '!bg-biru !text-hitam' : r === 'down' ? '!bg-permukaan !border-hitam !text-hitam' : ''
              return (
                <button
                  key={n.id}
                  type="button"
                  data-node={n.id}
                  title={n.kind === 'group' ? `${n.label} — ${n.desc}. Klik untuk tampilan rinci.` : `${n.label} (${n.kind === 'input' ? 'input kasus' : KIND_LABEL[n.kind]}): ${n.desc}`}
                  onClick={() => (n.kind === 'group' ? setMode('rinci') : select(n.id))}
                  className={`absolute flex cursor-pointer flex-col justify-center gap-0.5 overflow-hidden rounded-badge border px-2 text-left ${base} ${hl} ${r === 'dim' ? 'opacity-30' : ''} ${r === 'sel' ? 'outline-2 outline-offset-1 outline-biru' : ''}`}
                  style={{ left: n.x, top: n.y, width: n.w, height: n.h }}
                >
                  <span className="flex w-full items-center gap-1.5">
                    {(n.kind === 'input' || n.kind === 'group') && <InputMark />}
                    <span className="truncate text-[13px] leading-4">{n.label}</span>
                    {n.kind === 'group' && <span className="ml-auto font-mono text-[13px] text-abu">{n.members.length}</span>}
                  </span>
                  {n.h > H_IN && <span className={`truncate font-mono text-[13px] leading-4 ${n.kind === 'objective' && r !== 'up' && r !== 'down' ? 'text-white' : 'text-abu'}`}>{n.sub}</span>}
                </button>
              )
            })}
          </div>
        </div>
      </div>
      <Note>
        Posisi horizontal = tingkat dependensi (input di kiri, objektif di kanan). Registry dibuat dari <span className="font-mono">engine/src/tpt_engine/registry.py</span>; semua nilai masih placeholder. Mode ringkas menggabungkan input per entitas, klik kelompok untuk merinci.
      </Note>
    </>
  )
}
