"""Laporan selisih engine v2 vs Excel K15 per flow, beserta penyebabnya (temuan audit SPEC §11).

Untuk tiap flow (kapal & alat hasil Evolver K15) dan tiap seri operasi: nilai Excel vs engine pada tahun pertama
beroperasi, selisih maksimum 20 tahun, dan efek koreksi audit satu per satu (tiruan rumus Excel di
`engine/tests/excel_k15.py`, diterapkan berurutan A12 → A3 → A10 → A2 → A5 → A1 → A13 → A9 → A6 → A11 → A14 → A15; hasil akhirnya = engine).
Bagian akhir: terminal KEK (tambatan, BOR, alat) per tahun, dengan koreksi tambahan A16 → A17; penyimpanan
(sheet `Fasilitas Daratan`) dengan koreksi tambahan A18 → A19 → A20; perairan (`Fasilitas Perairan`, `Trestle`) dan
truk dermaga–lapangan dengan koreksi tambahan A21 → A22 → A23 → A24 → A25; investasi (`Investasi`, `Model!K369:AF395`)
per komponen dengan koreksi hulu sekaligus lalu A26 → A28 → A29 → A30 (A27 eskalasi = opsi, mati di K15).

Jalankan dari folder v2:  uv run --project engine python tools/diff_k15.py [--flow in.damai] [--year 10]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

V2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V2 / "engine" / "tests"))

from excel_k15 import (  # noqa: E402
    CAUSES,
    EXCEL_SERIES,
    FIXES,
    INVEST_CAUSES,
    INVEST_FIXES,
    INVEST_GOLDEN,
    STORAGE_CAUSES,
    STORAGE_FIXES,
    TERMINAL_CAUSES,
    TERMINAL_FIXES,
    TERMINAL_SERIES,
    TRUCK_FIXES,
    WATERSIDE_CAUSES,
    WATERSIDE_FIXES,
    engine_series,
    engine_terminal,
    excel_chain,
    excel_invest,
    excel_storage,
    excel_terminal,
    excel_trucks,
    excel_waterside,
)

from tpt_engine.calc.run import calculate  # noqa: E402
from tpt_engine.domain import load_case  # noqa: E402

LABEL = {
    "freq_required": "Frekuensi (call/th)", "cargo_per_call": "Muatan/call", "port_days_kek_per_year": "Port KEK (hr/th)",
    "port_days_ext_per_year": "Port ext (hr/th)", "sea_time_days_per_call": "Sea time (hr/call)",
    "port_days_per_year": "Port total (hr/th)", "port_days_per_call": "Port+fix (hr/call)", "rtd_days": "RTD (hr)",
    "voyages_max_per_ship": "F_max (call/kapal)", "ships": "Jumlah kapal", "consumption_days": "Lama konsumsi (hr)",
    "fuel_me_l": "BBM ME (l/th)", "fuel_ae_l": "BBM AE (l/th)", "fuel_cost_me_rp": "Biaya BBM ME (Rp)",
    "fuel_cost_ae_rp": "Biaya BBM AE (Rp)", "voyage_cost_rp": "Voyage cost (Rp)", "tch_cost_rp": "TCH (Rp/th)",
    "port_cost_rp": "Pelabuhan (Rp/th)", "shipping_cost_rp": "Shipping cost (Rp)",
}


def fmt(v: float) -> str:
    return f"{v:,.0f}" if abs(v) >= 1000 or float(v).is_integer() else f"{v:,.3f}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--flow", help="hanya satu flow")
    ap.add_argument("--year", type=int, help="tahun yang dibandingkan (default: tahun pertama beroperasi)")
    args = ap.parse_args()
    case = load_case(V2 / "cases" / "k15-batam.json")
    golden = json.loads((V2 / "engine" / "tests" / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
    res = calculate(case, ["shipcost", "terminal", "storage", "waterside", "invest"], plan_id="k15-excel")
    v = res.values
    steps = ["A12", *FIXES]

    for fid in golden["flow_order"]:
        if args.flow and fid != args.flow:
            continue
        g = golden["flows"][fid]["series"]
        first = next((i for i, d in enumerate(g["demand"]["values"]) if d > 0), 0)
        y = (args.year - 1) if args.year else first
        ship = next(s.name for s in case.ships if s.id == res.ship_by_flow[fid])
        print(f"\n== {fid}  ·  {ship}  ·  tahun {y + 1}  ·  nEq Excel {golden['flows'][fid]['equipment_per_berth']:g} → v2 "
              f"{v['vessel.neq'][fid]:g}  ·  satuan {res.units[fid]}")
        # efek koreksi berurutan pada tahun y
        chain: list[dict[str, list[float]]] = [excel_chain(case, golden, fid)]
        applied: set[str] = set()
        for st in steps:
            if st == "A12":
                chain.append(excel_chain(case, golden, fid, applied, v["cargo.demand_unit"][fid]))
            else:
                applied.add(st)
                chain.append(excel_chain(case, golden, fid, applied, v["cargo.demand_unit"][fid]))
        head = f"  {'seri':<22}{'Excel':>12}{'v2':>12}{'Δ%':>8}  {'maks Δ% 20 th':>13}  penyebab  ·  " + " → ".join(steps)
        print(head)
        for key in EXCEL_SERIES:
            ex = g[key]["values"]
            en = engine_series(v, fid, key)
            a, b = ex[y], en[y]
            d = (b - a) / a * 100 if a else (0.0 if b == 0 else float("inf"))
            dmax = max(((bb - aa) / aa * 100 if aa else 0.0) for aa, bb in zip(ex, en, strict=True))
            dmin = min(((bb - aa) / aa * 100 if aa else 0.0) for aa, bb in zip(ex, en, strict=True))
            span = dmax if abs(dmax) >= abs(dmin) else dmin
            hit = [st for st, prev, cur in zip(steps, chain[:-1], chain[1:], strict=True) if abs(cur[key][y] - prev[key][y]) > 1e-9 * max(1, abs(prev[key][y]))]
            cause = ",".join(hit) if hit else ("–" if abs(d) < 1e-9 else "?")
            trail = " → ".join(fmt(c[key][y]) for c in chain)
            print(f"  {LABEL[key]:<22}{fmt(a):>12}{fmt(b):>12}{d:>7.1f}%  {span:>12.1f}%  {cause:<9} ·  {trail}")
            if hit and not set(hit) - {"A12"} <= set(CAUSES[key]) | {"A12"}:
                print(f"    ! penyebab {hit} tidak terdaftar di CAUSES[{key}]")

    if not args.flow:
        terminal_report(case, golden, v, args.year)
        storage_report(case, golden, v, args.year)
        waterside_report(case, golden, res, args.year)
        invest_report(case, golden, res)


TLABEL = {"ship_days_kek": "Ship-days KEK", "berth_days": "Berth-days", "berths": "Tambatan", "bor": "BOR",
          "equipment": "Alat B/M"}


def terminal_report(case, golden: dict, v: dict, year: int | None) -> None:
    """Seri terminal per tahun: Excel → (koreksi flow berurutan) → A16 → A17 = engine."""
    fids = golden["flow_order"]
    steps = ["A12", *FIXES, *TERMINAL_FIXES]
    trail: list[dict[str, list[float]]] = []
    applied: set[str] = set()
    trail.append(excel_terminal(case, golden, {f: excel_chain(case, golden, f) for f in fids}))
    for st in steps:
        if st != "A12":
            applied.add(st)
        chains = {f: excel_chain(case, golden, f, applied, v["cargo.demand_unit"][f]) for f in fids}
        trail.append(excel_terminal(case, golden, chains, applied))
    years = [year - 1] if year else [0, 7, 12, 19]
    for term in ("mp", "cc"):
        print()
        print(f"== terminal {term.upper()}  ·  tahun {', '.join(str(y + 1) for y in years)}")
        print(f"  {'seri':<16}{'tahun':>6}{'Excel':>10}{'v2':>10}  penyebab  ·  " + " → ".join(steps))
        for name in TERMINAL_SERIES:
            key = f"{name}_{term}"
            ex, en = golden["terminal"][key]["values"], engine_terminal(case, v, key)
            for y in years:
                hit = [st for st, a, b in zip(steps, trail[:-1], trail[1:], strict=True)
                       if abs(b[key][y] - a[key][y]) > 1e-9 * max(1, abs(a[key][y]))]
                cause = ",".join(hit) if hit else ("–" if abs(ex[y] - en[y]) < 1e-9 else "?")
                print(f"  {TLABEL[name]:<16}{y + 1:>6}{fmt(ex[y]):>10}{fmt(en[y]):>10}  {cause:<9} ·  "
                      + " → ".join(fmt(t[key][y]) for t in trail))
                if hit and not set(hit) - {"A12"} <= set(TERMINAL_CAUSES[name]) | {"A12", "A1", "A3", "A5", "A13"}:
                    print(f"    ! penyebab {hit} tidak terdaftar di TERMINAL_CAUSES[{name}]")


SROWS = (("storage.cy", "total", "Luas CY (m²)"), ("storage.cy_slots", "total", "Ground slot"),
         ("storage.yard_equipment", "rtg", "RTG"), ("storage.gc", "total", "Gudang GC (m²)"),
         ("storage.yard_equipment", "forklift", "Forklift"), ("storage.bulk", "total", "Volume silo (m³)"),
         ("storage.silos", "total", "Silo"), ("storage.yard_equipment", "dozer", "Dozer"),
         ("storage.liquid", "total", "Volume tangki (m³)"), ("storage.tanks", "total", "Tangki"))


def storage_report(case, golden: dict, v: dict, year: int | None) -> None:
    """Kapasitas penyimpanan per fasilitas: Excel (Fasilitas Daratan) → koreksi flow → A18 → A19 → A20 = engine."""
    fids = golden["flow_order"]
    steps = ["A12", *FIXES, *STORAGE_FIXES]
    dem_xl = {f: golden["flows"][f]["series"]["demand"]["values"] for f in fids}
    dem_v2 = v["cargo.demand_unit"]
    trail = [excel_storage(case, golden, {f: excel_chain(case, golden, f) for f in fids}, dem_xl)["engine"]]
    applied: set[str] = set()
    for st in steps:
        if st != "A12":
            applied.add(st)
        chains = {f: excel_chain(case, golden, f, applied, dem_v2[f]) for f in fids}
        trail.append(excel_storage(case, golden, chains, dem_v2, applied)["engine"])
    years = [year - 1] if year else [0, 7, 12, 19]
    print()
    print(f"== penyimpanan (Fasilitas Daratan)  ·  tahun {', '.join(str(y + 1) for y in years)}  ·  total = kapasitas "
          "terpasang (tidak pernah turun)")
    print(f"  {'fasilitas':<20}{'tahun':>6}{'Excel':>12}{'v2':>12}  penyebab  ·  " + " → ".join(steps))
    for var, key, label in SROWS:
        en = v[var][key]
        for y in years:
            hit = [st for st, a, b in zip(steps, trail[:-1], trail[1:], strict=True)
                   if abs(b[var][key][y] - a[var][key][y]) > 1e-9 * max(1, abs(a[var][key][y]))]
            ex = trail[0][var][key][y]
            cause = ",".join(hit) if hit else ("–" if abs(ex - en[y]) < 1e-9 else "?")
            print(f"  {label:<20}{y + 1:>6}{fmt(ex):>12}{fmt(en[y]):>12}  {cause:<11} ·  "
                  + " → ".join(fmt(t[var][key][y]) for t in trail))
            if hit and not set(hit) <= set(STORAGE_CAUSES[var]) | {"A12"}:
                print(f"    ! penyebab {hit} tidak terdaftar di STORAGE_CAUSES[{var}]")


WROWS = (("waterside.gov_loa", "site", "LOA penentu (m)"), ("waterside.gov_beam", "site", "B penentu (m)"),
         ("waterside.gov_draft", "MP", "T penentu MP (m)"), ("waterside.gov_draft", "CC", "T penentu CC (m)"),
         ("waterside.depth_req", "MP", "Kedalaman MP (m)"), ("waterside.depth_req", "CC", "Kedalaman CC (m)"),
         ("waterside.channel_width", "site", "Lebar alur (m)"), ("waterside.turning_area", "site", "Kolam putar (m²)"),
         ("waterside.x_star", "MP", "x* MP (m)"), ("waterside.x_star", "CC", "x* CC (m)"),
         ("waterside.trestle_len", "CC", "Trestle CC (m)"), ("waterside.pocket_length", "CC", "Kolam jetty (m)"),
         ("waterside.pocket_width", "CC", "Lebar kolam CC (m)"), ("waterside.cost", "MP", "Biaya dasar MP (Rp)"),
         ("waterside.cost", "CC", "Biaya dasar CC (Rp)"), ("storage.trucks", "truk_petikemas", "Truk PK"),
         ("storage.trucks", "truk_curah", "Truk CK"), ("storage.trucks", "truk_gc", "Truk GC"))


def waterside_report(case, golden: dict, res, year: int | None) -> None:
    """Perairan & truk: Excel (Fasilitas Perairan, Trestle, Fasilitas Daratan truk) → koreksi hulu → A21 … A25 = engine.
    Excel hanya punya satu nilai per sel (tidak per tahun); seri Excel di sini = sel itu dengan pola engine
    (fasilitas ada sejak tahun pertama terminal punya tambatan). Truk Excel: Fasilitas Daratan!F125/F163/F217."""
    v = res.values
    fids = golden["flow_order"]
    steps = ["A12", *FIXES, *TERMINAL_FIXES, *STORAGE_FIXES, *WATERSIDE_FIXES, *TRUCK_FIXES]
    dem_xl = {f: golden["flows"][f]["series"]["demand"]["values"] for f in fids}
    dem_v2 = v["cargo.demand_unit"]

    def snap(applied: set[str], dem: dict, chains: dict) -> tuple[dict, dict]:
        term = excel_terminal(case, golden, chains, applied)
        ws = excel_waterside(case, golden, chains, term, applied)
        tl = max(ws["engine"]["waterside.trestle_len"]["MP"]) if "A25" in applied else 500.0
        vals = dict(ws["engine"])
        vals["storage.trucks"] = excel_trucks(case, golden, chains, term, tl, dem, applied)["engine"]
        return vals, ws["options"]

    trail = [snap(set(), dem_xl, {f: excel_chain(case, golden, f) for f in fids})]
    applied: set[str] = set()
    for st in steps:
        if st != "A12":
            applied.add(st)
        trail.append(snap(set(applied), dem_v2, {f: excel_chain(case, golden, f, applied, dem_v2[f]) for f in fids}))
    years = [year - 1] if year else [0, 7, 12, 19]
    print()
    print(f"== perairan & truk (Fasilitas Perairan, Trestle, Fasilitas Daratan)  ·  tahun {', '.join(str(y + 1) for y in years)}")
    print(f"  {'variabel':<22}{'tahun':>6}{'Excel':>18}{'v2':>18}  penyebab  ·  langkah yang mengubah")
    for var, key, label in WROWS:
        en = v[var][key]
        for y in years:
            vals = [t[0][var][key][y] for t in trail]
            hit = [st for st, a, b in zip(steps, vals[:-1], vals[1:], strict=True) if abs(b - a) > 1e-9 * max(1, abs(a))]
            cause = ",".join(hit) if hit else ("–" if abs(vals[0] - en[y]) < 1e-9 else "?")
            moves = " → ".join(f"{st} {fmt(b)}" for st, a, b in zip(steps, vals[:-1], vals[1:], strict=True)
                               if abs(b - a) > 1e-9 * max(1, abs(a)))
            print(f"  {label:<22}{y + 1:>6}{fmt(vals[0]):>18}{fmt(en[y]):>18}  {cause:<11} ·  {moves}")
            if hit and not set(hit) <= set(WATERSIDE_CAUSES[var]) | {"A2", "A3", "A5", "A10", "A12", "A13", "A16", "A17"}:
                print(f"    ! penyebab {hit} tidak terdaftar di WATERSIDE_CAUSES[{var}]")
    print()
    print("  opsi perairan (biaya dasar, Rp)   Excel → v2   ·   " + " · ".join(
        f"{o.mode}{' (rencana)' if o.selected else ''}" for o in res.waterside_options))
    for o in res.waterside_options:
        ex = trail[0][1][o.mode]["cost"]
        print(f"  {o.mode:<12}{fmt(ex):>22}{fmt(o.cost):>22}  "
              + ("  ".join(f"{t}: trestle {fmt(o.trestle_len[t])} m, keruk {fmt(o.dredge_vol[t])} m³" for t in o.trestle_len)))


ILABEL = {"yard_equipment_pk_rp": "RTG (PK)", "yard_equipment_ck_rp": "Dozer (CK)", "yard_equipment_gc_rp": "Forklift (GC)",
          "pipeline_cc_rp": "Pipa CC", "handling_equipment_cc_rp": "Alat B/M CC", "handling_equipment_mp_rp": "Alat B/M MP",
          "storage_pk_rp": "Lapangan CY", "storage_ck_rp": "Silo", "storage_gc_rp": "Lapangan GC",
          "storage_cc_rp": "Tangki", "berth_mp_rp": "Dermaga MP", "jetty_cc_rp": "Jetty CC", "trestle_rp": "Trestle/keruk"}


def invest_report(case, golden: dict, res) -> None:
    """Investasi per komponen: Excel (Model!K369:AF395) → koreksi hulu sekaligus → A26 → A28 → A29 → A30 = engine.
    Ditampilkan Σ nominal (Rp M) dan tahun bangun; truk (A25) tidak ada di Excel."""
    v = res.values
    fids = golden["flow_order"]
    dem_xl = {f: golden["flows"][f]["series"]["demand"]["values"] for f in fids}
    dem_v2 = v["cargo.demand_unit"]
    up = {"A12", *FIXES, *TERMINAL_FIXES, *STORAGE_FIXES, *WATERSIDE_FIXES, *TRUCK_FIXES}

    def snap(applied: set[str], dem: dict) -> dict:
        chains = {f: excel_chain(case, golden, f, applied, None if dem is dem_xl else dem[f]) for f in fids}
        term = excel_terminal(case, golden, chains, applied)
        store = excel_storage(case, golden, chains, dem, applied)
        ws = excel_waterside(case, golden, chains, term, applied)
        tr = None
        if "A25" in applied:
            tr = excel_trucks(case, golden, chains, term, max(ws["engine"]["waterside.trestle_len"]["MP"]), dem,
                              applied)["engine"]
        return excel_invest(case, golden, term, store, ws, tr, chains, dem, applied)

    steps = ["hulu", *INVEST_FIXES]
    trail = [snap(set(), dem_xl), snap(set(up), dem_v2)]
    applied = set(up)
    for st in INVEST_FIXES:
        applied.add(st)
        trail.append(snap(set(applied), dem_v2))

    def years_of(s: list[float], y0: int) -> str:
        return ",".join(str(i + y0) for i, x in enumerate(s) if abs(x) > 1e-6) or "–"

    y0 = res.invest_start_year
    print()
    print("== investasi (Investasi, Model!K369:AF395)  ·  Σ nominal Rp M  ·  tahun bangun  ·  staging "
          f"{case.plans[0].staging}, masa konstruksi {case.horizon.construction_lead_years} th, eskalasi "
          f"{'hidup' if case.params.apply_escalation else 'mati'}")
    print(f"  {'komponen':<16}{'Excel':>10}{'th Excel':>12}{'v2':>10}{'th v2':>12}  penyebab  ·  " + " → ".join(steps))
    for gk, (var, keys) in INVEST_GOLDEN.items():
        ex = golden["investment"][gk]["values"]
        en = [sum(x) for x in zip(*(v[var].get(k, [0.0] * 21) for k in keys), strict=True)]
        sums = [sum(t["golden"][gk]) for t in trail]
        hit = [st for st, a, b, ta, tb in zip(steps, sums[:-1], sums[1:], trail[:-1], trail[1:], strict=True)
               if abs(b - a) > 1e-6 * max(1, abs(a)) or ta["golden"][gk] != tb["golden"][gk]]
        cause = ",".join(hit) if hit else "–"
        print(f"  {ILABEL[gk]:<16}{sum(ex) / 1e9:>10,.1f}{years_of(ex, -1):>12}{sum(en) / 1e9:>10,.1f}"
              f"{years_of(en, y0):>12}  {cause:<16} ·  " + " → ".join(f"{x / 1e9:,.1f}" for x in sums))
        if not set(hit) - {"hulu"} <= set(INVEST_CAUSES[var]):
            print(f"    ! penyebab {hit} tidak terdaftar di INVEST_CAUSES[{var}]")
    trucks = {k: s for k, s in v["invest.yard_equipment"].items() if k.startswith("truk")}
    for k, s in trucks.items():
        print(f"  {k:<16}{'–':>10}{'–':>12}{sum(s) / 1e9:>10,.1f}{years_of(s, y0):>12}  A25 (Excel tanpa investasi truk)")
    tot_x = sum(sum(golden["investment"][gk]["values"]) for gk in INVEST_GOLDEN)
    print(f"  {'Σ investasi':<16}{tot_x / 1e9:>10,.1f}{'':>12}{sum(v['invest.total']['total']) / 1e9:>10,.1f}")
    print()
    print("  opsi perairan (Rp M)        biaya dasar   terjadwal          PV th 0   tahun bangun trestle")
    for o in res.waterside_options:
        print(f"  {o.mode + (' (rencana)' if o.selected else ''):<26}{o.cost / 1e9:>12,.1f}{o.invest_total / 1e9:>12,.1f}"
              f"{o.pv / 1e9:>17,.1f}   " + ", ".join(f"{t} th {y}" for t, y in o.build_year.items()))
    print("  Excel: Trestle!C94 'Total PV' = 415,0 (trestle penuh) vs C110 = 602,3 (trestle + keruk), tanpa diskon (A29)")


if __name__ == "__main__":
    main()
