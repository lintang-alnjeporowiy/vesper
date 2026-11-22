// ─────────────────────────────────────────────────────────────────────────────
// SEMUA ANGKA DI FILE INI ADALAH PLACEHOLDER (estimasi kasar / angka Excel K15),
// BUKAN hasil engine. Ditampilkan dengan badge `placeholder` sampai modul engine
// terkait tersambung (Tahap 4–10). Jangan dipakai sebagai acuan perhitungan.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Nilai placeholder turunan untuk contoh jejak in.damai · AETOS · tahun 10 (dan terminal MP tahun 13).
 * Dipakai laci jejak untuk mengisi kolom nilai masukan/turunan; konteks lain tampil "–".
 * Definisi variabel (rumus, dependensi, Excel) ada di registry.json, bukan di sini.
 */
export const PH_SAMPLE_CTX = { flow: 'in.damai', ship: 'ship.aetos', year: 10 }
export const PH_SAMPLE: Record<string, string> = {
  'demand.base': '4,65 jt t',
  'cargo.demand_unit': '4,65 jt t',
  'vessel.payload': '32.636 t',
  'vessel.feasible': 'layak',
  'vessel.compatible': 'ya',
  'vessel.neq': '4 alat',
  'vessel.ballast_speed': '15,6 kn',
  'voyage.freq': '143 call/th',
  'voyage.q': '32.517 t',
  'voyage.t_port_kek': '0,9 hari',
  'voyage.t_port_ext': '1,4 hari',
  'voyage.t_port': '2,3 hari',
  'voyage.t_fix': '0,4 hari',
  'voyage.t_sea': '5,3 hari',
  'voyage.rtd': '8,0 hari',
  'voyage.f_max': '45 call/kapal',
  'voyage.n_ship': '4 unit',
  'voyage.utilization': '78 %',
  'shipcost.tch': 'Rp 230 M',
  'shipcost.voyage': 'Rp 260 M',
  'shipcost.port': 'Rp 73 M',
  'shipcost.total': 'Rp 563 M',
  'shipcost.unit': '121 rb/t',
  'terminal.ship_days': '129 hari',
  'terminal.berth_days': '164 hari',
}

// ── Layar 6: armada in.damai ─────────────────────────────────────────────────
export const CHAIN_DAMAI: { id: string; label: string; value: string; input?: boolean; final?: boolean }[] = [
  { id: 'demand.base', label: 'Demand', value: '4,65 jt t', input: true },
  { id: 'vessel.payload', label: 'Payload', value: '32.636 t', input: true },
  { id: 'voyage.freq', label: 'Frekuensi', value: '143 /th' },
  { id: 'voyage.t_port', label: 'Port time', value: '2,7 hr' },
  { id: 'voyage.t_sea', label: 'Sea time', value: '5,3 hr' },
  { id: 'voyage.rtd', label: 'RTD', value: '8,0 hr' },
  { id: 'voyage.n_ship', label: 'Jumlah kapal', value: '4 unit', final: true },
]

export const KPI_FLEET = [
  { label: 'Utilisasi kapal', value: '78 %', v: 'voyage.utilization' },
  { label: 'Shipping cost / th', value: 'Rp 563 M', v: 'shipcost.total' },
  { label: 'Unit cost', value: '121 rb/t', v: 'shipcost.unit' },
  { label: 'Berth-days KEK', value: '164 hr', v: 'terminal.berth_days' },
]

/** Estimasi kasar per kandidat GC untuk in.damai tahun 10 (bukan engine). */
export const FLEET_CANDIDATES: Record<string, { rtd: number; ships: number; unitCostRb: number }> = {
  'ship.gemini_dream': { rtd: 6.5, ships: 12, unitCostRb: 168 },
  'ship.ashico_victoria': { rtd: 6.6, ships: 10, unitCostRb: 160 },
  'ship.al_amal': { rtd: 6.4, ships: 9, unitCostRb: 152 },
  'ship.21_panda': { rtd: 6.5, ships: 8, unitCostRb: 147 },
  'ship.simas': { rtd: 6.6, ships: 6, unitCostRb: 139 },
  'ship.han_ren': { rtd: 6.7, ships: 6, unitCostRb: 134 },
  'ship.aetos': { rtd: 8.0, ships: 4, unitCostRb: 121 },
}

// ── Layar 2: proyeksi inbound (juta ton; fantasi ribu TEU) ──────────────────
export const PROJECTION: Record<string, number[]> = {
  'in.damai': [3.0, 3.15, 3.31, 3.47, 3.65, 3.83, 4.02, 4.22, 4.43, 4.65, 4.89, 5.13, 5.39, 5.66, 5.94, 6.24, 6.55, 6.88, 7.22, 7.58],
  'in.esa': [0, 0, 0, 0, 0, 0, 0, 2.0, 2.06, 2.12, 2.19, 2.25, 2.32, 2.39, 2.46, 2.53, 2.61, 2.69, 2.77, 2.85],
  'in.baru': [0, 0, 0, 0, 0, 0, 0, 4.5, 4.68, 4.87, 5.06, 5.26, 5.47, 5.69, 5.92, 6.16, 6.4, 6.66, 6.93, 7.2],
  'in.adi': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5.0, 5.15, 5.3, 5.46, 5.63, 5.8, 5.97, 6.15],
  'in.fantasi': [0, 0, 100, 104, 108.2, 112.5, 117, 121.7, 126.5, 131.6, 136.9, 142.3, 148, 154, 160, 160, 160, 160, 160, 160],
}

export const TEU_CALC = { cartonsPerTeu: 392, tonPerTeu: 7.3, teuYear10: '545 rb' }

// ── Layar 7: biaya pelayaran tahun 10 (Rp miliar: TCH, BBM, pelabuhan) ─────
export const SHIPPING_Y10: Record<string, [number, number, number] | null> = {
  'in.damai': [230, 260, 73],
  'out.damai': [220, 176, 81],
  'in.fantasi': [140, 120, 50],
  'out.fantasi': [190, 220, 60],
  'in.esa': [80, 104, 24],
  'out.esa': [28, 24, 12],
  'in.baru': [140, 190, 24],
  'out.baru': [72, 56, 28],
  'in.adi': null,
  'out.adi': null,
}

export const SHIPPING_DETAIL_DAMAI = [
  { year: 1, ships: 3, calls: 92, tch: 172, bbm: 168, port: 47, rpPerT: 129 },
  { year: 5, ships: 3, calls: 112, tch: 172, bbm: 204, port: 57, rpPerT: 119 },
  { year: 10, ships: 4, calls: 143, tch: 230, bbm: 260, port: 73, rpPerT: 121 },
  { year: 15, ships: 5, calls: 182, tch: 287, bbm: 331, port: 93, rpPerT: 120 },
  { year: 20, ships: 6, calls: 232, tch: 345, bbm: 423, port: 119, rpPerT: 117 },
]

/** Komponen biaya pelabuhan per call (placeholder, contoh in.damai · AETOS di Badas). Dihitung engine Tahap 6. */
export const PORT_CALL_DAMAI = [
  { comp: 'Labuh', basis: 'GT × tarif labuh per kunjungan', value: 4.1 },
  { comp: 'Pandu', basis: 'gerakan × (tarif tetap + tarif variabel × GT)', value: 9.8 },
  { comp: 'Tunda', basis: 'gerakan × (tarif tetap + tarif variabel × GT), rentang GT', value: 21.6 },
  { comp: 'Tambat', basis: 'GT × tarif per etmal × lama tambat (etmal)', value: 6.3 },
  { comp: 'Bongkar muat', basis: 'muatan × tarif B/M per ton atau per TEU', value: 468.0 },
]

// ── Layar 8: terminal KEK ───────────────────────────────────────────────────
export const TERMINAL_Y13 = {
  MP: { berthDays: 547, berths: 3, equipment: 12, bor: 0.5 },
  CC: { berthDays: 183, berths: 1, equipment: 2, bor: 0.5 },
}
export const STAGING = {
  years: Array.from({ length: 20 }, (_, i) => i + 1),
  mpBerths: [1, 1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
  mpEquipment: [4, 4, 4, 4, 4, 4, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
  ccBerths: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1],
}
export const STORAGE_Y13 = [
  { v: 'storage.gc', commodity: 'Jagung, pelat, profil baja', facility: 'Lapangan GC', param: 'f 1,5 · 5 m · SOR 0,7', need: '48.000 m²', cost: 'Rp 96 M' },
  { v: 'storage.bulk', commodity: 'Gandum', facility: 'Silo', param: '23.379 m³ · isi 80 %', need: '9 silo', cost: 'USD 288 rb' },
  { v: 'storage.cy', commodity: 'Petikemas, 4 flow', facility: 'Container yard', param: '15 m²/TEU · 5 tier · YOR 0,7', need: '62.000 m²', cost: 'Rp 124 M' },
  { v: 'storage.liquid', commodity: 'CPO, RBD olein', facility: 'Tangki timbun', param: '20.000 m³ · okupansi 0,65', need: '14 tangki', cost: 'Rp 210 M' },
]
export const WATERSIDE_OPTIONS = [
  { id: 'trestle', name: 'Trestle penuh', spec: '500 × 40 m · tinggi 3,3 m · tanpa keruk', cost: 'Rp 1,9 T · PV Rp 1,6 T', delta: null },
  { id: 'trestle_dredge', name: 'Trestle 250 m + keruk', spec: '250 × 50 m · keruk 10,0 → 21,3 m', cost: 'Rp 2,1 T · PV Rp 1,8 T', delta: '+12 %' },
]

/** Kedalaman perlu (m LWS) placeholder = 1,5 × draft terbesar K15; dihitung engine di Tahap 8. */
export const REQUIRED_DEPTH_PH = 21.3

// ── Layar 9: investasi & ringkasan ──────────────────────────────────────────
export const KPI_SUMMARY = [
  { label: 'Total biaya 20 th', value: 'Rp 256 T', v: 'agg.tc' },
  { label: 'Investasi awal / th', value: 'Rp 88 M', v: 'invest.total' },
  { label: 'Anuitas', value: '551 rb/t', v: 'agg.annuity' },
  { label: 'NPV biaya total · objektif', value: 'Rp 48,2 T', v: 'obj.npv', final: true },
]
/** Rp miliar per tahun 0–19: [infrastruktur, alat, penyimpanan] */
export const INVEST_SCHEDULE: [number, number, number][] = Array.from({ length: 20 }, (_, y) => {
  const spikes: Record<number, [number, number, number]> = {
    0: [1900, 400, 270],
    2: [0, 130, 110],
    6: [810, 540, 320],
    11: [320, 160, 400],
    15: [0, 80, 135],
  }
  return spikes[y] ?? [0, 0, 0]
})
export const INVEST_ITEMS = [
  { v: 'invest.waterside', item: 'Trestle 500 m', cat: 'infrastruktur', years: '0', value: 'Rp 1,90 T' },
  { v: 'invest.berth', item: 'Dermaga MP · 3 tambatan', cat: 'infrastruktur', years: '0, 6', value: 'Rp 22,5 M' },
  { v: 'invest.berth', item: 'Jetty CC · 1 tambatan', cat: 'infrastruktur', years: '11', value: 'Rp 8,8 M' },
  { v: 'invest.handling', item: 'Alat HMC · 12 unit', cat: 'alat', years: '0, 6', value: 'Rp 27,9 M' },
  { v: 'invest.handling', item: 'Alat MLA · 2 unit', cat: 'alat', years: '11', value: 'Rp 9,3 M' },
  { v: 'invest.storage', item: 'Penyimpanan PK, CK, GC, CC', cat: 'penyimpanan', years: '0, 2, 6, 11, 15', value: 'Rp 434 M' },
  { v: 'invest.yard_equipment', item: 'Alat lapangan per bentuk muatan', cat: 'alat', years: '0, 6, 11', value: 'Rp 312 M' },
]

// ── Layar 10: optimasi ──────────────────────────────────────────────────────
/** Biaya pelayaran total semua flow per tahun (Rp miliar, placeholder) untuk grafik layar 9. */
export const SHIPPING_BY_YEAR: number[] = Array.from({ length: 20 }, (_, y) => Math.round(1700 + y * 95 + (y > 6 ? 260 : 0)))

/** Jejak konvergensi HiGHS (placeholder): waktu (detik), incumbent & batas bawah NPV biaya total (Rp T). */
export const CONVERGENCE: { t: number; incumbent: number | null; bound: number }[] = [
  { t: 0, incumbent: null, bound: 41.2 },
  { t: 0.4, incumbent: 49.8, bound: 42.0 },
  { t: 1.1, incumbent: 47.1, bound: 43.1 },
  { t: 2.3, incumbent: 46.2, bound: 44.0 },
  { t: 3.6, incumbent: 45.6, bound: 44.7 },
  { t: 5.2, incumbent: 45.3, bound: 45.0 },
  { t: 7.0, incumbent: 45.3, bound: 45.2 },
  { t: 8.4, incumbent: 45.28, bound: 45.28 },
]

export const OPTIM_RESULT = {
  npvDelta: '−6,2 %',
  rows: [
    { what: 'in.damai', manual: 'AETOS', optimum: 'AETOS', delta: null, binding: 'LOA Badas 187 m' },
    { what: 'out.damai', manual: 'INTEGRA', optimum: 'SEABOARD GALAXY', delta: '−3 %', binding: 'LOA Bangkok 202 m' },
    { what: 'in.fantasi', manual: 'ALS CERES', optimum: 'EVER EXCEL', delta: '−9 %', binding: 'kedalaman KEK → biaya trestle' },
    { what: 'in.baru', manual: 'ADELANTE', optimum: 'ADELANTE', delta: null, binding: 'tidak ada' },
    { what: 'Alat MP', manual: 'LHM 280', optimum: 'LHM 420', delta: '−2 %', binding: 'BOR MP mengikat th 8–20' },
    { what: 'Perairan', manual: 'trestle penuh', optimum: 'trestle penuh', delta: null, binding: 'draft terbesar 14,2 m' },
  ],
  top3: [
    { rank: '1 · terpilih', name: 'AETOS', note: '121 rb/t' },
    { rank: '2', name: 'HAN REN', note: '134 rb/t · +11 %' },
    { rank: 'lebih murah tapi gugur', name: 'ACER ARROW', note: 'draft 13,03 m > 11,5 m Badas', bad: true },
  ],
}

// ── Layar 11: skenario ──────────────────────────────────────────────────────
export const SCENARIOS = {
  columns: [
    { name: 'Hasil Evolver K15', sub: 'baseline' },
    { name: 'Optimum v2', sub: 'MILP, terkoreksi' },
    { name: 'HSD +20 %', sub: 'dari optimum v2' },
  ],
  rows: [
    { label: 'NPV biaya total', values: ['Rp 48,2 T', 'Rp 45,2 T', 'Rp 48,9 T'], deltas: [null, { v: '−6,2 %', good: true }, { v: '+8,2 %', good: false }] },
    { label: 'Anuitas', values: ['551 rb/t', '517 rb/t', '559 rb/t'] },
    { label: 'Investasi awal', values: ['Rp 2,12 T', 'Rp 2,05 T', 'Rp 2,05 T'] },
    { label: 'Total kapal tahun 20', values: ['41', '38', '38'] },
    { label: 'Tambatan MP / CC tahun 20', values: ['3 / 1', '3 / 1', '3 / 1'] },
    { label: 'Mode perairan', values: ['trestle penuh', 'trestle penuh', 'trestle penuh'] },
  ],
}
export const TORNADO = [
  { label: 'Harga HSD ±20 %', down: 8.2, up: 8.2 },
  { label: 'Growth muatan ±1 pp', down: 5.8, up: 7.1 },
  { label: 'Kurs ±10 %', down: 4.8, up: 4.8 },
  { label: 'Discount rate 8–12 %', down: 3.1, up: 3.9 },
  { label: 'Produktivitas alat ±20 %', down: 1.9, up: 2.5 },
  { label: 'BOR maks 0,6–0,8', down: 0.9, up: 1.4 },
]

// ── Layar 5: what-if alat ───────────────────────────────────────────────────
export const EQUIP_WHATIF = [
  { label: 'Port time KEK in.damai', value: '0,9 → 0,6 hr', delta: '−33 %', good: true },
  { label: 'Berth-days MP th 13', value: '547 → 410', delta: '−25 %', good: true },
  { label: 'Investasi alat MP', value: 'USD 1,8 → 2,6 jt', delta: '+47 %', good: false },
]

// Kelayakan kapal sementara (aturan SPEC §5.2) — mock sampai engine Tahap 5.
export function feasibilityMock(
  ship: { draft_m: number; loa_m: number },
  port: { max_draft_m: number; longest_berth_m?: number | null },
  loaRatio: number,
): { ok: boolean | null; reasons: string[] } {
  const reasons: string[] = []
  if (ship.draft_m > port.max_draft_m) reasons.push('draft')
  if (port.longest_berth_m == null) return { ok: reasons.length ? false : null, reasons: reasons.length ? reasons : ['LOA ?'] }
  if (ship.loa_m > port.longest_berth_m / loaRatio) reasons.push('LOA')
  return { ok: reasons.length === 0, reasons }
}
