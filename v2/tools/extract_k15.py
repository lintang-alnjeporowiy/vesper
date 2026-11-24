"""Ekstraksi workbook TPT Kelompok 15 (KI Batam).

Menghasilkan:
  1. cases/k15-batam.json              — seluruh INPUT kasus (divalidasi model Case)
  2. engine/tests/golden/k15_excel.json — nilai antara/hasil Excel sebagai PEMBANDING
     (rumus lama; tiap seri ditandai `affected_by` = temuan audit SPEC §11 yang membuatnya berbeda)

Pemetaan sel ditulis eksplisit (khusus layout workbook K15).

Jalankan dari folder v2:
  uv run --project engine python tools/extract_k15.py "../referensi/K15/TPT_Kelompok 15 Revisi 02-Januari-2025.xlsx"
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter

from tpt_engine.domain import Case

V2 = Path(__file__).resolve().parents[1]
OUT_CASE = V2 / "cases" / "k15-batam.json"
OUT_GOLDEN = V2 / "engine" / "tests" / "golden" / "k15_excel.json"

# nama sheet persis di workbook (beberapa berakhiran spasi)
SH = {
    "muatan": "Muatan", "proyeksi": "Proyeksi Muatan ", "rute": "Rute", "kapal": "Data Kapal",
    "pelabuhan": "Data Pelabuhan ", "alat": "Alat BM ", "tch": "TCH", "biaya": "Biaya Pelabuhan",
    "perairan": "Fasilitas Perairan ", "daratan_rata": "Fasilitas Daratan Rata2",
    "daratan": "Fasilitas Daratan", "investasi": "Investasi", "trestle": "Trestle", "model": "Model ",
}


# ------------------------------------------------------------------------------------------
# pembaca
# ------------------------------------------------------------------------------------------


class Book:
    def __init__(self, path: Path):
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        self.cells: dict[str, dict[str, object]] = {}
        for key, name in SH.items():
            d: dict[str, object] = {}
            for row in wb[name].iter_rows():
                for c in row:
                    if c.value is not None and getattr(c, "coordinate", None):
                        d[c.coordinate] = c.value
            self.cells[key] = d
        wb.close()

    def raw(self, sheet: str, coord: str):
        return self.cells[sheet].get(coord)

    @staticmethod
    def ref(sheet: str, coord: str) -> str:
        return f"{SH[sheet].strip()}!{coord}"


class Rd:
    """Membaca nilai sambil mencatat `refs` untuk satu record."""

    def __init__(self, book: Book):
        self.b = book
        self.refs: dict[str, str] = {}

    def __call__(self, field: str, sheet: str, coord: str, cast=float):
        val = self.b.raw(sheet, coord)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise KeyError(f"{Book.ref(sheet, coord)} kosong (field {field})")
        self.refs[field] = Book.ref(sheet, coord)
        if cast is None:
            return val
        if cast is str:
            return str(val).strip().replace("\xa0", "")
        return cast(val)

    def note_ref(self, field: str, text: str):
        self.refs[field] = text

    def take(self) -> dict[str, str]:
        r, self.refs = self.refs, {}
        return r


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower().replace("\xa0", " ")).strip("_")
    return s


# ------------------------------------------------------------------------------------------
# konstanta pemetaan K15
# ------------------------------------------------------------------------------------------

TENANTS = [  # (id, sektor) — urutan baris Proyeksi Muatan 4..8 / 12..16
    ("damai", "makanan"), ("fantasi", "elektronik"), ("esa", "manufaktur"),
    ("baru", "makanan"), ("adi", "energi"),
]
# per tenant: (komoditas in, bentuk in, pelabuhan in, komoditas out, bentuk out, pelabuhan out, unit out)
FLOWS = {
    "damai": ("jagung_karung", "GC", "badas", "tepung_jagung", "PK", "bangkok", "ton"),
    "fantasi": ("aluminium", "PK", "lampia", "baja_ringan", "PK", "kobe", "TEU"),
    "esa": ("pelat_baja", "GC", "visakhapatnam", "profil_baja", "GC", "tanjung_priok", "ton"),
    "baru": ("gandum", "CK", "melbourne", "tepung_terigu", "PK", "gresik", "ton"),
    "adi": ("cpo", "CC", "belawan", "rbd_olein", "CC", "chennai", "ton"),
}
# pelabuhan: id -> (negara, sel draft, sel prod, sel satuan prod, baris tabel ringkas, kolom tabel, baris Biaya Pelabuhan, baris Rute)
PORTS = {
    "badas": ("Indonesia", "G35", "G34", "H34", 21, "inbound", 3, 20),
    "lampia": ("Indonesia", "G48", "G47", "H47", 22, "inbound", 4, 21),
    "visakhapatnam": ("India", "G61", "G60", "H60", 23, "inbound", 5, 22),
    "melbourne": ("Australia", "G74", "G73", "H73", 24, "inbound", 6, 23),
    "belawan": ("Indonesia", "G87", "G86", "H86", 25, "inbound", 7, 24),
    "bangkok": ("Thailand", "Q35", "Q34", "R34", 21, "outbound", 8, 25),
    "kobe": ("Jepang", "Q48", "Q47", "R47", 22, "outbound", 9, 26),
    "tanjung_priok": ("Indonesia", "Q61", "Q60", "R60", 23, "outbound", 10, 27),
    "gresik": ("Indonesia", "Q74", "Q73", "R73", 24, "outbound", 11, 28),
    "chennai": ("India", "Q87", "Q86", "R86", 25, "outbound", 12, 29),
}
UNRELIABLE_BERTH = {"lampia"}
PORT_NOTES = {
    "lampia": "Tabel ringkas Data Pelabuhan!E22 menulis 'Pelabuhan Makasar' (dermaga 80 m) untuk POL Malili; "
              "angka itu tidak dipakai, longest_berth_m dikosongkan sampai ada data Lampia.",
    "bangkok": "Tabel ringkas Data Pelabuhan!O21 menulis 'laem chabang'.",
}
SHIP_TYPE_COLS = [  # kolom Model baris 24-39 per tipe
    ("tanker", "AL", "AT"), ("bulk_carrier", "AU", "BC"),
    ("container_ship", "BD", "BQ"), ("general_cargo_ship", "BR", "BZ"),
]
HMC = [  # (nama sel, baris awal blok di sheet Alat BM kolom C)
    ("C6", 6), ("C18", 18), ("C30", 30), ("C42", 42), ("C54", 54), ("C66", 66),
]
MLA = [6, 14, 22, 30, 38]  # baris nama di kolom J
YEAR_COLS_M = [get_column_letter(column_index_from_string("M") + i) for i in range(20)]  # M..AF
YEAR_COLS_N = [get_column_letter(column_index_from_string("N") + i) for i in range(20)]  # N..AG
YEAR_COLS_K = [get_column_letter(column_index_from_string("K") + i) for i in range(20)]  # K..AD
YEAR_COLS_F = [get_column_letter(column_index_from_string("F") + i) for i in range(20)]  # F..Y (Fasilitas Daratan)

# Fasilitas Daratan: baris per flow (seri → baris) dan total; dwell dari Model!M350:AF359 (A13, A18)
STORAGE_FLOW_ROWS: dict[str, dict[str, int]] = {
    "in.fantasi": dict(dwell_days=13, cy_area_full_m2=25, ground_slots_full=47, ground_slots_empty=48, rtg_full=73,
                       rtg_empty=79),
    "out.damai": dict(dwell_days=14, cy_area_full_m2=26, ground_slots_full=49, ground_slots_empty=50, rtg_full=85,
                      rtg_empty=91),
    "out.fantasi": dict(dwell_days=15, cy_area_full_m2=27, ground_slots_full=51, ground_slots_empty=52, rtg_full=97,
                        rtg_empty=103),
    "out.baru": dict(dwell_days=16, cy_area_full_m2=28, ground_slots_full=53, ground_slots_empty=54, rtg_full=109,
                     rtg_empty=115),
    "in.baru": dict(dwell_days=132, bulk_area_m2=137, silo_volume_m3=138, silos=139),
    "in.damai": dict(dwell_days=173, gc_area_m2=184),
    "in.esa": dict(dwell_days=174, gc_area_m2=185),
    "out.esa": dict(dwell_days=175, gc_area_m2=186),
    "in.adi": dict(dwell_days=224, tank_volume_m3=229, tanks=233),
    "out.adi": dict(dwell_days=225, tank_volume_m3=230, tanks=234),
}
STORAGE_TOTAL_ROWS = dict(cy_area_m2=33, dozers=150, forklifts=205)
STORAGE_AFFECTED = dict(dwell_days=["A13", "A18"], cy_area_full_m2=["A12", "A13", "A18"],
                        ground_slots_full=["A12", "A13", "A18"], ground_slots_empty=["A12", "A13", "A18"],
                        rtg_full=["A12", "A19"], rtg_empty=["A12", "A19"], bulk_area_m2=["A13", "A18"],
                        silo_volume_m3=["A13", "A18"], silos=["A13", "A18"], gc_area_m2=["A13", "A18"],
                        tank_volume_m3=["A13", "A18", "A20"], tanks=["A13", "A18", "A20"],
                        cy_area_m2=["A12", "A13", "A18"], dozers=[], forklifts=[])
FLOW_ORDER = [f"in.{t}" for t, _ in TENANTS] + [f"out.{t}" for t, _ in TENANTS]

# Fasilitas Perairan (§5.7, Tahap 8a). C6 berlabel "H" tetapi = sarat T (Model baris 29), C7 berlabel "T" = tinggi H.
WATERSIDE_CELLS = (
    ("governing_loa_m", "C4"), ("governing_beam_m", "C5"), ("governing_draft_m", "C6"), ("governing_depth_m", "C7"),
    ("governing_speed_kn", "C8"), ("wm_m", "E12"), ("wa_speed_m", "G18"), ("wa_wind_m", "G22"),
    ("wa_cross_current_m", "G32"), ("wa_long_current_m", "G42"), ("wa_wave_m", "G50"), ("wa_nav_aids_m", "G54"),
    ("wa_bottom_m", "G58"), ("wa_depth_m", "G63"), ("wa_total_m", "G66"), ("wb_m", "G70"), ("ws_m", "G82"),
    ("channel_width_1lane_m", "K14"), ("channel_width_2lane_m", "K16"), ("required_depth_m", "K18"),
    ("channel_length_long_high_m", "L21"), ("channel_length_long_low_m", "L22"), ("channel_length_m", "L23"),
    ("channel_length_short_low_m", "L24"), ("entrance_width_m", "K29"), ("stopping_distance_m", "K32"),
    ("turning_basin_d_no_tug_m", "K34"), ("turning_basin_d_m", "K35"), ("turning_basin_d_thruster_m", "K36"),
    ("turning_basin_area_m2", "K37"), ("berthing_area_length_m", "K40"), ("berthing_area_width_m", "K42"),
    ("anchorage_depth_m", "K47"), ("anchorage_radius_m", "L50"), ("anchorage_radius_poor_m", "L51"),
    ("anchorage_radius_wind20_m", "L52"), ("anchorage_radius_wind30_m", "L53"),
)
# Trestle: dimensi turunan (C35:C45), opsi trestle penuh (C50:C64, C92:C94) dan trestle + keruk (C69:C83, C110)
TRESTLE_CELLS = (
    ("required_depth_m", "C9"), ("mp_berth_length_m", "C25"), ("mp_berth_width_m", "C26"),
    ("cc_berth_length_m", "C30"), ("cc_berth_width_m", "C31"), ("turning_basin_m", "C35"),
    ("stopping_distance_m", "C36"), ("channel_width_m", "C37"), ("berth_area_width_m", "C38"),
    ("channel_length_m", "C40"), ("turning_area_m2", "C41"), ("stopping_area_m2", "C42"), ("channel_area_m2", "C43"),
    ("anchorage_m", "C44"), ("berth_area_mp_m2", "C45"),
    ("full_length_mp_m", "C50"), ("full_width_mp_m", "C51"), ("full_area_mp_m2", "C53"), ("full_cost_mp_rp", "C55"),
    ("full_length_jetty_m", "C59"), ("full_width_jetty_m", "C60"), ("full_area_jetty_m2", "C62"),
    ("full_cost_jetty_rp", "C64"), ("full_cost_rp", "C92"), ("full_total_rp", "C94"),
    ("mixed_length_mp_m", "C69"), ("mixed_width_mp_m", "C70"), ("mixed_area_mp_m2", "C72"),
    ("mixed_existing_depth_mp_m", "C73"), ("mixed_dredge_depth_mp_m", "C74"), ("mixed_length_jetty_m", "C78"),
    ("mixed_width_jetty_m", "C79"), ("mixed_area_jetty_m2", "C81"), ("mixed_existing_depth_jetty_m", "C82"),
    ("mixed_dredge_depth_jetty_m", "C83"), ("mixed_total_rp", "C110"),
)
# Fasilitas Daratan: truk dermaga–lapangan per bentuk muatan (§5.6, Tahap 8a; A25)
TRUCK_ROWS = {
    "PK": dict(speed_kmh=118, distance_km=119, crane_box_h=120, t_crane_min=121, t_rtg_load_min=122,
               t_rtg_unload_min=123, t_travel_min=124, trucks=125),
    "CK": dict(crane_t_h=153, capacity_t=154, t_quay_min=156, speed_kmh=158, distance_km=159, t_yard_min=160,
               t_travel_min=161, t_load_min=162, trucks=163, cycle_min=164),
    "GC": dict(capacity_t=208, crane_t_h=209, t_quay_min=210, speed_kmh=211, distance_km=212, t_yard_min=213,
               t_travel_min=214, t_load_min=215, cycle_min=216, trucks=217),
}


# Profil batimetri DUMMY (K15 tidak punya data). Disusun agar konsisten dengan K15:
#   - kedalaman eksisting 10 m pada 250 m  (Trestle!C69, C73 — opsi trestle + keruk)
#   - kedalaman perlu 21,3 m pertama tercapai tepat pada 500 m (Trestle!C9, C50 — trestle penuh)
# Bentuk: landai di dekat pantai, curam di 250–450 m, melandai lagi di laut dalam.
DUMMY_BATHY = [(0, 0.0), (25, 0.8), (50, 1.6), (100, 3.5), (150, 5.5), (200, 7.8), (250, 10.0),
               (300, 12.6), (350, 15.2), (400, 17.6), (450, 19.6), (500, 21.3), (550, 22.6),
               (600, 23.6), (700, 25.0), (800, 26.0), (1000, 27.5)]


def dummy_bathymetry(b: Book) -> list[dict]:
    d_dredge, z_dredge = float(b.raw("trestle", "C69")), float(b.raw("trestle", "C73"))
    d_full, z_req = float(b.raw("trestle", "C50")), float(b.raw("trestle", "C9"))
    pts = dict(DUMMY_BATHY)
    if pts.get(d_dredge) != z_dredge or abs(pts.get(d_full, -1) - round(z_req, 1)) > 1e-9:
        raise ValueError("profil dummy tidak lagi konsisten dengan Trestle!C69/C73/C50/C9")
    if any(z >= round(z_req, 1) for x, z in DUMMY_BATHY if x < d_full):
        raise ValueError("profil dummy mencapai kedalaman perlu sebelum panjang trestle penuh")
    out = []
    for x, z in DUMMY_BATHY:
        src = "dummy"
        if x == d_dredge:
            src = "dummy, dikunci ke Trestle!C69/C73 (10 m pada 250 m)"
        elif x == d_full:
            src = "dummy, dikunci ke Trestle!C50/C9 (21,3 m pada 500 m)"
        out.append(dict(distance_m=float(x), depth_m=z, refs={"distance_m": src, "depth_m": src}))
    return out


# ------------------------------------------------------------------------------------------
# INPUT
# ------------------------------------------------------------------------------------------


def build_case(b: Book, xlsx: Path) -> dict:
    r = Rd(b)
    today = dt.date.today().isoformat()

    meta = dict(
        id="k15-batam", name="K15 — KI Batam",
        kek_name="Kawasan Industri Batam", kek_port_name="TERSUS Batu Ampar, Batam",
        location="Batam, Kepulauan Riau",
        description="Tugas Perencanaan Transportasi Laut Kelompok 15 (Febiola G. Puspa, Yudho D. Wibowo), "
                    "Teknik Transportasi Laut ITS, 2024. Kasus referensi utama v2.",
        source_files=[xlsx.name, "K15_Laporan Revisi.pdf", "K15_Presentasi Sidang Revisi.pptx"],
        extracted_at=today,
    )

    horizon = dict(
        years=r("years", "investasi", "C14", int),
        phases=[dict(name=n, start_year=a, end_year=z,
                     refs={"start_year": "Laporan K15 §2.5 (PM 51/2015)", "end_year": "Laporan K15 §2.5 (PM 51/2015)"})
                for n, a, z in (("pendek", 1, 5), ("menengah", 6, 10), ("panjang", 11, 20))],
        construction_lead_years=r("construction_lead_years", "investasi", "C13", int),
        berth_lookahead_years=7, storage_lookahead_years=5,
    )
    r.note_ref("phases", "Laporan K15 §2.5 (PM 51/2015)")
    r.note_ref("berth_lookahead_years", "Investasi!L9 = SUM(L8:R8) → 7 tahun")
    r.note_ref("storage_lookahead_years", "Fasilitas Daratan!F196 = SUM(F193:J193) → 5 tahun")
    horizon["refs"] = r.take()

    # --- parameter global
    def bands(rows, label):
        out = []
        for row in rows:
            rr = Rd(b)
            mn = rr("min_kw", "kapal", f"V{row}")
            mx = b.raw("kapal", f"X{row}")
            sf = rr("sfoc_g_kwh", "kapal", f"Z{row}")
            rr.note_ref("max_kw", Book.ref("kapal", f"X{row}"))
            out.append(dict(min_kw=float(mn), max_kw=float(mx) if isinstance(mx, (int, float)) else None,
                            sfoc_g_kwh=sf, refs=rr.take(), note=None))
        out[0]["min_kw"] = 0.0
        out[0]["note"] = f"{label}: Excel mulai dari 1 kW; g/kWh = g/HP·h × 1,359"
        return out

    fuels = []
    for code, name, price, dens in (("MFO", "Marine Fuel Oil", "F45", "F41"), ("HSD", "High Speed Diesel", "F46", "F43")):
        fuels.append(dict(code=code, name=name, price_rp_per_l=r("price_rp_per_l", "model", price),
                          density_kg_m3=r("density_kg_m3", "model", dens), refs=r.take()))

    container = dict(
        inner_length_m=r("inner_length_m", "muatan", "C84"), inner_width_m=r("inner_width_m", "muatan", "D84"),
        inner_height_m=r("inner_height_m", "muatan", "E84"), tare_t=r("tare_t", "muatan", "G84"),
        max_gross_t=r("max_gross_t", "muatan", "H84"), max_net_t=r("max_net_t", "muatan", "I84"),
        share_20ft=r("share_20ft", "model", "F50"),
    )
    container["refs"] = r.take()

    params = dict(
        at_hours=r("at_hours", "model", "B34"), wt_hours=r("wt_hours", "model", "B35"),
        it_hours=r("it_hours", "model", "B36"),
        working_days_per_year=r("working_days_per_year", "model", "F51"),
        working_hours_per_day=24.0,
        commission_days=r("commission_days", "model", "F53"),
        bor_max=r("bor_max", "model", "F52"), mcr=r("mcr", "model", "F40"),
        fuel_share_me_sea=r("fuel_share_me_sea", "model", "F36"),
        fuel_share_me_port=r("fuel_share_me_port", "model", "F37"),
        fuel_share_ae_sea=r("fuel_share_ae_sea", "model", "F38"),
        fuel_share_ae_port=r("fuel_share_ae_port", "model", "F39"),
        fuels=fuels, me_fuel="HSD", ae_fuel="HSD",
        sfoc_me_bands=bands(range(8, 14), "ME"), sfoc_ae_bands=bands(range(16, 22), "AE"),
        ae_me_power_ratio=0.5,
        usd_rate=r("usd_rate", "alat", "Q4"),
        discount_rate=r("discount_rate", "model", "J403"),
        escalation_infra=r("escalation_infra", "investasi", "C15"),
        escalation_equipment=r("escalation_equipment", "investasi", "C21"),
        ballast_speed_ratio=1.0,
        payload_dwt_ratio=r("payload_dwt_ratio", "kapal", "V32"),
        teu_weight_dwt_ratio=0.9,
        teu_capacity_dwt_ratio=r("teu_capacity_dwt_ratio", "kapal", "V32"),
        teu_nominal_weight_t=r("teu_nominal_weight_t", "kapal", "O53"),
        berth_loa_min_ratio=0.85,
        cargo_per_call_mode="interval",
        container=container,
    )
    r.note_ref("working_hours_per_day", "Model (konstanta /24 di rumus port time)")
    r.note_ref("me_fuel", "Keputusan A6 (K15: ME=HSD)")
    r.note_ref("ae_fuel", "Keputusan A6 (K15: AE=MFO)")
    r.note_ref("ae_me_power_ratio", "Data Kapal!Q4 = 50%*P4")
    r.note_ref("ballast_speed_ratio", "Keputusan A5 (K15: Data Kapal!L4 = 130%*K4)")
    r.note_ref("teu_weight_dwt_ratio", "Muatan!AD5 = 90%*AC5")
    r.note_ref("berth_loa_min_ratio", "Keputusan data K15 (2026-11-21): dermaga ≥ 85% LOA")
    r.note_ref("cargo_per_call_mode", "Model!N41 = D/F")
    params["refs"] = r.take()

    cargo_forms = [
        dict(code="CC", name="Curah cair", default_unit="ton"),
        dict(code="CK", name="Curah kering", default_unit="ton"),
        dict(code="PK", name="Petikemas", default_unit="TEU"),
        dict(code="GC", name="General cargo", default_unit="ton"),
    ]

    def tch_points(lab_col, size_col, usd_col, rows):
        pts = []
        for row in rows:
            size, usd = b.raw("tch", f"{size_col}{row}"), b.raw("tch", f"{usd_col}{row}")
            if isinstance(size, (int, float)) and isinstance(usd, (int, float)):
                lab = b.raw("tch", f"{lab_col}{row}")
                pts.append(dict(label=str(lab).strip() if lab and str(lab).strip() else None,
                                size=float(size), usd_per_day=float(usd),
                                refs={"size": Book.ref("tch", f"{size_col}{row}"),
                                      "usd_per_day": Book.ref("tch", f"{usd_col}{row}")}))
        return pts

    ship_types = [
        dict(code="tanker", name="Tanker (curah cair)", size_basis="dwt", tch_points=tch_points("H", "I", "J", range(5, 13))),
        dict(code="bulk_carrier", name="Bulk carrier (curah kering)", size_basis="dwt", tch_points=tch_points("B", "C", "D", range(5, 13))),
        dict(code="container_ship", name="Kapal petikemas", size_basis="teu", tch_points=tch_points("N", "O", "P", range(5, 13))),
        dict(code="general_cargo_ship", name="Kapal general cargo", size_basis="dwt", tch_points=tch_points("T", "U", "V", range(5, 13))),
        dict(code="lct", name="LCT / tongkang", size_basis="dwt", tch_points=[],
             note="Ditambahkan v2 (keputusan §13 no.7); belum ada kandidat kapal & tarif charter di K15."),
    ]
    compatibility = {"CC": ["tanker"], "CK": ["bulk_carrier"], "PK": ["container_ship"],
                     "GC": ["general_cargo_ship", "lct"]}

    # --- komoditas
    def comm(id_, name, form, dens=None, sf=None, pack=None, note=None, dens_scale=1.0, sf_scale=1.0):
        d = dict(id=id_, name=name, cargo_form=form)
        if dens:
            d["density_t_m3"] = r("density_t_m3", "muatan", dens) * dens_scale
        if sf:
            d["stowage_factor_m3_t"] = r("stowage_factor_m3_t", "muatan", sf) * sf_scale
        if pack:
            kind, ln, w, h, wt, pcs = pack
            rp = Rd(b)
            d["packaging"] = dict(kind=kind, length_m=rp("length_m", "muatan", ln), width_m=rp("width_m", "muatan", w),
                                  height_m=rp("height_m", "muatan", h), weight_kg=rp("weight_kg", "muatan", wt),
                                  pieces_per_pack=rp("pieces_per_pack", "muatan", pcs, int) if pcs else None)
            d["packaging"]["refs"] = rp.take()
        d["refs"] = r.take()
        if note:
            d["note"] = note
        return d

    commodities = [
        comm("jagung_karung", "Jagung dalam karung", "GC", dens="C13", sf="C11", sf_scale=1000),
        comm("aluminium", "Aluminium", "PK", sf="C69",
             note="Volume inbound didefinisikan dalam TEU. Data kemasan di Muatan!B17:C22 adalah salinan "
                  "data kardus maizena, tidak dipakai."),
        comm("pelat_baja", "Pelat baja", "GC", dens="C45",
             pack=("pelat", "C40", "C41", "C42", "C39", None)),
        comm("gandum", "Gandum", "CK", dens="C51"),
        comm("cpo", "Crude palm oil (CPO)", "CC", dens="C56",
             note="Muatan!C56 berlabel kg/m³ tapi nilainya t/m³; Fasilitas Daratan memakai 0,9."),
        comm("tepung_jagung", "Tepung jagung (kardus)", "PK", dens="L13", dens_scale=1 / 1000,
             pack=("kardus", "L7", "L8", "L9", "L12", "L11")),
        comm("baja_ringan", "Baja ringan", "PK", dens="L32", dens_scale=1 / 1000,
             pack=("batang", "L26", "L27", "L28", "L31", "L30"),
             note="Volume outbound didefinisikan dalam TEU (1 TEU aluminium = 2 TEU baja ringan)."),
        comm("profil_baja", "Profil baja", "GC", dens="L72"),
        comm("tepung_terigu", "Tepung terigu (kardus)", "PK", dens="L51", dens_scale=1 / 1000,
             pack=("kardus", "L45", "L46", "L47", "L50", "L49")),
        comm("rbd_olein", "RBD olein", "CC", dens="L78", dens_scale=1 / 1000),
    ]

    # --- tenant & flow
    tenants, flows = [], []
    for i, (tid, sector) in enumerate(TENANTS):
        row_in, row_out = 4 + i, 12 + i
        tenants.append(dict(id=tid, name=r("name", "proyeksi", f"A{row_in}", str), sector=sector,
                            refs={**r.take(), "sector": "Laporan K15 §1.3"}))
        c_in, f_in, p_in, c_out, f_out, p_out, u_out = FLOWS[tid]
        unit_in = "TEU" if str(b.raw("proyeksi", f"E{row_in}")).strip().upper() == "TEU" else "ton"
        vol = dict(mode="independent", start_year=r("start_year", "proyeksi", f"B{row_in}", int),
                   initial=r("initial", "proyeksi", f"C{row_in}"), maximum=r("maximum", "proyeksi", f"D{row_in}"),
                   growth_rate=r("growth_rate", "proyeksi", f"F{row_in}"))
        vol["refs"] = r.take()
        flows.append(dict(id=f"in.{tid}", tenant_id=tid, direction="inbound", commodity_id=c_in, cargo_form=f_in,
                          unit=unit_in, route_id=f"rt.{p_in}", volume=vol))
        # outbound = rasio × inbound (awal & maks harus konsisten)
        o_init, o_max = float(b.raw("proyeksi", f"C{row_out}")), float(b.raw("proyeksi", f"D{row_out}"))
        ratio = o_init / vol["initial"]
        if abs(o_max / vol["maximum"] - ratio) > 1e-9:
            raise ValueError(f"out.{tid}: rasio awal {ratio} ≠ rasio maks {o_max / vol['maximum']}")
        out_note = None
        if int(b.raw("proyeksi", f"B{row_out}")) != vol["start_year"]:
            out_note = (f"Excel menulis tahun operasi outbound {b.raw('proyeksi', f'B{row_out}')} "
                        f"(Proyeksi Muatan!B{row_out}), tapi nilai baru muncul di tahun {vol['start_year']}; "
                        "ikut inbound.")
        flows.append(dict(id=f"out.{tid}", tenant_id=tid, direction="outbound", commodity_id=c_out, cargo_form=f_out,
                          unit=u_out, route_id=f"rt.{p_out}", note=out_note,
                          volume=dict(mode="ratio", basis_flow_id=f"in.{tid}", ratio=round(ratio, 10),
                                      refs={"ratio": f"Proyeksi Muatan!C{row_out}/C{row_in} "
                                                     f"(= D{row_out}/D{row_in})"})))

    # --- pelabuhan & rute
    ports, routes = [], []
    unit_map = {"ton/jam": "t/h", "teus/jam": "TEU/h"}
    for pid, (country, c_draft, c_prod, c_unit, trow, side, brow, rrow) in PORTS.items():
        col_name, col_len, col_type = ("E", "G", "D") if side == "inbound" else ("O", "Q", "N")
        name = r("name", "biaya", f"B{brow}", str)
        kind_raw = str(b.raw("biaya", f"D{brow}")).lower()
        cls_raw = b.raw("biaya", f"E{brow}")
        r.note_ref("kind", Book.ref("biaya", f"D{brow}"))
        r.note_ref("tariff_class", Book.ref("biaya", f"E{brow}"))
        prod_unit = unit_map[str(b.raw("pelabuhan", c_unit)).strip().lower()]
        rp = Rd(b)
        prod = dict(mode="total", value=rp("value", "pelabuhan", c_prod), unit=prod_unit)
        prod["refs"] = rp.take()
        ports.append(dict(
            id=pid, name=name, country=country,
            kind="domestic" if "dalam" in kind_raw else "foreign",
            terminal_type=r("terminal_type", "pelabuhan", f"{col_type}{trow}", str),
            max_draft_m=r("max_draft_m", "pelabuhan", c_draft),
            max_loa_m=None,
            longest_berth_m=None if pid in UNRELIABLE_BERTH else r("longest_berth_m", "pelabuhan", f"{col_len}{trow}"),
            productivity=prod,
            tariff_class="utama" if str(cls_raw).strip().lower() == "utama" else str(int(cls_raw)),
            berth_type=r("berth_type", "biaya", f"G{brow}", str).lower(),
            refs=r.take(),
            note=PORT_NOTES.get(pid),
        ))
        dist = r("distance_nm", "rute", f"Y{rrow}")
        dref = r.take()
        inbound = side == "inbound"
        legs = ([dict(origin=pid, destination="KEK", distance_nm=dist, laden=True, refs=dref),
                 dict(origin="KEK", destination=pid, distance_nm=dist, laden=False, refs=dref)] if inbound else
                [dict(origin="KEK", destination=pid, distance_nm=dist, laden=True, refs=dref),
                 dict(origin=pid, destination="KEK", distance_nm=dist, laden=False, refs=dref)])
        routes.append(dict(id=f"rt.{pid}", name=(f"{name} – Batu Ampar – {name}" if inbound
                                                  else f"Batu Ampar – {name} – Batu Ampar"),
                           pattern="round_trip", legs=legs,
                           refs={"code": Book.ref("rute", f"X{rrow}")}))

    # --- tapak KEK
    kek_site = dict(
        name="TERSUS KI Batam — Batu Ampar",
        terminals=[
            dict(id="MP", name="Dermaga multipurpose", cargo_forms=["PK", "GC", "CK"],
                 berth_unit_length_m=r("berth_unit_length_m", "investasi", "C3"),
                 berth_width_m=r("berth_width_m", "investasi", "C5"), equipment_kind="HMC", berth_layout="quay",
                 trestle_width_m=r("trestle_width_m", "trestle", "C51"), refs=r.take()),
            dict(id="CC", name="Jetty curah cair", cargo_forms=["CC"],
                 berth_unit_length_m=r("berth_unit_length_m", "investasi", "C4"),
                 berth_width_m=r("berth_width_m", "investasi", "C6"), equipment_kind="MLA", berth_layout="jetty",
                 trestle_width_m=r("trestle_width_m", "trestle", "C60"), refs=r.take()),
        ],
        bathymetry=dummy_bathymetry(b),
        bathymetry_source="dummy",
        # Trestle!C50 (500 m) = panjang trestle penuh K15 = x* batimetri dummy, bukan batas fisik → max_length_m kosong.
        # Lebar trestle per terminal (C51 MP, C60 jetty) dipakai semua opsi; opsi keruk Excel memakai 50 m (C70, C79; A24).
        trestle=dict(height_m=r("height_m", "trestle", "C52"), unit_price_key="trestle", refs=r.take()),
        trestle_dredge=dict(trestle_length_m=r("trestle_length_m", "trestle", "C69"), unit_price_key="dredging",
                            refs=r.take()),
        waterside=dict(
            wind_kn=r("wind_kn", "perairan", "J3"), cross_current_kn=r("cross_current_kn", "perairan", "J4"),
            longitudinal_current_kn=r("longitudinal_current_kn", "perairan", "J5"),
            wave_height_m=r("wave_height_m", "perairan", "J6"),
            exposure=r("exposure", "perairan", "J7", str).lower(),
            maneuverability=r("maneuverability", "perairan", "J8", str).lower(),
            nav_aids=r("nav_aids", "perairan", "L3", str).lower().replace(" ", "_"),
            seabed=r("seabed", "perairan", "L4", str).lower().replace(" ", "_"),
            channel_slope="sedang", ship_speed_class=r("ship_speed_class", "perairan", "L6", str).lower(),
            lanes=2, long_channel=False, high_frequency=True, tug_assisted=True, depth_factor_of_draft=1.5,
        ),
        port_charges="none",
    )
    r.note_ref("channel_slope", "Fasilitas Perairan!L5")
    kek_site["trestle"]["refs"].update(
        max_length_m="kosong: Trestle!C50 = 500 m adalah panjang trestle penuh (= x* batimetri dummy), bukan batas",
        unit_price_key="Investasi!F11 (Trestle, Rp/m²)")
    kek_site["trestle_dredge"]["refs"].update(
        unit_price_key="Investasi!F17 (Dredging, Rp/m³)",
        note="lebar trestle (C70, C79 = 50 m) & kedalaman eksisting (C73, C82) tidak dipakai: lebar per terminal, "
             "kedalaman di ujung trestle dibaca dari batimetri (A24)")
    r.note_ref("lanes", "Fasilitas Perairan!K16 (2 jalur)")
    r.note_ref("long_channel", "Trestle!C40 = Fasilitas Perairan!L23 (alur relatif pendek, frekuensi tinggi)")
    r.note_ref("tug_assisted", "Fasilitas Perairan!K35/J37")
    r.note_ref("depth_factor_of_draft", "Fasilitas Perairan!K18 = 1,5×T")
    kek_site["waterside"]["refs"] = r.take()

    # --- kapal (nilai yang dipakai sheet Model baris 24-39; atribut tambahan dari Data Kapal)
    dk = {}
    for row in range(3, 60):
        nm = b.raw("kapal", f"D{row}")
        if isinstance(nm, str) and nm.strip() and nm.strip().lower() != "nama kapal":
            dk[nm.strip().replace("\xa0", "").upper()] = row
    ships, ship_by_model_id = [], {}
    used_ids: set[str] = set()
    for stype, c0, c1 in SHIP_TYPE_COLS:
        for ci in range(column_index_from_string(c0), column_index_from_string(c1) + 1):
            col = get_column_letter(ci)
            mid = str(b.raw("model", f"{col}24")).strip()
            name = r("name", "model", f"{col}25", str)
            sid = "ship." + slug(name)
            while sid in used_ids:
                sid += "_2"
            used_ids.add(sid)
            ship_by_model_id[mid] = sid
            s = dict(id=sid, name=name, ship_type=stype,
                     loa_m=r("loa_m", "model", f"{col}27"), beam_m=r("beam_m", "model", f"{col}28"),
                     draft_m=r("draft_m", "model", f"{col}29"), depth_m=r("depth_m", "model", f"{col}30"),
                     speed_kn=r("speed_kn", "model", f"{col}31"),
                     dwt_t=r("dwt_t", "model", f"{col}39"), gt=r("gt", "model", f"{col}37"),
                     me_kw=r("me_kw", "model", f"{col}33"), ae_kw=r("ae_kw", "model", f"{col}34"))
            # kapasitas TEU: sebagian kapal K15 diturunkan dari DWT (Data Kapal!O32 = ⌊0,85·DWT/20⌋), sebagian
            # diisi angka riil. Yang turunan dibiarkan kosong (engine pakai parameter); yang riil disimpan sbg isian.
            if stype == "container_ship":
                teu_model = int(b.raw("model", f"{col}26"))
                derived = int(float(b.raw("kapal", "V32")) * s["dwt_t"] // float(b.raw("kapal", "O53")))
                if teu_model != derived:
                    s["teu_capacity"] = r("teu_capacity", "model", f"{col}26", int)
                    s["note"] = f"Kapasitas TEU riil dari K15 ({teu_model} TEU); rumus turunan akan memberi {derived}."
            drow = dk.get(name.upper())
            if drow:
                imo = b.raw("kapal", f"C{drow}")
                if isinstance(imo, (int, float)):
                    s["imo"] = str(int(imo))
                    r.note_ref("imo", Book.ref("kapal", f"C{drow}"))
                cls = b.raw("kapal", f"E{drow}")
                if isinstance(cls, str) and cls.strip():
                    s["classification"] = cls.strip()
                    r.note_ref("classification", Book.ref("kapal", f"E{drow}"))
                lpp = b.raw("kapal", f"F{drow}")
                if isinstance(lpp, (int, float)) and lpp > 0:
                    s["lpp_m"] = float(lpp)
                    r.note_ref("lpp_m", Book.ref("kapal", f"F{drow}"))
            s["refs"] = r.take()
            s["refs"]["model_id"] = f"{mid} (Model!{col}24)"
            ships.append(s)

    # --- alat B/M
    equipment, equip_by_alat = [], {}
    for idx, (_name_cell, r0) in enumerate(HMC):
        name = r("name", "alat", f"C{r0}", str)
        un_t, un_b = r("prod_unload_t", "alat", f"C{r0+1}"), r("prod_unload_box", "alat", f"C{r0+2}")
        ld_t, ld_b = r("prod_load_t", "alat", f"C{r0+3}"), r("prod_load_box", "alat", f"C{r0+4}")
        e = dict(id="eq." + slug(name), name=name, kind="HMC", terminal_id="MP",
                 price_usd=r("price_usd", "alat", f"C{r0+7}"),
                 productivity={k: dict(unload=u, load=ld, unit=un,
                                       refs={"unload": Book.ref("alat", cu), "load": Book.ref("alat", cl)})
                               for k, u, ld, un, cu, cl in (
                                   ("GC", un_t, ld_t, "t/h", f"C{r0+1}", f"C{r0+3}"),
                                   ("CK", un_t, ld_t, "t/h", f"C{r0+1}", f"C{r0+3}"),
                                   ("PK", un_b, ld_b, "box/h", f"C{r0+2}", f"C{r0+4}"))},
                 reach_m=r("reach_m", "alat", f"C{r0+5}"), lift_t=r("lift_t", "alat", f"C{r0+6}"),
                 in_reference_model=idx < 5, refs=r.take())
        if idx == 5:
            e["note"] = "Ada di sheet Alat BM, tidak dipakai sheet Model (Alat 1–10)."
        equipment.append(e)
        if idx < 5:
            equip_by_alat[f"Alat {6 + idx}"] = e["id"]
    for idx, r0 in enumerate(MLA):
        name = r("name", "alat", f"J{r0}", str)
        e = dict(id="eq." + slug(name), name=name, kind="MLA", terminal_id="CC",
                 price_usd=r("price_usd", "alat", f"J{r0+3}"),
                 productivity={"CC": dict(unload=r("prod_unload_t", "alat", f"J{r0+1}"),
                                          load=r("prod_load_t", "alat", f"J{r0+2}"), unit="t/h",
                                          refs={"unload": Book.ref("alat", f"J{r0+1}"),
                                                "load": Book.ref("alat", f"J{r0+2}")})},
                 refs=r.take())
        equipment.append(e)
        equip_by_alat[f"Alat {1 + idx}"] = e["id"]

    loa_bands = []
    for row in range(34, 38):
        loa_bands.append(dict(loa_min_m=r("loa_min_m", "model", f"CF{row}"),
                              loa_max_m=r("loa_max_m", "model", f"CG{row}"),
                              per_berth=r("per_berth", "model", f"CH{row}", int), refs=r.take()))
    equipment_rules = dict(loa_bands=loa_bands,
                           max_per_berth={"MP": r("MP", "model", "CH37", int), "CC": r("CC", "model", "CC22", int)},
                           refs=r.take(),
                           note="K15 Model!CC23 memakai ⌈LOA_maks / radius alat⌉ (maks 4) untuk jumlah alat per "
                                "tambatan; keputusan A10 memakai tabel rentang LOA.")

    # --- tarif
    classes = []
    for i, cls in enumerate(["utama", "1", "2", "3", "4", "5"]):
        row, row_rp = 20 + i, 33 + i

        def opt(coord):
            v = b.raw("biaya", coord)
            return float(v) if isinstance(v, (int, float)) else None

        tug = []
        for k in range(9):
            cf = get_column_letter(column_index_from_string("Q") + 2 * k)
            cv = get_column_letter(column_index_from_string("R") + 2 * k)
            df = get_column_letter(column_index_from_string("AI") + k)
            dv = get_column_letter(column_index_from_string("AR") + k)
            rt = Rd(b)
            tug.append(dict(fixed_foreign_usd=rt("fixed_foreign_usd", "biaya", f"{cf}{row}"),
                            var_foreign_usd_per_gt=rt("var_foreign_usd_per_gt", "biaya", f"{cv}{row}"),
                            fixed_domestic_rp=rt("fixed_domestic_rp", "biaya", f"{df}{row_rp}"),
                            var_domestic_rp_per_gt=rt("var_domestic_rp_per_gt", "biaya", f"{dv}{row_rp}"),
                            refs=rt.take()))
        c = dict(
            tariff_class=cls,
            labuh_foreign_usd_per_gt=r("labuh_foreign_usd_per_gt", "biaya", f"C{row}"),
            labuh_domestic_rp_per_gt=r("labuh_domestic_rp_per_gt", "biaya", f"D{row}"),
            pandu_foreign_fixed_usd=r("pandu_foreign_fixed_usd", "biaya", f"E{row}"),
            pandu_foreign_var_usd_per_gt=r("pandu_foreign_var_usd_per_gt", "biaya", f"F{row}"),
            pandu_domestic_fixed_rp=r("pandu_domestic_fixed_rp", "biaya", f"G{row}"),
            pandu_domestic_var_rp_per_gt=r("pandu_domestic_var_rp_per_gt", "biaya", f"H{row}"),
            tambat_foreign_usd_per_gt_etmal={"beton": r("tambat_foreign_beton", "biaya", f"I{row}"),
                                             "dolphin": r("tambat_foreign_dolphin", "biaya", f"J{row}")},
            tambat_domestic_rp_per_gt_etmal={"beton": r("tambat_domestic_beton", "biaya", f"K{row}"),
                                             "dolphin": r("tambat_domestic_dolphin", "biaya", f"L{row}")},
            bm_foreign_rp_per_ton=r("bm_foreign_rp_per_ton", "biaya", f"M{row}"),
            bm_foreign_rp_per_teu=opt(f"N{row}"),
            bm_domestic_rp_per_ton=r("bm_domestic_rp_per_ton", "biaya", f"P{row}"),
            bm_domestic_rp_per_teu=opt(f"O{row}"),
            tug=tug,
        )
        c["refs"] = {**r.take(), "bm_foreign_rp_per_teu": Book.ref("biaya", f"N{row}"),
                     "bm_domestic_rp_per_teu": Book.ref("biaya", f"O{row}")}
        classes.append(c)
    gt_bands = []
    for row in range(3, 12):
        mx = b.raw("biaya", f"K{row}")
        r.note_ref("gt_max", Book.ref("biaya", f"K{row}"))
        gt_bands.append(dict(gt_min=r("gt_min", "biaya", f"J{row}"),
                             gt_max=float(mx) if isinstance(mx, (int, float)) else None, refs=r.take()))
    tariffs = dict(classes=classes, tug_gt_bands=gt_bands,
                   note="Nilai 'foreign' dalam USD (dikonversi dengan params.usd_rate), 'domestic' dalam Rp; "
                        "tarif B/M sudah dalam Rp.")

    # --- penyimpanan — sheet `Fasilitas Daratan` (dirujuk Investasi & Rangkuman; `Fasilitas Daratan Rata2` tidak
    # dirujuk sheet mana pun → bukan acuan, keputusan Tahap 7b)
    dry_bulk = dict(f_area=r("f_area", "daratan", "F130"), capacity_ratio=r("capacity_ratio", "daratan", "F131"),
                    stack_height_m=r("stack_height_m", "daratan", "F135"),
                    sor_max=r("sor_max", "daratan", "F134"), gross_volume_factor=1.0,
                    silo_capacity_m3=r("silo_capacity_m3", "daratan", "AC140"), silo_fill_ratio=0.8,
                    silo_price_usd=r("silo_price_usd", "daratan", "AC143"))
    r.note_ref("gross_volume_factor", "Fasilitas Daratan!F138→F139: volume netto langsung dibagi kapasitas silo "
                                      "(faktor bruto 1,3 hanya di sheet Rata2 yang tidak dipakai)")
    r.note_ref("silo_fill_ratio", "Fasilitas Daratan!F139 (×80%)")
    dry_bulk["refs"] = r.take()
    storage = dict(
        dwell_time_mode="from_consumption", inbound_share=1.0, outbound_share=1.0,
        container_yard=dict(area_per_teu_m2=r("area_per_teu_m2", "daratan", "G22"),
                            height_ratio=r("height_ratio", "daratan", "F23"),
                            yor_max=r("yor_max", "daratan", "F24"),
                            max_tiers=r("max_tiers", "daratan", "F46", int),
                            empty_share=r("empty_share", "daratan", "F37"), refs=r.take()),
        general_cargo=dict(f_area=r("f_area", "daratan", "F171"), f_bulk=r("f_bulk", "daratan", "F172"),
                           stack_height_m=r("stack_height_m", "daratan", "F177"),
                           sor_max=r("sor_max", "daratan", "F176"), refs=r.take()),
        dry_bulk=dry_bulk,
        liquid=dict(occupancy=r("occupancy", "daratan", "F228"),
                    tank_capacity_m3=r("tank_capacity_m3", "daratan", "F231"), refs=r.take()),
        yard_equipment=[
            dict(id="rtg", name="Rubber tyred gantry (RTG)", cargo_form="PK", productivity=5, productivity_unit="TEU/jam",
                 utilization=0.75, unit_price_key="rtg",
                 refs={"productivity": "Fasilitas Daratan!F93:F111 (5 TEU/jam, konstanta di rumus; in.fantasi 4, "
                                       "out.damai 8/12 → A19)", "utilization": "Fasilitas Daratan!F71:F113"}),
            dict(id="truk_petikemas", name="Truk petikemas", cargo_form="PK", role="transport",
                 productivity=1, productivity_unit="box/rit", utilization=1.0, unit_price_key="headtruck",
                 params={"speed_kmh": r("speed_kmh", "daratan", "M118")},
                 refs={**r.take(), "productivity": "1 box per rit (Fasilitas Daratan!F121: satu kontainer per truk)",
                       "params.unload_min": "kosong → waktu RTG per box di lapangan (Fasilitas Daratan!F123, A25)",
                       "utilization": "tidak dipakai (truk per alat B/M, §5.6)"}),
            dict(id="dozer", name="Bull dozer", cargo_form="CK", productivity=20, productivity_unit="ton/jam",
                 utilization=0.7, unit_price_key="bull_dozer",
                 refs={"productivity": "Fasilitas Daratan!M146:Y146 (20 t/jam di tahun bermuatan curah; F146:L146 = 50 "
                                       "saat muatan 0)", "utilization": "Fasilitas Daratan!F148"}),
            dict(id="truk_curah", name="Truk curah", cargo_form="CK", role="transport",
                 productivity=r("productivity", "daratan", "M154"), productivity_unit="ton/rit", utilization=1.0,
                 params={"speed_kmh": r("speed_kmh", "daratan", "M158"), "unload_min": r("unload_min", "daratan", "M160")},
                 refs={**r.take(), "utilization": "tidak dipakai (truk per alat B/M, §5.6)",
                       "note": "F162 (3 menit muat di dermaga) tidak dipakai: waktu muat = kapasitas / produktivitas "
                               "alat B/M (F156); Excel menghitung keduanya (A25)"}),
            dict(id="forklift", name="Forklift", cargo_form="GC", productivity=20, productivity_unit="ton/jam",
                 utilization=0.7, unit_price_key="forklift",
                 refs={"productivity": "Fasilitas Daratan!F201", "utilization": "Fasilitas Daratan!F203"}),
            dict(id="truk_gc", name="Truk general cargo", cargo_form="GC", role="transport",
                 productivity=r("productivity", "daratan", "F208"), productivity_unit="ton/rit", utilization=1.0,
                 params={"speed_kmh": r("speed_kmh", "daratan", "F211"), "unload_min": r("unload_min", "daratan", "F213")},
                 refs={**r.take(), "utilization": "tidak dipakai (truk per alat B/M, §5.6)",
                       "unit_price_key": "kosong: sheet Investasi tidak punya harga truk GC/curah (A25)"}),
        ],
    )
    storage["refs"] = {"dwell_time_mode": "Model!M350:AF359 (lama konsumsi); Fasilitas Daratan merata-rata 20 th "
                                          "(F173 = AVERAGE(Model!M350:AF350)) → v2 per tahun (A18)",
                       "inbound_share": "Fasilitas Daratan!F167 (100% muatan inbound)",
                       "outbound_share": "Fasilitas Daratan!F9 (100% muatan outbound)"}

    # --- harga satuan
    unit_prices, keys = [], set()
    year = int(b.raw("investasi", "H2"))
    for row in range(3, 71):
        label = b.raw("investasi", f"F{row}")
        price = b.raw("investasi", f"H{row}")
        if not (isinstance(label, str) and isinstance(price, (int, float))):
            continue
        key = slug(label)
        while key in keys:
            key += "_2"
        keys.add(key)
        cat = b.raw("investasi", f"I{row}")
        unit_prices.append(dict(key=key, label=label.strip(), unit=str(b.raw("investasi", f"G{row}")).strip(),
                                price_rp=float(price), category=str(cat).strip().lower() if cat else None, year=year,
                                refs={"price_rp": Book.ref("investasi", f"H{row}"), "year": Book.ref("investasi", "H2")}))

    # --- rencana hasil Evolver K15
    ship_by_flow = {}
    for i, fid in enumerate(FLOW_ORDER):
        mid = str(b.raw("model", f"CG{8 + i}")).strip()
        ship_by_flow[fid] = ship_by_model_id[mid]
    trestle_cost = float(b.raw("model", "K395"))
    plans = [dict(
        id="k15-excel", name="Hasil optimasi K15 (Evolver)",
        description="Kapal & alat terpilih di workbook K15. Dihitung ulang dengan engine v2 akan berbeda "
                    "karena koreksi audit.",
        ship_by_flow=ship_by_flow,
        equipment_by_terminal={"MP": equip_by_alat[str(b.raw("model", "DB9")).strip()],
                               "CC": equip_by_alat[str(b.raw("model", "DB8")).strip()]},
        waterside_mode="trestle",
        refs={"ship_by_flow": "Model!CG8:CG17", "MP": "Model!DB9", "CC": "Model!DB8",
              "waterside_mode": f"Model!K395 = {trestle_cost:,.0f} (cabang trestle penuh)"},
    )]

    assumptions = [
        dict(id="bathymetry", topic="Batimetri tapak KEK", status="dikonfirmasi",
             text="K15 tidak punya profil batimetri; dipakai profil DUMMY 17 titik (kek_site.bathymetry_source = "
                  "'dummy') yang dikunci ke angka K15: 10 m pada 250 m (opsi trestle + keruk) dan kedalaman perlu "
                  "21,3 m pertama tercapai pada 500 m (trestle penuh). Ganti dengan data survei/peta navigasi."),
        dict(id="kek_existing_port", topic="Data Pelabuhan Batu Ampar", status="dikonfirmasi",
             text="Data Pelabuhan!H5:H12 (panjang/kedalaman/kapasitas dermaga eksisting) bernilai 0. "
                  "TERSUS dibangun baru (greenfield)."),
        dict(id="port_productivity_mode", topic="Produktivitas pelabuhan asal/tujuan (A3)", status="dikonfirmasi",
             text="Semua pelabuhan diisi mode 'total per kapal' (tidak dikali jumlah alat). Bisa diubah per "
                  "pelabuhan ke 'per_equipment'."),
        dict(id="max_loa", topic="Batas LOA pelabuhan", status="dikonfirmasi",
             text="Dermaga boleh lebih pendek dari kapal: kapal layak bila dermaga terpanjang ≥ 85% LOA "
                  "(params.berth_loa_min_ratio), wajar terutama untuk dermaga dolphin (1 dermaga 1 kapal). "
                  "Lampia: angka 80 m di tabel ringkas berasal dari baris 'Pelabuhan Makasar', jadi tidak dipakai "
                  "(longest_berth_m kosong, tidak dicek) sampai ada data."),
        dict(id="draft_source", topic="Draft pelabuhan", status="dari_excel",
             text="Ada dua sumber draft (tabel ringkas Data Pelabuhan!F21:P25 dan blok detail). Dipakai blok detail "
                  "karena itulah yang dirujuk sheet Model."),
        dict(id="teu_capacity", topic="Kapasitas TEU kapal petikemas", status="dikonfirmasi",
             text="Kapasitas TEU default = ⌊teu_capacity_dwt_ratio·DWT / teu_nominal_weight_t⌋ = ⌊0,85·DWT / 20⌋ "
                  "seperti K15 (Data Kapal!O32). Isi ships[].teu_capacity bila kapasitas riil kapal diketahui."),
        dict(id="port_cost_static", topic="Biaya pelabuhan Excel (A11)", status="dikonfirmasi",
             text="Sheet Biaya Pelabuhan berisi nilai statis (tidak ikut berubah saat kapal diganti) dan memakai "
                  "voyage maks per kapal (65) bukan frekuensi aktual (92). Engine v2 menghitung dari tarif × "
                  "frekuensi aktual (sejalan keputusan A9). Di TERSUS KEK tidak dikenakan jasa kepelabuhanan."),
        dict(id="melbourne_productivity", topic="Produktivitas Melbourne", status="dari_excel",
             text="Excel memakai 1.500 t/jam; laporan menulis 40.000 t/jam. Dipakai nilai Excel."),
        dict(id="sfoc_source", topic="SFOC", status="dari_excel",
             text="SFOC diambil dari tabel rentang daya (Data Kapal!V8:Z21) seperti sheet Model; kolom S "
                  "Data Kapal (0,135) tidak dipakai."),
        dict(id="lct", topic="LCT/tongkang", status="asumsi",
             text="Tipe kapal LCT ditambahkan dan boleh membawa GC, tapi belum ada kandidat kapal & tarif charter."),
        dict(id="lhm800", topic="Liebherr LHM 800", status="asumsi",
             text="Ada di sheet Alat BM tapi tidak dipakai Model; tetap dimasukkan sebagai kandidat alat."),
    ]

    case = dict(
        schema_version="1", meta=meta, horizon=horizon, params=params, cargo_forms=cargo_forms,
        ship_types=ship_types, compatibility=compatibility, commodities=commodities, tenants=tenants,
        flows=flows, ports=ports, routes=routes, kek_site=kek_site, ships=ships, equipment=equipment,
        equipment_rules=equipment_rules, tariffs=tariffs, storage=storage, unit_prices=unit_prices,
        plans=plans, assumptions=assumptions,
    )
    return case


# ------------------------------------------------------------------------------------------
# GOLDEN (pembanding)
# ------------------------------------------------------------------------------------------


def num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def series(b: Book, sheet: str, row: int, cols: list[str]):
    return [num(b.raw(sheet, f"{c}{row}")) for c in cols]


def rng(sheet: str, row: int, cols: list[str]) -> str:
    return f"{SH[sheet].strip()}!{cols[0]}{row}:{cols[-1]}{row}"


def build_golden(b: Book, xlsx: Path, case: dict) -> dict:
    # (kunci, baris awal blok 10 flow, kolom tahun, temuan audit yang mempengaruhi)
    blocks = [
        ("freq_required", 28, YEAR_COLS_M, []),
        ("sea_time_days_per_call", 156, YEAR_COLS_M, ["A5"]),
        ("port_days_per_year", 169, YEAR_COLS_M, ["A2", "A3", "A10"]),
        ("port_days_per_call", 182, YEAR_COLS_M, ["A2", "A3", "A10"]),
        ("rtd_days", 195, YEAR_COLS_M, ["A2", "A3", "A5", "A10"]),
        ("voyages_max_per_ship", 208, YEAR_COLS_M, ["A1", "A2", "A3", "A5", "A10"]),
        ("ships", 221, YEAR_COLS_M, ["A1", "A2", "A3", "A5", "A10"]),
        ("fuel_me_l", 247, YEAR_COLS_M, ["A1", "A5", "A9"]),
        ("fuel_ae_l", 260, YEAR_COLS_M, ["A1", "A2", "A3", "A6", "A9", "A10"]),
        ("fuel_cost_me_rp", 273, YEAR_COLS_M, ["A1", "A5", "A9"]),
        ("fuel_cost_ae_rp", 286, YEAR_COLS_M, ["A1", "A2", "A3", "A6", "A9", "A10"]),
        ("voyage_cost_rp", 299, YEAR_COLS_M, ["A1", "A2", "A3", "A5", "A6", "A9", "A10"]),
        ("tch_cost_rp", 312, YEAR_COLS_M, ["A1", "A2", "A3", "A5", "A10"]),
        ("port_cost_rp", 325, YEAR_COLS_M, ["A11"]),
        ("shipping_cost_rp", 338, YEAR_COLS_M, ["A1", "A2", "A3", "A5", "A6", "A9", "A10", "A11"]),
        ("consumption_days", 350, YEAR_COLS_M, []),
        ("berth_days_required", 106, YEAR_COLS_M, ["A2", "A10"]),
    ]
    flows = {}
    for i, fid in enumerate(FLOW_ORDER):
        inbound = i < 5
        j = i if inbound else i - 5
        form = str(b.raw("model", f"L{3 + i}")).strip()
        s = {}
        s["demand"] = dict(ref=rng("model", 3 + i, YEAR_COLS_N), affected_by=[],
                           values=series(b, "model", 3 + i, YEAR_COLS_N))
        cpc_row = (54 if form == "PK" else 41) + i
        s["cargo_per_call"] = dict(ref=rng("model", cpc_row, YEAR_COLS_N), affected_by=[],
                                   values=series(b, "model", cpc_row, YEAR_COLS_N))
        kek_row = (68 if inbound else 87) + j
        ext_row = (82 if inbound else 73) + j
        s["port_days_kek_per_year"] = dict(ref=rng("model", kek_row, YEAR_COLS_M),
                                           affected_by=["A10"] + ([] if inbound or form == "PK" else ["A2"]),
                                           values=series(b, "model", kek_row, YEAR_COLS_M))
        s["port_days_ext_per_year"] = dict(ref=rng("model", ext_row, YEAR_COLS_M), affected_by=["A3", "A10"],
                                           values=series(b, "model", ext_row, YEAR_COLS_M))
        for key, r0, cols, aff in blocks:
            s[key] = dict(ref=rng("model", r0 + i, cols), affected_by=aff, values=series(b, "model", r0 + i, cols))
        mid = str(b.raw("model", f"CG{8 + i}")).strip()
        flows[fid] = dict(cargo_form=form, model_ship=mid, ship_id=case["plans"][0]["ship_by_flow"][fid],
                          equipment_per_berth=num(b.raw("model", f"CI{8 + i}")), series=s,
                          refs={"model_ship": f"Model!CG{8 + i}", "equipment_per_berth": f"Model!CI{8 + i} (A10)"})

    def ks(row, aff=()):
        return dict(ref=rng("model", row, YEAR_COLS_K), affected_by=list(aff), values=series(b, "model", row, YEAR_COLS_K))

    terminal = {
        "ship_days_kek_cc": ks(101, ["A2", "A10"]), "ship_days_kek_mp": ks(102, ["A2", "A10"]),
        "berth_days_cc": ks(119, ["A2", "A10"]), "berth_days_mp": ks(120, ["A2", "A10"]),
        "berths_cc": ks(124, ["A2", "A10"]), "berths_mp": ks(125, ["A2", "A10"]),
        "bor_cc": ks(144, ["A2", "A10"]), "bor_mp": ks(145, ["A2", "A10"]),
        "equipment_cc": ks(362, ["A2", "A10"]), "equipment_mp": ks(363, ["A2", "A10"]),
    }
    investment = {
        "yard_equipment_pk_rp": ks(370), "yard_equipment_ck_rp": ks(371), "yard_equipment_gc_rp": ks(372),
        "yard_equipment_cc_rp": ks(373),
        "handling_equipment_cc_rp": ks(376, ["A2", "A10"]), "handling_equipment_mp_rp": ks(377, ["A2", "A10"]),
        "storage_pk_rp": ks(381), "storage_ck_rp": ks(382), "storage_gc_rp": ks(383), "storage_cc_rp": ks(384),
        "berth_mp_rp": ks(387, ["A2", "A10"]), "jetty_cc_rp": ks(391, ["A2", "A10"]), "trestle_rp": ks(395),
    }
    aggregate = {
        "total_cost_rp": ks(399, ["semua"]), "total_cost_with_demand_rp": ks(403, ["semua"]),
        "unit_cost_rp_per_unit": ks(404, ["semua", "A7"]), "pv_unit_cost": ks(405, ["semua", "A7"]),
        "annualized_initial_investment_rp": dict(ref="Model!K400", value=num(b.raw("model", "K400"))),
        "total_pv_unit_cost": dict(ref="Model!K406", value=num(b.raw("model", "K406"))),
        "annuity": dict(ref="Model!K407", value=num(b.raw("model", "K407"))),
        "grand_total_cost_rp": dict(ref="Model!K408", value=num(b.raw("model", "K408"))),
    }
    def fs(row, aff):
        return dict(ref=rng("daratan", row, YEAR_COLS_F), affected_by=list(aff), values=series(b, "daratan", row, YEAR_COLS_F))

    storage = dict(
        note="Sheet `Fasilitas Daratan` (dirujuk Investasi & Rangkuman). Luas petikemas kosong = salinan luas full "
             "(F29:F32), jadi luas total CY = 2 × Σ luas full. Kebutuhan per tahun apa adanya (bisa turun).",
        excel_params=dict(
            rtg_productivity_teu_h={"in.fantasi": [4.0, 4.0], "out.damai": [8.0, 12.0], "out.fantasi": [5.0, 5.0],
                                    "out.baru": [5.0, 5.0]},
            liquid_density_t_m3=num(b.raw("daratan", "F226")),
            refs={"rtg_productivity_teu_h": "[full, kosong] Fasilitas Daratan!F69/F75, F81/F87, F93/F99, F105/F111 "
                                            "(konstanta di rumus, A19)",
                  "liquid_density_t_m3": "Fasilitas Daratan!F226:F227 (CPO & RBD olein, A20)"}),
        flows={fid: {k: fs(row, STORAGE_AFFECTED[k]) for k, row in rows.items()}
               for fid, rows in STORAGE_FLOW_ROWS.items()},
        total={k: fs(row, STORAGE_AFFECTED[k]) for k, row in STORAGE_TOTAL_ROWS.items()},
    )
    tch_reg = {}
    for code, ic, sc in (("bulk_carrier", "C15", "C16"), ("tanker", "I15", "I16"),
                         ("container_ship", "O15", "O16"), ("general_cargo_ship", "U15", "U16")):
        tch_reg[code] = dict(intercept=num(b.raw("tch", ic)), slope=num(b.raw("tch", sc)),
                             ref=f"TCH!{ic}:{sc}")
    ships = {}
    for _stype, c0, c1 in SHIP_TYPE_COLS:
        for ci in range(column_index_from_string(c0), column_index_from_string(c1) + 1):
            col = get_column_letter(ci)
            mid = str(b.raw("model", f"{col}24")).strip()
            ships[mid] = dict(ship_id="ship." + slug(b.raw("model", f"{col}25")),
                              payload=num(b.raw("model", f"{col}26")), ballast_speed_kn=num(b.raw("model", f"{col}32")),
                              sfoc_me=num(b.raw("model", f"{col}35")), sfoc_ae=num(b.raw("model", f"{col}36")),
                              tch_rp_per_year=num(b.raw("model", f"{col}38")),
                              refs=f"Model!{col}26,{col}32,{col}35,{col}36,{col}38")
    waterside = {k: dict(ref=f"Fasilitas Perairan!{c}", value=num(b.raw("perairan", c)) or 0.0) for k, c in WATERSIDE_CELLS}
    trestle = {k: dict(ref=f"Trestle!{c}", value=num(b.raw("trestle", c))) for k, c in TRESTLE_CELLS}
    for k, row in (("dredge_vol_mp_m3", 105), ("dredge_vol_cc_m3", 106), ("dredge_vol_total_m3", 107),
                   ("invest_mixed_rp", 108)):  # opsi trestle + keruk: dibangun per fase di tahun −1, 5, 10
        trestle[k] = dict(ref=f"Trestle!C{row},I{row},N{row}", years=[-1, 5, 10],
                          values=[num(b.raw("trestle", f"{c}{row}")) for c in ("C", "I", "N")])
    for k, row in (("berth_added_mp", 103), ("berth_added_cc", 104)):  # tahun −1 … 20 (kolom C … X)
        cols = [get_column_letter(column_index_from_string("C") + i) for i in range(22)]
        trestle[k] = dict(ref=f"Trestle!C{row}:X{row}", years=list(range(-1, 21)),
                          values=[num(b.raw("trestle", f"{c}{row}")) for c in cols])
    trucks = {form: {k: dict(ref=rng("daratan", row, YEAR_COLS_F), values=series(b, "daratan", row, YEAR_COLS_F))
                     for k, row in rows.items()} for form, rows in TRUCK_ROWS.items()}
    derived = {
        "ton_per_teu": {
            "tepung_jagung": dict(ref="Muatan!L21", value=num(b.raw("muatan", "L21"))),
            "tepung_terigu": dict(ref="Muatan!L59", value=num(b.raw("muatan", "L59"))),
            "aluminium": dict(ref="Muatan!C70", value=num(b.raw("muatan", "C70")), note="dibatasi NetMax kapal"),
        },
        "tch_regression_usd_per_day": tch_reg,
        "ships": ships,
    }
    return dict(
        source=xlsx.name, extracted_at=dt.date.today().isoformat(),
        note="Nilai Excel K15 (rumus lama) sebagai pembanding, BUKAN kunci jawaban. Seri dengan affected_by "
             "kosong seharusnya sama dengan engine v2; selain itu selisih harus bisa dijelaskan oleh temuan "
             "audit yang disebut (SPEC §11). Indeks tahun: values[0] = tahun ke-1.",
        flow_order=FLOW_ORDER, plan=case["plans"][0], flows=flows, terminal=terminal, storage=storage,
        investment=investment, aggregate=aggregate, waterside=waterside, trestle=trestle, trucks=trucks,
        derived=derived,
    )


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    xlsx = Path(sys.argv[1]).resolve()
    b = Book(xlsx)
    raw_case = build_case(b, xlsx)
    case = Case.model_validate(raw_case)  # gagal keras bila tidak valid
    OUT_CASE.parent.mkdir(parents=True, exist_ok=True)
    OUT_CASE.write_text(json.dumps(case.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2),
                        encoding="utf-8", newline="\n")
    golden = build_golden(b, xlsx, raw_case)
    OUT_GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    OUT_GOLDEN.write_text(json.dumps(golden, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"case   -> {OUT_CASE.relative_to(V2)}  ({len(case.flows)} flow, {len(case.ships)} kapal, "
          f"{len(case.equipment)} alat, {len(case.ports)} pelabuhan)")
    print(f"golden -> {OUT_GOLDEN.relative_to(V2)}")


if __name__ == "__main__":
    main()
