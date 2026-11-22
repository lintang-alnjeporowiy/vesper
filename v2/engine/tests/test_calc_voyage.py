"""Tahap 5 — kelayakan kapal & operasi pelayaran (SPEC §5.2–5.3).

1. Fungsi murni + hitungan tangan in.damai th-1 (AETOS, Badas).
2. Laporan selisih vs Excel: tiruan rumus Excel (`excel_k15.py`) mereproduksi golden persis, dan tiruan yang
   sama dengan semua koreksi audit (A1, A2, A3, A5, A10, A13) + D_TEU engine (A12) = engine persis. Jadi setiap
   selisih engine vs Excel dijelaskan oleh temuan audit yang tercatat.
"""

import json
import math
from pathlib import Path

import pytest
from excel_k15 import CAUSES, EXCEL_SERIES, FIXES, engine_series, excel_chain

from tpt_engine.calc import vessel, voyage
from tpt_engine.calc.run import COMPUTES, calculate, compare
from tpt_engine.domain import Case, load_case

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
FLOWS = GOLDEN["flow_order"]


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["shipcost"], plan_id="k15-excel")


def ship(case, sid):
    return next(s for s in case.ships if s.id == sid)


def flow(case, fid):
    return next(f for f in case.flows if f.id == fid)


def close(a, b, rel=1e-9):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


# ─── §5.2 kapal ────────────────────────────────────────────────────────────────────────────────
def test_n_equipment_loa_bands_A10(case):
    rules = case.equipment_rules
    loa = {89.9: 1, 90.0: 2, 159.9: 2, 160.0: 3, 179.9: 3, 180.0: 4, 349.0: 4, 400.0: 4}
    for length, n in loa.items():
        s = ship(case, "ship.aetos").model_copy(update={"loa_m": length})
        assert vessel.n_equipment(s, rules, "MP") == n, length
    big = ship(case, "ship.thea")  # LOA > 180 → 4, dibatasi CC = 2
    assert vessel.n_equipment(big, rules, "CC") == 2


def test_payload(case):
    p = case.params
    assert close(vessel.payload(ship(case, "ship.aetos"), p, "ton"), 0.85 * 38395)
    assert vessel.payload(ship(case, "ship.integra"), p, "TEU") == 1708  # kapasitas TEU isian
    assert vessel.payload(ship(case, "ship.als_ceres"), p, "TEU") == 3505  # default ⌊0,85·DWT/20⌋


def test_ballast_speed_default_ratio_A5(case):
    assert vessel.ballast_speed(ship(case, "ship.aetos"), case.params) == 15.6  # rasio 100 %, Excel 130 %


def test_feasibility_reasons(case):
    f = flow(case, "in.damai")  # Badas: draft 11,5 m, dermaga 159 m → LOA ≤ 187 m
    ok = vessel.feasibility(case, f, ship(case, "ship.aetos"))
    assert ok.ok and ok.reasons == []
    deep = vessel.feasibility(case, f, ship(case, "ship.acer_arrow"))  # T 13,03 m, LOA 199,9 m
    assert not deep.ok
    assert any("draft" in r for r in deep.reasons) and any("dermaga" in r for r in deep.reasons)
    wrong = vessel.feasibility(case, f, ship(case, "ship.thea"))
    assert not wrong.ok and any("tidak boleh" in r for r in wrong.reasons)
    no_berth = vessel.feasibility(case, flow(case, "in.fantasi"), ship(case, "ship.als_ceres"))  # Lampia tanpa data
    assert no_berth.notes and all("dermaga" not in r for r in no_berth.reasons)


# ─── §5.3 pelayaran: hitungan tangan ───────────────────────────────────────────────────────────
def test_hand_calc_in_damai_year1(res):
    """AETOS, Badas 992,2 NM, LHM 280 (1000 t/j), D = 3 jt t.
    payload = 0,85·38 395 = 32 635,75 t → F = ⌈3 000 000 / 32 635,75⌉ = 92, q = 32 608,70 t
    nEq(LOA 184,75) = 4 → tPortKEK = q/(1000·4)/24 = 0,33967; tPortExt = q/1000/24 = 1,35870 (A3: total per kapal)
    tSea = 2·992,2/15,6/24 = 5,30021 (A5: V ballast = Vs); tFix = 6/24 = 0,25
    RTD = 7,24858 → F_max = ⌊365/7,24858⌋ = 50 (A1) → N = ⌈92/50⌉ = 2"""
    v, y = res.values, 0
    q = 3_000_000 / 92
    assert v["vessel.payload"]["in.damai"] == pytest.approx(32635.75)
    assert v["voyage.freq"]["in.damai"][y] == 92
    assert v["voyage.q"]["in.damai"][y] == pytest.approx(q)
    assert v["vessel.neq"]["in.damai"] == 4
    assert v["voyage.t_port_kek"]["in.damai"][y] == pytest.approx(q / 4000 / 24)
    assert v["voyage.t_port_ext"]["in.damai"][y] == pytest.approx(q / 1000 / 24)
    assert v["voyage.t_sea"]["in.damai"][y] == pytest.approx(2 * 992.2 / 15.6 / 24)
    rtd = 2 * 992.2 / 15.6 / 24 + q / 4000 / 24 + q / 1000 / 24 + 0.25
    assert v["voyage.rtd"]["in.damai"][y] == pytest.approx(rtd)
    assert v["voyage.f_max"]["in.damai"][y] == math.floor(365 / rtd) == 50
    assert v["voyage.n_ship"]["in.damai"][y] == 2
    assert v["voyage.utilization"]["in.damai"][y] == pytest.approx(92 / 100)
    assert v["voyage.consumption"]["in.damai"][y] == pytest.approx(q / (3_000_000 / 365))


def test_hand_calc_out_damai_pk_year1(res):
    """PK: INTEGRA 1708 TEU, D_TEU = 358 021 → F = 210, q = 1704,86 TEU; LHM 280 35 box/j, 1 box = 1 TEU (20');
    LOA 172 m → nEq 3; Bangkok 40 TEU/j total."""
    v = res.values
    q = 358021 / 210
    assert v["voyage.freq"]["out.damai"][0] == 210
    assert v["vessel.neq"]["out.damai"] == 3
    assert v["voyage.t_port_kek"]["out.damai"][0] == pytest.approx(q / (35 * 3) / 24)
    assert v["voyage.t_port_ext"]["out.damai"][0] == pytest.approx(q / 40 / 24)


def test_no_voyage_years_are_zero(res):
    for k in ("voyage.freq", "voyage.rtd", "voyage.n_ship", "voyage.t_sea"):
        assert res.values[k]["in.adi"][:12] == [0.0] * 12


def test_rate_conversions(case):
    p = case.params
    assert voyage.rate_to_ship_unit(35, "box/h", "TEU", None, p) == 35  # semua 20'
    p40 = p.model_copy(update={"container": p.container.model_copy(update={"share_20ft": 0.0})})
    assert voyage.rate_to_ship_unit(35, "box/h", "TEU", None, p40) == 70
    assert voyage.rate_to_ship_unit(1000, "t/h", "TEU", 10.0, p) == 100
    with pytest.raises(voyage.VoyageError):
        voyage.rate_to_ship_unit(1000, "t/h", "TEU", None, p)


def test_f_max_rounddown_A1():
    assert voyage.f_max(365, 5.618) == 64  # Excel ⌈365/5,618⌉ = 65
    assert voyage.n_ship(0, 0) == 0


# ─── laporan selisih vs Excel ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("fid", FLOWS)
def test_excel_replica_reproduces_golden(case, fid):
    """Tiruan rumus Excel (temuan audit apa adanya) = golden Excel, semua seri, 20 tahun. Toleransi 1e-6: Excel
    memakai konstanta liter/ton HSD yang dibulatkan (Model!F44 = 1201,923; tiruan 1000/0,832)."""
    ex = excel_chain(case, GOLDEN, fid)
    for key in EXCEL_SERIES:
        ref = GOLDEN["flows"][fid]["series"][key]["values"]
        assert all(close(a, b, rel=1e-6) for a, b in zip(ex[key], ref, strict=True)), (fid, key)


@pytest.mark.parametrize("fid", FLOWS)
def test_corrected_replica_equals_engine(case, res, fid):
    """Tiruan yang sama + semua koreksi audit + D_TEU engine (A12) = engine. Selisih engine vs Excel ⊆ temuan audit."""
    ex = excel_chain(case, GOLDEN, fid, set(FIXES), res.values["cargo.demand_unit"][fid])
    for key in EXCEL_SERIES:
        assert all(close(a, b) for a, b in zip(ex[key], engine_series(res.values, fid, key), strict=True)), (fid, key)


@pytest.mark.parametrize("key", [k for k in EXCEL_SERIES if not CAUSES[k]])
def test_series_without_causes_match_excel(res, key):
    """Seri tanpa temuan audit (frekuensi, muatan per call) = Excel, kecuali tahun yang terbawa A12 dari D_TEU."""
    a12_flows = {"out.damai", "in.fantasi", "out.fantasi"}
    for fid in FLOWS:
        got, ref = engine_series(res.values, fid, key), GOLDEN["flows"][fid]["series"][key]["values"]
        bad = [t for t, (a, b) in enumerate(zip(got, ref, strict=True), 1) if not close(a, b)]
        assert not bad or fid in a12_flows, (fid, key, bad)


# ─── kontrak hasil & bandingkan kandidat ──────────────────────────────────────────────────────
def test_result_contract(res):
    assert res.modules == ["demand", "voyage", "shipcost"]  # shipcost menarik voyage & demand
    assert set(COMPUTES["voyage"]) <= set(res.computed)
    assert res.equipment_by_terminal == {"MP": "eq.liebherr_lhm_280", "CC": "eq.emco_wheaton_b0300_10"}
    assert all(len(res.values["voyage.rtd"][f]) == 20 for f in FLOWS)
    assert res.reasons == {} and res.warnings == []


def test_feasibility_matrix(case, res):
    m = res.feasibility
    assert set(m) == set(FLOWS)
    assert set(m["in.damai"]) == {s.id for s in case.ships if s.ship_type in case.compatibility["GC"]}
    assert m["in.damai"]["ship.aetos"].ok and not m["in.damai"]["ship.acer_arrow"].ok
    assert m["in.fantasi"]["ship.als_ceres"].notes  # Lampia: panjang dermaga kosong


def test_equipment_override_changes_port_time(case, res):
    alt = calculate(case, ["voyage"], equipment_by_terminal={"MP": "eq.liebherr_lhm_600"})
    assert alt.values["voyage.t_port_kek"]["in.damai"][0] == pytest.approx(res.values["voyage.t_port_kek"]["in.damai"][0] / 2)


def test_infeasible_selected_ship_is_reported(case):
    r = calculate(case, ["voyage"], ship_by_flow={"in.damai": "ship.acer_arrow"})
    assert r.values["vessel.feasible"]["in.damai"] == 0.0
    assert r.reasons["in.damai"] and any("gugur" in w for w in r.warnings)


def test_compare_candidates(case):
    c = compare(case, "in.damai", plan_id="k15-excel")
    assert c.unit == "ton" and c.equipment_id == "eq.liebherr_lhm_280"
    rows = {r.ship_id: r for r in c.rows}
    assert len(rows) == len(case.ships)
    assert rows["ship.aetos"].selected and rows["ship.aetos"].feasible
    assert rows["ship.aetos"].values["voyage.n_ship"][0] == 2
    assert not rows["ship.thea"].compatible and rows["ship.thea"].values == {}
    assert rows["ship.acer_arrow"].compatible and not rows["ship.acer_arrow"].feasible
    assert "voyage.rtd" in rows["ship.acer_arrow"].values  # rantai tetap dihitung untuk perbandingan
    pk = compare(case, "out.damai")
    assert pk.unit == "TEU"
    assert {r.ship_id for r in pk.rows if r.compatible} == {s.id for s in case.ships if s.ship_type == "container_ship"}


def test_compare_unknown_flow(case):
    with pytest.raises(ValueError):
        compare(case, "x")
