"""Tiruan rumus Excel K15 (sheet `Model` baris 28–359, `Biaya Pelabuhan`) — HANYA untuk validasi, bukan engine.

Tujuannya membuktikan bahwa selisih engine v2 vs golden Excel berasal dari temuan audit yang disebut: bila tiruan
ini (dengan kekeliruan Excel A1–A3, A5, A6, A9–A11, A13–A15 dan demand golden yang memuat A12) mereproduksi golden persis,
maka engine — yang identik kecuali pada titik-titik itu — hanya berbeda karena temuan tersebut.
Dipakai oleh `test_calc_voyage.py`, `test_calc_shipcost.py` dan `tools/diff_k15.py`.
"""

from __future__ import annotations

import math

from tpt_engine.calc import shipcost, vessel
from tpt_engine.domain import Case

EXCEL_SERIES = ("freq_required", "cargo_per_call", "port_days_kek_per_year", "port_days_ext_per_year",
                "sea_time_days_per_call", "port_days_per_year", "port_days_per_call", "rtd_days",
                "voyages_max_per_ship", "ships", "consumption_days", "fuel_me_l", "fuel_ae_l", "fuel_cost_me_rp",
                "fuel_cost_ae_rp", "voyage_cost_rp", "tch_cost_rp", "port_cost_rp", "shipping_cost_rp")


# urutan laporan: A3 dulu agar A10 hanya mengenai port KEK; biaya setelah operasi
FIXES = ("A3", "A10", "A2", "A5", "A1", "A13", "A9", "A6", "A11", "A14", "A15")

# konstanta sel Excel: liter per ton MFO (Model!F42)
XL_L_PER_T_MFO = 1123.596


def excel_chain(case: Case, golden: dict, fid: str, fixes: frozenset[str] | set[str] = frozenset(),
                demand: list[float] | None = None) -> dict[str, list[float]]:
    """Seri Excel untuk satu flow dengan rumus Excel apa adanya; `fixes` menerapkan koreksi audit satu per satu
    (semua FIXES + demand engine = engine v2). `demand` mengganti seri demand golden (mis. D_TEU engine, A12)."""
    gf = golden["flows"][fid]
    flow = next(f for f in case.flows if f.id == fid)
    model_ship = next(v for v in golden["derived"]["ships"].values() if v["ship_id"] == gf["ship_id"])
    ship = next(s for s in case.ships if s.id == gf["ship_id"])
    pk = flow.cargo_form == "PK"
    payload = model_ship["payload"]  # Model!AL26:BZ26 (TEU untuk PK)
    vb = model_ship["ballast_speed_kn"]  # A5: Model!AL32 = 130 % Vs
    if "A5" in fixes:
        vb = vessel.ballast_speed(ship, case.params)
    ci = gf["equipment_per_berth"]  # A10: Model!CI = 4 (2 untuk CC) apa pun LOA-nya
    term_id = "CC" if flow.cargo_form == "CC" else "MP"
    if "A10" in fixes:
        ci = vessel.n_equipment(ship, case.equipment_rules, term_id)
    equip = next(e for e in case.equipment if e.id == golden["plan"]["equipment_by_terminal"][term_id])
    pr = equip.productivity[flow.cargo_form]
    dd = pr.unload if flow.direction == "inbound" else pr.load  # Model!DD12:DD21 (box/h untuk PK, 1 TEU = 1 box)
    route = next(r for r in case.routes if r.id == flow.route_id)
    port = next(p for p in case.ports if p.id in {leg.origin for leg in route.legs} | {leg.destination for leg in route.legs})
    p_ext = port.productivity.value  # Data Pelabuhan!P5:P14
    dist = route.legs[0].distance_nm  # Model!G3:G12 (sekali jalan)
    fix = (case.params.at_hours + case.params.wt_hours + case.params.it_hours) / 24  # Model!F49
    days = case.params.working_days_per_year  # Model!F51 (dipakai sebagai hari operasi kapal)
    prm = case.params
    hsd = next(x for x in prm.fuels if x.code == "HSD")
    mfo = next(x for x in prm.fuels if x.code == "MFO")
    me_kw, ae_kw = ship.me_kw, shipcost.ae_kw(ship, prm)  # Model!AL33, AL34 (= 50 % ME)
    sfoc_me, sfoc_ae = model_ship["sfoc_me"], model_ship["sfoc_ae"]  # Model!AL35, AL36
    tch_yr = model_ship["tch_rp_per_year"]  # Model!AL38
    tr = next(c for c in case.tariffs.classes if c.tariff_class == port.tariff_class)
    gt = ship.gt  # Biaya Pelabuhan!C3:C12
    foreign = port.kind == "foreign" and "A14" in fixes  # A14: Excel selalu memakai kolom dalam negeri
    fx = prm.usd_rate if foreign else 1.0
    tug = tr.tug[shipcost.tug_band(case.tariffs, gt)]
    moves = 2 if "A15" in fixes else 1

    out: dict[str, list[float]] = {k: [] for k in EXCEL_SERIES}
    for d in (demand if demand is not None else gf["series"]["demand"]["values"]):
        f = math.ceil(d / payload - 1e-12) if d > 0 else 0  # Model!M28
        q = d / f if f else 0.0  # Model!N41 / N54
        kek_rate = dd * ci
        if flow.direction == "outbound" and not pk and "A2" not in fixes:
            kek_yr = (q / dd * ci) / 24 * f  # A2: Model!M87…M91 cabang non-PK — dikali jumlah alat
        else:
            kek_yr = q / kek_rate / 24 * f  # Model!M68 / M87 (PK)
        ext_yr = q / (p_ext * (1 if "A3" in fixes else ci)) / 24 * f  # A3: Model!M73 / M82 — × alat KEK
        sea = (dist / ship.speed_kn + dist / vb) / 24 if f else 0.0  # Model!M156
        port_yr = kek_yr + ext_yr + fix * f  # Model!M169
        port_call = port_yr / f if f else 0.0  # Model!M182
        rtd = sea + port_call  # Model!M195
        if not rtd:
            fmax = 0
        elif "A1" in fixes:
            fmax = math.floor(case.params.commission_days / rtd + 1e-9)
        else:
            fmax = math.ceil(days / rtd - 1e-12)  # A1: Model!M208 ROUNDUP
        ns = (math.ceil(f / fmax - 1e-12) if fmax else 0) if f >= fmax else 1  # Model!M221
        if "A13" in fixes:
            cons = q / (d / 365) if d > 0 else 0.0
        else:
            cons = math.ceil(payload / (d / 365) - 1e-12) if d > 0 else 0  # A13: Model!M350 — payload, ROUNDUP
        # §5.4 BBM (Model!M247, M260, M273, M286): Excel memakai F_max·N_ship voyage (A9), AE = MFO (A6)
        voy = f if "A9" in fixes else fmax * ns
        l_me = 1e6 / hsd.density_kg_m3  # Model!F44 = 1201,923 (pembulatan 1000/0,832; selisih < 1e-7, bukan temuan)
        l_ae = 1e6 / hsd.density_kg_m3 if "A6" in fixes else XL_L_PER_T_MFO
        me_l = (me_kw * voy * sfoc_me / 1e6 * l_me * sea * prm.mcr * 24
                + me_kw * voy * sfoc_me / 1e6 * l_me * port_call * prm.fuel_share_me_port * 24)
        ae_l = ae_kw * voy * sfoc_ae / 1e6 * l_ae * port_call * prm.mcr * 24
        me_rp = me_l * hsd.price_rp_per_l
        ae_rp = ae_l * (hsd.price_rp_per_l if "A6" in fixes else mfo.price_rp_per_l)
        tch = tch_yr * ns  # Model!M312
        # biaya pelabuhan (Biaya Pelabuhan!E71…E142): × F_max (A11), tarif dalam negeri (A14), 1 gerakan,
        # tunda tetap tidak dikali frekuensi, tambat × seluruh port time per call (A15)
        calls = f if "A11" in fixes else fmax
        if f:
            labuh = (tr.labuh_foreign_usd_per_gt * fx if foreign else tr.labuh_domestic_rp_per_gt) * gt
            # A14: baris pandu out.adi (Biaya Pelabuhan!E93:AF93) kolomnya terbalik → satu-satunya yang memakai tarif
            # luar negeri; baris lain selalu dalam negeri
            pandu_foreign = foreign or (fid == "out.adi" and "A14" not in fixes)
            if pandu_foreign:
                pandu = (tr.pandu_foreign_fixed_usd + tr.pandu_foreign_var_usd_per_gt * gt) * prm.usd_rate
            else:
                pandu = tr.pandu_domestic_fixed_rp + tr.pandu_domestic_var_rp_per_gt * gt
            if foreign:
                tug_fix, tug_var = tug.fixed_foreign_usd * fx, tug.var_foreign_usd_per_gt * fx
                tb = tr.tambat_foreign_usd_per_gt_etmal[port.berth_type] * fx
            else:
                tug_fix, tug_var = tug.fixed_domestic_rp, tug.var_domestic_rp_per_gt
                tb = tr.tambat_domestic_rp_per_gt_etmal[port.berth_type]
            berth = math.ceil(ext_yr / f - 1e-9) if "A15" in fixes else port_call
            if pk:
                bm_rate = tr.bm_foreign_rp_per_teu if foreign else tr.bm_domestic_rp_per_teu
            else:
                bm_rate = tr.bm_foreign_rp_per_ton if foreign else tr.bm_domestic_rp_per_ton
            if "A15" in fixes:
                tunda = (tug_fix + tug_var * gt) * moves * calls
            else:
                tunda = tug_fix + tug_var * gt * calls
            port_cost = (labuh + pandu * moves + tb * gt * berth + q * bm_rate) * calls + tunda
        else:
            port_cost = 0.0
        for k, v in (("freq_required", f), ("cargo_per_call", q), ("port_days_kek_per_year", kek_yr),
                     ("port_days_ext_per_year", ext_yr), ("sea_time_days_per_call", sea),
                     ("port_days_per_year", port_yr), ("port_days_per_call", port_call), ("rtd_days", rtd),
                     ("voyages_max_per_ship", fmax), ("ships", ns), ("consumption_days", cons),
                     ("fuel_me_l", me_l), ("fuel_ae_l", ae_l), ("fuel_cost_me_rp", me_rp), ("fuel_cost_ae_rp", ae_rp),
                     ("voyage_cost_rp", me_rp + ae_rp), ("tch_cost_rp", tch), ("port_cost_rp", port_cost),
                     ("shipping_cost_rp", me_rp + ae_rp + tch + port_cost)):
            out[k].append(float(v))
    return out


#: seri golden → (id variabel engine, faktor: 'per_call' = engine × F bila Excel per tahun) dan penyebab selisih
ENGINE_MAP: dict[str, tuple[str, str | None]] = {
    "freq_required": ("voyage.freq", None),
    "cargo_per_call": ("voyage.q", None),
    "port_days_kek_per_year": ("voyage.t_port_kek", "per_year"),
    "port_days_ext_per_year": ("voyage.t_port_ext", "per_year"),
    "sea_time_days_per_call": ("voyage.t_sea", None),
    "port_days_per_year": ("voyage.t_port", "per_year_fix"),
    "port_days_per_call": ("voyage.t_port", "plus_fix"),
    "rtd_days": ("voyage.rtd", None),
    "voyages_max_per_ship": ("voyage.f_max", None),
    "ships": ("voyage.n_ship", None),
    "consumption_days": ("voyage.consumption", None),
    "fuel_me_l": ("shipcost.fuel_me_l", None),
    "fuel_ae_l": ("shipcost.fuel_ae_l", None),
    "fuel_cost_me_rp": ("shipcost.fuel_me", None),
    "fuel_cost_ae_rp": ("shipcost.fuel_ae", None),
    "voyage_cost_rp": ("shipcost.voyage", None),
    "tch_cost_rp": ("shipcost.tch", None),
    "port_cost_rp": ("shipcost.port", None),
    "shipping_cost_rp": ("shipcost.total", None),
}

#: penyebab selisih per seri (selain A12 yang terbawa dari demand TEU)
CAUSES: dict[str, tuple[str, ...]] = {
    "freq_required": (),
    "cargo_per_call": (),
    "port_days_kek_per_year": ("A2", "A10"),
    "port_days_ext_per_year": ("A3",),
    "sea_time_days_per_call": ("A5",),
    "port_days_per_year": ("A2", "A3", "A10"),
    "port_days_per_call": ("A2", "A3", "A10"),
    "rtd_days": ("A2", "A3", "A5", "A10"),
    "voyages_max_per_ship": ("A1", "A2", "A3", "A5", "A10"),
    "ships": ("A1", "A2", "A3", "A5", "A10"),
    "consumption_days": ("A13",),
    "fuel_me_l": ("A1", "A2", "A3", "A5", "A9", "A10"),
    "fuel_ae_l": ("A1", "A2", "A3", "A5", "A6", "A9", "A10"),
    "fuel_cost_me_rp": ("A1", "A2", "A3", "A5", "A9", "A10"),
    "fuel_cost_ae_rp": ("A1", "A2", "A3", "A5", "A6", "A9", "A10"),
    "voyage_cost_rp": ("A1", "A2", "A3", "A5", "A6", "A9", "A10"),
    "tch_cost_rp": ("A1", "A2", "A3", "A5", "A10"),
    "port_cost_rp": ("A1", "A2", "A3", "A5", "A10", "A11", "A14", "A15"),
    "shipping_cost_rp": ("A1", "A2", "A3", "A5", "A6", "A9", "A10", "A11", "A14", "A15"),
}


def engine_series(values: dict, fid: str, key: str) -> list[float]:
    """Seri engine dalam bentuk yang sebanding dengan seri golden `key`."""
    vid, mode = ENGINE_MAP[key]
    s = values[vid][fid]
    f = values["voyage.freq"][fid]
    fix = values["voyage.t_fix"][fid]
    if mode == "per_year":
        return [a * b for a, b in zip(s, f, strict=True)]
    if mode == "per_year_fix":
        return [(a + fix) * b for a, b in zip(s, f, strict=True)]
    if mode == "plus_fix":
        return [a + fix if b else 0.0 for a, b in zip(s, f, strict=True)]
    return list(s)
