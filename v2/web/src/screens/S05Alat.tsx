import { useState } from 'react'
import type { Equipment } from '../api/case'
import { Badge, Button, EditNum, EditText, Note, PH, ScreenHeader, Section, Split, Table } from '../components/ui'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { EQUIP_WHATIF } from '../mock/placeholders'
import { usePlanner } from '../store'

function Cell(props: { path: (string | number)[]; label: string; digits?: number; scale?: number }) {
  const f = useField(props.path, props.label)
  if (f.value === undefined || f.value === null) return <span className="font-mono text-abu">–</span>
  return <EditNum {...f} mark={false} digits={props.digits} scale={props.scale} />
}

type Prod = Record<string, { unload: number; load: number; unit: string } | undefined>

const isCustom = (e: Equipment) => e.id.startsWith('eq.baru_')

/** Kandidat alat baru dengan nilai awal yang wajar; semua angkanya bisa diedit. */
function newEquipment(kind: 'HMC' | 'MLA', n: number): Equipment {
  const prod = (unload: number, unit: 't/h' | 'box/h') => ({ refs: {}, unload, load: unload, unit })
  return {
    refs: {},
    id: `eq.baru_${kind.toLowerCase()}_${n}`,
    name: `${kind === 'HMC' ? 'HMC' : 'MLA'} baru ${n}`,
    kind,
    terminal_id: kind === 'HMC' ? 'MP' : 'CC',
    price_usd: kind === 'HMC' ? 100000 : 50000,
    productivity: (kind === 'HMC' ? { GC: prod(800, 't/h'), CK: prod(800, 't/h'), PK: prod(30, 'box/h') } : { CC: prod(1000, 't/h') }) as Equipment['productivity'],
    in_reference_model: false,
  } as Equipment
}

function Rule(props: { path: (string | number)[]; label: string }) {
  const f = useField(props.path, props.label)
  return <EditNum {...f} mark={false} onChange={(v) => v >= 0 && f.onChange(Math.round(v))} />
}

export default function S05Alat() {
  const c = usePlanner((s) => s.caseData)
  const chosen = c.plans?.[0]?.equipment_by_terminal ?? {}
  const assumed = new Set((c.assumptions ?? []).filter((a) => a.status === 'asumsi').map((a) => a.id))
  const hmc = c.equipment.filter((e) => e.kind === 'HMC')
  const mla = c.equipment.filter((e) => e.kind === 'MLA')
  const [alt, setAlt] = useState('eq.liebherr_lhm_420')
  const idx = (e: Equipment) => c.equipment.indexOf(e)
  const prod = (e: Equipment) => e.productivity as unknown as Prod
  const status = (e: Equipment) =>
    Object.values(chosen).includes(e.id) ? <span className="text-[13px] font-medium">terpilih</span> : assumed.has(e.id.replace('eq.liebherr_', '').replace('_', '')) || e.id.endsWith('800') ? <Badge kind="asumsi">asumsi</Badge> : <span className="text-[13px] text-abu">kandidat</span>
  const setInput = usePlanner((s) => s.setInput)
  const addEq = (kind: 'HMC' | 'MLA') => {
    const n = c.equipment.filter((e) => e.id.startsWith(`eq.baru_${kind.toLowerCase()}_`)).length + 1
    setInput(['equipment'], [...c.equipment, newEquipment(kind, n)], `Tambah alat ${kind}`)
  }
  const removeEq = (e: Equipment) => setInput(['equipment'], c.equipment.filter((x) => x.id !== e.id), `Hapus ${e.name}`)
  const nameCell = (e: Equipment) =>
    isCustom(e) ? (
      <span className="inline-flex items-center gap-1">
        <EditText value={e.name} width="16ch" label={`Nama ${e.name}`} onChange={(v) => v && setInput(['equipment', idx(e), 'name'], v, `Nama alat ${e.name}`)} />
        <button type="button" aria-label={`Hapus ${e.name}`} onClick={() => removeEq(e)} className="cursor-pointer border-0 bg-transparent text-abu hover:text-merah">×</button>
      </span>
    ) : (
      e.name.replace("''", '″')
    )
  const prodCell = (e: Equipment, form: string) =>
    prod(e)[form] ? <Cell path={['equipment', idx(e), 'productivity', form, 'unload']} label={`Produktivitas ${form} ${e.name}`} /> : <span className="font-mono text-abu">–</span>

  return (
    <>
      <ScreenHeader step={5} kind="input" title="Alat bongkar muat" lead="Produktivitas alat menentukan port time di KEK, lalu RTD, berth-days, dan jumlah tambatan." badge={<Badge kind="input">input K15 · {c.equipment.length} alat</Badge>} />

      <Section title="Harbour mobile crane · dermaga MP" aside={<span className="flex items-center gap-3"><span className="font-mono text-[13px] text-abu">{hmc.length} alat</span><Button size="sm" onClick={() => addEq('HMC')}>Tambah alat</Button></span>}>
        <Table<Equipment>
          rowKey={(e) => e.id}
          rows={hmc}
          selected={(e) => Object.values(chosen).includes(e.id)}
          columns={[
            { key: 'n', head: 'Alat', width: 190, render: nameCell },
            { key: 'h', head: 'Harga, USD', width: 130, input: true, render: (e) => <Cell path={['equipment', idx(e), 'price_usd']} label={`Harga ${e.name}`} /> },
            { key: 'gc', head: 'GC, t/jam', width: 110, input: true, render: (e) => prodCell(e, 'GC') },
            { key: 'ck', head: 'CK, t/jam', width: 110, input: true, render: (e) => prodCell(e, 'CK') },
            { key: 'pk', head: 'PK, box/jam', width: 110, input: true, render: (e) => prodCell(e, 'PK') },
            { key: 'r', head: 'Jangkau, m', width: 90, mono: true, render: (e) => (e.reach_m ? num(e.reach_m) : '–') },
            { key: 's', head: 'Status', render: status },
          ]}
        />
      </Section>

      <Section title="Marine loading arm · jetty CC" aside={<span className="flex items-center gap-3"><span className="font-mono text-[13px] text-abu">{mla.length} alat</span><Button size="sm" onClick={() => addEq('MLA')}>Tambah alat</Button></span>}>
        <Table<Equipment>
          rowKey={(e) => e.id}
          rows={mla}
          selected={(e) => Object.values(chosen).includes(e.id)}
          columns={[
            { key: 'n', head: 'Alat', width: 260, render: nameCell },
            { key: 'h', head: 'Harga, USD', width: 130, input: true, render: (e) => <Cell path={['equipment', idx(e), 'price_usd']} label={`Harga ${e.name}`} /> },
            { key: 'cc', head: 'CC, t/jam', width: 130, input: true, render: (e) => prodCell(e, 'CC') },
            { key: 's', head: 'Status', render: status },
          ]}
        />
      </Section>

      <Split
        left={
          <>
            <h2 className="m-0 pb-4 text-xl font-normal">Alat per tambatan dari LOA</h2>
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-hitam text-left text-[13px] text-abu">
                  <th className="py-1.5 font-medium">LOA dari, m</th>
                  <th className="font-medium">sampai, m</th>
                  <th className="font-medium">Alat per tambatan</th>
                </tr>
              </thead>
              <tbody>
                {c.equipment_rules.loa_bands.map((b, i) => (
                  <tr key={i} className="border-b border-garis">
                    <td className="py-1"><Rule path={['equipment_rules', 'loa_bands', i, 'loa_min_m']} label={`LOA min rentang ${i + 1}`} /></td>
                    <td>{b.loa_max_m == null ? <span className="font-mono text-abu">–</span> : <Rule path={['equipment_rules', 'loa_bands', i, 'loa_max_m']} label={`LOA maks rentang ${i + 1}`} />}</td>
                    <td><Rule path={['equipment_rules', 'loa_bands', i, 'per_berth']} label={`Alat per tambatan rentang ${i + 1}`} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex flex-col pt-4">
              <span className="pb-1 text-[13px] font-medium text-abu">Batas maksimum alat per tambatan</span>
              {Object.keys(c.equipment_rules.max_per_berth).map((t) => (
                <span key={t} className="flex items-center gap-2 border-b border-garis py-1 text-sm">
                  <span className="grow">{c.kek_site.terminals.find((x) => x.id === t)?.name ?? t}</span>
                  <Rule path={['equipment_rules', 'max_per_berth', t]} label={`Batas alat per tambatan ${t}`} />
                </span>
              ))}
            </div>
            <span className="pt-2">
              <Note>Jumlah alat per tambatan diambil dari rentang LOA kapal terbesar yang dilayani, dibatasi angka maksimum terminal (A10).</Note>
            </span>
          </>
        }
        right={
          <div className="flex flex-col gap-4">
            <h2 className="m-0 text-xl font-normal">What-if produktivitas (I3)</h2>
            <label className="flex flex-col gap-2">
              <span className="text-[13px] text-abu">Ganti alat MP {hmc.find((e) => e.id === chosen.MP)?.name.replace('Liebherr ', '')} dengan</span>
              <select value={alt} onChange={(e) => setAlt(e.target.value)} className="h-10 rounded-kontrol border border-hitam bg-white px-3 text-sm">
                {hmc.filter((e) => e.id !== chosen.MP).map((e) => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </label>
            <div className="flex flex-col">
              {EQUIP_WHATIF.map((w, i) => (
                <div key={w.label} className={`flex items-center gap-2 border-t border-garis py-2 ${i === EQUIP_WHATIF.length - 1 ? 'border-b' : ''}`}>
                  <span className="grow text-sm">{w.label}</span>
                  <span className="font-mono text-sm text-abu">{w.value}</span>
                  <Badge kind={w.good ? 'baik' : 'buruk'}>{w.delta}</Badge>
                </div>
              ))}
            </div>
            <span><PH>efek berantai: placeholder, contoh untuk LHM 420</PH></span>
          </div>
        }
      />
    </>
  )
}
