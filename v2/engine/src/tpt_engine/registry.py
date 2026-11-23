"""Registry variabel TPT Planner v2 (SPEC §5, §9.3).

Satu entri = satu variabel: input kasus (per atribut, menunjuk path di `Case`), variabel keputusan,
turunan (satu per baris rumus SPEC §5), metrik laporan, dan objektif. Registry ini HANYA definisi:
rumus ditulis sebagai teks untuk ditampilkan; implementasi hitung ada di `calc/` (Tahap 4+) dan ditunjuk oleh
`impl` ("modul:fungsi" di bawah `tpt_engine.calc`, lihat `IMPL`).

Konvensi
- id: `<modul>.<nama>`; input `in.<entitas>.<atribut>`, keputusan `dv.*`, objektif `obj.*`.
  Modul turunan = nama file di `calc/`: demand, cargo, vessel, voyage, shipcost, terminal, storage,
  waterside, invest, agg.
- case_path (input saja): path di model `Case`; `nama[kunci]` = elemen list yang dipilih konteks
  (flow, ship, port, route, equip, terminal, commodity, ship_type, fuel, tariff_class).
- kind: input | decision | derived | metric (dilaporkan, tidak dipakai variabel lain) | objective.
- audit: ID temuan audit Excel (SPEC §11) yang membuat nilai v2 berbeda dari Excel K15.

Jalankan `uv run --project engine python tools/dump_registry.py` (dari v2/) setelah mengubah file ini.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Literal

from .registry_desc import DESC

Kind = Literal["input", "decision", "derived", "metric", "objective"]
KINDS: tuple[str, ...] = ("input", "decision", "derived", "metric", "objective")


@dataclass(frozen=True)
class VarDef:
    id: str
    label: str
    unit: str
    scope: str  # "global" | "flow" | "ship" | "flow×ship" | "flow×year" | "terminal×year" | ...
    kind: Kind
    formula: str
    deps: tuple[str, ...] = ()
    excel_ref: str | None = None
    section: str = ""  # bagian SPEC, mis. "5.3"
    audit: tuple[str, ...] = ()
    case_path: str | None = None
    screens: tuple[int, ...] = ()  # layar tempat angka/inputnya tampil
    note: str | None = None
    symbol: str | None = None  # notasi singkat di rumus, mis. "RTD", "F_req"
    desc: str = ""  # keterangan singkat & gamblang (registry_desc.py)
    impl: str | None = None  # fungsi engine yang menghitungnya, mis. "demand:demand_base" (IMPL)


def _in(id: str, label: str, unit: str, path: str, *, excel: str | None = None, scope: str = "global",
        sec: str = "4.1", screens: tuple[int, ...] = (), symbol: str | None = None, note: str | None = None) -> VarDef:
    return VarDef(id=id, label=label, unit=unit, scope=scope, kind="input", formula="input kasus",
                  excel_ref=excel, section=sec, case_path=path, screens=screens, symbol=symbol, note=note)


def _d(id: str, label: str, unit: str, scope: str, formula: str, deps: tuple[str, ...] | list[str], *,
       sec: str, excel: str | None = None, audit: tuple[str, ...] = (), screens: tuple[int, ...] = (),
       kind: Kind = "derived", symbol: str | None = None, note: str | None = None) -> VarDef:
    return VarDef(id=id, label=label, unit=unit, scope=scope, kind=kind, formula=formula, deps=tuple(deps),
                  excel_ref=excel, section=sec, audit=audit, screens=screens, symbol=symbol, note=note)


# ─── Input kasus (SPEC §4) ──────────────────────────────────────────────────────────────────────
INPUTS: tuple[VarDef, ...] = (
    # §4.1 kasus & parameter global
    _in("in.horizon.years", "Periode tinjauan", "th", "horizon.years", excel="Model!J403", screens=(1,), symbol="T"),
    _in("in.horizon.phases", "Tahap perencanaan", "th", "horizon.phases", screens=(1, 8)),
    _in("in.horizon.lead", "Masa konstruksi", "th", "horizon.construction_lead_years", screens=(1, 8)),
    _in("in.horizon.berth_lookahead", "Lookahead dermaga", "th", "horizon.berth_lookahead_years", screens=(1, 8)),
    _in("in.horizon.storage_lookahead", "Lookahead penyimpanan", "th", "horizon.storage_lookahead_years", screens=(1,)),
    _in("in.param.at", "Approach time", "jam/call", "params.at_hours", excel="Model!F36", screens=(1,), symbol="AT"),
    _in("in.param.wt", "Waiting time", "jam/call", "params.wt_hours", excel="Model!F37", screens=(1,), symbol="WT"),
    _in("in.param.it", "Idle time", "jam/call", "params.it_hours", excel="Model!F38", screens=(1,), symbol="IT"),
    _in("in.param.working_days", "Hari kerja terminal", "hari/th", "params.working_days_per_year", screens=(1, 8), symbol="WD"),
    _in("in.param.working_hours", "Jam kerja per hari", "jam", "params.working_hours_per_day", screens=(1,)),
    _in("in.param.commission_days", "Commission days kapal", "hari/th", "params.commission_days", screens=(1,), symbol="CD"),
    _in("in.param.bor_max", "BOR maksimum", "–", "params.bor_max", screens=(1, 8), symbol="BOR_max"),
    _in("in.param.mcr", "MCR mesin", "–", "params.mcr", screens=(1,), symbol="MCR"),
    _in("in.param.fuel_share_me", "Porsi pemakaian ME (laut, pelabuhan)", "–", "params.fuel_share_me_sea", screens=(1,)),
    _in("in.param.fuel_share_ae", "Porsi pemakaian AE (laut, pelabuhan)", "–", "params.fuel_share_ae_port", screens=(1,)),
    _in("in.param.fuel_price", "Harga BBM", "Rp/l", "params.fuels[fuel].price_rp_per_l", excel="Model!F45:F46", screens=(1, 7)),
    _in("in.param.fuel_choice", "Jenis BBM ME & AE", "kode", "params.me_fuel", screens=(1,), note="A6: default HSD untuk keduanya"),
    _in("in.param.fuel_density", "Berat jenis BBM", "kg/m³", "params.fuels[fuel].density_kg_m3", excel="Model!F41:F43", screens=(1,)),
    _in("in.param.sfoc_bands", "Tabel SFOC per rentang daya", "g/kWh", "params.sfoc_me_bands", screens=(1,)),
    _in("in.param.ae_me_ratio", "Rasio daya AE/ME default", "–", "params.ae_me_power_ratio", screens=(1,)),
    _in("in.param.usd_rate", "Kurs", "Rp/USD", "params.usd_rate", excel="Model!F47", screens=(1, 7)),
    _in("in.param.discount_rate", "Discount rate (WACC)", "/th", "params.discount_rate", excel="Model!J403", screens=(1, 9), symbol="r"),
    _in("in.param.escalation_infra", "Eskalasi harga infrastruktur", "/th", "params.escalation_infra", screens=(1, 9)),
    _in("in.param.escalation_equipment", "Eskalasi harga alat", "/th", "params.escalation_equipment", screens=(1,)),
    _in("in.param.ballast_ratio", "Rasio kecepatan ballast", "–", "params.ballast_speed_ratio", screens=(1,), note="A5"),
    _in("in.param.payload_ratio", "α payload/DWT", "–", "params.payload_dwt_ratio", screens=(1,), symbol="α"),
    _in("in.param.teu_weight_ratio", "α batas berat per TEU", "–", "params.teu_weight_dwt_ratio", screens=(1,)),
    _in("in.param.teu_capacity_ratio", "Rasio kapasitas TEU default", "–", "params.teu_capacity_dwt_ratio", screens=(1,)),
    _in("in.param.teu_nominal_weight", "Berat nominal per TEU", "t/TEU", "params.teu_nominal_weight_t", screens=(1,)),
    _in("in.param.berth_loa_ratio", "Rasio dermaga ÷ LOA minimum", "–", "params.berth_loa_min_ratio", screens=(1, 3, 6)),
    _in("in.param.cargo_per_call_mode", "Mode muatan per call", "interval | full_load", "params.cargo_per_call_mode", screens=(1,)),
    # §4.3 komoditas & kontainer
    _in("in.container.dims", "Dimensi dalam kontainer 20′", "m", "params.container.inner_length_m", sec="4.3", screens=(2,), symbol="Lc·Wc·Hc"),
    _in("in.container.tare", "Tare kontainer", "t", "params.container.tare_t", sec="4.3", screens=(2,)),
    _in("in.container.max_net", "Muatan bersih maks kontainer", "t", "params.container.max_net_t", sec="4.3", screens=(2,)),
    _in("in.cmdty.packaging", "Kemasan komoditas (dimensi, berat)", "m · kg", "commodities[commodity].packaging", excel="Muatan!B:M",
        scope="commodity", sec="4.3", screens=(2,), symbol="l·w·h, w_box"),
    _in("in.cmdty.stowage", "Stowage factor", "m³/t", "commodities[commodity].stowage_factor_m3_t", scope="commodity", sec="4.3", screens=(2,), symbol="SF"),
    _in("in.cmdty.density", "Densitas komoditas", "t/m³", "commodities[commodity].density_t_m3", scope="commodity", sec="4.3", screens=(2,), symbol="ρ"),
    # §4.2 tenant & aliran muatan
    _in("in.flow.start_year", "Tahun mulai", "th-ke", "flows[flow].volume.start_year", excel="Proyeksi Muatan!F", scope="flow", sec="4.2", screens=(2,), symbol="t₀"),
    _in("in.flow.initial", "Volume awal", "t | TEU", "flows[flow].volume.initial", excel="Proyeksi Muatan!C", scope="flow", sec="4.2", screens=(2,), symbol="V₀"),
    _in("in.flow.maximum", "Volume maksimum", "t | TEU", "flows[flow].volume.maximum", excel="Proyeksi Muatan!D", scope="flow", sec="4.2", screens=(2,), symbol="Dmax"),
    _in("in.flow.growth", "Laju pertumbuhan", "/th", "flows[flow].volume.growth_rate", excel="Proyeksi Muatan!E", scope="flow", sec="4.2", screens=(2,), symbol="g"),
    _in("in.flow.ratio", "Rasio konversi in→out", "–", "flows[flow].volume.ratio", excel="Proyeksi Muatan!C12", scope="flow", sec="4.2", screens=(2,), symbol="r"),
    _in("in.flow.unit", "Satuan flow", "ton | TEU", "flows[flow].unit", scope="flow", sec="4.2", screens=(2,)),
    _in("in.flow.cargo_form", "Bentuk muatan", "kode", "flows[flow].cargo_form", scope="flow", sec="4.2", screens=(2, 6)),
    _in("in.flow.route", "Rute flow", "id", "flows[flow].route_id", scope="flow", sec="4.2", screens=(2, 6)),
    _in("in.compat", "Matriks bentuk muatan × tipe kapal", "boolean", "compatibility", sec="4.6", screens=(4,)),
    # §4.4 pelabuhan eksternal & rute
    _in("in.port.max_draft", "Draft maks pelabuhan", "m", "ports[port].max_draft_m", excel="Data Pelabuhan", scope="port", sec="4.4", screens=(3, 6)),
    _in("in.port.max_loa", "LOA maks eksplisit", "m", "ports[port].max_loa_m", scope="port", sec="4.4", screens=(3,)),
    _in("in.port.longest_berth", "Dermaga terpanjang", "m", "ports[port].longest_berth_m", scope="port", sec="4.4", screens=(3, 6)),
    _in("in.port.productivity", "Produktivitas B/M pelabuhan", "t/jam | TEU/jam", "ports[port].productivity", excel="Data Pelabuhan",
        scope="port", sec="4.4", screens=(3,), note="A3: total per kapal atau per alat × jumlah alat"),
    _in("in.port.tariff_class", "Kelas tarif pelabuhan", "kelas", "ports[port].tariff_class", scope="port", sec="4.4", screens=(3,)),
    _in("in.port.kind", "Domestik / luar negeri", "–", "ports[port].kind", scope="port", sec="4.4", screens=(3,)),
    _in("in.port.berth_type", "Jenis dermaga (beton/dolphin)", "–", "ports[port].berth_type", scope="port", sec="4.4", screens=(3,)),
    _in("in.route.distance", "Jarak rute", "NM", "routes[route].legs", excel="Rute!Y20:Y29", scope="route", sec="4.4", screens=(3, 6)),
    _in("in.route.laden", "Kaki bermuatan / ballast", "–", "routes[route].legs", scope="route", sec="4.4", screens=(3,)),
    # §4.5 tapak TERSUS
    _in("in.term.cargo_forms", "Bentuk muatan per terminal", "kode", "kek_site.terminals[terminal].cargo_forms", scope="terminal", sec="4.5", screens=(8,)),
    _in("in.term.berth_length", "Panjang unit tambatan", "m", "kek_site.terminals[terminal].berth_unit_length_m", scope="terminal", sec="4.5", screens=(8,), symbol="L_unit"),
    _in("in.term.berth_width", "Lebar dermaga", "m", "kek_site.terminals[terminal].berth_width_m", scope="terminal", sec="4.5", screens=(8,)),
    _in("in.term.layout", "Tata letak tambatan (dermaga menerus / jetty)", "–", "kek_site.terminals[terminal].berth_layout", scope="terminal", sec="4.5", screens=(8,)),
    _in("in.site.bathymetry", "Profil batimetri tapak", "m vs m", "kek_site.bathymetry", excel="Trestle!B34:B46", sec="4.5", screens=(3, 8)),
    _in("in.site.waterside", "Kondisi perairan (angin, arus, gelombang, alur)", "–", "kek_site.waterside", excel="Fasilitas Perairan", sec="4.5", screens=(3,)),
    _in("in.site.depth_factor", "Faktor kedalaman ÷ draft", "–", "kek_site.waterside.depth_factor_of_draft", sec="4.5", screens=(3, 8)),
    _in("in.site.trestle", "Spesifikasi trestle (panjang maks, lebar, tinggi)", "m", "kek_site.trestle", excel="Trestle", sec="4.5", screens=(3, 8)),
    _in("in.site.trestle_dredge", "Opsi trestle + keruk", "m", "kek_site.trestle_dredge", excel="Trestle", sec="4.5", screens=(8,)),
    _in("in.site.port_charges", "Jasa kepelabuhanan TERSUS", "none | tariff", "kek_site.port_charges", sec="4.5", screens=(3,)),
    # §4.6 kandidat kapal
    _in("in.ship.type", "Tipe kapal", "kode", "ships[ship].ship_type", excel="Data Kapal", scope="ship", sec="4.6", screens=(4, 6)),
    _in("in.ship.dwt", "DWT", "t", "ships[ship].dwt_t", excel="Data Kapal!M", scope="ship", sec="4.6", screens=(4, 6), symbol="DWT"),
    _in("in.ship.payload", "Payload override", "t", "ships[ship].payload_t", scope="ship", sec="4.6", screens=(4,)),
    _in("in.ship.teu", "Kapasitas TEU", "TEU", "ships[ship].teu_capacity", scope="ship", sec="4.6", screens=(4,), symbol="TEU_k"),
    _in("in.ship.loa", "LOA", "m", "ships[ship].loa_m", scope="ship", sec="4.6", screens=(4, 6), symbol="LOA_k"),
    _in("in.ship.beam", "Lebar (B)", "m", "ships[ship].beam_m", scope="ship", sec="4.6", screens=(4,), symbol="B"),
    _in("in.ship.draft", "Sarat (T)", "m", "ships[ship].draft_m", scope="ship", sec="4.6", screens=(4, 6), symbol="T_k"),
    _in("in.ship.speed", "Kecepatan dinas", "knot", "ships[ship].speed_kn", scope="ship", sec="4.6", screens=(4, 6), symbol="Vs"),
    _in("in.ship.ballast_speed", "Kecepatan ballast", "knot", "ships[ship].ballast_speed_kn", scope="ship", sec="4.6", screens=(4,)),
    _in("in.ship.gt", "GT", "GT", "ships[ship].gt", scope="ship", sec="4.6", screens=(4,)),
    _in("in.ship.me_kw", "Daya mesin induk", "kW", "ships[ship].me_kw", scope="ship", sec="4.6", screens=(4, 6), symbol="P_ME"),
    _in("in.ship.ae_kw", "Daya mesin bantu", "kW", "ships[ship].ae_kw", scope="ship", sec="4.6", screens=(4,), symbol="P_AE"),
    _in("in.ship.sfoc", "SFOC override", "g/kWh", "ships[ship].sfoc_me_g_kwh", scope="ship", sec="4.6", screens=(4,)),
    _in("in.stype.tch_points", "Tabel tarif charter pasar", "USD/hari", "ship_types[ship_type].tch_points", excel="TCH!B4:W12",
        scope="ship_type", sec="4.6", screens=(4,)),
    # §4.7 alat B/M
    _in("in.equip.productivity", "Produktivitas alat per bentuk muatan", "t/jam", "equipment[equip].productivity", excel="Alat BM",
        scope="equip", sec="4.7", screens=(5, 8), symbol="prod_e"),
    _in("in.equip.price", "Harga alat", "USD", "equipment[equip].price_usd", excel="Alat BM", scope="equip", sec="4.7", screens=(5, 8)),
    _in("in.equip.reach", "Jangkauan alat", "m", "equipment[equip].reach_m", scope="equip", sec="4.7", screens=(5,)),
    _in("in.rule.loa_bands", "Alat per tambatan menurut LOA", "unit", "equipment_rules.loa_bands", excel="Model!CF34:CH37", sec="4.7", screens=(5, 8)),
    _in("in.rule.max_per_berth", "Batas alat per tambatan", "unit", "equipment_rules.max_per_berth", sec="4.7", screens=(5, 8)),
    # §4.8 tarif pelabuhan
    _in("in.tariff.labuh", "Tarif labuh", "Rp | USD /GT", "tariffs.classes[tariff_class].labuh_domestic_rp_per_gt", excel="Biaya Pelabuhan", sec="4.8", screens=(3, 7)),
    _in("in.tariff.pandu", "Tarif pandu", "Rp | USD /GT/gerakan", "tariffs.classes[tariff_class].pandu_domestic_var_rp_per_gt", excel="Biaya Pelabuhan", sec="4.8", screens=(3, 7)),
    _in("in.tariff.tambat", "Tarif tambat", "Rp | USD /GT/etmal", "tariffs.classes[tariff_class].tambat_domestic_rp_per_gt_etmal", excel="Biaya Pelabuhan", sec="4.8", screens=(3, 7)),
    _in("in.tariff.tunda", "Tarif tunda per rentang GT", "Rp | USD", "tariffs.classes[tariff_class].tug", excel="Biaya Pelabuhan", sec="4.8", screens=(3, 7)),
    _in("in.tariff.bm", "Tarif B/M (OPP/OPT)", "Rp/t | Rp/TEU", "tariffs.classes[tariff_class].bm_domestic_rp_per_ton", excel="Biaya Pelabuhan", sec="4.8", screens=(3, 7)),
    _in("in.tariff.gt_bands", "Rentang GT tarif tunda", "GT", "tariffs.tug_gt_bands", excel="Biaya Pelabuhan", sec="4.8", screens=(3,)),
    # §4.9 penyimpanan
    _in("in.storage.dwell", "Mode dwell time", "from_consumption | fixed", "storage.dwell_time_mode", excel="Fasilitas Daratan!F13:F16 · F132 · F173:F175 · F224:F225", sec="4.9", screens=(8,)),
    _in("in.storage.share", "Porsi muatan masuk penyimpanan", "–", "storage.inbound_share", sec="4.9", screens=(8,)),
    _in("in.storage.cy", "Parameter container yard", "m²/TEU · tier · YOR", "storage.container_yard", excel="Fasilitas Daratan", sec="4.9", screens=(8,)),
    _in("in.storage.gc", "Parameter lapangan/gudang GC", "f · m · SOR", "storage.general_cargo", excel="Fasilitas Daratan", sec="4.9", screens=(8,)),
    _in("in.storage.bulk", "Parameter curah kering & silo", "f · Rc · m³", "storage.dry_bulk", excel="Fasilitas Daratan", sec="4.9", screens=(8,)),
    _in("in.storage.liquid", "Parameter tangki timbun", "okupansi · m³", "storage.liquid", excel="Fasilitas Daratan", sec="4.9", screens=(8,)),
    _in("in.storage.yard_equipment", "Alat lapangan per bentuk muatan", "unit/jam", "storage.yard_equipment", excel="Fasilitas Daratan", sec="4.9", screens=(8,)),
    _in("in.storage.yard_role", "Peran alat lapangan (penumpukan / angkutan)", "yard | transport", "storage.yard_equipment[alat].role", sec="4.9", screens=(8,)),
    # §5.8 harga satuan investasi (sheet Investasi)
    _in("in.price.berth", "Harga satuan dermaga & jetty", "Rp/m²", "unit_prices", excel="Investasi!B2:F34", sec="5.8", screens=(9,)),
    _in("in.price.trestle", "Harga satuan trestle", "Rp/m²", "unit_prices", excel="Investasi", sec="5.8", screens=(9,)),
    _in("in.price.dredge", "Harga satuan keruk", "Rp/m³", "unit_prices", excel="Investasi", sec="5.8", screens=(9,)),
    _in("in.price.storage", "Harga satuan lapangan, gudang, tangki", "Rp/m² | Rp/unit", "unit_prices", excel="Investasi", sec="5.8", screens=(9,)),
    _in("in.price.yard_equipment", "Harga alat lapangan", "Rp/unit", "unit_prices", excel="Investasi", sec="5.8", screens=(9,)),
)

# ─── Variabel keputusan (SPEC §6.1) ─────────────────────────────────────────────────────────────
DECISIONS: tuple[VarDef, ...] = (
    _d("dv.ship", "Kapal terpilih per flow", "y[f,k] ∈ {0,1}", "flow×ship", "Σ_k y[f,k] = 1, hanya kapal feasible",
       ("vessel.feasible",), sec="6.1", excel="Model!CG8:CG17", screens=(6, 10), kind="decision", symbol="y[f,k]"),
    _d("dv.equip", "Alat B/M per terminal", "z[τ,e] ∈ {0,1}", "terminal×equip", "Σ_e z[τ,e] = 1, alat dengan jangkauan cukup",
       ("vessel.reach_ok",), sec="6.1", excel="Model!DB8:DB9", screens=(8, 10), kind="decision", symbol="z[τ,e]"),
    _d("dv.waterside", "Mode perairan: trestle / keruk / campuran", "w[m] | θ ∈ [0,1]", "global", "pilih biaya perairan termurah",
       (), sec="6.1", excel="Model!K395", screens=(8, 10), kind="decision", symbol="w, θ"),
    _d("dv.speed", "Kecepatan operasi (opsional)", "knot", "flow", "≤ Vs kapal; slow steaming = ekstensi v2",
       ("in.ship.speed",), sec="6.1", screens=(6, 10), kind="decision", symbol="V"),
)

# ─── Turunan (SPEC §5) ──────────────────────────────────────────────────────────────────────────
DERIVED: tuple[VarDef, ...] = (
    # §5.1 demand & konversi muatan
    _d("demand.base", "Demand flow independen", "t | TEU per th", "flow×year",
       "D[t] = 0 bila t < t₀; V₀ di t₀; min(Dmax, D[t−1]·(1+g))",
       ("in.flow.start_year", "in.flow.initial", "in.flow.maximum", "in.flow.growth", "in.horizon.years"),
       sec="5.1", excel="Model!N3:AG3", audit=("A4", "A12"), screens=(2, 6), symbol="D[f,t]"),
    _d("demand.ratio", "Demand flow rasio (outbound)", "t | TEU per th", "flow×year", "D_out[t] = r · D_in[t] (aturan volume §4.2)",
       ("demand.base", "in.flow.ratio"), sec="5.1", excel="Proyeksi Muatan!G12:Z16", audit=("A4",), screens=(2,)),
    _d("cargo.netmax", "Muatan bersih maks per TEU", "t/TEU", "flow×ship", "NetMax = min(payload kontainer, α·DWT_k / TEU_k − tare)",
       ("in.container.max_net", "in.param.teu_weight_ratio", "in.ship.dwt", "vessel.teu_cap", "in.container.tare"),
       sec="5.1", excel="Muatan", audit=("A8",), screens=(2,), symbol="NetMax"),
    _d("cargo.box_per_teu", "Kemasan per TEU", "kemasan/TEU", "flow×ship", "nBox = min(⌊Lc/l⌋·⌊Wc/w⌋·⌊Hc/h⌋, ⌊NetMax / w_box⌋)",
       ("in.container.dims", "in.cmdty.packaging", "cargo.netmax"), sec="5.1", excel="Muatan", screens=(2,), symbol="nBox"),
    _d("cargo.ton_per_teu", "Ton per TEU", "t/TEU", "flow×ship", "nBox · w_box (atau Vc / SF), dibatasi NetMax",
       ("cargo.box_per_teu", "in.cmdty.packaging", "in.cmdty.stowage", "in.container.dims", "cargo.netmax"),
       sec="5.1", excel="Muatan!L19:L22", screens=(2,), symbol="tonPerTEU"),
    _d("cargo.demand_unit", "Demand dalam satuan kapal", "t | TEU per th", "flow×year",
       "D_TEU = ⌈D_ton / tonPerTEU⌉ untuk muatan PK bersatuan ton; selain itu D",
       ("demand.base", "demand.ratio", "cargo.ton_per_teu", "in.flow.unit", "in.flow.cargo_form", "dv.ship"),
       sec="5.1", excel="Proyeksi Muatan!G20:Z24", audit=("A12",), screens=(2, 6), symbol="D"),
    # §5.2 kandidat & kelayakan kapal
    _d("vessel.teu_cap", "Kapasitas TEU efektif", "TEU", "ship", "TEU_k isian; bila kosong ⌊rasio · DWT / berat nominal per TEU⌋",
       ("in.ship.teu", "in.ship.dwt", "in.param.teu_capacity_ratio", "in.param.teu_nominal_weight"), sec="5.2", screens=(4,)),
    _d("vessel.payload", "Payload efektif", "t | TEU", "flow×ship",
       "GC/CK/CC: α·DWT (atau override); PK: kapasitas TEU, cek TEU·tonPerTEU ≤ 0,9·DWT",
       ("in.ship.dwt", "in.param.payload_ratio", "in.ship.payload", "vessel.teu_cap", "cargo.ton_per_teu", "in.flow.cargo_form"),
       sec="5.2", excel="Data Kapal!N · Model!AL26", audit=("A8",), screens=(4, 6), symbol="payload[k]"),
    _d("vessel.compatible", "Kompatibel bentuk muatan", "boolean", "flow×ship", "tipe kapal k ∈ tipe yang diizinkan untuk bentuk muatan f",
       ("in.ship.type", "in.flow.cargo_form", "in.compat"), sec="5.2", screens=(4, 6)),
    _d("vessel.feasible", "Kelayakan kapal (+ alasan gugur)", "boolean", "flow×ship",
       "compatible ∧ T_k ≤ draft pelabuhan ∧ dermaga terpanjang ≥ rasio·LOA_k ∧ LOA_k ≤ LOA maks",
       ("vessel.compatible", "in.ship.draft", "in.ship.loa", "in.port.max_draft", "in.port.longest_berth", "in.port.max_loa",
        "in.param.berth_loa_ratio", "in.flow.route"),
       sec="5.2", excel="Model!CH24:CJ32", screens=(4, 6), symbol="feasible[f,k]"),
    _d("vessel.neq", "Alat per tambatan", "unit", "ship×terminal", "dari tabel rentang LOA, dibatasi batas per terminal",
       ("in.ship.loa", "in.rule.loa_bands", "in.rule.max_per_berth"), sec="5.2", excel="Model!CI8:CI17", audit=("A10",),
       screens=(5, 6, 8), symbol="nEq[k]"),
    _d("vessel.reach_ok", "Jangkauan alat cukup", "boolean", "ship×equip", "radius alat ≥ B kapal + margin",
       ("in.equip.reach", "in.ship.beam"), sec="5.2", screens=(5,), symbol="reach_ok[k,e]"),
    _d("vessel.ballast_speed", "Kecepatan ballast efektif", "knot", "ship", "V_ballast isian; bila kosong rasio · Vs",
       ("in.ship.ballast_speed", "in.param.ballast_ratio", "dv.speed"), sec="5.3", audit=("A5",), screens=(4,)),
    _d("vessel.ae_kw", "Daya AE efektif", "kW", "ship", "P_AE isian; bila kosong rasio · P_ME",
       ("in.ship.ae_kw", "in.ship.me_kw", "in.param.ae_me_ratio"), sec="5.4", screens=(4,)),
    _d("vessel.sfoc_me", "SFOC mesin induk", "g/kWh", "ship", "override kapal; bila kosong dari tabel rentang daya ME",
       ("in.ship.sfoc", "in.param.sfoc_bands", "in.ship.me_kw"), sec="5.4", excel="Model!AL35:BZ35", screens=(4,)),
    _d("vessel.sfoc_ae", "SFOC mesin bantu", "g/kWh", "ship", "override kapal; bila kosong dari tabel rentang daya AE",
       ("in.ship.sfoc", "in.param.sfoc_bands", "vessel.ae_kw"), sec="5.4", excel="Model!AL36:BZ36", screens=(4,)),
    # §5.3 operasi pelayaran
    _d("voyage.freq", "Frekuensi", "call/th", "flow×year", "F_req = ⌈D / payload⌉",
       ("cargo.demand_unit", "vessel.payload", "dv.ship"), sec="5.3", excel="Model!M28:AF28", screens=(6, 7), symbol="F_req"),
    _d("voyage.q", "Muatan per call", "t | TEU", "flow×year", "interval: D / F; full-load: payload",
       ("cargo.demand_unit", "voyage.freq", "vessel.payload", "in.param.cargo_per_call_mode"), sec="5.3", excel="Model!N41:AG41",
       screens=(6,), symbol="q"),
    _d("voyage.t_port_kek", "Port time KEK", "hari/call", "flow×year", "q / (prod_e,form · nEq) / 24",
       ("voyage.q", "in.equip.productivity", "vessel.neq", "dv.equip", "in.term.cargo_forms"), sec="5.3",
       excel="Model!M68:AF68 (Excel: hari/th)", audit=("A2", "A10"), screens=(6,), symbol="tPortKEK"),
    _d("voyage.t_port_ext", "Port time pelabuhan asal/tujuan", "hari/call", "flow×year",
       "q / prodTotal_port / 24 (total per kapal atau per alat × jumlah alat)",
       ("voyage.q", "in.port.productivity", "in.flow.route"), sec="5.3", excel="Model!M82:AF82 (Excel: hari/th)", audit=("A3",),
       screens=(6,), symbol="tPortExt"),
    _d("voyage.t_port", "Port time per call", "hari/call", "flow×year", "tPortKEK + tPortExt",
       ("voyage.t_port_kek", "voyage.t_port_ext"), sec="5.3", excel="Model!M182:AF182", screens=(6,)),
    _d("voyage.t_fix", "Waktu tetap per call", "hari/call", "global", "tFix = (AT + WT + IT) / 24",
       ("in.param.at", "in.param.wt", "in.param.it"), sec="5.3", screens=(6,), symbol="tFix"),
    _d("voyage.t_sea", "Sea time", "hari/call", "flow×year", "(jarak bermuatan / Vs + jarak ballast / V_ballast) / 24",
       ("in.route.distance", "in.route.laden", "in.ship.speed", "vessel.ballast_speed", "dv.speed", "dv.ship", "in.flow.route"),
       sec="5.3", excel="Model!M156:AF156", audit=("A5",), screens=(6,), symbol="tSea"),
    _d("voyage.rtd", "Round trip days", "hari", "flow×year", "RTD = tSea + tPortKEK + tPortExt + tFix",
       ("voyage.t_sea", "voyage.t_port", "voyage.t_fix"), sec="5.3", excel="Model!M195:AF195", screens=(6,), symbol="RTD"),
    _d("voyage.f_max", "Voyage maks per kapal", "call/kapal/th", "flow×year", "F_max = ⌊CD / RTD⌋",
       ("voyage.rtd", "in.param.commission_days"), sec="5.3", excel="Model!M208:AF208", audit=("A1",), screens=(6,), symbol="F_max"),
    _d("voyage.n_ship", "Jumlah kapal", "unit", "flow×year", "N_ship = ⌈F_req / F_max⌉",
       ("voyage.freq", "voyage.f_max"), sec="5.3", excel="Model!M221:AF221", screens=(6, 7), symbol="N_ship"),
    _d("voyage.utilization", "Utilisasi kapal", "–", "flow×year", "F_req / (N_ship · F_max)",
       ("voyage.freq", "voyage.n_ship", "voyage.f_max"), sec="5.3", screens=(6,), kind="metric"),
    _d("voyage.consumption", "Lama konsumsi", "hari stok/pengapalan", "flow×year", "q / (D / 365)",
       ("voyage.q", "cargo.demand_unit"), sec="5.3", excel="Model!M350:AF350", audit=("A13",), screens=(8,),
       symbol="lamaKonsumsi"),
    # §5.4 biaya pelayaran
    _d("shipcost.fuel_me_l", "Konsumsi BBM ME", "l/th", "flow×year",
       "P_ME · MCR · SFOC_ME · 24 · (tSea · %ME_laut + (tPort + tFix) · %ME_pelabuhan) · F ÷ berat jenis",
       ("in.ship.me_kw", "in.param.mcr", "vessel.sfoc_me", "voyage.t_sea", "voyage.t_port", "voyage.t_fix", "voyage.freq",
        "in.param.fuel_share_me", "in.param.fuel_choice", "in.param.fuel_density"), sec="5.4", excel="Model!M247:AF247",
       audit=("A9",), screens=(7,)),
    _d("shipcost.fuel_ae_l", "Konsumsi BBM AE", "l/th", "flow×year",
       "P_AE · MCR · SFOC_AE · 24 · (tSea · %AE_laut + (tPort + tFix) · %AE_pelabuhan) · F ÷ berat jenis",
       ("vessel.ae_kw", "vessel.sfoc_ae", "in.param.mcr", "voyage.t_sea", "voyage.t_port", "voyage.t_fix", "voyage.freq",
        "in.param.fuel_share_ae", "in.param.fuel_choice", "in.param.fuel_density"), sec="5.4", excel="Model!M260:AF260",
       audit=("A6", "A9"), screens=(7,)),
    _d("shipcost.fuel_me", "Biaya BBM ME", "Rp/th", "flow×year", "liter ME × harga BBM ME",
       ("shipcost.fuel_me_l", "in.param.fuel_price", "in.param.fuel_choice"), sec="5.4", excel="Model!M273:AF273", audit=("A6",), screens=(7,)),
    _d("shipcost.fuel_ae", "Biaya BBM AE", "Rp/th", "flow×year", "liter AE × harga BBM AE",
       ("shipcost.fuel_ae_l", "in.param.fuel_price", "in.param.fuel_choice"), sec="5.4", excel="Model!M286:AF286", audit=("A6",), screens=(7,)),
    _d("shipcost.voyage", "Voyage cost (BBM)", "Rp/th", "flow×year", "BBM ME + BBM AE",
       ("shipcost.fuel_me", "shipcost.fuel_ae"), sec="5.4", excel="Model!M299:AF299", screens=(7,)),
    _d("shipcost.tch_rate", "Tarif TCH per hari", "USD/hari", "ship", "a_tipe · ukuran_k + b_tipe (regresi linier tabel pasar)",
       ("in.stype.tch_points", "in.ship.type", "in.ship.dwt", "vessel.teu_cap"), sec="5.4", excel="TCH!C15:U16", screens=(4, 7)),
    _d("shipcost.tch", "Biaya time charter", "Rp/th", "flow×year", "tarif TCH · kurs · CD · N_ship",
       ("shipcost.tch_rate", "in.param.usd_rate", "in.param.commission_days", "voyage.n_ship"), sec="5.4", excel="Model!M312:AF312",
       screens=(7,)),
    _d("shipcost.port_call", "Biaya pelabuhan per call", "Rp/call", "flow×ship",
       "Σ_{ext, KEK} labuh(GT) + 2·pandu(GT) + tambat(GT, ⌈etmal⌉) + 2·tunda(GT) + B/M(q)",
       ("in.ship.gt", "in.tariff.labuh", "in.tariff.pandu", "in.tariff.tambat", "in.tariff.tunda", "in.tariff.bm", "in.tariff.gt_bands",
        "in.port.tariff_class", "in.port.kind", "in.port.berth_type", "in.site.port_charges", "in.param.usd_rate", "voyage.q",
        "voyage.t_port_ext", "voyage.t_port_kek"), sec="5.4", excel="Biaya Pelabuhan!E71:E142", audit=("A14", "A15"), screens=(7,)),
    _d("shipcost.port", "Biaya pelabuhan per tahun", "Rp/th", "flow×year", "F · biaya pelabuhan per call",
       ("shipcost.port_call", "voyage.freq"), sec="5.4", excel="Model!M325:AF325", audit=("A11",), screens=(7,)),
    _d("shipcost.total", "Shipping cost", "Rp/th", "flow×year", "voyage cost + TCH + biaya pelabuhan",
       ("shipcost.voyage", "shipcost.tch", "shipcost.port"), sec="5.4", excel="Model!M338:AF338", screens=(6, 7, 9)),
    _d("shipcost.unit", "Biaya pelayaran per satuan", "Rp/t | Rp/TEU", "flow×year", "shipping cost / D (satuan flow, A7)",
       ("shipcost.total", "cargo.demand_unit"), sec="5.4", audit=("A7",), screens=(6, 7), kind="metric"),
    # §5.5 terminal KEK
    _d("terminal.ship_days", "Ship-days di KEK", "hari/th", "flow×year", "F · (tPortKEK + IT)",
       ("voyage.freq", "voyage.t_port_kek", "in.param.it"), sec="5.5", excel="Model!M68:AF72 · M87:AF91 (Σ: K101:AD102)",
       audit=("A2", "A17"), screens=(8,), symbol="shipDays[f]"),
    _d("terminal.berth_days", "Berth-days required", "hari/th", "flow×year",
       "dermaga menerus: ⌈shipDays · LOA_k / L_unit,τ⌉; jetty: ⌈shipDays⌉",
       ("terminal.ship_days", "in.ship.loa", "dv.ship", "in.term.berth_length", "in.term.layout", "in.term.cargo_forms"), sec="5.5",
       excel="Model!M106:AF115 (Σ: K119:AD120)", audit=("A16",), screens=(8,), symbol="berthDaysReq[f]"),
    _d("terminal.n_berth", "Jumlah tambatan", "unit", "terminal×year", "⌈Σ_f∈τ berthDaysReq / (BOR_max · WD)⌉, tidak pernah turun",
       ("terminal.berth_days", "in.param.bor_max", "in.param.working_days"),
       sec="5.5", excel="Model!K124:AD125", screens=(8, 9), symbol="nBerth[τ]"),
    _d("terminal.bor", "BOR realisasi", "–", "terminal×year", "Σ berthDaysReq / (nBerth · WD)",
       ("terminal.berth_days", "terminal.n_berth", "in.param.working_days"), sec="5.5",
       excel="Model!K144:AD145", screens=(8,), kind="metric", symbol="BOR[τ]"),
    _d("terminal.berth_length", "Panjang dermaga", "m", "terminal×year", "nBerth · L_unit,τ (jetty: panjang platform per jetty)",
       ("terminal.n_berth", "in.term.berth_length"), sec="5.5", excel="Fasilitas Daratan Rata2!F5", screens=(8, 9)),
    _d("terminal.n_equip", "Jumlah alat B/M", "unit", "terminal×year", "nBerth · nEq(kapal terpanjang yang melayani τ); penambahan per tahun",
       ("terminal.n_berth", "vessel.neq", "dv.equip", "dv.ship"), sec="5.5", excel="Model!K362:AD363", audit=("A10",),
       screens=(8, 9), symbol="nAlat[τ]"),
    # §5.6 penyimpanan
    _d("storage.dwell", "Dwell time", "hari", "flow×year", "lama konsumsi tahun itu (atau isian tetap per komoditas)",
       ("voyage.consumption", "in.storage.dwell"), sec="5.6", excel="Fasilitas Daratan!F13:Y16 · F132 · F173:F175 · F224:F225",
       audit=("A13", "A18"), screens=(8,), symbol="Tdw"),
    _d("storage.throughput", "Arus masuk penyimpanan", "t | TEU per th", "flow×year", "Q = porsi masuk · D (TEU untuk petikemas)",
       ("cargo.demand_unit", "in.storage.share"), sec="5.6", excel="Fasilitas Daratan!F8:Y11 · F128 · F167:F169 · F222:F223",
       screens=(8,), symbol="Q"),
    _d("storage.cy", "Lapangan penumpukan petikemas", "m²", "flow×year",
       "(1 + porsi kosong) · Q_TEU · Tdw · A_TEU / (365 · H_ratio · YOR); total = Σ flow, tidak pernah turun",
       ("storage.throughput", "storage.dwell", "in.storage.cy"), sec="5.6", excel="Fasilitas Daratan!F25:Y33",
       audit=("A18",), screens=(8,), symbol="A_CY"),
    _d("storage.cy_slots", "Ground slot petikemas", "slot", "flow×year",
       "(1 + porsi kosong) · Q_TEU · Tdw / (365 · H_ratio · YOR · tier maks)",
       ("storage.throughput", "storage.dwell", "in.storage.cy"), sec="5.6", excel="Fasilitas Daratan!F47:Y58",
       audit=("A18",), screens=(8,)),
    _d("storage.gc", "Gudang / lapangan GC", "m²", "flow×year", "Q · Tdw · f_area · f_bulk / (365 · ρ · H · SOR)",
       ("storage.throughput", "storage.dwell", "in.storage.gc", "in.cmdty.density"), sec="5.6", excel="Fasilitas Daratan!F184:Y186",
       audit=("A18",), screens=(8,), symbol="A_GC"),
    _d("storage.bulk", "Volume silo curah kering", "m³", "flow×year", "faktor bruto · Q · Tdw · Rc / (365 · ρ · SOR)",
       ("storage.throughput", "storage.dwell", "in.storage.bulk", "in.cmdty.density"), sec="5.6", excel="Fasilitas Daratan!F138:Y138",
       audit=("A18",), screens=(8,), symbol="V_silo"),
    _d("storage.bulk_area", "Lapangan curah kering (alternatif silo)", "m²", "flow×year", "f_area · V_netto / H",
       ("storage.throughput", "storage.dwell", "in.storage.bulk", "in.cmdty.density"), sec="5.6", excel="Fasilitas Daratan!F137:Y137",
       audit=("A18",), screens=(8,)),
    _d("storage.silos", "Jumlah silo", "unit", "flow×year", "⌈V_silo / (kapasitas silo · rasio isi)⌉",
       ("storage.bulk", "in.storage.bulk"), sec="5.6", excel="Fasilitas Daratan!F139:Y139", screens=(8,), symbol="nSilo"),
    _d("storage.liquid", "Volume tangki curah cair", "m³", "flow×year", "Q · Tdw / (365 · ρ · okupansi)",
       ("storage.throughput", "storage.dwell", "in.storage.liquid", "in.cmdty.density"), sec="5.6",
       excel="Fasilitas Daratan!F229:Y230", audit=("A18", "A20"), screens=(8,), symbol="V_tank"),
    _d("storage.tanks", "Jumlah tangki", "unit", "flow×year", "⌈V_tank / kapasitas tangki⌉ per produk",
       ("storage.liquid", "in.storage.liquid"), sec="5.6", excel="Fasilitas Daratan!F233:Y234", screens=(8,), symbol="nTangki"),
    _d("storage.yard_equipment", "Alat lapangan", "unit", "equipment×year",
       "⌈Σ_bentuk Q (petikemas: × (1 + porsi kosong)) / (produktivitas · utilisasi · WD · jam/hari)⌉, tidak pernah turun",
       ("storage.throughput", "in.storage.yard_equipment", "in.storage.yard_role", "in.storage.cy", "in.param.working_days",
        "in.param.working_hours"), sec="5.6", excel="Fasilitas Daratan!F73:Y115 (RTG) · F150 (dozer) · F205 (forklift)",
       audit=("A19",), screens=(8,)),
    # §5.7 fasilitas perairan & trestle vs keruk
    _d("waterside.governing", "Kapal penentu (T, LOA, B maks)", "m", "global", "maks atas kapal terpilih yang singgah KEK",
       ("dv.ship", "in.ship.draft", "in.ship.loa", "in.ship.beam"), sec="5.7", excel="Fasilitas Perairan!C4", screens=(8,)),
    _d("waterside.depth_req", "Kedalaman perlu", "m LWS", "global", "faktor × T_maks (K15: 1,5; K21: 1,2)",
       ("waterside.governing", "in.site.depth_factor"), sec="5.7", excel="Fasilitas Perairan!K18", screens=(8,)),
    _d("waterside.channel", "Lebar & panjang alur", "m", "global", "1 jalur Wm + Wa + 2Wb; 2 jalur 2(Wm + Wa + 2Wb) + Ws; panjang L … 2L",
       ("waterside.governing", "in.site.waterside"), sec="5.7", excel="Fasilitas Perairan!K14:L23", screens=(8,)),
    _d("waterside.basin", "Kolam putar, pintu masuk, area sandar, labuh", "m · m²", "global",
       "kolam putar 1,5–4 LOA; pintu masuk 0,7–1 LOA; stopping 7–8 LOA; area sandar 1,25 LOA × 1,5 B; radius labuh L + 6D",
       ("waterside.governing", "in.site.waterside"), sec="5.7", excel="Fasilitas Perairan!K29:L50", screens=(8,)),
    _d("waterside.x_star", "Jarak ke kedalaman perlu", "m", "global", "x* : batimetri(x*) ≥ kedalaman perlu",
       ("waterside.depth_req", "in.site.bathymetry"), sec="5.7", excel="Trestle!B86:K108", screens=(8,), symbol="x*"),
    _d("waterside.trestle_len", "Panjang trestle", "m", "global", "opsi trestle: x* (≤ maks); campuran: θ · x*",
       ("waterside.x_star", "in.site.trestle", "in.site.trestle_dredge", "dv.waterside"), sec="5.7", excel="Trestle", screens=(8,)),
    _d("waterside.dredge_vol", "Volume keruk", "m³", "global", "Σ luas · (kedalaman perlu − kedalaman eksisting)",
       ("waterside.depth_req", "in.site.bathymetry", "in.site.trestle_dredge", "waterside.basin", "waterside.channel", "dv.waterside"),
       sec="5.7", excel="Trestle", screens=(8,)),
    # §5.8 investasi & staging
    _d("invest.berth", "Investasi dermaga MP & jetty CC", "Rp/th", "terminal×year", "Δ panjang dermaga · lebar · harga satuan · eskalasi, saat dibangun",
       ("terminal.berth_length", "in.term.berth_width", "in.price.berth", "in.param.escalation_infra", "in.horizon.phases",
        "in.horizon.lead", "in.horizon.berth_lookahead"),
       sec="5.8", excel="Model!K387:AD387 · K391:AD391", screens=(9,)),
    _d("invest.handling", "Investasi alat B/M", "Rp/th", "terminal×year", "Δ jumlah alat · harga · kurs · eskalasi",
       ("terminal.n_equip", "in.equip.price", "dv.equip", "in.param.usd_rate", "in.param.escalation_equipment"),
       sec="5.8", excel="Model!K376:AD377", screens=(9,)),
    _d("invest.storage", "Investasi penyimpanan", "Rp/th", "year", "Δ luas / volume / unit · harga satuan, dibangun untuk N th ke depan",
       ("storage.cy", "storage.gc", "storage.silos", "storage.tanks", "storage.bulk_area", "storage.cy_slots", "in.price.storage",
        "in.storage.bulk", "in.param.escalation_infra",
        "in.horizon.storage_lookahead"), sec="5.8", excel="Model!K381:AD384", screens=(8, 9)),
    _d("invest.yard_equipment", "Investasi alat lapangan", "Rp/th", "year", "Δ alat lapangan · harga · eskalasi",
       ("storage.yard_equipment", "in.price.yard_equipment", "in.param.escalation_equipment"), sec="5.8", excel="Model!K370:AD373",
       screens=(9,)),
    _d("invest.waterside", "Investasi trestle / keruk", "Rp", "year", "panjang · lebar · Rp/m²  +  volume keruk · Rp/m³",
       ("waterside.trestle_len", "waterside.dredge_vol", "in.site.trestle", "in.price.trestle", "in.price.dredge", "dv.waterside"),
       sec="5.8", excel="Model!K395:AD395", screens=(8, 9)),
    _d("invest.total", "Investasi per tahun", "Rp/th", "year", "Σ komponen investasi yang dibangun di tahun t",
       ("invest.berth", "invest.handling", "invest.storage", "invest.yard_equipment", "invest.waterside"), sec="5.8", screens=(9,)),
    # §5.9 agregasi & objektif
    _d("agg.tc", "Total cost", "Rp/th", "year", "TC[t] = Σ shipping cost + investasi tahun t",
       ("shipcost.total", "invest.total"), sec="5.9", excel="Model!K399:AD399", screens=(9,), symbol="TC[t]",
       note="K15 membagi investasi awal 20 lalu menambahkannya tiap tahun (Model!K400)"),
    _d("agg.uc", "Unit cost per kelompok satuan", "Rp/t | Rp/TEU", "unit×year", "TC[t] dialokasikan ke flow / muatan[t], dipisah Rp/ton dan Rp/TEU",
       ("agg.tc", "cargo.demand_unit", "in.flow.unit"), sec="5.9", excel="Model!K404:AD404", audit=("A7",), screens=(9,), symbol="UC[t]"),
    _d("agg.pv_uc", "PV unit cost", "Rp/t | Rp/TEU", "unit×year", "UC[t] / (1+r)^t",
       ("agg.uc", "in.param.discount_rate"), sec="5.9", excel="Model!K405:AD405", screens=(9,)),
    _d("agg.annuity", "Anuitas unit cost", "Rp/t | Rp/TEU", "unit", "PMT(r, T, Σ PV_UC)",
       ("agg.pv_uc", "in.param.discount_rate", "in.horizon.years"), sec="5.9", excel="Model!K407", screens=(9, 11), kind="metric"),
    _d("obj.npv", "NPV biaya total (objektif)", "Rp", "global", "Σ_t TC[t] / (1+r)^t → diminimumkan atas y, z, w (dan V)",
       ("agg.tc", "in.param.discount_rate", "in.horizon.years"), sec="5.9", screens=(9, 10, 11), kind="objective",
       note="K15/Evolver meminimumkan anuitas (Model!K407); v2 memakai NPV total cost sebagai objektif default"),
)

# Variabel → fungsi engine yang menghitungnya ("modul:fungsi" di bawah tpt_engine.calc). Dites: dapat diimpor.
IMPL: dict[str, str] = {
    "demand.base": "demand:demand_base",
    "demand.ratio": "demand:demand_ratio",
    "vessel.teu_cap": "vessel:teu_capacity",
    "cargo.netmax": "cargo:net_max",
    "cargo.box_per_teu": "cargo:box_per_teu",
    "cargo.ton_per_teu": "cargo:ton_per_teu",
    "cargo.demand_unit": "cargo:demand_unit",
    # Tahap 5 (§5.2–5.3)
    "vessel.payload": "vessel:payload",
    "vessel.compatible": "vessel:compatible",
    "vessel.feasible": "vessel:feasibility",
    "vessel.neq": "vessel:n_equipment",
    "vessel.ballast_speed": "vessel:ballast_speed",
    "voyage.freq": "voyage:freq",
    "voyage.q": "voyage:cargo_per_call",
    "voyage.t_port_kek": "voyage:t_port_kek",
    "voyage.t_port_ext": "voyage:t_port_ext",
    "voyage.t_port": "voyage:t_port",
    "voyage.t_fix": "voyage:t_fix",
    "voyage.t_sea": "voyage:t_sea",
    "voyage.rtd": "voyage:rtd",
    "voyage.f_max": "voyage:f_max",
    "voyage.n_ship": "voyage:n_ship",
    "voyage.utilization": "voyage:utilization",
    "voyage.consumption": "voyage:consumption_days",
    # Tahap 6 (§5.4)
    "vessel.ae_kw": "shipcost:ae_kw",
    "vessel.sfoc_me": "shipcost:sfoc",
    "vessel.sfoc_ae": "shipcost:sfoc",
    "shipcost.fuel_me_l": "shipcost:fuel_litres",
    "shipcost.fuel_ae_l": "shipcost:fuel_litres",
    "shipcost.fuel_me": "shipcost:fuel_cost",
    "shipcost.fuel_ae": "shipcost:fuel_cost",
    "shipcost.voyage": "shipcost:fuel_cost",
    "shipcost.tch_rate": "shipcost:tch_rate",
    "shipcost.tch": "shipcost:tch_cost",
    "shipcost.port_call": "shipcost:port_call_cost",
    "shipcost.port": "shipcost:port_call_cost",
    "shipcost.total": "shipcost:unit_cost",
    "shipcost.unit": "shipcost:unit_cost",
    # Tahap 7a (§5.5)
    "terminal.ship_days": "terminal:ship_days",
    "terminal.berth_days": "terminal:berth_days",
    "terminal.n_berth": "terminal:n_berth",
    "terminal.bor": "terminal:bor",
    "terminal.berth_length": "terminal:berth_length",
    "terminal.n_equip": "terminal:n_equip",
    "storage.dwell": "storage:dwell",
    "storage.throughput": "storage:throughput",
    "storage.cy": "storage:cy_area",
    "storage.cy_slots": "storage:ground_slots",
    "storage.gc": "storage:gc_area",
    "storage.bulk": "storage:bulk_volume",
    "storage.bulk_area": "storage:bulk_area",
    "storage.silos": "storage:silos",
    "storage.liquid": "storage:liquid_volume",
    "storage.tanks": "storage:tanks",
    "storage.yard_equipment": "storage:yard_equipment",
}

REGISTRY: tuple[VarDef, ...] = tuple(replace(v, desc=DESC.get(v.id, ""), impl=IMPL.get(v.id))
                                     for v in INPUTS + DECISIONS + DERIVED)

# Interaksi wajib SPEC §7: titik awal penelusuran di peta variabel.
INTERACTIONS: tuple[tuple[str, str, str], ...] = (
    ("I1", "Kapal lebih besar", "dv.ship"),
    ("I2", "Kecepatan", "dv.speed"),
    ("I3", "Alat B/M lebih produktif", "in.equip.productivity"),
    ("I4", "Growth, volume maks, tahun mulai", "in.flow.growth"),
    ("I5", "Rasio konversi in→out, ton/TEU", "in.flow.ratio"),
    ("I6", "BOR maks, hari kerja", "in.param.bor_max"),
    ("I7", "Harga BBM, kurs, tarif", "in.param.fuel_price"),
    ("I8", "Batimetri / clearance", "in.site.bathymetry"),
    ("I9", "Discount rate", "in.param.discount_rate"),
)

# Lajur graf peta variabel (baris, atas → bawah) dan modul yang masuk ke tiap lajur. Posisi horizontal simpul =
# tingkat dependensi (`depth`), sehingga semua panah mengalir kiri → kanan; lajur 0 = kolom input di kiri.
GRAPH_LANES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Input kasus", ("in",)),
    ("Keputusan", ("dv",)),
    ("Muatan & konversi", ("demand", "cargo")),
    ("Kapal", ("vessel",)),
    ("Operasi", ("voyage",)),
    ("Biaya pelayaran", ("shipcost",)),
    ("Terminal & penyimpanan", ("terminal", "storage")),
    ("Perairan", ("waterside",)),
    ("Investasi & objektif", ("invest", "agg", "obj")),
)

# Kelompok input (prefiks entitas) → label, untuk tampilan ringkas di graf.
INPUT_GROUPS: dict[str, str] = {
    "horizon": "Periode & staging",
    "param": "Parameter global",
    "container": "Kontainer",
    "cmdty": "Komoditas",
    "flow": "Flow muatan",
    "compat": "Kompatibilitas",
    "port": "Pelabuhan",
    "route": "Rute",
    "term": "Terminal KEK",
    "site": "Tapak & perairan",
    "ship": "Kapal",
    "stype": "Tipe kapal (TCH)",
    "equip": "Alat B/M",
    "rule": "Aturan alat",
    "tariff": "Tarif pelabuhan",
    "storage": "Penyimpanan",
    "price": "Harga satuan",
}

# Ringkasan temuan audit Excel K15 → perilaku v2 (SPEC §11), untuk catatan "≠ Excel" di laci jejak.
AUDIT: dict[str, str] = {
    "A1": "Excel: F_max = ROUNDUP(365/RTD). v2: ⌊CD/RTD⌋ — jumlah kapal bisa bertambah 1.",
    "A2": "Excel (non-PK): waktu muat dikali jumlah alat. v2: dibagi jumlah alat.",
    "A3": "Excel memakai jumlah alat KEK untuk pelabuhan asal. v2: mode produktivitas per pelabuhan (total / per alat).",
    "A4": "Excel: batas volume maks dicek ke sel tetap. v2: min(Dmax, D[t−1]·(1+g)); K15 tidak terdampak.",
    "A5": "Excel: V ballast = 130 % Vs. v2: rasio parameter, default 100 %.",
    "A6": "Excel: ME = HSD, AE = MFO. v2: jenis BBM per mesin = parameter, default keduanya HSD.",
    "A7": "Excel membagi biaya dengan muatan campuran ton & TEU. v2: unit cost dipisah Rp/ton dan Rp/TEU.",
    "A8": "Excel: payload 85 % DWT di satu tempat, 90 % di tempat lain. v2: dua parameter α.",
    "A9": "Excel: BBM dari F_max · N_ship voyage. v2: dari frekuensi aktual F.",
    "A10": "Excel: alat per tambatan selalu 4 (XLOOKUP nama alat). v2: dari tabel rentang LOA.",
    "A11": "Excel: biaya pelabuhan statis, 65 call. v2: tarif × frekuensi aktual; TERSUS tanpa jasa.",
    "A12": "Excel: pembulatan TEU tak seragam (tahun-1 ROUNDDOWN, lain ROUNDUP; TEU inbound dibulatkan lalu "
           "dikompounding). v2: proyeksi kontinu, ⌈·⌉ sekali di D_TEU; selisih ≤ 6 TEU di K15.",
    "A13": "Excel: lama konsumsi = ⌈payload / (D/365)⌉ (payload, dibulatkan ke hari). v2: q / (D/365) kontinu.",
    "A14": "Excel: label 'Dalam Negeri' dibandingkan dengan 'Dalam' → semua pelabuhan kena tarif dalam negeri. "
           "v2: tarif luar negeri (USD × kurs) untuk pelabuhan luar negeri.",
    "A15": "Excel: pandu & tunda 1 gerakan/call, tunda tetap tidak dikali frekuensi, tambat × seluruh port time "
           "(KEK + asal + waktu tetap). v2: 2 gerakan, tunda tetap per call, tambat ⌈port time asal/tujuan⌉ etmal.",
    "A16": "Excel: cek label 'CC' berth-days memakai referensi relatif yang bergeser → mulai tahun ke-2 jetty CC dibagi "
           "300 m (unit MP); rumus aslinya LOA/40 m membuat satu tanker menempati ±4 jetty. v2: jetty = satu kapal satu jetty.",
    "A17": "Excel: ship-days KEK hanya waktu bongkar muat. v2: + idle time (IT) di tambatan; AT dan WT tidak menempati tambatan.",
    "A18": "Excel (Fasilitas Daratan): dwell time = rata-rata lama konsumsi 20 tahun termasuk tahun tanpa muatan (in.fantasi "
           "per tahun, kecuali 3 sel MAX blok). v2: lama konsumsi tahun itu.",
    "A19": "Excel: RTG dihitung per tenant & per full/kosong, masing-masing dibulatkan, produktivitas di-hardcode beda per "
           "tenant (4, 8/12, 5 TEU/jam). v2: satu armada per bentuk muatan, satu produktivitas per jenis alat.",
    "A20": "Excel: densitas CPO & RBD olein di tangki = 0,9 tetap. v2: densitas komoditas (CPO 0,909; RBD 0,91).",
}
AUDIT_IDS = tuple(AUDIT)


# ─── Utilitas graf ──────────────────────────────────────────────────────────────────────────────
def by_id() -> dict[str, VarDef]:
    return {v.id: v for v in REGISTRY}


def dependents() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {v.id: [] for v in REGISTRY}
    for v in REGISTRY:
        for d in v.deps:
            out.setdefault(d, []).append(v.id)
    return out


def input_group(var_id: str) -> str:
    return var_id.split(".")[1]


def lane_of(v: VarDef) -> int:
    mod = "in" if v.kind == "input" else v.id.split(".")[0]
    for i, (_, mods) in enumerate(GRAPH_LANES):
        if mod in mods:
            return i
    raise KeyError(f"modul '{mod}' tidak punya lajur graf")


def depths() -> dict[str, int]:
    """Tingkat dependensi: input = 0; selain input = 1 + tingkat masukan terdalam (minimal 1)."""
    ids = by_id()
    out: dict[str, int] = {}
    for vid in topo_order():
        v = ids[vid]
        out[vid] = 0 if v.kind == "input" else max([1, *(out[d] + 1 for d in v.deps)])
    return out


def _closure(start: str, edges: dict[str, list[str]] | dict[str, tuple[str, ...]]) -> set[str]:
    seen: set[str] = set()
    stack = list(edges.get(start, ()))
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(edges.get(n, ()))
    return seen


def upstream(var_id: str) -> set[str]:
    return _closure(var_id, {v.id: v.deps for v in REGISTRY})


def downstream(var_id: str) -> set[str]:
    return _closure(var_id, dependents())


def topo_order() -> list[str]:
    """Urutan topologis (Kahn). ValueError bila ada dependensi melingkar."""
    deps = {v.id: set(v.deps) for v in REGISTRY}
    kids = dependents()
    ready = sorted(k for k, d in deps.items() if not d)
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for k in kids.get(n, []):
            deps[k].discard(n)
            if not deps[k]:
                ready.append(k)
    if len(order) != len(deps):
        stuck = sorted(k for k, d in deps.items() if d)
        raise ValueError(f"dependensi melingkar di antara: {stuck}")
    return order


def to_json_dict() -> dict:
    kids = dependents()
    order = {vid: i for i, vid in enumerate(topo_order())}
    depth = depths()
    variables = []
    for v in REGISTRY:
        d = {k: val for k, val in asdict(v).items() if val not in (None, (), "")}
        d["deps"] = list(v.deps)
        d["dependents"] = kids[v.id]
        d["lane"] = lane_of(v)
        d["depth"] = depth[v.id]
        d["topo"] = order[v.id]
        if v.kind == "input":
            d["group"] = input_group(v.id)
        for key in ("audit", "screens"):
            if key in d:
                d[key] = list(d[key])
        variables.append(d)
    return {
        "note": "Dibuat oleh tools/dump_registry.py dari tpt_engine/registry.py — jangan diedit manual.",
        "lanes": [name for name, _ in GRAPH_LANES],
        "input_groups": INPUT_GROUPS,
        "audit": AUDIT,
        "interactions": [{"id": i, "label": label, "start": start} for i, label, start in INTERACTIONS],
        "variables": variables,
    }


def to_json() -> str:
    return json.dumps(to_json_dict(), ensure_ascii=False, indent=2) + "\n"


__all__ = [
    "VarDef", "REGISTRY", "INPUTS", "DECISIONS", "DERIVED", "INTERACTIONS", "GRAPH_LANES", "INPUT_GROUPS", "KINDS",
    "AUDIT", "AUDIT_IDS", "IMPL", "by_id", "dependents", "upstream", "downstream", "topo_order", "lane_of", "depths", "to_json", "to_json_dict",
]
