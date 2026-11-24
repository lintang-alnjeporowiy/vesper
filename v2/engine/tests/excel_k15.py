"""Tiruan rumus Excel K15 (sheet `Model` baris 28–363, `Biaya Pelabuhan`) — HANYA untuk validasi, bukan engine.

Tujuannya membuktikan bahwa selisih engine v2 vs golden Excel berasal dari temuan audit yang disebut: bila tiruan
ini (dengan kekeliruan Excel A1–A3, A5, A6, A9–A11, A13–A15 dan demand golden yang memuat A12) mereproduksi golden persis,
maka engine — yang identik kecuali pada titik-titik itu — hanya berbeda karena temuan tersebut.
Terminal KEK (`excel_terminal`): A16, A17 di atas rantai per flow. Penyimpanan (`excel_storage`): A18–A20.
Perairan (`excel_waterside`, sheet `Fasilitas Perairan` & `Trestle`): A21–A24; truk dermaga–lapangan (`excel_trucks`): A25.
Dipakai oleh `test_calc_voyage.py`, `test_calc_shipcost.py`, `test_calc_terminal.py`, `test_calc_storage.py`,
`test_calc_waterside.py` dan `tools/diff_k15.py`.
"""

from __future__ import annotations

import math

from tpt_engine.calc import shipcost, storage, vessel, waterside
from tpt_engine.calc.cargo import ceil_
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


#: seri golden terminal (per terminal KEK, Model!K101:AD363)
TERMINAL_SERIES = ("ship_days_kek", "berth_days", "berths", "bor", "equipment")
TERMINAL_FIXES = ("A16", "A17")


def excel_terminal(case: Case, golden: dict, chains: dict[str, dict[str, list[float]]],
                   fixes: frozenset[str] | set[str] = frozenset()) -> dict[str, dict[str, list[float]]]:
    """Seri terminal Excel (`{seri}_{mp|cc}` → nilai) dari seri per flow `excel_chain` (`chains`).

    Excel: shipDays = waktu bongkar muat KEK per tahun saja (A17: tanpa IT); berth-days = ⌈shipDays · LOA / L⌉ dengan
    L = 40 m (CC) hanya di kolom tahun ke-1 — cek label `L107` relatif bergeser ke sel tahun sehingga mulai tahun ke-2
    semua flow memakai 300 m (MP); baris pertama memakai `$L$106` absolut (A16). Jumlah alat = tambatan × CC22/CC23.
    """
    prm = case.params
    flows = {f.id: f for f in case.flows}
    order = golden["flow_order"]
    it_days = prm.it_hours / prm.working_hours_per_day
    n_years = len(next(iter(chains.values()))["freq_required"])
    l_mp = next(t for t in case.kek_site.terminals if t.id == "MP").berth_unit_length_m  # Model!F54
    l_cc = next(t for t in case.kek_site.terminals if t.id == "CC").berth_unit_length_m  # Model!C58
    out: dict[str, list[float]] = {}
    for term in ("mp", "cc"):
        is_cc = term == "cc"
        fids = [f for f in order if (flows[f].cargo_form == "CC") == is_cc]
        sd_t, bd_t = [0.0] * n_years, [0.0] * n_years
        ci = next(golden["flows"][f]["equipment_per_berth"] for f in fids)  # Model!CC22 / CC23
        neq = [0] * n_years
        for fid in fids:
            ch = chains[fid]
            ship = next(s for s in case.ships if s.id == golden["flows"][fid]["ship_id"])
            for y in range(n_years):
                f = ch["freq_required"][y]
                sd = ch["port_days_kek_per_year"][y] + (it_days * f if "A17" in fixes else 0.0)  # Model!M68…M91
                if "A16" in fixes:
                    bd = (ceil_(sd) if is_cc else ceil_(sd * ship.loa_m / l_mp)) if sd else 0
                else:
                    cc_label = is_cc and y == 0 and fid != order[0]  # Model!M106…M115
                    bd = ceil_(sd * ship.loa_m / (l_cc if cc_label else l_mp)) if sd else 0
                sd_t[y] += sd
                bd_t[y] += bd
                if f:
                    neq[y] = max(neq[y], vessel.n_equipment(ship, case.equipment_rules, term.upper()))
        berths = [float(ceil_(s_ / (prm.bor_max * (s_ / b_) * prm.working_days_per_year))) if s_ else 0.0
                  for s_, b_ in zip(sd_t, bd_t, strict=True)]  # Model!K124:AD125
        bor = [b_ / (n * prm.working_days_per_year) if n else 0.0 for b_, n in zip(bd_t, berths, strict=True)]
        if "A10" in fixes:
            m = 0
            eq = []
            for n, e in zip(berths, neq, strict=True):
                m = max(m, e)
                eq.append(n * m)
        else:
            eq = [n * ci for n in berths]  # Model!K362:AD363
        for k, v in (("ship_days_kek", sd_t), ("berth_days", bd_t), ("berths", berths), ("bor", bor), ("equipment", eq)):
            out[f"{k}_{term}"] = [float(x) for x in v]
    return out


#: seri golden terminal → id variabel engine (per terminal; ship_days/berth_days = Σ flow di terminal)
TERMINAL_MAP = {"ship_days_kek": "terminal.ship_days", "berth_days": "terminal.berth_days", "berths": "terminal.n_berth",
                "bor": "terminal.bor", "equipment": "terminal.n_equip"}
TERMINAL_CAUSES = {"ship_days_kek": ("A2", "A10", "A17"), "berth_days": ("A2", "A10", "A16", "A17"),
                   "berths": ("A2", "A10", "A16", "A17"), "bor": ("A2", "A10", "A16", "A17"),
                   "equipment": ("A2", "A10", "A16", "A17")}


def engine_terminal(case: Case, values: dict, key: str) -> list[float]:
    """Seri engine sebanding dengan seri golden terminal `key` (mis. `berths_mp`)."""
    name, term = key.rsplit("_", 1)
    vid = TERMINAL_MAP[name]
    if vid in ("terminal.ship_days", "terminal.berth_days"):
        fids = [f.id for f in case.flows if (f.cargo_form == "CC") == (term == "cc")]
        rows = [values[vid][f] for f in fids if f in values[vid]]
        return [float(sum(x)) for x in zip(*rows, strict=True)]
    return list(values[vid][term.upper()])


#: koreksi penyimpanan (§5.6), di atas koreksi per flow (A12 demand, A13 lama konsumsi)
STORAGE_FIXES = ("A18", "A19", "A20")


def _never_decrease(seq: list[float]) -> list[float]:
    m, out = 0.0, []
    for v in seq:
        m = max(m, v)
        out.append(m)
    return out


def excel_storage(case: Case, golden: dict, chains: dict[str, dict[str, list[float]]],
                  demands: dict[str, list[float]], fixes: frozenset[str] | set[str] = frozenset()) -> dict[str, dict]:
    """Tiruan sheet `Fasilitas Daratan` dari demand (`demands`, satuan flow; TEU untuk PK) dan lama konsumsi per flow
    (`chains[f]["consumption_days"]`). Mengembalikan `flows`/`total` (bentuk golden, kebutuhan per tahun apa adanya)
    dan `engine` (bentuk variabel engine `storage.*`: kunci flow + `total` = Σ tidak pernah turun; alat berkunci id).

    Excel: dwell = AVERAGE lama konsumsi 20 tahun (termasuk tahun nol); in.fantasi per tahun kecuali F13/J13/O13 = MAX
    blok tahun 1–5 / 6–10 / 11–20 (A18). RTG per flow & per full/kosong, produktivitas per tenant (A19). Densitas curah
    cair 0,9 tetap (A20). Luas kosong = salinan luas full (F29:F32) — sama dengan (1 + porsi kosong) bila porsi = 100 %.
    """
    gs = golden["storage"]
    xp = gs["excel_params"]
    sp = case.storage
    cy, gc, db, lq = sp.container_yard, sp.general_cargo, sp.dry_bulk, sp.liquid
    prm = case.params
    hours = prm.working_days_per_year * prm.working_hours_per_day  # Fasilitas Daratan: 365 · 24
    flows = {f.id: f for f in case.flows}
    com = {c.id: c for c in case.commodities}
    eq = {e.id: e for e in sp.yard_equipment}
    n = len(next(iter(demands.values())))
    e_share = cy.empty_share

    def dwell(fid: str) -> list[float]:
        c = list(chains[fid]["consumption_days"])
        if "A18" in fixes:
            return c
        if fid == "in.fantasi":  # Fasilitas Daratan!F13:Y13
            out = list(c)
            out[0], out[4], out[9] = max(c[0:5]), max(c[5:10]), max(c[10:20])
            return out
        return [sum(c) / len(c)] * n  # AVERAGE(Model!M35x:AF35x)

    res_f: dict[str, dict[str, list[float]]] = {}
    eng: dict[str, dict[str, list[float]]] = {}

    def put(var: str, fid: str, s: list[float]) -> None:
        eng.setdefault(var, {})[fid] = [float(x) for x in s]

    cy_tot = [0.0] * n
    rtg_xl = [0.0] * n
    q_by_form: dict[str, list[float]] = {}
    for fid, rows in gs["flows"].items():
        fl = flows[fid]
        q = list(demands[fid])
        t = dwell(fid)
        r: dict[str, list[float]] = {"dwell_days": t}
        put("storage.throughput", fid, q)
        put("storage.dwell", fid, [tt if qq > 0 else 0.0 for qq, tt in zip(q, t, strict=True)])
        if "cy_area_full_m2" in rows:
            area = [qq * tt * cy.area_per_teu_m2 / (cy.height_ratio * 365 * cy.yor_max) for qq, tt in zip(q, t, strict=True)]
            gsf = [qq * tt / (cy.height_ratio * 365 * cy.yor_max * cy.max_tiers) for qq, tt in zip(q, t, strict=True)]
            gse = [qq * e_share * tt / (cy.height_ratio * 365 * cy.yor_max * cy.max_tiers) for qq, tt in zip(q, t, strict=True)]
            p_full, p_empty = xp["rtg_productivity_teu_h"][fid]
            u = eq["rtg"].utilization
            rf = [float(ceil_(qq / (p_full * hours * u))) if qq else 0.0 for qq in q]
            re_ = [float(ceil_(qq * e_share / (p_empty * hours * u))) if qq else 0.0 for qq in q]
            r.update(cy_area_full_m2=area, ground_slots_full=gsf, ground_slots_empty=gse, rtg_full=rf, rtg_empty=re_)
            cy_tot = [a + 2 * b for a, b in zip(cy_tot, area, strict=True)]  # F33 = Σ full + salinan kosong
            rtg_xl = [a + b + c for a, b, c in zip(rtg_xl, rf, re_, strict=True)]
            put("storage.cy", fid, [(1 + e_share) * a for a in area])
            put("storage.cy_slots", fid, [a + b for a, b in zip(gsf, gse, strict=True)])
            qe = [qq * (1 + e_share) for qq in q]
        elif "gc_area_m2" in rows:
            rho = com[fl.commodity_id].density_t_m3
            assert rho
            area = [gc.f_area * gc.f_bulk * qq * tt / (gc.stack_height_m * 365 * gc.sor_max * rho) for qq, tt in zip(q, t, strict=True)]
            r["gc_area_m2"] = area
            put("storage.gc", fid, area)
            qe = q
        elif "silo_volume_m3" in rows:
            rho = com[fl.commodity_id].density_t_m3
            assert rho
            vol = [qq * tt * db.capacity_ratio / (365 * rho * db.sor_max) for qq, tt in zip(q, t, strict=True)]
            area = [db.f_area * qq * tt * db.capacity_ratio / (db.stack_height_m * 365 * db.sor_max * rho) for qq, tt in zip(q, t, strict=True)]
            assert db.silo_capacity_m3
            ns = [float(ceil_(v / (db.silo_capacity_m3 * db.silo_fill_ratio))) if v else 0.0 for v in vol]
            r.update(bulk_area_m2=area, silo_volume_m3=vol, silos=ns)
            put("storage.bulk", fid, [db.gross_volume_factor * v for v in vol])
            put("storage.bulk_area", fid, area)
            put("storage.silos", fid, ns)
            qe = q
        else:
            rho = com[fl.commodity_id].density_t_m3 if "A20" in fixes else xp["liquid_density_t_m3"]
            assert rho
            vol = [qq * tt / (365 * lq.occupancy * rho) for qq, tt in zip(q, t, strict=True)]
            nt = [float(ceil_(v / lq.tank_capacity_m3)) if v else 0.0 for v in vol]
            r.update(tank_volume_m3=vol, tanks=nt)
            put("storage.liquid", fid, vol)
            put("storage.tanks", fid, nt)
            qe = q
        res_f[fid] = r
        acc = q_by_form.setdefault(fl.cargo_form, [0.0] * n)
        q_by_form[fl.cargo_form] = [a + b for a, b in zip(acc, qe, strict=True)]

    def pool(eid: str) -> list[float]:
        e = eq[eid]
        return [float(ceil_(x / (e.productivity * e.utilization * hours))) if x else 0.0 for x in q_by_form[e.cargo_form]]

    dozers, forklifts = pool("dozer"), pool("forklift")  # F150 (curah), F205 (GC: sudah satu armada di Excel)
    rtg = pool("rtg") if "A19" in fixes else rtg_xl
    for var, by in list(eng.items()):
        if var in ("storage.throughput", "storage.dwell"):
            continue
        by["total"] = _never_decrease([sum(x) for x in zip(*by.values(), strict=True)])
    eng["storage.yard_equipment"] = {"rtg": _never_decrease(rtg), "dozer": _never_decrease(dozers),
                                     "forklift": _never_decrease(forklifts)}
    return dict(flows=res_f, total=dict(cy_area_m2=cy_tot, dozers=dozers, forklifts=forklifts, rtg=rtg), engine=eng)


#: penyebab selisih per variabel penyimpanan engine (selain A12/A13 dari demand & lama konsumsi)
STORAGE_CAUSES = {"storage.dwell": ("A13", "A18"), "storage.throughput": ("A12",),
                  "storage.cy": ("A12", "A13", "A18"), "storage.cy_slots": ("A12", "A13", "A18"),
                  "storage.gc": ("A13", "A18"), "storage.bulk": ("A13", "A18"), "storage.bulk_area": ("A13", "A18"),
                  "storage.silos": ("A13", "A18"), "storage.liquid": ("A13", "A18", "A20"),
                  "storage.tanks": ("A13", "A18", "A20"), "storage.yard_equipment": ("A12", "A19")}


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


# ─── §5.7 perairan & trestle vs keruk, truk dermaga–lapangan (Tahap 8a) ─────────────────────────────────────────────
#: koreksi perairan & truk, di atas koreksi flow/terminal/penyimpanan
WATERSIDE_FIXES = ("A21", "A22", "A23", "A24")
TRUCK_FIXES = ("A25",)
#: baris tabel Fasilitas Perairan yang dipilih tangan di Excel (kelipatan B): G22 = D26, G32 = D36, G42 = D44,
#: G50 = D51, G54 = D55, G58 = D60 (tanah lunak, walau h = 1,5 T), G63 kosong, G70 = D74, G82 = D83, E12 = C13
XL_WM, XL_WB, XL_WS = 1.5, 0.5, 1.6
XL_WA = dict(wa_wind=0.4, wa_cross_current=0.7, wa_long_current=0.1, wa_wave=0.5, wa_nav_aids=0.2, wa_bottom=0.1,
             wa_depth=0.0)
WATERSIDE_VARS = ("waterside.gov_loa", "waterside.gov_beam", "waterside.gov_draft", "waterside.depth_req",
                  "waterside.channel_width", "waterside.channel_length", "waterside.entrance_width",
                  "waterside.stopping_distance", "waterside.turning_basin", "waterside.turning_area",
                  "waterside.anchorage_radius", "waterside.x_star", "waterside.trestle_len", "waterside.tip_depth",
                  "waterside.pocket_length", "waterside.pocket_width", "waterside.dredge_vol", "waterside.cost")
OPTION_KEYS = ("trestle_len", "tip_depth", "trestle_area", "dredge_vol", "cost_trestle", "cost_dredge")


def _x_star(bathy, depth: float) -> float:
    x = waterside.x_star(bathy, depth)
    assert x is not None
    return x


def excel_waterside(case: Case, golden: dict, chains: dict[str, dict[str, list[float]]],
                    term: dict[str, list[float]], fixes: frozenset[str] | set[str] = frozenset()) -> dict[str, dict]:
    """Tiruan sheet `Fasilitas Perairan` & `Trestle` dari kapal rencana K15, frekuensi per flow (`chains`) dan jumlah
    tambatan (`term` = `excel_terminal`). `cells` = bentuk golden (sel tunggal & per fase), `engine` = bentuk
    variabel `waterside.*` (kunci terminal + `site`), `options` = tiga opsi perairan (bentuk `WatersideOption`).

    Excel: satu kapal penentu = LOA terbesar atas 10 kapal rencana, B & T dari kapal itu (A21); Wa kecepatan
    = 0,1 · Vs (knot), Wa dasar laut 0,1 B walau h = 1,5 T, alur 1 jalur satu Wb (A22); luas kolam putar dari
    1,5 LOA (A23); opsi trestle + keruk: lebar trestle 50 m (MP & jetty), kolam jetty 40 m (A24). Panjang trestle
    penuh = x* batimetri (dummy dikunci ke Trestle!C50 = 500 m). Nilai per tahun mengikuti pola engine: fasilitas
    desain ada sejak tahun pertama terminal punya tambatan.
    """
    site = case.kek_site
    w = site.waterside
    bathy = site.bathymetry
    n = len(next(iter(chains.values()))["freq_required"])
    flows = {f.id: f for f in case.flows}
    ships = {s.id: s for s in case.ships}
    order = golden["flow_order"]
    term_of = {f: ("CC" if flows[f].cargo_form == "CC" else "MP") for f in order}
    ship_of = {f: ships[golden["flows"][f]["ship_id"]] for f in order}
    site_key = waterside.SITE
    keys = ("MP", "CC", site_key)
    big = max((ship_of[f] for f in order), key=lambda s: s.loa_m)  # Fasilitas Perairan!C4 = MAX(Model!CH8:CH17)
    gov: dict[str, dict[str, list[float]]] = {}
    for key in keys:
        if "A21" in fixes:
            act = [[ship_of[f] for f in order if (key == site_key or term_of[f] == key) and chains[f]["freq_required"][y]]
                   for y in range(n)]
            gov[key] = {d: waterside.governing([[getattr(s, a) for s in ys] for ys in act])
                        for d, a in (("loa", "loa_m"), ("beam", "beam_m"), ("draft", "draft_m"))}
        else:  # C5:C6 = XLOOKUP(LOA, …) → B dan T kapal ber-LOA terbesar
            gov[key] = {"loa": [big.loa_m] * n, "beam": [big.beam_m] * n, "draft": [big.draft_m] * n}
    fac = w.depth_factor_of_draft  # K18 = 1,5 · T
    depth = {k: [fac * t for t in gov[k]["draft"]] for k in keys}

    def channel(b: float) -> tuple[float, float, dict[str, float]]:
        wa = {k: v * b for k, v in XL_WA.items()}
        wa["wa_speed"] = 0.0 if "A22" in fixes else 0.1 * big.speed_kn  # G18 = D18 · C8 (Vs, baris "cepat")
        if "A22" in fixes:
            wa["wa_bottom"] = 0.0  # h = 1,5 T → baris B58 (0)
        tot = sum(wa.values())
        wm, wb, wss = XL_WM * b, XL_WB * b, XL_WS * b
        w1 = wm + tot + (2 if "A22" in fixes else 1) * wb  # K14 = E12 + G66 + G70
        w2 = 2 * (wm + tot + wb) + wss  # K16 = 2 · K14(Excel) + G82
        return w1, w2, dict(wa, wm=wm, wb=wb, ws=wss, wa_total=tot)

    s_loa, s_beam, s_dep = gov[site_key]["loa"], gov[site_key]["beam"], depth[site_key]
    eng: dict[str, dict[str, list[float]]] = {v: {} for v in WATERSIDE_VARS}
    for d in ("loa", "beam", "draft"):
        for k in keys:
            eng[f"waterside.gov_{d}"][k] = list(gov[k][d])
    for k in keys:
        eng["waterside.depth_req"][k] = list(depth[k])
    eng["waterside.channel_width"][site_key] = [channel(b)[0 if w.lanes == 1 else 1] if b else 0.0 for b in s_beam]
    eng["waterside.channel_length"][site_key] = [1.5 * x for x in s_loa]  # L23 (alur pendek, frekuensi tinggi)
    eng["waterside.entrance_width"][site_key] = [1.0 * x for x in s_loa]  # K29
    eng["waterside.stopping_distance"][site_key] = [7.0 * x for x in s_loa]  # K32
    eng["waterside.turning_basin"][site_key] = [2.0 * x for x in s_loa]  # K35 (dengan kapal tunda)
    eng["waterside.turning_area"][site_key] = [math.pi * ((2.0 if "A23" in fixes else 1.5) * x / 2) ** 2
                                              for x in s_loa]  # K37 = π (K36/2)²
    eng["waterside.anchorage_radius"][site_key] = [x + 6 * dd if x else 0.0 for x, dd in zip(s_loa, s_dep, strict=True)]

    p_tr = next(u.price_rp for u in case.unit_prices if u.key == site.trestle.unit_price_key)  # Investasi!H11
    p_dr = next(u.price_rp for u in case.unit_prices if u.key == site.trestle_dredge.unit_price_key)  # H17
    mixed_len = site.trestle_dredge.trestle_length_m  # Trestle!C69 = C78
    terms = {t.id: t for t in site.terminals}
    plan_mode = case.plans[0].waterside_mode
    options: dict[str, dict] = {m: dict({k: {} for k in OPTION_KEYS}, cost=0.0) for m in ("trestle", "mixed", "dredge")}
    for tid in ("MP", "CC"):
        tm = terms[tid]
        nb = term[f"berths_{tid.lower()}"]
        used = [any(v > 0 for v in nb[: y + 1]) for y in range(n)]
        eng["waterside.x_star"][tid] = [_x_star(bathy, dd) for dd in depth[tid]]
        d_des = depth[tid][-1]
        xs = _x_star(bathy, d_des)
        loa_d, beam_d = gov[tid]["loa"][-1], gov[tid]["beam"][-1]
        pl = 1.175 * loa_d if tm.berth_layout == "jetty" and "A24" in fixes else tm.berth_unit_length_m  # C25 / C30
        pw = 1.5 * beam_d  # Trestle!C38 = Fasilitas Perairan!K42
        chosen = None
        for m, opt in options.items():
            ln = xs if m == "trestle" else (0.0 if m == "dredge" else min(mixed_len, xs))
            wd_ = tm.trestle_width_m if (m != "mixed" or "A24" in fixes) else 50.0  # C70, C79 = 50 m
            tip = waterside.depth_at(bathy, ln)  # C73 = C82 = 10 m pada 250 m
            area, vol = ln * wd_, nb[-1] * pl * pw * max(0.0, d_des - tip)
            for k, val in zip(OPTION_KEYS, (ln, tip, area, vol, area * p_tr, vol * p_dr), strict=True):
                opt[k][tid] = val
            opt["cost"] += area * p_tr + vol * p_dr
            if m == plan_mode:
                chosen = (ln, tip, area)
        assert chosen is not None
        ln, tip, area = chosen
        vol = [b * pl * pw * max(0.0, d_des - tip) for b in nb]
        eng["waterside.trestle_len"][tid] = [ln if u else 0.0 for u in used]
        eng["waterside.tip_depth"][tid] = [tip if u else 0.0 for u in used]
        eng["waterside.pocket_length"][tid] = [pl if u else 0.0 for u in used]
        eng["waterside.pocket_width"][tid] = [pw if u else 0.0 for u in used]
        eng["waterside.dredge_vol"][tid] = vol
        eng["waterside.cost"][tid] = [(area if u else 0.0) * p_tr + v * p_dr for u, v in zip(used, vol, strict=True)]

    # bentuk golden: nilai akhir horizon kapal penentu site (Fasilitas Perairan) dan opsi (Trestle)
    w1, w2, parts = channel(s_beam[-1])
    loa_s, beam_s, dep_s = s_loa[-1], s_beam[-1], s_dep[-1]
    cells: dict[str, object] = dict(
        governing_loa_m=loa_s, governing_beam_m=beam_s, governing_draft_m=gov[site_key]["draft"][-1],
        governing_speed_kn=big.speed_kn, wm_m=parts["wm"], wa_total_m=parts["wa_total"], wb_m=parts["wb"],
        ws_m=parts["ws"], channel_width_1lane_m=w1, channel_width_2lane_m=w2, required_depth_m=dep_s,
        channel_length_m=1.5 * loa_s, entrance_width_m=loa_s, stopping_distance_m=7 * loa_s,
        turning_basin_d_m=2 * loa_s, turning_basin_area_m2=eng["waterside.turning_area"][site_key][-1],
        berthing_area_length_m=1.175 * loa_s, berthing_area_width_m=1.5 * beam_s, anchorage_depth_m=dep_s,
        anchorage_radius_m=loa_s + 6 * dep_s)
    cells.update({f"{k}_m": parts[k] for k in ("wa_speed", "wa_wind", "wa_cross_current", "wa_long_current", "wa_wave",
                                               "wa_nav_aids", "wa_bottom", "wa_depth")})
    mx, tr = options["mixed"], options["trestle"]
    berths = {t: term[f"berths_{t.lower()}"] for t in ("MP", "CC")}
    adds = {t: [b - (s[i - 1] if i else 0.0) for i, b in enumerate(s)] for t, s in berths.items()}
    per_berth = {t: mx["dredge_vol"][t] / berths[t][-1] if berths[t][-1] else 0.0 for t in berths}
    phases = ((0, 5), (5, 10), (10, n))  # tahun 1–5 (keruk th −1), 6–10 (th 5), 11–20 (th 10): Trestle!C105, I105, N105
    vol_ph = {t: [sum(adds[t][a:b]) * per_berth[t] for a, b in phases] for t in berths}
    cells.update(
        full_length_mp_m=tr["trestle_len"]["MP"], full_area_mp_m2=tr["trestle_area"]["MP"],
        full_cost_mp_rp=tr["cost_trestle"]["MP"], full_length_jetty_m=tr["trestle_len"]["CC"],
        full_area_jetty_m2=tr["trestle_area"]["CC"], full_cost_jetty_rp=tr["cost_trestle"]["CC"],
        full_cost_rp=tr["cost"], full_total_rp=tr["cost"],
        mixed_length_mp_m=mx["trestle_len"]["MP"], mixed_area_mp_m2=mx["trestle_area"]["MP"],
        mixed_existing_depth_mp_m=mx["tip_depth"]["MP"], mixed_dredge_depth_mp_m=depth["MP"][-1] - mx["tip_depth"]["MP"],
        mixed_length_jetty_m=mx["trestle_len"]["CC"], mixed_area_jetty_m2=mx["trestle_area"]["CC"],
        mixed_existing_depth_jetty_m=mx["tip_depth"]["CC"],
        mixed_dredge_depth_jetty_m=depth["CC"][-1] - mx["tip_depth"]["CC"], mixed_total_rp=mx["cost"],
        dredge_vol_mp_m3=vol_ph["MP"], dredge_vol_cc_m3=vol_ph["CC"],
        dredge_vol_total_m3=[a + b for a, b in zip(vol_ph["MP"], vol_ph["CC"], strict=True)],
        invest_mixed_rp=[(sum(mx["trestle_area"].values()) * p_tr if i == 0 else 0.0) + (a + b) * p_dr
                         for i, (a, b) in enumerate(zip(vol_ph["MP"], vol_ph["CC"], strict=True))],
        selected_full=tr["cost"] <= mx["cost"],  # Model!K395 = IF(Trestle!C94 <= C110, trestle penuh, trestle + keruk)
    )
    return dict(cells=cells, engine=eng, options=options)


#: penyebab selisih per variabel perairan engine (selain koreksi hulu yang mengubah tambatan, A2/A10/A16/A17)
WATERSIDE_CAUSES = {"waterside.gov_loa": ("A21",), "waterside.gov_beam": ("A21",), "waterside.gov_draft": ("A21",),
                    "waterside.depth_req": ("A21",), "waterside.channel_width": ("A21", "A22"),
                    "waterside.channel_length": ("A21",), "waterside.entrance_width": ("A21",),
                    "waterside.stopping_distance": ("A21",), "waterside.turning_basin": ("A21",),
                    "waterside.turning_area": ("A21", "A23"), "waterside.anchorage_radius": ("A21",),
                    "waterside.x_star": ("A21",), "waterside.trestle_len": ("A21",), "waterside.tip_depth": ("A21",),
                    "waterside.pocket_length": ("A21", "A24"), "waterside.pocket_width": ("A21",),
                    "waterside.dredge_vol": ("A21", "A24"), "waterside.cost": ("A21", "A24"),
                    "storage.trucks": ("A10", "A17", "A19", "A21", "A25")}
TRUCK_FORMS = {"truk_petikemas": "PK", "truk_curah": "CK", "truk_gc": "GC"}


def excel_trucks(case: Case, golden: dict, chains: dict[str, dict[str, list[float]]], term: dict[str, list[float]],
                 trestle_len_mp: float, demands: dict[str, list[float]],
                 fixes: frozenset[str] | set[str] = frozenset()) -> dict[str, dict]:
    """Tiruan truk `Fasilitas Daratan!F117:Y126` (PK), `F152:Y165` (CK), `F207:Y220` (GC). `golden` = bentuk sheet
    (waktu muat, waktu jalan, jumlah truk per bentuk muatan), `engine` = `storage.trucks` per id alat (tidak turun).

    Excel (A25): produktivitas alat B/M (box/jam) ÷ 60 dianggap menit per box; siklus PK = (muat + RTG muat + jalan) +
    (RTG bongkar + jalan + muat) dengan waktu RTG = produktivitas ÷ 60 (in.fantasi 4 TEU/jam, A19); siklus GC/CK =
    bongkar 3 + jalan sekali + muat 3 menit + waktu di dermaga; jarak = trestle opsi keruk (Trestle!C69) walau terpilih
    trestle penuh; jumlah = ⌈siklus / waktu muat⌉ untuk SATU alat. Koreksi: satuan menit benar, jalan pergi-pulang,
    waktu di dermaga sekali, jarak = trestle desain terminal, × alat B/M aktif (nEq × kapal sandar bersamaan).
    """
    prm = case.params
    flows = {f.id: f for f in case.flows}
    ships = {s.id: s for s in case.ships}
    order = golden["flow_order"]
    n = len(next(iter(chains.values()))["freq_required"])
    eqs = {e.id: e for e in case.storage.yard_equipment}
    crane = next(e for e in case.equipment if e.id == case.plans[0].equipment_by_terminal["MP"])
    it_days = prm.it_hours / prm.working_hours_per_day
    rtg_xl = golden["storage"]["excel_params"]["rtg_productivity_teu_h"]["in.fantasi"][0]  # Fasilitas Daratan!F69
    dist_xl = case.kek_site.trestle_dredge.trestle_length_m / 1000  # Trestle!C69 / 1000
    gold: dict[str, dict[str, list[float]]] = {}
    eng: dict[str, list[float]] = {}
    for eid, form in TRUCK_FORMS.items():
        e = eqs[eid]
        rate = crane.productivity[form]
        fids = [f for f in order if flows[f].cargo_form == form]
        v = e.params["speed_kmh"]
        res: list[float] = []
        g = {k: [0.0] * n for k in ("t_crane_min", "t_travel_min", "trucks")}
        for y in range(n):
            act = [f for f in fids if chains[f]["freq_required"][y]]
            if "A25" not in fixes:
                if not any(demands[f][y] for f in fids):
                    res.append(0.0)
                    continue
                trav = dist_xl / v * 60  # F124 / F161 / F214 (sekali jalan)
                if form == "PK":
                    tc = rate.unload / 60  # F121 = produktivitas / 60
                    rtg = rtg_xl / 60 if demands["in.fantasi"][y] else 0.0  # F123 = F69 / 60
                    k = ceil_(((tc + tc / 60 + trav) + (rtg + trav + tc)) / tc)  # F125
                else:
                    tc = 60 * e.productivity / rate.unload  # F156 / F210
                    k = ceil_((e.params["unload_min"] + trav + 3.0 + tc) / tc)  # F163 / F217 (muat 3 menit F162/F215)
                g["t_crane_min"][y], g["t_travel_min"][y], g["trucks"][y] = tc, trav, float(k)
                res.append(float(k))
                continue
            if not act:
                res.append(0.0)
                continue
            if e.params.get("unload_min") is not None:
                yard = e.params["unload_min"]
            else:
                yard = 60.0 * e.productivity / (eqs["rtg"].productivity if "A19" in fixes else rtg_xl)
            per = max(storage.trucks_per_crane(*storage.truck_cycle(
                e.productivity, rate.unload if flows[f].direction == "inbound" else rate.load, trestle_len_mp / 1000, v,
                yard)) for f in act)
            neq = max((vessel.n_equipment(ships[golden["flows"][f]["ship_id"]], case.equipment_rules, "MP")
                       if "A10" in fixes else int(golden["flows"][f]["equipment_per_berth"])) for f in act)
            sd = sum(chains[f]["port_days_kek_per_year"][y] + (it_days * chains[f]["freq_required"][y]
                                                               if "A17" in fixes else 0.0) for f in act)
            res.append(storage.trucks(per, storage.active_cranes(term["equipment_mp"][y], neq, sd,
                                                                 prm.working_days_per_year)))
        gold[form] = g
        eng[eid] = _never_decrease(res)
    return dict(golden=gold, engine=eng)
