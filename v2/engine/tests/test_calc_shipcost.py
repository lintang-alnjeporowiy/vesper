"""Tahap 6 — biaya pelayaran (SPEC §5.4): BBM, TCH, biaya pelabuhan, shipping cost.

DoD: tarif TCH & SFOC = Excel untuk input yang sama (semua 41 kapal); biaya pelabuhan & BBM sesuai hitungan
tangan; selisih vs Excel terjelaskan — tiruan rumus Excel (excel_k15.py) = golden dan tiruan + koreksi = engine
untuk seri biaya juga (lihat test_calc_voyage.py, EXCEL_SERIES mencakup BBM, TCH, pelabuhan, shipping cost).
"""

import json
import math
from pathlib import Path

import pytest

from tpt_engine.calc import shipcost, vessel
from tpt_engine.calc.run import PORT_PARTS, calculate, compare
from tpt_engine.domain import Case, load_case

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["shipcost"], plan_id="k15-excel")


def ship(case, sid):
    return next(s for s in case.ships if s.id == sid)


# ─── kapal: SFOC & TCH = Excel ─────────────────────────────────────────────────────────────────
def test_sfoc_matches_excel_for_all_ships(case):
    for v in GOLDEN["derived"]["ships"].values():
        me, ae = shipcost.sfoc(ship(case, v["ship_id"]), case.params)
        assert me == pytest.approx(v["sfoc_me"]) and ae == pytest.approx(v["sfoc_ae"]), v["ship_id"]


def test_tch_regression_matches_excel(case):
    for code, ref in GOLDEN["derived"]["tch_regression_usd_per_day"].items():
        st = next(t for t in case.ship_types if t.code == code)
        a, b = shipcost.tch_regression(st)
        assert a == pytest.approx(ref["slope"]) and b == pytest.approx(ref["intercept"]), code


def test_tch_per_year_matches_excel_for_all_ships(case):
    """Model!AL38:BZ38 = (a·ukuran + b) · kurs · 365; ukuran = DWT, atau kapasitas TEU untuk petikemas."""
    p = case.params
    for v in GOLDEN["derived"]["ships"].values():
        s = ship(case, v["ship_id"])
        st = next(t for t in case.ship_types if t.code == s.ship_type)
        size = vessel.teu_capacity(s, p) if st.size_basis == "teu" else s.dwt_t
        got = shipcost.tch_cost(shipcost.tch_rate(st, size), p.usd_rate, p.commission_days, 1)
        assert got == pytest.approx(v["tch_rp_per_year"], rel=1e-9), v["ship_id"]


def test_tch_needs_two_points(case):
    lct = next(t for t in case.ship_types if t.code == "lct")
    with pytest.raises(shipcost.CostError):
        shipcost.tch_regression(lct)


# ─── hitungan tangan ───────────────────────────────────────────────────────────────────────────
def test_port_call_domestic_in_damai(case, res):
    """Badas: kelas 2, dalam negeri, beton; AETOS 23 853 GT; q = 32 608,70 t; tPortExt = 1,3587 hr → 2 etmal."""
    tr = next(c for c in case.tariffs.classes if c.tariff_class == "2")
    gt, q = 23853, 3_000_000 / 92
    tug = tr.tug[5]  # rentang 18 001–26 000 GT
    expect = {
        "labuh": 84 * gt,
        "pandu": 2 * (101000 + 28 * gt),
        "tambat": 70 * gt * 2,
        "tunda": 2 * (tug.fixed_domestic_rp + tug.var_domestic_rp_per_gt * gt),
        "bm": 650 * q,
    }
    for k, v in expect.items():
        assert res.port_breakdown["in.damai"][k][0] == pytest.approx(v), k
    assert res.values["shipcost.port_call"]["in.damai"][0] == pytest.approx(sum(expect.values()))
    assert res.values["shipcost.port"]["in.damai"][0] == pytest.approx(sum(expect.values()) * 92)


def test_port_call_foreign_out_damai_A14(case, res):
    """Bangkok: luar negeri (A14: tarif USD × kurs), kelas utama, beton; INTEGRA 17 200 GT; B/M per TEU."""
    tr = next(c for c in case.tariffs.classes if c.tariff_class == "utama")
    fx, gt = case.params.usd_rate, 17200
    q = res.values["voyage.q"]["out.damai"][0]
    te = res.values["voyage.t_port_ext"]["out.damai"][0]
    tug = tr.tug[4]  # 14 001–18 000 GT
    b = res.port_breakdown["out.damai"]
    assert b["labuh"][0] == pytest.approx(0.115 * fx * gt)
    assert b["pandu"][0] == pytest.approx(2 * (109 + 0.04 * gt) * fx)
    assert b["tambat"][0] == pytest.approx(0.11 * fx * gt * math.ceil(te))
    assert b["tunda"][0] == pytest.approx(2 * (tug.fixed_foreign_usd + tug.var_foreign_usd_per_gt * gt) * fx)
    assert b["bm"][0] == pytest.approx(2_350_000 * q)


def test_fuel_hand_calc_in_damai_year1(case, res):
    """ME: 6780 kW · 0,8 · 190,26 g/kWh · 24 · tSea 5,3002 · F 92 → ton ÷ 0,832 = liter (A9: F aktual).
    AE: 3390 kW · 0,8 · 183,465 · 24 · (tPort + tFix) · 92 (A6: HSD)."""
    v = res.values
    tsea, tk, te = (v[k]["in.damai"][0] for k in ("voyage.t_sea", "voyage.t_port_kek", "voyage.t_port_ext"))
    me_t = 6780 * 0.8 * 190.26 / 1e6 * 24 * tsea * 92
    ae_t = 3390 * 0.8 * 183.465 / 1e6 * 24 * (tk + te + 0.25) * 92
    assert v["shipcost.fuel_me_l"]["in.damai"][0] == pytest.approx(me_t * 1e6 / 832)
    assert v["shipcost.fuel_ae_l"]["in.damai"][0] == pytest.approx(ae_t * 1e6 / 832)
    assert v["shipcost.fuel_me"]["in.damai"][0] == pytest.approx(me_t * 1e6 / 832 * 24000)
    assert v["shipcost.voyage"]["in.damai"][0] == pytest.approx((me_t + ae_t) * 1e6 / 832 * 24000)


def test_tch_and_total_in_damai_year1(res):
    v = res.values
    assert v["shipcost.tch"]["in.damai"][0] == pytest.approx(133506396248.49 * 2)  # N_ship = 2, sama dengan Excel
    total = v["shipcost.voyage"]["in.damai"][0] + v["shipcost.tch"]["in.damai"][0] + v["shipcost.port"]["in.damai"][0]
    assert v["shipcost.total"]["in.damai"][0] == pytest.approx(total)
    assert v["shipcost.unit"]["in.damai"][0] == pytest.approx(total / 3_000_000)  # Rp/t


def test_unit_cost_in_flow_unit_A7(res):
    """out.damai didefinisikan dalam ton walau diangkut dalam TEU → Rp/t (A7: satuan flow)."""
    v = res.values
    assert v["shipcost.unit"]["out.damai"][0] == pytest.approx(v["shipcost.total"]["out.damai"][0] / 2_550_000)
    assert v["shipcost.unit"]["in.fantasi"][2] == pytest.approx(v["shipcost.total"]["in.fantasi"][2] / 100_000)  # Rp/TEU


def test_breakdown_sums_to_port_call(res):
    for fid, parts in res.port_breakdown.items():
        for y, total in enumerate(res.values["shipcost.port_call"][fid]):
            assert sum(parts[k][y] for k in PORT_PARTS) == pytest.approx(total), (fid, y)


def test_kek_tariff_option(case):
    """TERSUS tanpa jasa (default K15) → port_call sama dengan pelabuhan eksternal saja; bila KEK bertarif, naik."""
    base = calculate(case, ["shipcost"])
    site = case.kek_site.model_copy(update={"port_charges": "tariff", "tariff_class": "1"})
    alt = calculate(case.model_copy(update={"kek_site": site}), ["shipcost"])
    assert alt.values["shipcost.port_call"]["in.damai"][0] > base.values["shipcost.port_call"]["in.damai"][0]


def test_compare_includes_costs(case):
    c = compare(case, "in.damai")
    rows = {r.ship_id: r for r in c.rows}
    assert rows["ship.aetos"].values["shipcost.unit"][0] > 0
    assert "shipcost.total" in rows["ship.simas"].values


def test_fuel_choice_A6(case):
    """Jenis BBM AE = parameter: MFO menurunkan biaya AE (harga lebih murah) dan mengubah liter (berat jenis)."""
    base = calculate(case, ["shipcost"])
    mfo = calculate(case.model_copy(update={"params": case.params.model_copy(update={"ae_fuel": "MFO"})}), ["shipcost"])
    a, b = base.values["shipcost.fuel_ae"]["in.damai"][0], mfo.values["shipcost.fuel_ae"]["in.damai"][0]
    assert b < a
    assert mfo.values["shipcost.fuel_ae_l"]["in.damai"][0] == pytest.approx(base.values["shipcost.fuel_ae_l"]["in.damai"][0] * 832 / 890)
