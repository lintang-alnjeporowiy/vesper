import type { ReactNode } from 'react'
import { Badge, DefRow, EditNum, InputMark, Label, Note, ScreenHeader, Section, Split, Table } from '../components/ui'
import { useField } from '../lib/useField'
import { usePlanner } from '../store'

function Param(props: { path: (string | number)[]; label: string; unit?: string; digits?: number; scale?: number; last?: boolean }) {
  const f = useField(props.path, props.label)
  return (
    <DefRow label={<span className="text-sm text-hitam">{props.label}</span>} justify last={props.last}>
      <EditNum {...f} unit={props.unit} digits={props.digits} scale={props.scale} />
    </DefRow>
  )
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col pb-5">
      <span className="pb-1.5"><Label>{title}</Label></span>
      {children}
    </div>
  )
}

const STATUS: Record<string, ReactNode> = {
  dikonfirmasi: <Badge kind="dihitung">dikonfirmasi</Badge>,
  dari_excel: <Badge kind="audit">dari Excel</Badge>,
  asumsi: <Badge kind="asumsi">asumsi</Badge>,
}

export default function S01Soal() {
  const c = usePlanner((s) => s.caseData)
  const dirty = usePlanner((s) => s.dirty)
  const fuelIdx = (code: string) => c.params.fuels.findIndex((f) => f.code === code)
  const nDirty = Object.keys(dirty).length

  return (
    <>
      <ScreenHeader step={1} kind="input" title="Soal & asumsi" lead="Identitas kawasan, horizon perencanaan, dan parameter global yang dipakai semua perhitungan." badge={<Badge kind="input">input K15</Badge>} />

      <Split
        left={
          <>
            <h2 className="m-0 pb-4 text-xl font-normal">Identitas</h2>
            <DefRow label="Kawasan">{c.meta.kek_name}</DefRow>
            <DefRow label="Pelabuhan">{c.meta.kek_port_name}</DefRow>
            <DefRow label="Lokasi">{c.meta.location}</DefRow>
            <DefRow label="Kondisi tapak" last>greenfield, tanpa tarif pelabuhan KEK</DefRow>
          </>
        }
        right={
          <div className="flex flex-col gap-4">
            <h2 className="m-0 text-xl font-normal">Horizon {(c.horizon.years ?? 20)} tahun</h2>
            <div className="flex gap-0.5">
              {c.horizon.phases.map((p, i) => (
                <div key={p.name} className={`flex flex-col gap-1 p-2 ${i === 0 ? 'w-24 bg-hitam text-white' : i === 1 ? 'w-24 bg-abu text-white' : 'grow bg-permukaan'}`}>
                  <span className="text-[13px] capitalize">{p.name}</span>
                  <span className="font-mono text-[13px]">th {p.start_year}–{p.end_year}</span>
                </div>
              ))}
            </div>
            <div>
              <DefRow label="Waktu bangun" justify><span className="font-mono">{c.horizon.construction_lead_years} th</span></DefRow>
              <DefRow label="Lookahead tambatan / penyimpanan" justify last><span className="font-mono">{c.horizon.berth_lookahead_years} th / {c.horizon.storage_lookahead_years} th</span></DefRow>
            </div>
          </div>
        }
      />

      <Section title="Parameter global" aside={<span className="flex items-center gap-1.5 text-[13px] text-abu"><InputMark />klik angka untuk mengedit</span>}>
        <div className="flex w-full gap-8">
          <div className="flex w-[392px] shrink-0 flex-col">
            <Group title="Operasi">
              <Param path={['params', 'at_hours']} label="Approach time" unit="jam" />
              <Param path={['params', 'wt_hours']} label="Waiting time" unit="jam" />
              <Param path={['params', 'it_hours']} label="Idle time" unit="jam" />
              <Param path={['params', 'working_days_per_year']} label="Hari kerja per tahun" unit="hr" />
              <Param path={['params', 'working_hours_per_day']} label="Jam kerja per hari" unit="j" />
              <Param path={['params', 'bor_max']} label="BOR maksimum" digits={2} />
              <Param path={['params', 'berth_loa_min_ratio']} label="Dermaga minimum × LOA" digits={2} />
              <Param path={['params', 'payload_dwt_ratio']} label="Payload / DWT" digits={2} last />
            </Group>
            <Group title="Petikemas">
              <Param path={['params', 'teu_nominal_weight_t']} label="Berat nominal per TEU" unit="t" />
              <Param path={['params', 'teu_capacity_dwt_ratio']} label="Kapasitas TEU / DWT" digits={2} />
              <Param path={['params', 'container', 'max_net_t']} label="Berat bersih maks" unit="t" digits={1} last />
            </Group>
          </div>
          <div className="flex min-w-0 grow flex-col">
            <Group title="Ekonomi">
              <Param path={['params', 'usd_rate']} label="Kurs Rp per USD" digits={1} />
              <Param path={['params', 'discount_rate']} label="Discount rate (I9)" unit="%" scale={100} digits={1} />
              <Param path={['params', 'escalation_infra']} label="Eskalasi infrastruktur" unit="%" scale={100} digits={1} />
              <Param path={['params', 'escalation_equipment']} label="Eskalasi alat" unit="%" scale={100} digits={1} />
              {fuelIdx('HSD') >= 0 && <Param path={['params', 'fuels', fuelIdx('HSD'), 'price_rp_per_l']} label="Harga HSD (ME, AE)" unit="Rp/l" />}
              {fuelIdx('MFO') >= 0 && <Param path={['params', 'fuels', fuelIdx('MFO'), 'price_rp_per_l']} label="Harga MFO" unit="Rp/l" last />}
            </Group>
            <Group title="Mesin">
              <Param path={['params', 'mcr']} label="MCR" digits={2} />
              <Param path={['params', 'ae_me_power_ratio']} label="Daya AE / ME" digits={2} />
              <DefRow label={<span className="text-sm text-hitam">SFOC ME</span>} justify last>
                <span className="font-mono">{c.params.sfoc_me_bands.length} pita · {Math.round(Math.min(...c.params.sfoc_me_bands.map((b) => b.sfoc_g_kwh)))}–{Math.round(Math.max(...c.params.sfoc_me_bands.map((b) => b.sfoc_g_kwh)))} g/kWh</span>
              </DefRow>
            </Group>
          </div>
        </div>
        <div className="flex gap-2">
          <span className={`w-0.5 shrink-0 ${nDirty ? 'bg-merah' : 'bg-hitam'}`} />
          <Note>
            {nDirty
              ? `${nDirty} input berubah: ${Object.values(dirty).map((d) => d.label).join(', ')}. Tekan "Hitung ulang" di bar atas untuk menjadikannya baseline.`
              : 'Nilai yang diedit ditandai merah "diubah" dan bar atas menampilkan "perlu hitung ulang".'}
          </Note>
        </div>
      </Section>

      <Section title="Asumsi dan celah data" aside={<span className="font-mono text-[13px] text-abu">{c.assumptions?.length ?? 0} tercatat</span>}>
        <Table
          rowKey={(a) => a.id}
          rows={c.assumptions ?? []}
          columns={[
            { key: 't', head: 'Topik', width: 260, render: (a) => a.topic },
            { key: 's', head: 'Status', width: 140, render: (a) => STATUS[a.status as string] ?? <Badge kind="audit">{String(a.status)}</Badge> },
            { key: 'x', head: 'Keterangan', render: (a) => <span className="text-[13px] text-abu">{a.text}</span> },
          ]}
        />
      </Section>
    </>
  )
}
