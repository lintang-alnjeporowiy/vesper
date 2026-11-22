import type { ReactNode } from 'react'
// Grafik sederhana berbasis div/SVG sesuai wireframe 2a. Recharts/ECharts (SPEC §9.1)
// bisa menggantikan ini setelah engine mengirim data nyata.
export const C = { hitam: '#000000', biru: '#56BDCC', hijau: '#90B148', merah: '#AA3A36', abu: '#9A9A9A', garis: '#DEDEDE' }

/** Kolom bertumpuk vertikal. series[i] = nilai per kolom; urutan bawah→atas. */
export function ColumnStack(props: { columns: number[][]; colors: string[]; height?: number; labels?: string[]; yUnit?: string; xUnit?: string }) {
  const h = props.height ?? 220
  const max = Math.max(1e-9, ...props.columns.map((c) => c.reduce((a, b) => a + b, 0)))
  const fmt = (v: number) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(v)
  return (
    <div className="flex w-full flex-col gap-2">
      {props.yUnit && <span className="font-mono text-[13px] text-abu">↑ {props.yUnit}</span>}
      <div className="flex w-full items-stretch gap-2">
      {props.yUnit && (
        <div className="flex w-12 shrink-0 flex-col justify-between text-right font-mono text-[13px] text-abu" style={{ height: h }}>
          <span>{fmt(max)}</span>
          <span>{fmt(max / 2)}</span>
          <span>0</span>
        </div>
      )}
      <div className="flex min-w-0 grow items-end gap-1.5 border-b border-l border-hitam px-1" style={{ height: h }}>
        {props.columns.map((col, i) => {
          const total = col.reduce((a, b) => a + b, 0)
          return (
            <div key={i} className="flex grow basis-0 flex-col-reverse gap-px" title={`kolom ${i + 1}: ${total.toFixed(2)}`}>
              {total === 0 ? (
                <div className="h-0.5 bg-garis" />
              ) : (
                col.map((v, j) => (v > 0 ? <div key={j} style={{ height: (v / max) * (h - 8), background: props.colors[j] }} /> : null))
              )}
            </div>
          )
        })}
      </div>
      </div>
      {props.labels && (
        <div className={`flex justify-between px-1 font-mono text-[13px] text-abu ${props.yUnit ? 'ml-14' : ''}`}>
          {props.labels.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      )}
      {props.xUnit && <span className="self-end font-mono text-[13px] text-abu">{props.xUnit} →</span>}
    </div>
  )
}

/** Batang horizontal bertumpuk dengan label kiri dan total kanan. */
export function BarRows(props: { rows: { label: string; parts: number[] | null; total?: ReactNode; emptyText?: string; strong?: boolean }[]; colors: string[]; width?: number; onSegment?: (label: string, j: number, value: number) => void; segmentTitle?: (label: string, j: number, value: number) => string; xUnit?: string }) {
  const w = props.width ?? 560
  const max = Math.max(1e-9, ...props.rows.map((r) => (r.parts ? r.parts.reduce((a, b) => a + b, 0) : 0)))
  return (
    <div className="flex w-full flex-col gap-2">
      {props.rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <span className={`w-[150px] shrink-0 text-[13px] ${r.parts ? 'text-hitam' : 'text-abu'} ${r.strong ? 'font-medium' : ''}`}>{r.label}</span>
          {r.parts ? (
            <>
              <span className="flex gap-px" style={{ width: w }}>
                {r.parts.map((v, j) => (
                  props.onSegment ? (
                    <button key={j} type="button" title={props.segmentTitle?.(r.label, j, v)} onClick={() => props.onSegment!(r.label, j, v)} className="h-4 cursor-pointer border-0 p-0 hover:opacity-80" style={{ width: (v / max) * w, background: props.colors[j] }} />
                  ) : (
                    <span key={j} className="h-4" style={{ width: (v / max) * w, background: props.colors[j] }} />
                  )
                ))}
              </span>
              <span className="font-mono text-[13px] text-abu">{r.total}</span>
            </>
          ) : (
            <span className="text-[13px] text-abu">{r.emptyText}</span>
          )}
        </div>
      ))}
      {props.xUnit && (
        <div className="flex items-start gap-3">
          <span className="w-[150px] shrink-0" />
          <span className="relative h-9 border-t border-hitam" style={{ width: w }}>
            {[0, 0.25, 0.5, 0.75, 1].map((f) => (
              <span key={f} className="absolute top-0 flex flex-col items-center font-mono text-[13px] text-abu" style={{ left: f * w, transform: f === 0 ? 'none' : f === 1 ? 'translateX(-100%)' : 'translateX(-50%)', alignItems: f === 0 ? 'flex-start' : f === 1 ? 'flex-end' : 'center' }}>
                <span className="h-1 w-px bg-hitam" />
                {new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(max * f)}
              </span>
            ))}
          </span>
          <span className="pt-1 font-mono text-[13px] text-abu">{props.xUnit}</span>
        </div>
      )}
    </div>
  )
}

/** Titik pada sumbu x (log-ish ditentukan pemanggil) dan y. */
export function DotPlot(props: { points: { x: number; y: number; color: string; size?: number; outline?: boolean; label?: string }[]; height?: number; xLabels?: string[]; yInvert?: boolean }) {
  const h = props.height ?? 200
  const xs = props.points.map((p) => p.x)
  const ys = props.points.map((p) => p.y)
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)]
  return (
    <div className="flex w-full flex-col gap-2">
      <div className="relative w-full border-b border-l border-hitam" style={{ height: h }}>
        {props.points.map((p, i) => {
          const s = p.size ?? 10
          const left = x1 === x0 ? 50 : 4 + ((p.x - x0) / (x1 - x0)) * 92
          const top = y1 === y0 ? 50 : 8 + ((y1 - p.y) / (y1 - y0)) * 80
          return (
            <span
              key={i}
              title={p.label}
              className="absolute rounded-full"
              style={{ left: `${left}%`, top: `${top}%`, width: s, height: s, marginLeft: -s / 2, marginTop: -s / 2, ...(p.outline ? { border: `1.5px solid ${p.color}`, background: '#fff' } : { background: p.color }) }}
            />
          )
        })}
      </div>
      {props.xLabels && (
        <div className="flex w-full justify-between font-mono text-[13px] text-abu">
          {props.xLabels.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export function Tornado(props: { rows: { label: string; down: number; up: number }[]; halfWidth?: number }) {
  const hw = props.halfWidth ?? 240
  const max = Math.max(...props.rows.map((r) => Math.max(r.down, r.up)))
  return (
    <div className="flex w-full flex-col gap-2">
      {props.rows.map((r) => (
        <div key={r.label} className="flex items-center">
          <span className="w-[220px] shrink-0 text-[13px]">{r.label}</span>
          <span className="flex justify-end" style={{ width: hw }}>
            <span className="h-4 bg-hijau" style={{ width: (r.down / max) * hw }} />
          </span>
          <span className="h-6 w-px bg-hitam" />
          <span className="flex" style={{ width: hw }}>
            <span className="h-4 bg-merah" style={{ width: (r.up / max) * hw }} />
          </span>
          <span className="pl-3 font-mono text-[13px] text-abu">
            {r.down === r.up ? `±${r.down.toLocaleString('id-ID')} %` : `−${r.down.toLocaleString('id-ID')} / +${r.up.toLocaleString('id-ID')} %`}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Profil batimetri berskala: sumbu x = jarak dari garis pantai (proporsional), kedalaman ke bawah.
 * `required` = garis kedalaman perlu (putus-putus merah); `marks` = garis tegak (mis. ujung trestle).
 */
export function BathyProfile(props: {
  points: { distance_m: number; depth_m: number }[]
  required?: { depth: number; label: string }
  marks?: { at: number; label: string }[]
  highlight?: number
  width?: number
  height?: number
}) {
  const W = props.width ?? 520
  const H = props.height ?? 220
  const L = 44
  const R = 12
  const T = 22
  const B = 26
  const pts = [...props.points].filter((p) => Number.isFinite(p.distance_m) && Number.isFinite(p.depth_m)).sort((a, b) => a.distance_m - b.distance_m)
  if (pts.length < 2) return <p className="m-0 text-[13px] text-abu">Isi minimal 2 titik untuk menggambar profil.</p>
  const maxX = Math.max(...pts.map((p) => p.distance_m), ...(props.marks ?? []).map((m) => m.at))
  const maxY = Math.max(...pts.map((p) => p.depth_m), props.required?.depth ?? 0) * 1.1 || 1
  const x = (d: number) => L + (d / (maxX || 1)) * (W - L - R)
  const y = (z: number) => T + (z / maxY) * (H - T - B)
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.distance_m).toFixed(1)},${y(p.depth_m).toFixed(1)}`).join(' ')
  const area = `${line} L${x(pts[pts.length - 1].distance_m).toFixed(1)},${H - B} L${x(pts[0].distance_m).toFixed(1)},${H - B} Z`
  const yTicks = [0, maxY / 2, maxY / 1.1].map((v) => Math.round(v))
  const xTicks = [0, maxX / 2, maxX].map((v) => Math.round(v))
  const fmt = (v: number) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 }).format(v)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Profil batimetri tapak" className="font-mono" style={{ maxWidth: W }}>
      {/* muka air & sumbu */}
      <line x1={L} x2={W - R} y1={T} y2={T} stroke={C.hitam} />
      <text x={L} y={T - 7} fontSize={13} fill={C.abu}>muka air · 0 m LWS</text>
      {yTicks.map((v) => (
        <g key={`y${v}`}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={C.garis} strokeDasharray={v === 0 ? undefined : '2 3'} />
          <text x={L - 6} y={y(v) + 4} fontSize={13} fill={C.abu} textAnchor="end">{fmt(v)}</text>
        </g>
      ))}
      {xTicks.map((v, i) => (
        <text key={`x${v}`} x={x(v)} y={H - 8} fontSize={13} fill={C.abu} textAnchor={i === 0 ? 'start' : i === 2 ? 'end' : 'middle'}>{`${fmt(v)} m`}</text>
      ))}
      {/* air di atas dasar laut */}
      <path d={area} fill={C.biru} opacity={0.25} />
      <path d={line} fill="none" stroke={C.biru} strokeWidth={2} />
      {pts.map((p, i) => (
        <circle key={i} cx={x(p.distance_m)} cy={y(p.depth_m)} r={i === props.highlight ? 5 : 3} fill={i === props.highlight ? C.hitam : C.biru}>
          <title>{`${fmt(p.distance_m)} m dari pantai · kedalaman ${fmt(p.depth_m)} m`}</title>
        </circle>
      ))}
      {props.required && (
        <g>
          <line x1={L} x2={W - R} y1={y(props.required.depth)} y2={y(props.required.depth)} stroke={C.merah} strokeDasharray="6 4" strokeWidth={1.5} />
          <text x={L + 6} y={y(props.required.depth) - 6} fontSize={13} fill={C.merah}>{props.required.label}</text>
        </g>
      )}
      {(props.marks ?? []).map((m, i) => {
        const right = x(m.at) > W * 0.6
        return (
          <g key={m.label}>
            <line x1={x(m.at)} x2={x(m.at)} y1={T} y2={H - B} stroke={C.hitam} strokeWidth={1.5} />
            <text x={x(m.at) + (right ? -4 : 4)} y={T + 16 + i * 16} fontSize={13} fill={C.hitam} textAnchor={right ? 'end' : 'start'}>{m.label}</text>
          </g>
        )
      })}
    </svg>
  )
}

/**
 * Konvergensi MILP (branch-and-bound): incumbent (solusi terbaik, turun) dan batas bawah
 * (dual bound, naik) terhadap waktu. Keduanya bertemu = optimal (gap 0 %).
 */
export function ConvergenceChart(props: { points: { t: number; incumbent: number | null; bound: number }[]; yUnit: string; xUnit: string; width?: number; height?: number }) {
  const W = props.width ?? 860
  const H = props.height ?? 240
  const L = 64
  const R = 16
  const T = 24
  const B = 40
  const pts = props.points
  const vals = pts.flatMap((p) => [p.bound, ...(p.incumbent === null ? [] : [p.incumbent])])
  const y0 = Math.min(...vals)
  const y1 = Math.max(...vals)
  const pad = (y1 - y0) * 0.08 || 1
  const lo = y0 - pad
  const hi = y1 + pad
  const tMax = Math.max(...pts.map((p) => p.t)) || 1
  const x = (t: number) => L + (t / tMax) * (W - L - R)
  const y = (v: number) => T + ((hi - v) / (hi - lo)) * (H - T - B)
  const step = (key: 'incumbent' | 'bound') => {
    const seq = pts.filter((p) => p[key] !== null)
    return seq.map((p, i) => (i === 0 ? `M${x(p.t)},${y(p[key]!)}` : `H${x(p.t)} V${y(p[key]!)}`)).join(' ')
  }
  const fmt = (v: number, d = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: d }).format(v)
  const last = pts[pts.length - 1]
  const firstInc = pts.find((p) => p.incumbent !== null)
  const yTicks = [lo + pad, (lo + hi) / 2, hi - pad]
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Grafik konvergensi optimasi" className="font-mono" style={{ maxWidth: W }}>
      <text x={0} y={T - 10} fontSize={13} fill={C.abu}>{`↑ ${props.yUnit}`}</text>
      {yTicks.map((v) => (
        <g key={v}>
          <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={C.garis} strokeDasharray="2 3" />
          <text x={L - 8} y={y(v) + 4} fontSize={13} fill={C.abu} textAnchor="end">{fmt(v, 2)}</text>
        </g>
      ))}
      <line x1={L} x2={L} y1={T} y2={H - B} stroke={C.hitam} />
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={C.hitam} />
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <text key={f} x={x(f * tMax)} y={H - B + 18} fontSize={13} fill={C.abu} textAnchor={f === 0 ? 'start' : f === 1 ? 'end' : 'middle'}>{fmt(f * tMax)}</text>
      ))}
      <text x={W - R} y={H - 4} fontSize={13} fill={C.abu} textAnchor="end">{props.xUnit} →</text>
      <path d={step('bound')} fill="none" stroke={C.biru} strokeWidth={2} />
      <path d={step('incumbent')} fill="none" stroke={C.hitam} strokeWidth={2} />
      {pts.filter((p) => p.incumbent !== null).map((p, i) => (
        <circle key={i} cx={x(p.t)} cy={y(p.incumbent!)} r={3} fill={C.hitam}>
          <title>{`t = ${fmt(p.t)} · incumbent ${fmt(p.incumbent!, 3)} · bound ${fmt(p.bound, 3)} · gap ${fmt(((p.incumbent! - p.bound) / p.incumbent!) * 100, 2)} %`}</title>
        </circle>
      ))}
      {firstInc && <text x={x(firstInc.t) + 6} y={y(firstInc.incumbent!) - 8} fontSize={13} fill={C.hitam}>solusi layak pertama</text>}
      {last && last.incumbent !== null && (
        <text x={x(last.t) - 4} y={y(last.incumbent) - 10} fontSize={13} fill={C.hitam} textAnchor="end">{`gap ${fmt(((last.incumbent - last.bound) / last.incumbent) * 100, 2)} %`}</text>
      )}
    </svg>
  )
}
