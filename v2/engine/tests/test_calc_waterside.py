"""§5.7 Fasilitas perairan & trestle vs keruk + truk dermaga–lapangan (Tahap 8a) vs golden K15.

Pembuktian sama seperti Tahap 5–7b: tiruan rumus Excel (`excel_waterside`, `excel_trucks`) = golden `Fasilitas
Perairan`, `Trestle` dan `Fasilitas Daratan` (truk), dan tiruan + semua koreksi (koreksi hulu + A21–A25) = engine
untuk setiap variabel dan kunci. Hitungan tangan: kedalaman perlu & x* per terminal, lebar alur 2 jalur, truk per alat.
"""

import json
import math
from pathlib import Path

import pytest
from excel_k15 import (
    FIXES,
    OPTION_KEYS,
    STORAGE_FIXES,
    TERMINAL_FIXES,
    TRUCK_FIXES,
    WATERSIDE_FIXES,
    excel_chain,
    excel_terminal,
    excel_trucks,
    excel_waterside,
)

from tpt_engine.calc import storage, waterside
from tpt_engine.calc.run import COMPUTES, calculate
from tpt_engine.domain import Case, load_case
from tpt_engine.domain.case import BathyPoint

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
FLOWS = GOLDEN["flow_order"]
ALL_FIXES = set(FIXES) | set(TERMINAL_FIXES) | set(STORAGE_FIXES) | set(WATERSIDE_FIXES) | set(TRUCK_FIXES)


def close(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-6)


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["waterside"], plan_id="k15-excel")


@pytest.fixture(scope="module")
def replica(case):
    chains = {f: excel_chain(case, GOLDEN, f) for f in FLOWS}
    term = excel_terminal(case, GOLDEN, chains)
    dem = {f: GOLDEN["flows"][f]["series"]["demand"]["values"] for f in FLOWS}
    return chains, term, dem


def test_excel_replica_reproduces_golden(case, replica):
    """Tiruan (A21–A24 apa adanya) = golden Fasilitas Perairan & Trestle: kapal penentu, Wm/Wa/Wb/Ws, lebar alur 1 & 2
    jalur, kolam, opsi trestle penuh & trestle + keruk, volume keruk dan investasi per fase (th −1, 5, 10)."""
    chains, term, _ = replica
    cells = excel_waterside(case, GOLDEN, chains, term)["cells"]
    checked = 0
    for key, val in cells.items():
        g = GOLDEN["waterside"].get(key) or GOLDEN["trestle"].get(key)
        if g is None:
            continue
        got = val if isinstance(val, list) else [val]
        exp = g["values"] if "values" in g else [g["value"]]
        assert all(close(a, b or 0.0) for a, b in zip(got, exp, strict=True)), (key, got, exp)
        checked += 1
    assert checked == 49
    # Model!K395 = IF(Trestle!C94 ≤ C110, trestle penuh, trestle + keruk) → trestle penuh Rp 415 M di tahun −1
    assert cells["selected_full"] is True
    assert close(GOLDEN["investment"]["trestle_rp"]["values"][0], cells["full_cost_rp"])


def test_excel_truck_replica_reproduces_golden(case, replica):
    """Tiruan truk Excel (satuan ÷ 60, jalan sekali, satu alat; A25) = golden Fasilitas Daratan: 6 truk per bentuk."""
    chains, term, dem = replica
    tr = excel_trucks(case, GOLDEN, chains, term, 500.0, dem)["golden"]
    for form, rows in tr.items():
        for key, s in rows.items():
            gkey = key if form == "PK" or key != "t_crane_min" else "t_quay_min"
            assert all(close(a, b) for a, b in zip(s, GOLDEN["trucks"][form][gkey]["values"], strict=True)), (form, key)
    assert set(GOLDEN["trucks"]["PK"]["trucks"]["values"]) == {6.0}


def test_corrected_replica_equals_engine(case, res):
    """Tiruan + semua koreksi + D_TEU engine = engine untuk setiap variabel waterside.* & storage.trucks, setiap kunci,
    dan ketiga opsi perairan."""
    dem = res.values["cargo.demand_unit"]
    chains = {f: excel_chain(case, GOLDEN, f, ALL_FIXES, dem[f]) for f in FLOWS}
    term = excel_terminal(case, GOLDEN, chains, ALL_FIXES)
    ex = excel_waterside(case, GOLDEN, chains, term, ALL_FIXES)
    assert set(ex["engine"]) | {"storage.trucks", "storage.pipeline"} == set(COMPUTES["waterside"])
    for var, by in ex["engine"].items():
        assert set(by) == set(res.values[var]), var
        for key, s in by.items():
            assert all(close(a, b) for a, b in zip(s, res.values[var][key], strict=True)), (var, key)
    for opt in res.waterside_options:
        xo = ex["options"][opt.mode]
        for k in OPTION_KEYS:
            assert {t: round(v, 6) for t, v in getattr(opt, k).items()} == {t: round(v, 6) for t, v in xo[k].items()}, \
                (opt.mode, k)
        assert close(opt.cost, xo["cost"])
    tr = excel_trucks(case, GOLDEN, chains, term, max(res.values["waterside.trestle_len"]["MP"]), dem, ALL_FIXES)
    assert tr["engine"] == res.values["storage.trucks"]


def test_governing_and_depth_by_terminal_A21(res):
    """Hitungan tangan: MP = ALS CERES (LOA 255, T 14,2) mulai th-3 → 21,3 m, x* = 500 m; CC = THEA (T 14,918) mulai
    th-13 → 22,377 m, x* = 500 + 50 · (22,377 − 21,3) / (22,6 − 21,3). Excel: satu kapal (21,3 m untuk semua)."""
    v = res.values
    assert v["waterside.gov_draft"]["MP"][0] == 10.02 and v["waterside.gov_draft"]["MP"][2] == 14.2
    assert close(v["waterside.depth_req"]["MP"][-1], 21.3)
    assert close(v["waterside.x_star"]["MP"][-1], 500.0)
    assert v["waterside.depth_req"]["CC"][11] == 0.0
    assert close(v["waterside.depth_req"]["CC"][12], 1.5 * 14.918)
    assert close(v["waterside.x_star"]["CC"][-1], 500 + 50 * (1.5 * 14.918 - 21.3) / 1.3)
    assert res.governing_ships["site"] == {"loa": "ship.als_ceres", "beam": "ship.als_ceres", "draft": "ship.thea"}
    assert close(v["waterside.depth_req"]["site"][-1], 1.5 * 14.918)


def test_channel_width_two_lanes_A22(res):
    """2 jalur = 2(Wm + ΣWa) + 2Wb + Ws = 2(1,5 + 1,9)B + 2 · 0,5B + 1,6B = 9,4 B (B = 42,8 → 402,32 m);
    Excel 415,94 m (Wa kecepatan 0,1 · Vs dan Wa dasar laut 0,1 B)."""
    assert close(res.values["waterside.channel_width"]["site"][-1], 9.4 * 42.8)
    parts = res.channel_parts
    assert parts["wa_speed"][-1] == 0.0 and parts["wa_bottom"][-1] == 0.0
    assert close(parts["wa"][-1], 1.9 * 42.8)
    assert close(res.values["waterside.turning_area"]["site"][-1], math.pi * 255.0**2)  # A23: D = 2 LOA


def test_options_and_selection(case, res):
    """Opsi rencana K15 = trestle penuh (tanpa keruk); trestle + keruk memakai 250 m dan lebar trestle per terminal
    (A24), kolam jetty 1,175 LOA × 1,5 B THEA."""
    opts = {o.mode: o for o in res.waterside_options}
    assert [o.mode for o in res.waterside_options if o.selected] == ["trestle"]
    assert opts["trestle"].dredge_vol == {"MP": 0.0, "CC": 0.0}
    mx = opts["mixed"]
    assert mx.trestle_len == {"MP": 250.0, "CC": 250.0} and mx.tip_depth == {"MP": 10.0, "CC": 10.0}
    assert close(mx.dredge_vol["MP"], 3 * 300 * 1.5 * 42.8 * 11.3)
    assert close(mx.dredge_vol["CC"], 1 * 1.175 * 243.96 * 1.5 * 42.0 * (1.5 * 14.918 - 10.0))
    assert close(mx.trestle_area["CC"], 250 * 1.5)
    assert all(o.feasible for o in opts.values())
    assert res.values["waterside.trestle_len"]["CC"][11] == 0.0 and close(res.values["waterside.trestle_len"]["CC"][12],
                                                                          opts["trestle"].trestle_len["CC"])
    # rencana diubah ke trestle + keruk dengan θ = 0,6 → panjang = 0,6 · x*, keruk kolam tambat
    c2 = case.model_copy(deep=True)
    c2.plans[0].waterside_mode = "mixed"
    c2.plans[0].trestle_fraction = 0.6
    r2 = calculate(c2, ["waterside"], plan_id="k15-excel")
    assert close(r2.values["waterside.trestle_len"]["MP"][-1], 300.0)
    tip = waterside.depth_at(c2.kek_site.bathymetry, 300.0)
    assert close(r2.values["waterside.dredge_vol"]["MP"][-1], 3 * 300 * 1.5 * 42.8 * (21.3 - tip))
    assert [o.mode for o in r2.waterside_options if o.selected] == ["mixed"]


def test_bathymetry_drives_trestle_I8(case, res):
    """I8: perairan 2 m lebih dalam di semua titik → x* lebih pendek → biaya trestle turun; kedalaman tidak tercapai
    → trestle penuh tidak layak; batas panjang trestle → trestle penuh gugur."""
    c2 = case.model_copy(deep=True)
    c2.kek_site.bathymetry = [BathyPoint(distance_m=p.distance_m, depth_m=p.depth_m + 2.0) for p in case.kek_site.bathymetry]
    r2 = calculate(c2, ["waterside"], plan_id="k15-excel")
    assert r2.values["waterside.x_star"]["MP"][-1] < res.values["waterside.x_star"]["MP"][-1]
    assert r2.values["waterside.cost"]["MP"][-1] < res.values["waterside.cost"]["MP"][-1]
    c3 = case.model_copy(deep=True)
    c3.kek_site.bathymetry = [p for p in case.kek_site.bathymetry if p.depth_m < 22.0]
    r3 = calculate(c3, ["waterside"], plan_id="k15-excel")
    tr = next(o for o in r3.waterside_options if o.mode == "trestle")
    assert not tr.feasible and "CC" not in r3.values["waterside.x_star"]
    assert any("tidak tercapai" in w for w in r3.warnings)
    c4 = case.model_copy(deep=True)
    c4.kek_site.trestle.max_length_m = 520.0
    tr4 = next(o for o in calculate(c4, ["waterside"], plan_id="k15-excel").waterside_options if o.mode == "trestle")
    assert not tr4.feasible and any("panjang maks" in r for r in tr4.reasons)


def test_trucks_per_crane_times_active_cranes(case, res):
    """Truk PK: muat 60/35 menit, siklus = 60/35 + 2 · 0,5 km / 15 km/jam + 60/5 (RTG) → 11 truk per alat; th-1 alat
    aktif = nEq INTEGRA (3) × 1 kapal sandar bersamaan → 33. GC: (1,5 + 4 + 3) / 1,5 → 6 per alat × 4 (AETOS) = 24."""
    t_load, cycle = storage.truck_cycle(1.0, 35.0, 0.5, 15.0, 12.0)
    assert close(t_load, 60 / 35) and close(cycle, 60 / 35 + 4.0 + 12.0)
    assert storage.trucks_per_crane(t_load, cycle) == 11
    tr = res.values["storage.trucks"]
    assert tr["truk_petikemas"][0] == 33.0 and tr["truk_gc"][0] == 24.0
    assert tr["truk_curah"][6] == 0.0 and tr["truk_curah"][7] == 24.0
    n_eq = res.values["terminal.n_equip"]["MP"]
    assert all(t <= 11 * e for t, e in zip(tr["truk_petikemas"], n_eq, strict=True))
    for s in tr.values():
        assert all(b >= a for a, b in zip(s, s[1:], strict=False))
    # trestle lebih panjang → jalan lebih lama → truk per alat bertambah
    c2 = case.model_copy(deep=True)
    c2.kek_site.bathymetry = [BathyPoint(distance_m=p.distance_m * 3, depth_m=p.depth_m) for p in case.kek_site.bathymetry]
    r2 = calculate(c2, ["waterside"], plan_id="k15-excel")
    assert r2.values["storage.trucks"]["truk_gc"][0] > tr["truk_gc"][0]


def test_bigger_ship_deeper_basin_I1(case, res):
    """I1: kapal in.fantasi lebih dalam (T + 2 m) → kedalaman perlu MP naik → x* dan biaya trestle naik."""
    c2 = case.model_copy(deep=True)
    ship = next(s for s in c2.ships if s.id == res.ship_by_flow["in.fantasi"])
    ship.draft_m += 2.0
    r2 = calculate(c2, ["waterside"], plan_id="k15-excel")
    assert close(r2.values["waterside.depth_req"]["MP"][-1], 1.5 * 16.2)
    assert r2.values["waterside.cost"]["MP"][-1] > res.values["waterside.cost"]["MP"][-1]
