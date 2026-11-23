import { C, Tornado } from '../charts/charts'
import { Badge, Button, Legend, Note, PH, ScreenHeader, Section, Split } from '../components/ui'
import { SCENARIOS, TORNADO } from '../mock/placeholders'

const EXPORT_ITEMS = ['Rangkuman (format sheet Rangkuman)', 'Armada per flow per tahun', 'Biaya pelayaran dan terminal', 'Jadwal investasi', 'Daftar asumsi dan selisih vs Excel (A1–A17)']

export default function S11Skenario() {
  return (
    <>
      <ScreenHeader
        step={11}
        kind="hasil"
        title="Skenario & laporan"
        lead="Bandingkan skenario berdampingan, lihat parameter mana yang paling menggeser biaya, lalu ekspor rangkuman."
        actions={
          <>
            <Button disabled>Export PDF</Button>
            <Button variant="utama" disabled>Export Excel</Button>
          </>
        }
      />

      <Section title="Perbandingan skenario" aside={<Button size="sm" disabled>Tambah skenario</Button>}>
        <div className="w-full overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-hitam text-left">
                <th className="w-[236px] py-2 text-[13px] font-medium text-abu">Indikator</th>
                {SCENARIOS.columns.map((col) => (
                  <th key={col.name} className="py-2 font-normal">
                    <span className="block text-[13px] font-medium">{col.name}</span>
                    <span className="block text-[13px] text-abu">{col.sub}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SCENARIOS.rows.map((r) => (
                <tr key={r.label} className="border-b border-garis">
                  <td className="py-2.5">{r.label}</td>
                  {r.values.map((v, i) => {
                    const d = r.deltas?.[i]
                    return (
                      <td key={i} className="py-2.5">
                        <span className="flex items-center gap-1.5">
                          <span className={`text-abu ${/\d/.test(v) ? 'font-mono' : ''}`}>{v}</span>
                          {d && <Badge kind={d.good ? 'baik' : 'buruk'}>{d.v}</Badge>}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Note>Semua nilai placeholder. Baseline dihitung ulang dengan engine terkoreksi, jadi akan berbeda dari angka di workbook (A1–A17).</Note>
      </Section>

      <Section title="Sensitivitas NPV biaya total" aside={<Legend items={[{ color: C.hijau, label: 'turun' }, { color: C.merah, label: 'naik' }]} />}>
        <Tornado rows={TORNADO} />
        <span><PH>placeholder · engine tahap 10</PH></span>
      </Section>

      <Split
        left={
          <div className="flex flex-col gap-2">
            <h2 className="m-0 pb-2 text-xl font-normal">Isi ekspor Excel</h2>
            {EXPORT_ITEMS.map((t) => (
              <span key={t} className="flex items-center gap-2 text-sm"><span className="h-1.5 w-1.5 bg-hitam" />{t}</span>
            ))}
          </div>
        }
        right={
          <div className="flex flex-col gap-2">
            <h2 className="m-0 pb-2 text-xl font-normal">Format lain</h2>
            {['PDF ringkas, 4 halaman', 'File kasus JSON', 'Jejak perhitungan (CSV)'].map((t) => (
              <span key={t} className="flex h-9 items-center rounded-kontrol border border-garis px-3 text-sm">
                <span className="grow">{t}</span>
                <span className="text-[13px] text-abu">tahap 11</span>
              </span>
            ))}
          </div>
        }
      />
    </>
  )
}
