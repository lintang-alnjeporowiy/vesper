"""§5.5 Terminal KEK (Tahap 7a): ship-days, berth-days, tambatan, BOR, panjang dermaga, alat B/M vs golden K15.

Pembuktian sama seperti Tahap 5–6: tiruan rumus Excel (`excel_terminal`) = golden, dan tiruan + semua koreksi
(A2, A10, …, A16, A17) = engine. Hitungan tangan untuk satu tahun MP dan CC.
"""

import json
import math
from pathlib import Path

import pytest
from excel_k15 import FIXES, TERMINAL_FIXES, TERMINAL_SERIES, engine_terminal, excel_chain, excel_terminal

from tpt_engine.calc import terminal
from tpt_engine.calc.run import calculate
from tpt_engine.domain import Case, load_case

V2 = Path(__file__).resolve().parents[2]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "k15_excel.json").read_text(encoding="utf-8"))
FLOWS = GOLDEN["flow_order"]
KEYS = [f"{s}_{t}" for s in TERMINAL_SERIES for t in ("mp", "cc")]


def close(a: float, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(V2 / "cases" / "k15-batam.json")


@pytest.fixture(scope="module")
def res(case):
    return calculate(case, ["terminal"], plan_id="k15-excel")


def test_excel_replica_reproduces_golden(case):
    """Tiruan rumus Excel (temuan audit apa adanya) = golden Model!K101:AD363, 20 tahun."""
    chains = {f: excel_chain(case, GOLDEN, f) for f in FLOWS}
    ex = excel_terminal(case, GOLDEN, chains)
    for key in KEYS:
        ref = GOLDEN["terminal"][key]["values"]
        assert all(close(a, b, rel=1e-6) for a, b in zip(ex[key], ref, strict=True)), (key, ex[key], ref)


def test_corrected_replica_equals_engine(case, res):
    """Tiruan + semua koreksi + D_TEU engine = engine. Selisih engine vs Excel ⊆ temuan audit."""
    fixes = set(FIXES) | set(TERMINAL_FIXES)
    chains = {f: excel_chain(case, GOLDEN, f, fixes, res.values["cargo.demand_unit"][f]) for f in FLOWS}
    ex = excel_terminal(case, GOLDEN, chains, fixes)
    for key in KEYS:
        got = engine_terminal(case, res.values, key)
        assert all(close(a, b) for a, b in zip(ex[key], got, strict=True)), (key, ex[key], got)


def test_hand_calc_mp_year8(case, res):
    """Tahun 8 MP: berth-days = Σ ⌈F·(tPortKEK + IT)·LOA/300⌉; tambatan = ⌈Σ/(0,7·365)⌉; BOR = Σ/(n·365)."""
    y = 7
    ships = {s.id: s for s in case.ships}
    it = case.params.it_hours / 24
    tot = 0
    for f in case.flows:
        if f.cargo_form == "CC":
            continue
        fr = res.values["voyage.freq"][f.id][y]
        tk = res.values["voyage.t_port_kek"][f.id][y]
        loa = ships[res.ship_by_flow[f.id]].loa_m
        bd = math.ceil(fr * (tk + it) * loa / 300 - 1e-9) if fr else 0
        assert res.values["terminal.berth_days"][f.id][y] == bd
        tot += bd
    n = math.ceil(tot / (0.7 * 365))
    assert res.values["terminal.n_berth"]["MP"][y] == n
    assert close(res.values["terminal.bor"]["MP"][y], tot / (n * 365))
    assert res.values["terminal.berth_length"]["MP"][y] == n * 300
    assert res.values["terminal.n_equip"]["MP"][y] == n * 4  # kapal terpanjang ≥ 180 m → 4 alat


def test_jetty_one_ship_one_berth_A16(case, res):
    """CC (jetty): berth-days = ⌈shipDays⌉, tidak bergantung LOA."""
    for fid in ("in.adi", "out.adi"):
        for sd, bd in zip(res.values["terminal.ship_days"][fid], res.values["terminal.berth_days"][fid], strict=True):
            assert bd == math.ceil(sd - 1e-9)
    assert res.values["terminal.berth_length"]["CC"][12] == 40.0


def test_ship_days_include_idle_time_A17(res):
    """shipDays = F · (tPortKEK + IT), IT = 2 jam."""
    fr, tk = res.values["voyage.freq"]["in.damai"], res.values["voyage.t_port_kek"]["in.damai"]
    assert close(res.values["terminal.ship_days"]["in.damai"][0], fr[0] * (tk[0] + 2 / 24))


def test_berths_never_decrease():
    assert terminal.n_berth([300, 100, 0, 600], 0.7, 365) == [2.0, 2.0, 2.0, 3.0]
    assert terminal.additions([1.0, 1.0, 2.0, 3.0]) == [1.0, 0.0, 1.0, 1.0]


def test_bor_max_drives_berths_I6(case):
    """I6: BOR maks lebih rendah → tambatan lebih banyak."""
    base = calculate(case, ["terminal"], plan_id="k15-excel").values["terminal.n_berth"]["MP"]
    c2 = case.model_copy(deep=True)
    c2.params.bor_max = 0.5
    low = calculate(c2, ["terminal"], plan_id="k15-excel").values["terminal.n_berth"]["MP"]
    assert all(b >= a for a, b in zip(base, low, strict=True)) and low[-1] > base[-1]


def test_productivity_reduces_berth_days_I3(case):
    """I3: alat lebih produktif → port time KEK turun → berth-days turun."""
    base = calculate(case, ["terminal"], plan_id="k15-excel").values["terminal.berth_days"]["in.damai"]
    c2 = case.model_copy(deep=True)
    eq = next(e for e in c2.equipment if e.id == "eq.liebherr_lhm_280")
    eq.productivity["GC"].unload *= 2
    fast = calculate(c2, ["terminal"], plan_id="k15-excel").values["terminal.berth_days"]["in.damai"]
    assert sum(fast) < sum(base)
