import { useState } from 'react'
import type { BathyPoint, KekSite } from '../api/case'
import { BathyProfile } from '../charts/charts'
import { num, parseNum } from '../lib/format'
import { REQUIRED_DEPTH_PH } from '../mock/placeholders'
import { usePlanner } from '../store'
import { Tv } from './trace'
import { Badge, Button, EditNum, InputMark, Note } from './ui'

const SOURCE_LABEL: Record<NonNullable<KekSite['bathymetry_source']>, string> = {
  survei: 'survei',
  peta_navigasi: 'peta navigasi',
  dummy: 'dummy (asumsi)',
}

/** Baca tabel tempelan Excel/CSV: dua kolom jarak & kedalaman, pemisah tab, titik koma, atau spasi. */
function parseBathyTable(text: string): { points: BathyPoint[]; skipped: number } {
  const points: BathyPoint[] = []
  let skipped = 0
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim()
    if (!line) continue
    const cells = line.split(/\t|;|\s{2,}|\s(?=[\d-])/).map((c) => c.trim()).filter(Boolean)
    const a = cells.length >= 2 ? parseNum(cells[0]) : null
    const b = cells.length >= 2 ? parseNum(cells[1]) : null
    if (a === null || b === null) {
      skipped++ // baris judul atau tidak terbaca
      continue
    }
    points.push({ refs: {}, distance_m: a, depth_m: Math.abs(b) })
  }
  return { points, skipped }
}

/** Masalah urutan/data yang membuat Case tidak valid (validator: jarak harus naik). */
function issues(pts: BathyPoint[]): Set<number> {
  const bad = new Set<number>()
  pts.forEach((p, i) => {
    if (p.distance_m < 0 || p.depth_m < 0) bad.add(i)
    if (i > 0 && p.distance_m <= pts[i - 1].distance_m) bad.add(i)
  })
  return bad
}

export function BathyEditor() {
  const site = usePlanner((s) => s.caseData.kek_site)
  const changed = usePlanner((s) => Object.keys(s.dirty).some((k) => k.startsWith('kek_site.bathymetry')))
  const setInput = usePlanner((s) => s.setInput)
  const [sel, setSel] = useState<number | undefined>()
  const [paste, setPaste] = useState<string | null>(null)
  const [pasteMsg, setPasteMsg] = useState<string | null>(null)
  const pts = site.bathymetry
  const bad = issues(pts)
  const setPts = (next: BathyPoint[], label: string) => setInput(['kek_site', 'bathymetry'], next, label)
  const setCell = (i: number, key: 'distance_m' | 'depth_m', v: number) =>
    setPts(pts.map((p, j) => (j === i ? { ...p, [key]: Math.abs(v), refs: {} } : p)), `Batimetri titik ${i + 1}`)
  const addRow = () => {
    const last = pts[pts.length - 1]
    const step = pts.length > 1 ? last.distance_m - pts[pts.length - 2].distance_m : 50
    setPts([...pts, { refs: {}, distance_m: (last?.distance_m ?? 0) + step, depth_m: last?.depth_m ?? 0 }], 'Batimetri: tambah titik')
    setSel(pts.length)
  }
  const removeRow = (i: number) => {
    setPts(pts.filter((_, j) => j !== i), `Batimetri: hapus titik ${i + 1}`)
    setSel(undefined)
  }
  const sortRows = () => setPts([...pts].sort((a, b) => a.distance_m - b.distance_m), 'Batimetri: urutkan')
  const applyPaste = () => {
    const { points, skipped } = parseBathyTable(paste ?? '')
    if (points.length < 2) {
      setPasteMsg('Minimal 2 baris angka (jarak, kedalaman).')
      return
    }
    setPts(points, `Batimetri: tempel ${points.length} titik`)
    setPasteMsg(skipped ? `${points.length} titik dipakai, ${skipped} baris dilewati (judul/tidak terbaca).` : null)
    setPaste(null)
  }
  const unsorted = pts.some((p, i) => i > 0 && p.distance_m <= pts[i - 1].distance_m)
  const td = site.trestle_dredge
  const marks = [
    ...(td?.trestle_length_m ? [{ at: td.trestle_length_m, label: `trestle+keruk ${num(td.trestle_length_m)} m` }] : []),
    ...(site.trestle?.max_length_m ? [{ at: site.trestle.max_length_m, label: `trestle maks ${num(site.trestle.max_length_m)} m` }] : []),
  ]

  return (
    <div className="flex w-full gap-8">
      <div className="flex w-[300px] shrink-0 flex-col">
        <div className="flex items-center gap-2 pb-2">
          <span className="text-[13px] text-abu">Sumber</span>
          <select
            aria-label="Sumber batimetri"
            value={site.bathymetry_source ?? 'dummy'}
            onChange={(e) => setInput(['kek_site', 'bathymetry_source'], e.target.value, 'Sumber batimetri')}
            className="h-8 rounded-kontrol border border-garis bg-white px-2 text-[13px]"
          >
            {Object.entries(SOURCE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          {site.bathymetry_source === 'dummy' && <Badge kind="asumsi">asumsi</Badge>}
          {changed && <Badge kind="gugur">diubah</Badge>}
        </div>
        <div className="max-h-[360px] overflow-y-auto">
          <table className="w-full border-collapse text-sm">
            <thead className="sticky top-0 bg-white">
              <tr className="border-b border-hitam text-[13px] text-abu">
                <th className="w-8 py-2 text-left font-medium">#</th>
                <th className="py-2 text-left font-medium"><span className="inline-flex items-center gap-1"><InputMark />Jarak dari pantai, m</span></th>
                <th className="py-2 text-left font-medium"><span className="inline-flex items-center gap-1"><InputMark />Kedalaman, m</span></th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {pts.map((p, i) => (
                <tr
                  key={i}
                  onFocus={() => setSel(i)}
                  onMouseEnter={() => setSel(i)}
                  className={`border-t border-garis ${sel === i ? 'bg-permukaan shadow-[inset_3px_0_0_var(--color-biru)]' : ''}`}
                >
                  <td className={`py-1 pl-1 font-mono text-[13px] ${bad.has(i) ? 'text-merah' : 'text-abu'}`}>{i + 1}</td>
                  <td className="py-1"><EditNum value={p.distance_m} digits={0} mark={false} label={`Jarak titik ${i + 1}`} onChange={(v) => setCell(i, 'distance_m', v)} /></td>
                  <td className="py-1"><EditNum value={p.depth_m} digits={1} mark={false} label={`Kedalaman titik ${i + 1}`} onChange={(v) => setCell(i, 'depth_m', v)} /></td>
                  <td>
                    <button type="button" aria-label={`Hapus titik ${i + 1}`} disabled={pts.length <= 2} onClick={() => removeRow(i)} className="cursor-pointer border-0 bg-transparent text-abu hover:text-merah disabled:cursor-not-allowed disabled:opacity-30">×</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap gap-2 pt-3">
          <Button size="sm" variant="tipis" onClick={addRow}>+ Titik</Button>
          <Button size="sm" variant="tipis" onClick={() => { setPaste(''); setPasteMsg(null) }}>Tempel dari Excel</Button>
          {unsorted && <Button size="sm" onClick={sortRows}>Urutkan jarak</Button>}
        </div>
        {paste !== null && (
          <div className="flex flex-col gap-2 pt-3">
            <textarea
              aria-label="Tempel tabel batimetri"
              autoFocus
              rows={6}
              value={paste}
              onChange={(e) => setPaste(e.target.value)}
              placeholder={'jarak\tkedalaman\n0\t0\n12\t5\n50\t8,5'}
              className="w-full rounded-kontrol border border-garis p-2 font-mono text-[13px] outline-none focus:border-biru"
            />
            <span className="flex gap-2">
              <Button size="sm" variant="utama" onClick={applyPaste}>Ganti tabel</Button>
              <Button size="sm" variant="tipis" onClick={() => setPaste(null)}>Batal</Button>
            </span>
            <Note>Salin dua kolom (jarak dari pantai, kedalaman) dari Excel. Baris judul dilewati; kedalaman negatif dibaca sebagai positif.</Note>
          </div>
        )}
        {pasteMsg && <Note>{pasteMsg}</Note>}
        {bad.size > 0 && <p className="m-0 pt-2 text-[13px] text-merah">Jarak harus naik dari baris ke baris dan tidak boleh negatif (baris merah).</p>}
      </div>
      <div className="flex min-w-0 grow flex-col gap-2 border-l border-garis pl-8">
        <BathyProfile
          points={pts}
          highlight={sel}
          required={{ depth: REQUIRED_DEPTH_PH, label: `kedalaman perlu ${num(REQUIRED_DEPTH_PH, 1)} m · placeholder` }}
          marks={marks}
        />
        <Note>
          {pts.length} titik, sampai {num(pts[pts.length - 1]?.distance_m ?? 0)} m dari pantai. Garis merah = <Tv v="waterside.depth_req">kedalaman perlu</Tv> (placeholder sampai engine Tahap 8);
          titik tempat profil memotong garis ini menentukan panjang trestle (<Tv v="waterside.x_star">x*</Tv>). Arahkan kursor ke baris tabel untuk menyorot titiknya.
        </Note>
      </div>
    </div>
  )
}
