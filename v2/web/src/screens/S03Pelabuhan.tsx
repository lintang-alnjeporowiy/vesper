import type { Case, ExternalPort } from '../api/case'
import { BarRows, C } from '../charts/charts'
import { BathyEditor } from '../components/BathyEditor'
import { Badge, DefRow, EditNum, Note, ScreenHeader, Section, Split, Table } from '../components/ui'
import { portOfRoute, shortPortName } from '../lib/case'
import { num } from '../lib/format'
import { useField } from '../lib/useField'
import { usePlanner } from '../store'

function Cell(props: { path: (string | number)[]; label: string; digits?: number; unit?: string }) {
  const f = useField(props.path, props.label)
  if (f.value === undefined || f.value === null) return <Badge kind="asumsi">kosong</Badge>
  return <EditNum {...f} mark={false} digits={props.digits} unit={props.unit} />
}

/** Rute pulang-pergi yang menyinggahi pelabuhan ini (K15: satu rute per pelabuhan). */
function routeIndexOfPort(c: Case, portId: string) {
  return c.routes.findIndex((r) => r.legs.some((l) => l.origin === portId || l.destination === portId))
}

/** Jarak KEK ↔ pelabuhan; pada pola round trip kedua leg diisi nilai yang sama. */
function DistanceCell({ portId }: { portId: string }) {
  const c = usePlanner((s) => s.caseData)
  const setInput = usePlanner((s) => s.setInput)
  const ri = routeIndexOfPort(c, portId)
  const changed = usePlanner((s) => Object.keys(s.dirty).some((k) => k.startsWith(`routes.${ri}.`)))
  if (ri < 0) return <Badge kind="asumsi">tanpa rute</Badge>
  const r = c.routes[ri]
  const legs = r.legs.filter((l) => l.origin === portId || l.destination === portId)
  const d = legs[0].distance_nm
  const uneven = legs.some((l) => l.distance_nm !== d)
  return (
    <span className="inline-flex items-center gap-1" title={uneven ? 'Jarak pergi dan pulang berbeda; mengedit akan menyamakan keduanya' : r.name}>
      <EditNum
        value={d}
        digits={1}
        mark={false}
        changed={changed}
        label={`Jarak ${r.name}`}
        onChange={(v) => v > 0 && setInput(['routes', ri, 'legs'], r.legs.map((l) => (l.origin === portId || l.destination === portId ? { ...l, distance_nm: v, refs: {} } : l)), `Jarak ${r.name}`)}
      />
      {uneven && <span className="text-[13px] text-merah">≠</span>}
    </span>
  )
}

export default function S03Pelabuhan() {
  const c = usePlanner((s) => s.caseData)
  const flowId = usePlanner((s) => s.flowId)
  const ratio = c.params.berth_loa_min_ratio
  const missing = c.ports.filter((p) => p.longest_berth_m == null)
  const site = c.kek_site
  const w = site.waterside

  const routeRows = c.flows
    .map((f) => ({ f, d: c.routes.find((r) => r.id === f.route_id)?.legs[0]?.distance_nm ?? 0 }))
    .sort((a, b) => b.d - a.d)

  return (
    <>
      <ScreenHeader
        step={3}
        kind="input"
        title="Pelabuhan & rute"
        lead="Pelabuhan asal dan tujuan membatasi ukuran kapal lewat draft dan panjang dermaga."
        badge={missing.length ? <Badge kind="asumsi">{missing.length} celah data</Badge> : <Badge kind="input">input K15</Badge>}
      />

      <Section title="Pelabuhan asal dan tujuan" aside={<span className="font-mono text-[13px] text-abu">{c.ports.length} pelabuhan · {c.ports.filter((p) => p.kind === 'domestic').length} domestik</span>}>
        <Table<ExternalPort>
          rowKey={(p) => p.id}
          rows={c.ports}
          columns={[
            { key: 'n', head: 'Pelabuhan', width: 130, render: (p) => shortPortName(p.name) },
            { key: 'c', head: 'Negara', width: 90, render: (p) => p.country },
            { key: 't', head: 'Terminal', width: 100, render: (p) => <span className="text-[13px] text-abu">{p.terminal_type}</span> },
            { key: 'd', head: 'Draft maks, m', width: 110, input: true, render: (p) => <Cell path={['ports', c.ports.indexOf(p), 'max_draft_m']} label={`Draft ${p.name}`} digits={1} /> },
            { key: 'r', head: 'Jarak ke KEK, NM', width: 130, input: true, render: (p) => <DistanceCell portId={p.id} /> },
            { key: 'b', head: 'Dermaga terpanjang, m', width: 120, input: true, render: (p) => <Cell path={['ports', c.ports.indexOf(p), 'longest_berth_m']} label={`Panjang dermaga ${p.name}`} /> },
            { key: 'l', head: 'LOA maks, m', width: 80, mono: true, render: (p) => <span className="text-abu">{p.longest_berth_m ? num(p.longest_berth_m / ratio) : '–'}</span> },
            { key: 'p', head: 'Produktivitas bongkar muat', width: 150, input: true, render: (p) => <Cell path={['ports', c.ports.indexOf(p), 'productivity', 'value']} label={`Produktivitas ${p.name}`} unit={p.productivity.unit.replace('/h', '/j')} /> },
            { key: 'k', head: 'Tarif', render: (p) => <span className="text-[13px] text-abu">{/^\d/.test(String(p.tariff_class)) ? `kelas ${p.tariff_class}` : p.tariff_class}</span> },
          ]}
        />
        <Note>Jarak ke KEK = mil laut sekali jalan ke Batu Ampar (K15: sheet Rute, kolom X); pola round trip, jadi pergi = pulang. LOA maks = dermaga terpanjang ÷ {num(ratio, 2)} (turunan langsung, abu). {missing.map((p) => shortPortName(p.name)).join(', ')}: panjang dermaga belum ada datanya.</Note>
      </Section>

      <Section title="Jarak rute ke Batu Ampar" aside={<span className="text-[13px] text-abu">mil laut (NM) sekali jalan · diedit di tabel atas</span>}>
        <BarRows
          colors={[C.biru]}
          rows={routeRows.map(({ f, d }) => ({
            label: `${shortPortName(portOfRoute(c, f.route_id)?.name ?? '')} · ${f.id}`,
            parts: [d],
            total: num(d),
            strong: f.id === flowId,
          }))}
        />
        <Note>Flow yang sedang dipilih (layar 6) ditebalkan. Semua rute pola round trip; muatan penuh satu arah.</Note>
      </Section>

      <Split
        left={
          <>
            <h2 className="m-0 pb-4 text-xl font-normal">Tapak TERSUS</h2>
            {site.terminals.map((t) => (
              <DefRow key={t.id} label={t.name} labelWidth={150}>
                <span className="font-mono">{num(t.berth_unit_length_m)} × {num(t.berth_width_m)} m · {t.cargo_forms.join(' ')}</span>
              </DefRow>
            ))}
            <DefRow label="Trestle maks" labelWidth={150}><span className="font-mono">{num(site.trestle?.max_length_m ?? 0)} m · lebar {num(site.trestle?.width_mp_m ?? 0)} m</span></DefRow>
            <DefRow label="Opsi keruk" labelWidth={150} last><span className="font-mono">trestle {num(site.trestle_dredge?.trestle_length_m ?? 0)} m · {num(site.trestle_dredge?.existing_depth_m ?? 0, 1)} m</span></DefRow>
          </>
        }
        right={
          <>
            <div className="flex items-center pb-4">
              <h2 className="m-0 grow text-xl font-normal">Kondisi perairan</h2>
              {site.bathymetry_source === 'dummy' && <Badge kind="asumsi">batimetri dummy</Badge>}
            </div>
            {w && (
              <>
                <DefRow label="Angin · gelombang" justify><span className="font-mono">{num(w.wind_kn)} kn · {num(w.wave_height_m, 2)} m</span></DefRow>
                <DefRow label="Arus melintang · memanjang" justify><span className="font-mono">{num(w.cross_current_kn, 1)} · {num(w.longitudinal_current_kn, 1)} kn</span></DefRow>
                <DefRow label="Dasar laut · jalur" justify>{String(w.seabed).replace('_', ' ')} · {w.lanes} jalur</DefRow>
                <DefRow label="Kedalaman perlu" justify last><span className="font-mono">{num(w.depth_factor_of_draft, 1)} × draft</span></DefRow>
              </>
            )}
            <span className="pt-2"><Note>Pilihan trestle atau keruk berdasarkan profil ini ada di layar 8 (I8).</Note></span>
          </>
        }
      />

      <Section title="Profil batimetri tapak (I8)" aside={<span className="text-[13px] text-abu">kedalaman diukur dari LWS, positif ke bawah</span>}>
        <BathyEditor />
      </Section>
    </>
  )
}
