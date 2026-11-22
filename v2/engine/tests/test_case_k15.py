"""Tahap 1 — kontrak data: file kasus K15 valid, lengkap, dan setiap angka punya asal."""

import json
import math
from pathlib import Path

import pytest
from pydantic import BaseModel

from tpt_engine.domain import Case, case_json_schema, load_case

V2 = Path(__file__).resolve().parents[2]
CASE_PATH = V2 / "cases" / "k15-batam.json"
SCHEMA_PATH = V2 / "cases" / "case.schema.json"
GOLDEN_PATH = Path(__file__).parent / "golden" / "k15_excel.json"
AUDIT_IDS = {f"A{i}" for i in range(1, 16)} | {"semua"}


@pytest.fixture(scope="module")
def case() -> Case:
    return load_case(CASE_PATH)


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- isi kasus


def test_counts(case):
    assert len(case.tenants) == 5
    assert len(case.flows) == 10
    assert sum(f.direction == "inbound" for f in case.flows) == 5
    assert len(case.ports) == 10 and len(case.routes) == 10
    assert len(case.ships) == 41
    assert {t.code: sum(s.ship_type == t.code for s in case.ships) for t in case.ship_types} == {
        "tanker": 9, "bulk_carrier": 9, "container_ship": 14, "general_cargo_ship": 9, "lct": 0}
    assert len(case.equipment) == 11
    assert [t.id for t in case.kek_site.terminals] == ["MP", "CC"]


def test_reference_values(case):
    """Beberapa angka kunci dibandingkan langsung dengan laporan/Excel K15."""
    f = case.by_id("flows")["in.damai"]
    assert (f.volume.start_year, f.volume.initial, f.volume.maximum, f.volume.growth_rate) == (1, 3e6, 7.9e6, 0.05)
    assert case.by_id("flows")["out.fantasi"].volume.ratio == 2.0
    aetos = case.by_id("ships")["ship.aetos"]
    assert (aetos.dwt_t, aetos.loa_m, aetos.draft_m, aetos.gt, aetos.me_kw) == (38395, 184.75, 10.02, 23853, 6780)
    badas = case.by_id("ports")["badas"]
    assert (badas.max_draft_m, badas.productivity.value, badas.kind, badas.tariff_class) == (11.5, 1000, "domestic", "2")
    assert case.by_id("routes")["rt.badas"].legs[0].distance_nm == 992.2
    assert case.params.usd_rate == pytest.approx(15521.4)
    assert case.plans[0].ship_by_flow["in.damai"] == "ship.aetos"
    assert case.plans[0].equipment_by_terminal == {"MP": "eq.liebherr_lhm_280", "CC": "eq.emco_wheaton_b0300_10"}


def test_dummy_bathymetry_matches_k15(case):
    """Profil dummy dikunci ke K15: 10 m @250 m, 21,3 m pertama tercapai @500 m (trestle penuh)."""
    site = case.kek_site
    assert site.bathymetry_source == "dummy"
    pts = {p.distance_m: p.depth_m for p in site.bathymetry}
    assert pts[site.trestle_dredge.trestle_length_m] == site.trestle_dredge.existing_depth_m == 10.0
    req = 1.5 * 14.2  # kapal penentu K15: ALS CERES T = 14,2 m × depth_factor 1,5 (Fasilitas Perairan!K18)
    first = next(p.distance_m for p in site.bathymetry if p.depth_m >= req - 1e-9)
    assert first == site.trestle.max_length_m == 500.0
    depths = [p.depth_m for p in site.bathymetry]
    assert depths == sorted(depths)


def test_teu_capacity_default_reproduces_k15(case, golden):
    """Kapasitas TEU default (parameter) = nilai yang dipakai Model K15 untuk semua kapal petikemas."""
    p = case.params
    by_id = {v["ship_id"]: v for v in golden["derived"]["ships"].values()}
    pk = [s for s in case.ships if s.ship_type == "container_ship"]
    assert len(pk) == 14
    manual = [s.name for s in pk if s.teu_capacity is not None]
    assert 0 < len(manual) < 14  # K15 mencampur kapasitas riil & turunan
    for s in pk:
        cap = s.teu_capacity or math.floor(p.teu_capacity_dwt_ratio * s.dwt_t / p.teu_nominal_weight_t)
        assert cap == by_id[s.id]["payload"], s.name


def test_berth_loa_rule_keeps_k15_plan(case):
    """Aturan dermaga ≥ 85 % LOA tidak menggugurkan kapal pilihan K15 di pelabuhan asal/tujuan."""
    ships, ports, routes = case.by_id("ships"), case.by_id("ports"), case.by_id("routes")
    flows = case.by_id("flows")
    for fid, sid in case.plans[0].ship_by_flow.items():
        s = ships[sid]
        port = next(ports[n] for lg in routes[flows[fid].route_id].legs for n in (lg.origin, lg.destination)
                    if n in ports)
        if port.longest_berth_m is not None:
            assert port.longest_berth_m >= case.params.berth_loa_min_ratio * s.loa_m, (fid, s.name, port.name)


def test_decisions_applied(case):
    """Keputusan SPEC §11/§13 tercermin di data."""
    p = case.params
    assert (p.me_fuel, p.ae_fuel) == ("HSD", "HSD")  # A6
    assert p.ballast_speed_ratio == 1.0  # A5
    assert (p.payload_dwt_ratio, p.teu_weight_dwt_ratio) == (0.85, 0.9)  # A8
    assert all(pt.productivity.mode in ("total", "per_equipment") for pt in case.ports)  # A3
    assert all(s.ballast_speed_kn is None for s in case.ships)  # tidak membawa 130 % Vs
    assert "lct" in case.compatibility["GC"]  # §13 no.7
    assert case.kek_site.port_charges == "none"


# ---------------------------------------------------------------- asal-usul angka


def _walk(obj, path="case"):
    if isinstance(obj, BaseModel):
        yield path, obj
        for name in type(obj).model_fields:
            yield from _walk(getattr(obj, name), f"{path}.{name}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            yield from _walk(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, x in obj.items():
            yield from _walk(x, f"{path}[{k}]")


def test_every_number_has_a_source(case):
    """DoD Tahap 1: setiap angka input menunjuk ke sel Excel, catatan, atau keputusan."""
    missing = []
    for path, m in _walk(case):
        refs = getattr(m, "refs", None)
        if refs is None:
            continue
        for name in type(m).model_fields:
            v = getattr(m, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if name == "schema_version":
                continue
            if name not in refs:
                missing.append(f"{path}.{name}")
    assert not missing, "angka tanpa refs:\n" + "\n".join(missing)


# ---------------------------------------------------------------- golden


def test_golden_shape(golden, case):
    assert set(golden["flow_order"]) == {f.id for f in case.flows}
    for fid, fl in golden["flows"].items():
        for key, s in fl["series"].items():
            assert len(s["values"]) == 20, (fid, key)
            assert set(s["affected_by"]) <= AUDIT_IDS, (fid, key)
    # contoh yang sudah diverifikasi manual di blueprint: AETOS, Badas, tahun-1
    s = golden["flows"]["in.damai"]["series"]
    assert s["shipping_cost_rp"]["values"][0] == pytest.approx(734_309_498_915, rel=1e-9)
    assert s["freq_required"]["values"][0] == 92 and s["ships"]["values"][0] == 2


def test_golden_demand_starts_with_case(golden, case):
    """Tahun mulai di golden konsisten dengan data kasus (dasar test Tahap 4)."""
    flows = case.by_id("flows")
    for fid, fl in golden["flows"].items():
        f = flows[fid]
        start = (f.volume.start_year if f.volume.mode == "independent"
                 else flows[f.volume.basis_flow_id].volume.start_year)
        vals = fl["series"]["demand"]["values"]
        first = next(i for i, v in enumerate(vals) if v and not math.isclose(v, 0))
        assert first + 1 == start, fid


# ---------------------------------------------------------------- validasi


def _raw():
    return json.loads(CASE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("mutate, expected", [
    (lambda d: d["flows"][0].update(route_id="rt.tidak_ada"), "rute 'rt.tidak_ada' tidak dikenal"),
    (lambda d: d["ships"].append(dict(d["ships"][0])), "id ganda"),
    (lambda d: d["flows"][0].update(cargo_form="XX"), "bentuk muatan 'XX' tidak dikenal"),
    (lambda d: d["compatibility"].update(CC=["lct"]), "tidak ada kandidat kapal yang kompatibel"),
    (lambda d: d["flows"][1]["volume"].update(basis_flow_id="out.fantasi"), "flow acuan harus bervolume independen"),
    (lambda d: d["kek_site"]["bathymetry"].reverse(), "jarak harus naik"),
    (lambda d: d["plans"][0]["ship_by_flow"].update({"in.damai": "ship.x"}), "kapal 'ship.x' tidak dikenal"),
    (lambda d: d["params"].update(me_fuel="LNG"), "BBM 'LNG'"),
])
def test_validation_catches_errors(mutate, expected):
    d = _raw()
    mutate(d)
    with pytest.raises(ValueError, match=expected):
        Case.model_validate(d)


def test_numeric_bounds():
    d = _raw()
    d["params"]["bor_max"] = 1.4
    with pytest.raises(ValueError):
        Case.model_validate(d)


# ---------------------------------------------------------------- schema


def test_schema_file_up_to_date():
    """cases/case.schema.json harus sama dengan model (jalankan tools/export_schema.py bila gagal)."""
    current = json.dumps(case_json_schema(), ensure_ascii=False, indent=2)
    assert SCHEMA_PATH.read_text(encoding="utf-8") == current
