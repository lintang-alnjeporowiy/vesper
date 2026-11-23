"""§5.6 Penyimpanan (Tahap 7b): CY, gudang GC, silo, tangki, alat lapangan vs golden `Fasilitas Daratan` K15.

Pembuktian sama seperti Tahap 5–7a: tiruan rumus Excel (`excel_storage`) = golden, dan tiruan + semua koreksi
(A12, A13 dari rantai flow; A18, A19, A20) = engine. Hitungan tangan: dengan dwell = lama konsumsi, stok = satu
pengapalan (Q · Tdw / 365 = q per call).
"""

import json
import math
from pathlib import Path

import pytest
from excel_k15 import FIXES, STORAGE_FIXES, excel_chain, excel_storage

from tpt_engine.calc import storage
from tpt_engine.calc.run import COMPUTES, calculate
from tpt_engine.domain import Case, load_case

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
FLOWS = GOLDEN["flow_order"]


def close(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["storage"], plan_id="k15-excel")


def test_excel_replica_reproduces_golden(case):
    """Tiruan rumus Excel (temuan A13, A18–A20 apa adanya) = golden Fasilitas Daratan, semua baris, 20 tahun."""
    chains = {f: excel_chain(case, GOLDEN, f) for f in FLOWS}
    dem = {f: GOLDEN["flows"][f]["series"]["demand"]["values"] for f in FLOWS}
    ex = excel_storage(case, GOLDEN, chains, dem)
    for fid, rows in GOLDEN["storage"]["flows"].items():
        for key, s in rows.items():
            assert all(close(a, b, 1e-6) for a, b in zip(ex["flows"][fid][key], s["values"], strict=True)), (fid, key)
    for key, s in GOLDEN["storage"]["total"].items():
        assert all(close(a, b, 1e-6) for a, b in zip(ex["total"][key], s["values"], strict=True)), key


def test_corrected_replica_equals_engine(case, res):
    """Tiruan + semua koreksi + D_TEU engine = engine untuk setiap variabel storage.* dan setiap kunci."""
    fixes = set(FIXES) | set(STORAGE_FIXES)
    dem = res.values["cargo.demand_unit"]
    chains = {f: excel_chain(case, GOLDEN, f, fixes, dem[f]) for f in FLOWS}
    ex = excel_storage(case, GOLDEN, chains, dem, fixes)["engine"]
    assert set(ex) == set(COMPUTES["storage"])
    for var, by in ex.items():
        assert set(by) == set(res.values[var]), var
        for key, s in by.items():
            assert all(close(a, b) for a, b in zip(s, res.values[var][key], strict=True)), (var, key)


def test_stock_equals_one_shipment(case, res):
    """Hitungan tangan th-1: Q · Tdw / 365 = q per call, sehingga luas CY out.damai = (1 + kosong) · q · A_TEU / (H · YOR),
    gudang in.damai = q · f_area · f_bulk / (ρ · H · SOR)."""
    v = res.values
    cy, gc = case.storage.container_yard, case.storage.general_cargo
    q = v["voyage.q"]["out.damai"][0]
    assert close(v["storage.throughput"]["out.damai"][0] * v["storage.dwell"]["out.damai"][0] / 365, q)
    assert close(v["storage.cy"]["out.damai"][0], 2 * q * 15 / (0.9 * 0.7))
    assert close(v["storage.cy_slots"]["out.damai"][0], 2 * q / (0.9 * 0.7 * cy.max_tiers))
    qg = v["voyage.q"]["in.damai"][0]
    assert close(v["storage.gc"]["in.damai"][0], qg * gc.f_area * gc.f_bulk / (0.72 * gc.stack_height_m * gc.sor_max))
    y = 12  # CPO tahun ke-13: V = q / (ρ · okupansi), tangki = ⌈V / 20.000⌉
    qc = v["voyage.q"]["in.adi"][y]
    vol = qc / (0.909 * 0.65)
    assert close(v["storage.liquid"]["in.adi"][y], vol)
    assert v["storage.tanks"]["in.adi"][y] == math.ceil(vol / 20000)


def test_forklift_dozer_match_excel(res):
    """Forklift (GC, sudah satu armada di Excel) dan dozer (20 t/jam) tidak terkena temuan audit → sama dengan Excel."""
    eq = res.values["storage.yard_equipment"]
    assert eq["forklift"] == GOLDEN["storage"]["total"]["forklifts"]["values"]
    assert eq["dozer"] == GOLDEN["storage"]["total"]["dozers"]["values"]
    assert "truk_petikemas" not in eq and "truk_curah" not in eq  # role transport → Tahap 8


def test_totals_never_decrease(res):
    for var in ("storage.cy", "storage.cy_slots", "storage.gc", "storage.bulk", "storage.silos", "storage.liquid",
                "storage.tanks"):
        tot = res.values[var][storage.TOTAL]
        flows = [s for k, s in res.values[var].items() if k != storage.TOTAL]
        raw = [sum(x) for x in zip(*flows, strict=True)]
        assert all(b >= a for a, b in zip(tot, tot[1:], strict=False)), var
        assert all(t >= r - 1e-9 for t, r in zip(tot, raw, strict=True)), var
    for s in res.values["storage.yard_equipment"].values():
        assert all(b >= a for a, b in zip(s, s[1:], strict=False))


def test_bigger_ship_needs_more_storage_I1(case, res):
    """I1: payload ↑ → muatan per call ↑ → lama konsumsi ↑ → gudang ↑ (frekuensi turun, stok per pengapalan naik)."""
    c2 = case.model_copy(deep=True)
    sid = res.ship_by_flow["in.damai"]
    ship = next(s for s in c2.ships if s.id == sid)
    ship.dwt_t *= 1.5
    big = calculate(c2, ["storage"], plan_id="k15-excel").values["storage.gc"]["in.damai"]
    assert all(b > a for a, b in zip(res.values["storage.gc"]["in.damai"], big, strict=True))


def test_fixed_dwell_and_empty_share(case, res):
    c2 = case.model_copy(deep=True)
    c2.storage.dwell_time_mode = "fixed"
    c2.storage.fixed_dwell_days = {"jagung_karung": 7.0}
    r2 = calculate(c2, ["storage"], plan_id="k15-excel")
    assert r2.values["storage.dwell"]["in.damai"][0] == 7.0
    ratio = r2.values["storage.gc"]["in.damai"][0] / res.values["storage.gc"]["in.damai"][0]
    assert close(ratio, 7.0 / res.values["storage.dwell"]["in.damai"][0])
    assert "out.damai" not in r2.values["storage.cy"]
    assert any("tepung_jagung" in w for w in r2.warnings)
    c3 = case.model_copy(deep=True)
    c3.storage.container_yard.empty_share = 0.0
    r3 = calculate(c3, ["storage"], plan_id="k15-excel")
    assert close(r3.values["storage.cy"]["out.damai"][0], res.values["storage.cy"]["out.damai"][0] / 2)
