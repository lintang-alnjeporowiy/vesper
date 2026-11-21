import { useRef, useState } from 'react'
import type { Case } from '../api/case'
import { Badge, Button, Note, ScreenHeader, Section, Table } from '../components/ui'
import { CASES, type CaseListItem } from '../mock/case'
import { usePlanner } from '../store'

function download(name: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

export default function S00Beranda() {
  const caseData = usePlanner((s) => s.caseData)
  const setScreen = usePlanner((s) => s.setScreen)
  const fileRef = useRef<HTMLInputElement>(null)
  const [importMsg, setImportMsg] = useState<string | null>(null)

  const onImport = async (file: File) => {
    try {
      const data = JSON.parse(await file.text()) as Partial<Case>
      if (!data.meta || !Array.isArray(data.flows) || !Array.isArray(data.ships)) throw new Error('bukan file kasus (meta/flows/ships tidak ada)')
      usePlanner.setState({ caseData: data as Case, baseline: data as Case, dirty: {} })
      setImportMsg(`Terbuka: ${data.meta.name}. Validasi skema penuh menyusul bersama API (tahap 3+).`)
    } catch (e) {
      setImportMsg(`Gagal import: ${(e as Error).message}`)
    }
  }

  const stats = [
    { label: 'Tenant', value: caseData.tenants.length },
    { label: 'Flow', value: caseData.flows.length },
    { label: 'Kapal', value: caseData.ships.length },
    { label: 'Asumsi', value: caseData.assumptions?.length ?? 0, red: true },
  ]

  return (
    <>
      <ScreenHeader
        step={0}
        kind="beranda"
        title="Kasus perencanaan"
        lead="Satu kasus = satu kawasan industri dengan tenant, pelabuhan, kandidat kapal, dan alat. Buka kasus contoh untuk mulai."
        actions={
          <>
            <Button onClick={() => fileRef.current?.click()}>Import file</Button>
            <Button variant="utama" disabled>Kasus baru</Button>
          </>
        }
      />
      <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])} />
      {importMsg && <Note>{importMsg}</Note>}

      <div className="flex w-full gap-8 border-y border-garis py-6">
        <div className="flex grow flex-col gap-2">
          <div className="flex items-center gap-2">
            <h2 className="m-0 text-xl font-normal">{caseData.meta.name.replace('—', '·')}</h2>
            <Badge kind="aktif">terbuka</Badge>
          </div>
          <span className="text-sm">{caseData.meta.kek_port_name}, {caseData.meta.location}</span>
          <Note>{caseData.meta.description}</Note>
          <div className="flex gap-2 pt-2">
            <Button variant="utama" size="sm" onClick={() => setScreen(1)}>Lanjutkan</Button>
            <Button size="sm" disabled>Duplikat</Button>
            <Button variant="tipis" size="sm" onClick={() => download(`${caseData.meta.id}.json`, caseData)}>Export JSON</Button>
          </div>
        </div>
        <div className="flex w-[420px] shrink-0">
          {stats.map((s) => (
            <div key={s.label} className="flex grow basis-0 flex-col gap-1 border-l border-garis px-3">
              <span className="text-[13px] text-abu">{s.label}</span>
              <span className={`font-mono text-[28px] leading-none ${s.red ? 'text-merah' : ''}`}>{s.value}</span>
            </div>
          ))}
        </div>
      </div>

      <Section title="Semua kasus">
        <Table<CaseListItem>
          rowKey={(r) => r.id}
          rows={CASES}
          selected={(r) => r.id === caseData.meta.id}
          columns={[
            { key: 'n', head: 'Kasus', width: 200, render: (r) => r.name },
            { key: 'l', head: 'Lokasi', width: 180, render: (r) => r.location },
            { key: 'f', head: 'Tenant/flow', width: 100, mono: true, render: (r) => (r.data ? `${r.data.tenants.length} / ${r.data.flows.length}` : '–') },
            { key: 's', head: 'Status', width: 160, render: (r) => (r.status === 'siap' ? <Badge kind="input">input lengkap</Badge> : <Badge kind="asumsi">belum diekstrak</Badge>) },
            { key: 'd', head: 'Diekstrak', mono: true, render: (r) => <span className="text-[13px] text-abu">{r.data?.meta.extracted_at ?? '–'}</span> },
          ]}
        />
        <Note>K21 dan K24 menjadi uji lanjutan di tahap 12. K7 (hub-spoke) di luar cakupan.</Note>
      </Section>

      <div className="flex w-full gap-8">
        <div className="flex grow basis-0 flex-col gap-2 rounded-kontrol border border-garis p-6">
          <span className="text-base font-medium">Import dari JSON</span>
          <Note>File kasus sesuai case.schema.json. Untuk sekarang hanya dicek bentuk dasarnya; validasi penuh lewat API menyusul.</Note>
          <span className="font-mono text-[13px]">k15-batam.json</span>
        </div>
        <div className="flex grow basis-0 flex-col gap-2 rounded-kontrol border border-garis p-6">
          <span className="text-base font-medium">Import dari Excel TPT</span>
          <Note>Workbook dengan sheet Model, Muatan, Data Kapal. Pemetaan sel dibuat per kasus (tahap 11).</Note>
          <span className="font-mono text-[13px] text-abu">belum tersedia</span>
        </div>
      </div>
    </>
  )
}
