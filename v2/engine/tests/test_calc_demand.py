"""Tahap 4 — demand & konversi muatan (SPEC §5.1) dibandingkan dengan golden Excel K15.

Golden = nilai Excel (rumus lama), bukan kunci jawaban. Seri yang berbeda dijelaskan dengan ID audit:
- A4  batas maks dicek ke tahun sebelumnya — tidak mengubah angka K15 (batas tidak terlampaui / tepat di batas).
- A12 pembulatan TEU di `Proyeksi Muatan`: tahun-1 ROUNDDOWN (G20), tahun lain ROUNDUP; TEU inbound dibulatkan lalu
      dikompounding (J5…); outbound TEU tidak dibulatkan. Engine: proyeksi kontinu, ⌈·⌉ sekali di D_TEU.
"""

import json
import math
from pathlib import Path

import pytest

from tpt_engine.calc import cargo, demand, vessel
from tpt_engine.calc.run import COMPUTES, calculate
from tpt_engine.domain import Case, load_case
from tpt_engine.registry import REGISTRY

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["demand"], plan_id="k15-excel")


def excel(fid: str) -> list[float]:
    return GOLDEN["flows"][fid]["series"]["demand"]["values"]


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)


# ─── fungsi murni ──────────────────────────────────────────────────────────────────────────────
def test_demand_base_start_growth_cap():
    s = demand.demand_base(start_year=3, initial=100.0, maximum=120.0, growth_rate=0.1, years=6)
    assert s[:2] == [0.0, 0.0]
    assert s[2] == 100.0 and close(s[3], 110.0) and s[4] == 120.0 and s[5] == 120.0  # 121 dipotong ke Dmax


def test_demand_cap_uses_previous_year_A4():
    """A4: Excel mengecek `$G$12·(1+g) > Dmax` (sel tetap) sehingga batas tak pernah aktif bila V₀·(1+g) ≤ Dmax.
    Engine mengecek nilai tahun sebelumnya: seri tidak pernah melampaui Dmax."""
    s = demand.demand_base(1, 100.0, 150.0, 0.25, 5)
    excel_a4 = [100.0]
    for _ in range(4):  # tiruan rumus Excel yang salah (H12…)
        excel_a4.append(150.0 if 100.0 * 1.25 > 150.0 else excel_a4[-1] * 1.25)
    assert max(excel_a4) > 150.0  # bug Excel: menembus batas
    assert max(s) == 150.0 and s == [100.0, 125.0, 150.0, 150.0, 150.0]


def test_initial_above_maximum_is_capped():
    assert demand.demand_base(1, 200.0, 150.0, 0.0, 2) == [150.0, 150.0]


def test_ratio_follows_basis():
    assert demand.demand_ratio([0.0, 10.0, 20.0], 0.5) == [0.0, 5.0, 10.0]


def test_box_per_teu_geometry_and_weight_limit(case):
    cont = case.params.container
    jag = next(c for c in case.commodities if c.id == "tepung_jagung")
    assert cargo.box_per_teu(cont, jag.packaging, 22.1) == 11 * 5 * 7  # dibatasi geometri
    assert cargo.box_per_teu(cont, jag.packaging, 5.0) == math.floor(5.0 / 0.0185)  # dibatasi NetMax


def test_ceil_is_float_safe():
    assert cargo.ceil_(104000.00000000001) == 104000
    assert cargo.ceil_(358020.36) == 358021


# ─── golden K15: proyeksi D[f,t] ──────────────────────────────────────────────────────────────
TON_FLOWS = ["in.damai", "in.esa", "in.baru", "in.adi", "out.esa", "out.adi"]


@pytest.mark.parametrize("fid", TON_FLOWS)
def test_ton_flows_match_excel(res, fid):
    """Flow bersatuan ton & diangkut dalam ton: D[f,t] = Excel persis (A4 tidak aktif di K15)."""
    assert GOLDEN["flows"][fid]["series"]["demand"]["affected_by"] == []
    got = res.values["cargo.demand_unit"][fid]
    assert len(got) == 20
    assert all(close(a, b) for a, b in zip(got, excel(fid), strict=True)), fid


def test_ratio_teu_flow_projection_matches_excel(res):
    """out.fantasi = 2 × in.fantasi (aturan rasio TEU); Excel memproyeksikannya kontinu → sama persis."""
    assert all(close(a, b) for a, b in zip(res.values["demand.ratio"]["out.fantasi"], excel("out.fantasi"), strict=True))


@pytest.mark.parametrize("fid", ["in.fantasi", "out.fantasi"])
def test_teu_flows_rounded_once_A12(res, fid):
    """A12: D_TEU = ⌈D⌉ satu kali. Excel membulatkan in.fantasi tiap tahun lalu mengompounding hasil bulat
    (drift naik ≤ 6 TEU sebelum batas), dan tidak membulatkan out.fantasi. Selisih ≤ 6 TEU; setelah batas sama."""
    got, ref = res.values["cargo.demand_unit"][fid], excel(fid)
    for t, (a, b) in enumerate(zip(got, ref, strict=True), start=1):
        assert a == math.ceil(a), (fid, t)
        assert abs(a - b) <= 6, (fid, t, a, b)
        if b in (0.0, 160000.0, 320000.0) or t <= 4:  # sebelum mulai, di batas, dan sebelum drift pembulatan
            assert a == math.ceil(b), (fid, t, a, b)


def test_in_fantasi_excel_drift_is_compounded_rounding(res):
    """Bukti penyebab A12 untuk in.fantasi: tiruan ROUNDUP-lalu-kompounding Excel mereproduksi golden persis."""
    ref = excel("in.fantasi")
    sim, prev = [], 0.0
    for t in range(1, 21):
        d = 0.0 if t < 3 else (100000.0 if t == 3 else math.ceil(min(160000.0, prev * 1.04) - 1e-9))
        sim.append(d)
        prev = d
    assert sim == ref


@pytest.mark.parametrize("fid,tpt_key", [("out.damai", "tepung_jagung"), ("out.baru", "tepung_terigu")])
def test_pk_ton_flows_to_teu(res, fid, tpt_key):
    """PK bersatuan ton: D_TEU = ⌈D_ton / tonPerTEU⌉ = Excel, kecuali tahun-1 out.damai (A12: Excel ROUNDDOWN)."""
    assert close(res.values["cargo.ton_per_teu"][fid], GOLDEN["derived"]["ton_per_teu"][tpt_key]["value"])
    got, ref = res.values["cargo.demand_unit"][fid], excel(fid)
    for t, (a, b) in enumerate(zip(got, ref, strict=True), start=1):
        if fid == "out.damai" and t == 1:
            assert (a, b) == (358021.0, 358020.0)  # 2 550 000 / 7,1225 = 358 020,36
        else:
            assert a == b, (fid, t, a, b)


# ─── golden K15: tonPerTEU & NetMax (bergantung kapal) ─────────────────────────────────────────
def test_ton_per_teu_aluminium_capped_by_ship_netmax(res, case):
    """Aluminium: Vc/SF = 37,5 t > NetMax ALS Ceres (0,9·82 488,7/3 505 − 1,9 = 19,28) → dibatasi NetMax."""
    assert res.ship_by_flow["in.fantasi"] == "ship.als_ceres"
    assert res.values["vessel.teu_cap"]["ship.als_ceres"] == 3505  # kapasitas TEU default (parameter)
    assert close(res.values["cargo.netmax"]["in.fantasi"], GOLDEN["derived"]["ton_per_teu"]["aluminium"]["value"])
    assert close(res.values["cargo.ton_per_teu"]["in.fantasi"], GOLDEN["derived"]["ton_per_teu"]["aluminium"]["value"])


def test_netmax_depends_on_ship(case):
    """NetMax = min(22,1; 0,9·DWT/TEU − tare): Integra 9,435 (Muatan!G70); kapal besar dibatasi payload kontainer."""
    ships = {s.id: s for s in case.ships}
    p, cont = case.params, case.params.container
    integra = ships["ship.integra"]
    assert close(cargo.net_max(cont, p, integra.dwt_t, vessel.teu_capacity(integra, p)), 9.435362997658078)
    big = cargo.net_max(cont, p, 100000.0, 1000)
    assert big == cont.max_net_t


def test_ship_override_changes_teu_demand(case):
    """Ganti kapal → NetMax berubah → tonPerTEU & D_TEU ikut berubah (interaksi I5)."""
    base = calculate(case, ["demand"])
    alt = calculate(case, ["demand"], ship_by_flow={"out.damai": "ship.tanto_selalu"})
    assert alt.values["cargo.netmax"]["out.damai"] != base.values["cargo.netmax"]["out.damai"]
    assert alt.ship_by_flow["out.damai"] == "ship.tanto_selalu"


# ─── kontrak hasil ─────────────────────────────────────────────────────────────────────────────
def test_result_keys_are_registry_ids(res):
    ids = {v.id for v in REGISTRY}
    assert set(res.values) <= ids
    assert set(res.computed) == set(COMPUTES["demand"]) <= ids
    assert set(res.values["cargo.demand_unit"]) == {f.id for f in res_case_flows()}
    assert res.warnings == []


def res_case_flows():
    return load_case(V2 / "cases" / "k15-batam.json").flows


def test_unknown_module_rejected(case):
    with pytest.raises(ValueError):
        calculate(case, ["waterside"])
