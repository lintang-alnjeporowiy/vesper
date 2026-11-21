import { useState } from 'react'
import type { Equipment1 } from '../api/case'
import { Badge, EditNum, Note, PH, ScreenHeader, Section, Split, Table } from '../components/ui'
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

export default function S05Alat() {
  const c = usePlanner((s) => s.caseData)
  const chosen = c.plans?.[0]?.equipment_by_terminal ?? {}
  const assumed = new Set((c.assumptions ?? []).filter((a) => a.status === 'asumsi').map((a) => a.id))
  const hmc = c.equipment.filter((e) => e.kind === 'HMC')
  const mla = c.equipment.filter((e) => e.kind === 'MLA')
  const [alt, setAlt] = useState('eq.liebherr_lhm_420')
  const idx = (e: Equipment1) => c.equipment.indexOf(e)
  const prod = (e: Equipment1) => e.productivity as unknown as Prod
  const status = (e: Equipment1) =>
    Object.values(chosen).includes(e.id) ? <span className="text-[13px] font-medium">terpilih</span> : assumed.has(e.id.replace('eq.liebherr_', '').replace('_', '')) || e.id.endsWith('800') ? <Badge kind="asumsi">asumsi</Badge> : <span className="text-[13px] text-abu">kandidat</span>
  const prodCell = (e: Equipment1, form: string) =>
    prod(e)[form] ? <Cell path={['equipment', idx(e), 'productivity', form, 'unload']} label={`Produktivitas ${form} ${e.name}`} /> : <span className="font-mono text-abu">–</span>

  return (
    <>
      <ScreenHeader step={5} kind="input" title="Alat bongkar muat" lead="Produktivitas alat menentukan port time di KEK, lalu RTD, berth-days, dan jumlah tambatan." badge={<Badge kind="input">input K15 · {c.equipment.length} alat</Badge>} />

      <Section title="Harbour mobile crane · dermaga MP" aside={<span className="font-mono text-[13px] text-abu">{hmc.length} alat</span>}>
        <Table<Equipment1>
          rowKey={(e) => e.id}
          rows={hmc}
          selected={(e) => Object.values(chosen).includes(e.id)}
          columns={[
            { key: 'n', head: 'Alat', width: 170, render: (e) => e.name },
            { key: 'h', head: 'Harga USD', width: 130, input: true, render: (e) => <Cell path={['equipment', idx(e), 'price_usd']} label={`Harga ${e.name}`} /> },
            { key: 'gc', head: 'GC t/j', width: 110, input: true, render: (e) => prodCell(e, 'GC') },
            { key: 'ck', head: 'CK t/j', width: 110, input: true, render: (e) => prodCell(e, 'CK') },
            { key: 'pk', head: 'PK box/j', width: 110, input: true, render: (e) => prodCell(e, 'PK') },
            { key: 'r', head: 'Jangkau', width: 70, mono: true, render: (e) => (e.reach_m ? `${num(e.reach_m)} m` : '–') },
            { key: 's', head: 'Status', render: status },
          ]}
        />
      </Section>

      <Section title="Marine loading arm · jetty CC" aside={<span className="font-mono text-[13px] text-abu">{mla.length} alat</span>}>
        <Table<Equipment1>
          rowKey={(e) => e.id}
          rows={mla}
          selected={(e) => Object.values(chosen).includes(e.id)}
          columns={[
            { key: 'n', head: 'Alat', width: 260, render: (e) => e.name.replace("''", '″') },
            { key: 'h', head: 'Harga USD', width: 130, input: true, render: (e) => <Cell path={['equipment', idx(e), 'price_usd']} label={`Harga ${e.name}`} /> },
            { key: 'cc', head: 'CC t/j', width: 130, input: true, render: (e) => prodCell(e, 'CC') },
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
                  <th className="py-1.5 font-medium">LOA kapal</th>
                  <th className="w-24 font-medium">Alat</th>
                </tr>
              </thead>
              <tbody>
                {c.equipment_rules.loa_bands.map((b) => (
                  <tr key={b.loa_min_m} className="border-b border-garis font-mono">
                    <td className="py-2">{num(b.loa_min_m)}–{num(b.loa_max_m ?? 0)} m</td>
                    <td>{b.per_berth}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <span className="pt-2">
              <Note>Batas per tambatan: {Object.entries(c.equipment_rules.max_per_berth as Record<string, number>).map(([k, v]) => `${k} ${v}`).join(', ')}.</Note>
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
