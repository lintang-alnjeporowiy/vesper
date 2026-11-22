"""Integritas registry variabel (Tahap 3): graf lengkap, tanpa yatim, tanpa siklus, path input valid."""

import re
import types
import typing
from pathlib import Path

import pytest
from pydantic import BaseModel

from tpt_engine import registry as R
from tpt_engine.domain import Case

V2 = Path(__file__).resolve().parents[2]
WEB_JSON = V2 / "web" / "src" / "mock" / "registry.json"


def test_ids_unique_and_well_formed():
    ids = [v.id for v in R.REGISTRY]
    assert len(ids) == len(set(ids))
    for v in R.REGISTRY:
        assert re.fullmatch(r"[a-z]+(\.[a-z_]+)+", v.id), v.id
        assert v.kind in R.KINDS, v.id
        assert v.label and v.unit and v.formula and v.section, v.id
        if v.kind == "input":
            assert v.id.startswith("in."), v.id
        elif v.kind == "decision":
            assert v.id.startswith("dv."), v.id


def test_every_variable_has_description():
    ids = {v.id for v in R.REGISTRY}
    from tpt_engine.registry_desc import DESC

    assert not (set(DESC) - ids), f"keterangan untuk id yang tidak ada: {sorted(set(DESC) - ids)}"
    for v in R.REGISTRY:
        assert len(v.desc) >= 20, f"{v.id}: keterangan kosong/terlalu pendek"


def test_deps_exist():
    ids = R.by_id()
    for v in R.REGISTRY:
        for d in v.deps:
            assert d in ids, f"{v.id} -> {d} tidak ada di registry"
        assert len(set(v.deps)) == len(v.deps), f"{v.id}: dep ganda"
        assert v.id not in v.deps, f"{v.id}: bergantung pada diri sendiri"


def test_no_cycles():
    order = R.topo_order()
    pos = {vid: i for i, vid in enumerate(order)}
    assert len(order) == len(R.REGISTRY)
    for v in R.REGISTRY:
        for d in v.deps:
            assert pos[d] < pos[v.id]


def test_depth_flows_left_to_right():
    depth = R.depths()
    for v in R.REGISTRY:
        for d in v.deps:
            assert depth[d] < depth[v.id], f"{d} -> {v.id}"


def test_cycle_is_detected(monkeypatch):
    a = R.VarDef(id="x.a", label="a", unit="-", scope="global", kind="derived", formula="b", deps=("x.b",), section="5")
    b = R.VarDef(id="x.b", label="b", unit="-", scope="global", kind="derived", formula="a", deps=("x.a",), section="5")
    monkeypatch.setattr(R, "REGISTRY", R.REGISTRY + (a, b))
    with pytest.raises(ValueError, match="melingkar"):
        R.topo_order()


def test_no_orphans():
    """Input selalu dipakai; turunan selalu punya masukan; hanya metric/objective yang boleh jadi ujung."""
    kids = R.dependents()
    for v in R.REGISTRY:
        if v.kind in ("input",):
            assert not v.deps, v.id
        if v.kind in ("derived", "metric", "objective"):
            assert v.deps, f"{v.id}: turunan tanpa masukan"
        if v.kind in ("metric", "objective"):
            assert not kids[v.id], f"{v.id}: metric/objective tidak boleh dipakai variabel lain (jadikan derived)"
        else:
            assert kids[v.id], f"{v.id}: simpul yatim (tidak dipakai variabel mana pun)"


def test_everything_reaches_a_sink_and_objective_sees_decisions():
    up = R.upstream("obj.npv")
    for dv in ("dv.ship", "dv.equip", "dv.waterside", "dv.speed"):
        assert dv in up, f"objektif tidak dipengaruhi {dv}"
    sinks = {v.id for v in R.REGISTRY if v.kind in ("metric", "objective")}
    for v in R.REGISTRY:
        assert v.id in sinks or R.downstream(v.id) & sinks, v.id


def test_spec_sections_covered():
    secs = {v.section for v in R.DERIVED}
    for s in ("5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "5.8", "5.9"):
        assert s in secs, f"SPEC §{s} belum punya variabel"
    for s in ("4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8", "4.9"):
        assert s in {v.section for v in R.INPUTS}, f"SPEC §{s} belum punya input"


def test_audit_screens_columns():
    for v in R.REGISTRY:
        assert set(v.audit) <= set(R.AUDIT_IDS), v.id
        assert all(0 <= s <= 12 for s in v.screens), v.id
        R.lane_of(v)
        if v.kind == "input":
            assert R.input_group(v.id) in R.INPUT_GROUPS, v.id
    for _, _, start in R.INTERACTIONS:
        assert start in R.by_id()


def test_result_screens_have_traceable_variables():
    for s in (6, 7, 8, 9):
        assert any(s in v.screens and v.kind != "input" for v in R.REGISTRY), f"layar {s}"


# ── case_path menunjuk field yang benar-benar ada di model Case ──────────────────────────────────
def _models_of(tp) -> list[type[BaseModel]]:
    """Buka Annotated/Optional/Union/list/dict sampai ketemu model Pydantic."""
    origin = typing.get_origin(tp)
    if origin is typing.Annotated:
        return _models_of(typing.get_args(tp)[0])
    if origin in (typing.Union, types.UnionType, list, tuple):
        return [m for a in typing.get_args(tp) for m in _models_of(a)]
    if origin is dict:
        return _models_of(typing.get_args(tp)[1])
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return [tp]
    return []


def _resolve(path: str) -> bool:
    current: list[type[BaseModel]] = [Case]
    for seg in path.split("."):
        name = seg.split("[")[0]
        nxt: list[type[BaseModel]] = []
        found = False
        for m in current:
            f = m.model_fields.get(name)
            if f is not None:
                found = True
                nxt += _models_of(f.annotation)
        if not found:
            return False
        current = nxt
    return True


def test_input_case_paths_exist():
    for v in R.INPUTS:
        assert v.case_path, v.id
        assert _resolve(v.case_path), f"{v.id}: case_path '{v.case_path}' tidak ada di Case"


def test_web_json_in_sync():
    assert WEB_JSON.exists(), "jalankan: uv run --project engine python tools/dump_registry.py"
    assert WEB_JSON.read_text(encoding="utf-8") == R.to_json(), (
        "registry.json basi — jalankan: uv run --project engine python tools/dump_registry.py"
    )


def test_impl_points_to_engine_functions():
    """Tahap 4: variabel yang sudah dihitung engine menunjuk fungsi `calc` yang ada; §5.1 lengkap."""
    import importlib

    from tpt_engine.calc.run import COMPUTES

    for v in R.REGISTRY:
        if v.impl is None:
            continue
        mod, fn = v.impl.split(":")
        assert callable(getattr(importlib.import_module(f"tpt_engine.calc.{mod}"), fn)), v.id
    with_impl = {v.id for v in R.REGISTRY if v.impl}
    assert {v.id for v in R.REGISTRY if v.section in ("5.1", "5.3") and v.kind in ("derived", "metric")} <= with_impl
    assert {v.id for v in R.REGISTRY if v.section == "5.2"} - with_impl == {"vessel.reach_ok"}  # Tahap 7
    assert {v.id for v in R.REGISTRY if v.section == "5.4" and v.kind in ("derived", "metric")} <= with_impl
    assert {vid for ids in COMPUTES.values() for vid in ids} == with_impl
