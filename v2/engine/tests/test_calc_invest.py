"""§5.8 Investasi & staging (Tahap 8b) vs golden K15.

Pembuktian sama seperti Tahap 5–8a: tiruan rumus Excel (`excel_invest`) = golden `Model!K369:AF395` (13 baris
investasi, tahun −1..20) dan baris antara `Investasi!N78` (GC) & `N59` (pipa); tiruan + semua koreksi (koreksi hulu +
A26, A28–A30) = engine untuk setiap variabel `invest.*`, setiap kunci, dan investasi & PV per opsi perairan.
Hitungan tangan: fase th 0/5/10, eskalasi, pola inkremental + lookahead, masa konstruksi, batas kedalaman KEK.
"""

import json
import math
from pathlib import Path

import pytest
from excel_k15 import (
    FIXES,
    INVEST_FIXES,
    STORAGE_FIXES,
    TERMINAL_FIXES,
    TRUCK_FIXES,
    WATERSIDE_FIXES,
    excel_chain,
    excel_invest,
    excel_storage,
    excel_terminal,
    excel_trucks,
    excel_waterside,
)

from tpt_engine.calc import invest
from tpt_engine.calc.run import COMPUTES, calculate
from tpt_engine.domain import Case, load_case

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
FLOWS = GOLDEN["flow_order"]
UPSTREAM = set(FIXES) | set(TERMINAL_FIXES) | set(STORAGE_FIXES) | set(WATERSIDE_FIXES) | set(TRUCK_FIXES)
ALL_FIXES = UPSTREAM | set(INVEST_FIXES)


def close(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-3)


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["invest"], plan_id="k15-excel")


def _replica(case, fixes, dem=None):
    chains = {f: excel_chain(case, GOLDEN, f, fixes, dem[f] if dem else None) for f in FLOWS}
    term = excel_terminal(case, GOLDEN, chains, fixes)
    demands = dem or {f: GOLDEN["flows"][f]["series"]["demand"]["values"] for f in FLOWS}
    store = excel_storage(case, GOLDEN, chains, demands, fixes)
    water = excel_waterside(case, GOLDEN, chains, term, fixes)
    return chains, term, demands, store, water


def test_excel_replica_reproduces_golden(case):
    """Tiruan (A26, A28–A30 apa adanya, hulu tanpa koreksi) = golden Model!K370:AF395 (alat lapangan, pipa, alat B/M,
    penyimpanan, dermaga, jetty, trestle; th −1..20) dan Investasi!N78 (luas GC = penambahan) & N59 (pipa)."""
    chains, term, demands, store, water = _replica(case, frozenset())
    ex = excel_invest(case, GOLDEN, term, store, water, None, chains, demands)
    for key, s in ex["golden"].items():
        exp = GOLDEN["investment"][key]["values"]
        assert all(close(a, b) for a, b in zip(s, exp, strict=True)), (key, s, exp)
    for key, s in ex["rows"].items():
        assert all(close(a, b or 0.0) for a, b in zip(s, GOLDEN["investment"][key]["values"], strict=True)), key
    assert len(ex["golden"]) == 13


def test_corrected_replica_equals_engine(case, res):
    """Tiruan + semua koreksi + D_TEU engine = engine untuk setiap variabel invest.* dan kunci, serta investasi
    terjadwal & PV ketiga opsi perairan."""
    dem = res.values["cargo.demand_unit"]
    chains, term, demands, store, water = _replica(case, UPSTREAM, dem)
    tr = excel_trucks(case, GOLDEN, chains, term, max(res.values["waterside.trestle_len"]["MP"]), dem, UPSTREAM)
    ex = excel_invest(case, GOLDEN, term, store, water, tr["engine"], chains, demands, ALL_FIXES)
    assert ex["start_year"] == res.invest_start_year == 0
    assert set(ex["engine"]) == set(COMPUTES["invest"])
    for var, by in ex["engine"].items():
        got = {k: v for k, v in by.items() if any(v)}
        assert set(got) == set(res.values[var]), var
        for key, s in got.items():
            assert all(close(a, b) for a, b in zip(s, res.values[var][key], strict=True)), (var, key)
    for opt in res.waterside_options:
        xo = ex["options"][opt.mode]
        assert close(opt.invest_total, xo["invest_total"]) and close(opt.pv, xo["pv"]), opt.mode


def test_phase_schedule_hand(res):
    """Hitungan tangan K15 (rencana per fase, masa konstruksi 1 th): tambatan MP 1 → 2 (th-8) → 3 (th-14) dibangun di
    th 0, 5, 10 masing-masing 300 m × Rp 25 jt; jetty CC (th-13) di th 10 Rp 8,8 M; trestle MP di th 0, CC di th 10."""
    v, y0 = res.values, res.invest_start_year
    assert [i + y0 for i, x in enumerate(v["invest.berth"]["MP"]) if x] == [0, 5, 10]
    assert all(close(x, 300 * 25e6) for x in v["invest.berth"]["MP"] if x)
    assert [i + y0 for i, x in enumerate(v["invest.berth"]["CC"]) if x] == [10]
    assert close(v["invest.berth"]["CC"][10 - y0], 8.8e9)
    opts = {o.mode: o for o in res.waterside_options}
    assert opts["trestle"].build_year == {"MP": 0, "CC": 10}
    tr = opts["trestle"]
    assert close(v["invest.waterside"]["MP"][0 - y0], tr.cost_trestle["MP"])
    assert close(tr.pv, tr.cost_trestle["MP"] + tr.cost_trestle["CC"] / 1.1**10)
    # Σ komponen = total
    tot = [0.0] * len(v["invest.total"]["total"])
    for var in COMPUTES["invest"]:
        if var != "invest.total":
            for s in v[var].values():
                tot = [a + b for a, b in zip(tot, s, strict=True)]
    assert all(close(a, b) for a, b in zip(tot, v["invest.total"]["total"], strict=True))


def test_gc_uses_installed_area_A28(case, res):
    """A28: Excel memakai baris penambahan F193:F195 sebagai luas (Rp 4,5 M total); engine = luas GC terpasang × Rp 2 jt."""
    gc = res.values["storage.gc"]["total"]
    total = sum(res.values["invest.storage"]["gc"])
    assert close(total, gc[-1] * 2e6)
    assert sum(GOLDEN["investment"]["storage_gc_rp"]["values"]) < total / 10


def test_escalation_option_A27(case, res):
    """A27: eskalasi = opsi. Dinyalakan → investasi th t dikali (1 + e)^t (infra 1 %, alat 1 %); th 0 tetap."""
    c2 = case.model_copy(deep=True)
    c2.params.apply_escalation = True
    r2 = calculate(c2, ["invest"], plan_id="k15-excel")
    y0 = res.invest_start_year
    for var, key in (("invest.berth", "MP"), ("invest.handling", "MP"), ("invest.storage", "cy")):
        a, b = res.values[var][key], r2.values[var][key]
        for i, (x, z) in enumerate(zip(a, b, strict=True)):
            assert close(z, x * 1.01 ** (i + y0)), (var, i)
    o1 = {o.mode: o for o in res.waterside_options}
    o2 = {o.mode: o for o in r2.waterside_options}
    assert close(o2["trestle"].invest_total, o1["trestle"].cost_trestle["MP"] + o1["trestle"].cost_trestle["CC"] * 1.01**10)


def test_incremental_lookahead_and_lead(case, res):
    """Pola inkremental: dibangun saat kebutuhan melampaui kapasitas, untuk kebutuhan N th ke depan. Lookahead 1 →
    tambatan MP di th 0, 7, 13 (dipakai th 1, 8, 14); lookahead 7 → th 0 untuk th 1–7 (1 tambatan), th 7 untuk th 8–14
    (3 tambatan). Masa konstruksi 0 → seri mulai th 1."""
    assert invest.schedule([1, 1, 2, 2, 3], "incremental", [], 1, 1) == {0: 1, 2: 1, 4: 1}
    assert invest.schedule([1, 1, 2, 2, 3], "incremental", [], 1, 3) == {0: 2, 4: 1}
    assert invest.schedule([1, 1, 2, 2, 3], "phase", [(1, 2), (3, 5)], 1, 0) == {0: 1, 2: 2}
    c2 = case.model_copy(deep=True)
    c2.plans[0].staging = "incremental"
    c2.horizon.berth_lookahead_years = 1
    r2 = calculate(c2, ["invest"], plan_id="k15-excel")
    y0 = r2.invest_start_year
    assert [i + y0 for i, x in enumerate(r2.values["invest.berth"]["MP"]) if x] == [0, 7, 13]
    c2.horizon.berth_lookahead_years = 7
    r3 = calculate(c2, ["invest"], plan_id="k15-excel")
    mp = r3.values["invest.berth"]["MP"]
    assert [(i + y0, x / 7.5e9) for i, x in enumerate(mp) if x] == [(0, 1.0), (7, 2.0)]
    c2.horizon.construction_lead_years = 0
    r4 = calculate(c2, ["invest"], plan_id="k15-excel")
    assert r4.invest_start_year == 1 and len(r4.values["invest.total"]["total"]) == 20
    # total nominal tidak bergantung pada pola bangun (tanpa eskalasi): yang berubah tahun & PV
    assert close(sum(r2.values["invest.berth"]["MP"]), sum(res.values["invest.berth"]["MP"]))


def test_discount_rate_ranks_waterside_options_I9(case, res):
    """I9: PV opsi perairan memakai discount rate; keruk bertahap (opsi campuran & keruk penuh) lebih diuntungkan
    diskon daripada trestle penuh. PV < investasi nominal bila ada pembangunan setelah th 0."""
    o1 = {o.mode: o for o in res.waterside_options}
    for o in o1.values():
        assert o.pv < o.invest_total
    c2 = case.model_copy(deep=True)
    c2.params.discount_rate = 0.2
    o2 = {o.mode: o for o in calculate(c2, ["invest"], plan_id="k15-excel").waterside_options}
    for m in o1:
        assert o2[m].pv < o1[m].pv
        assert close(o2[m].invest_total, o1[m].invest_total)
    assert min(o1, key=lambda m: o1[m].pv) == "dredge"


def test_trucks_and_pipeline_invested(res):
    """Truk (A25: tidak diinvestasikan di Excel) × harga Headtruck; pipa CC = trestle desain CC + LOA × jetty (A30)."""
    v = res.values
    tr = v["storage.trucks"]["truk_petikemas"]
    assert close(sum(v["invest.yard_equipment"]["truk_petikemas"]), tr[-1] * 1.2e9)
    x_cc = next(o for o in res.waterside_options if o.selected).trestle_len["CC"]
    assert close(v["storage.pipeline"]["in.adi"][-1], x_cc + 174.38)
    assert close(sum(v["invest.pipeline"]["in.adi"]), v["storage.pipeline"]["in.adi"][-1] * 5e6)


def test_max_depth_limit_rejects_deep_ships(case):
    """Batas kedalaman rencana KEK (opsional): 1,5 · T > batas → kapal gugur dengan alasan; kosong = tanpa batas."""
    c2 = case.model_copy(deep=True)
    c2.kek_site.waterside.max_depth_m = 21.0
    r2 = calculate(c2, ["voyage"], plan_id="k15-excel")
    assert any("batas KEK" in x for x in r2.reasons["in.fantasi"])  # ALS CERES T 14,2 → 21,3 m
    assert "in.damai" not in r2.reasons  # AETOS T 10,02 → 15,03 m
    assert r2.values["vessel.feasible"]["in.fantasi"] == 0.0
