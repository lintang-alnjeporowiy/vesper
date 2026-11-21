// Grafik sederhana berbasis div/SVG sesuai wireframe 2a. Recharts/ECharts (SPEC §9.1)
// bisa menggantikan ini setelah engine mengirim data nyata.
export const C = { hitam: '#000000', biru: '#56BDCC', hijau: '#90B148', merah: '#AA3A36', abu: '#9A9A9A', garis: '#DEDEDE' }

/** Kolom bertumpuk vertikal. series[i] = nilai per kolom; urutan bawah→atas. */
export function ColumnStack(props: { columns: number[][]; colors: string[]; height?: number; labels?: string[] }) {
  const h = props.height ?? 220
  const max = Math.max(1e-9, ...props.columns.map((c) => c.reduce((a, b) => a + b, 0)))
  return (
    <div className="flex w-full flex-col gap-2">
      <div className="flex w-full items-end gap-1.5 border-b border-hitam px-1" style={{ height: h }}>
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
      {props.labels && (
        <div className="flex w-full justify-between px-1 font-mono text-[13px] text-abu">
          {props.labels.map((l) => (
            <span key={l}>{l}</span>
          ))}
        </div>
      )}
    </div>
  )
}

/** Batang horizontal bertumpuk dengan label kiri dan total kanan. */
export function BarRows(props: { rows: { label: string; parts: number[] | null; total?: string; emptyText?: string; strong?: boolean }[]; colors: string[]; width?: number }) {
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
                  <span key={j} className="h-4" style={{ width: (v / max) * w, background: props.colors[j] }} />
                ))}
              </span>
              <span className="font-mono text-[13px] text-abu">{r.total}</span>
            </>
          ) : (
            <span className="text-[13px] text-abu">{r.emptyText}</span>
          )}
        </div>
      ))}
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

/** Profil kedalaman: batang turun dari garis pantai. */
export function Bathymetry(props: { points: { distance_m: number; depth_m: number }[]; marks: number[]; required: number }) {
  const maxD = Math.max(...props.points.map((p) => p.depth_m))
  const h = 110
  return (
    <div className="flex w-full flex-col gap-2">
      <div className="h-px w-full bg-hitam" />
      <div className="flex w-full items-start gap-0.5">
        {props.points.map((p) => (
          <span
            key={p.distance_m}
            title={`${p.distance_m} m · ${p.depth_m} m`}
            className="grow basis-0"
            style={{ height: Math.max(2, (p.depth_m / maxD) * h), background: props.marks.includes(p.distance_m) ? C.hitam : C.biru }}
          />
        ))}
      </div>
    </div>
  )
}
