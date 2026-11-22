import { useState } from 'react'
import type { Case } from '../api/case'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { usePlanner } from '../store'
import { Tv } from './trace'
import { EditNum, Note, Tabs } from './ui'

type Row = Case['tariffs']['classes'][number]
type Scope = 'foreign' | 'domestic'

const CLASS_LABEL = (k: string) => (k === 'utama' ? 'Utama' : `Kelas ${k}`)

function Cell(props: { path: (string | number)[]; label: string; digits?: number }) {
  const f = useField(props.path, props.label)
  if (f.value === undefined || f.value === null) return <span className="font-mono text-abu">–</span>
  return <EditNum {...f} mark={false} digits={props.digits} />
}

/** Kolom per lingkup (luar/dalam negeri): [kunci path, kepala kolom, satuan, digit, id registry]. */
function columns(scope: Scope): { path: (string | number)[]; head: string; unit: string; digits: number; v: string }[] {
  const f = scope === 'foreign'
  const cur = f ? 'USD' : 'Rp'
  return [
    { path: [f ? 'labuh_foreign_usd_per_gt' : 'labuh_domestic_rp_per_gt'], head: 'Labuh', unit: `${cur}/GT/kunjungan`, digits: f ? 3 : 0, v: 'in.tariff.labuh' },
    { path: [f ? 'pandu_foreign_fixed_usd' : 'pandu_domestic_fixed_rp'], head: 'Pandu tetap', unit: `${cur}/gerakan`, digits: 0, v: 'in.tariff.pandu' },
    { path: [f ? 'pandu_foreign_var_usd_per_gt' : 'pandu_domestic_var_rp_per_gt'], head: 'Pandu variabel', unit: `${cur}/GT/gerakan`, digits: f ? 3 : 0, v: 'in.tariff.pandu' },
    { path: [f ? 'tambat_foreign_usd_per_gt_etmal' : 'tambat_domestic_rp_per_gt_etmal', 'beton'], head: 'Tambat beton', unit: `${cur}/GT/etmal`, digits: f ? 3 : 0, v: 'in.tariff.tambat' },
    { path: [f ? 'tambat_foreign_usd_per_gt_etmal' : 'tambat_domestic_rp_per_gt_etmal', 'dolphin'], head: 'Tambat dolphin', unit: `${cur}/GT/etmal`, digits: f ? 3 : 0, v: 'in.tariff.tambat' },
    { path: [f ? 'bm_foreign_rp_per_ton' : 'bm_domestic_rp_per_ton'], head: 'B/M per ton', unit: 'Rp/ton', digits: 0, v: 'in.tariff.bm' },
    { path: [f ? 'bm_foreign_rp_per_teu' : 'bm_domestic_rp_per_teu'], head: 'B/M per TEU', unit: 'Rp/TEU', digits: 0, v: 'in.tariff.bm' },
  ]
}

/** Tarif pelabuhan per kelas (sheet Biaya Pelabuhan K15): labuh, pandu, tambat, B/M, dan tunda per rentang GT. */
export function TariffTable() {
  const c = usePlanner((s) => s.caseData)
  const [scope, setScope] = useState<Scope>('foreign')
  const [tugClass, setTugClass] = useState(0)
  const rows = c.tariffs.classes
  const cols = columns(scope)
  const usedBy = (r: Row) => c.ports.filter((p) => p.tariff_class === r.tariff_class).length
  const f = scope === 'foreign'
  const cur = f ? 'USD' : 'Rp'
  const tug = rows[tugClass]?.tug ?? []

  return (
    <div className="flex w-full flex-col gap-4">
      <Tabs
        items={[{ id: 'foreign', label: 'Kapal luar negeri' }, { id: 'domestic', label: 'Kapal dalam negeri' }]}
        value={scope}
        onChange={setScope}
        right={<span className="text-[13px] text-abu">pelabuhan luar negeri dipakai untuk rute impor/ekspor</span>}
      />
      <div className="w-full overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-hitam text-[13px] text-abu">
              <th className="py-2 pr-2 text-left font-medium">Kelas</th>
              {cols.map((k) => (
                <th key={k.head} className="py-2 pr-2 text-right font-medium">
                  <Tv v={k.v} className="text-abu">{k.head}</Tv>
                  <span className="block font-mono font-normal">{k.unit}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.tariff_class} className="border-b border-garis">
                <td className="py-1.5 pr-2">
                  {CLASS_LABEL(r.tariff_class)}
                  {usedBy(r) > 0 && <span className="pl-1.5 font-mono text-[13px] text-abu">· {usedBy(r)} pel.</span>}
                </td>
                {cols.map((k) => (
                  <td key={k.head} className="py-1.5 pr-2 text-right">
                    <Cell path={['tariffs', 'classes', i, ...k.path]} label={`${k.head} ${CLASS_LABEL(r.tariff_class)} (${f ? 'LN' : 'DN'})`} digits={k.digits} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-2">
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="pr-2 text-sm font-medium"><Tv v="in.tariff.tunda">Tunda</Tv> per rentang GT</span>
          {rows.map((r, i) => (
            <button key={r.tariff_class} type="button" aria-pressed={tugClass === i} onClick={() => setTugClass(i)} className={`h-7 cursor-pointer rounded-badge border px-2 text-[13px] ${tugClass === i ? 'border-hitam bg-hitam text-white' : 'border-garis bg-white hover:border-hitam'}`}>
              {CLASS_LABEL(r.tariff_class)}
            </button>
          ))}
        </span>
        <table className="w-full max-w-[560px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-hitam text-[13px] text-abu">
              <th className="py-1.5 text-left font-medium">GT kapal</th>
              <th className="py-1.5 text-right font-medium">Tetap, {cur}/gerakan</th>
              <th className="py-1.5 text-right font-medium">Variabel, {cur}/GT/gerakan</th>
            </tr>
          </thead>
          <tbody>
            {c.tariffs.tug_gt_bands.map((b, j) => (
              <tr key={j} className="border-b border-garis">
                <td className="py-1 font-mono text-[13px]">{num(b.gt_min)}{b.gt_max == null ? ' ke atas' : `–${num(b.gt_max)}`}</td>
                <td className="py-1 text-right">{tug[j] ? <Cell path={['tariffs', 'classes', tugClass, 'tug', j, f ? 'fixed_foreign_usd' : 'fixed_domestic_rp']} label={`Tunda tetap rentang ${j + 1} ${CLASS_LABEL(rows[tugClass].tariff_class)}`} /> : '–'}</td>
                <td className="py-1 text-right">{tug[j] ? <Cell path={['tariffs', 'classes', tugClass, 'tug', j, f ? 'var_foreign_usd_per_gt' : 'var_domestic_rp_per_gt']} label={`Tunda variabel rentang ${j + 1} ${CLASS_LABEL(rows[tugClass].tariff_class)}`} digits={f ? 2 : 0} /> : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        Sumber K15: sheet Biaya Pelabuhan. Kelas tiap pelabuhan dipilih di tabel pelabuhan di atas (kolom Tarif). Tapak TERSUS di KEK {c.kek_site.port_charges === 'none' ? 'tidak dikenai tarif pelabuhan (greenfield)' : `memakai ${CLASS_LABEL(String(c.kek_site.tariff_class))}`}.
        Rincian biaya per call (labuh, pandu, tunda, tambat, B/M) tampil di layar 7.
      </Note>
    </div>
  )
}
