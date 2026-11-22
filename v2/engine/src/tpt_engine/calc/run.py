"""Orkestrasi kalkulasi per modul. Hasil berkunci id variabel registry (SPEC §9.3).

Modul: `demand` (§5.1) → `voyage` (§5.2–5.3, butuh demand). Variabel bergantung kapal/alat memakai rencana kasus
(default plan pertama) + override dari UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..domain.case import CargoFlow, Case, Ship, teu_forms
from . import cargo, demand, vessel, voyage

Module = Literal["demand", "voyage"]
MODULES: tuple[str, ...] = ("demand", "voyage")
REQUIRES: dict[str, tuple[str, ...]] = {"voyage": ("demand",)}

#: modul → id variabel registry yang dihitungnya (dites terhadap registry)
COMPUTES: dict[str, tuple[str, ...]] = {
    "demand": ("demand.base", "demand.ratio", "vessel.teu_cap", "cargo.netmax", "cargo.box_per_teu",
               "cargo.ton_per_teu", "cargo.demand_unit"),
    "voyage": ("vessel.payload", "vessel.compatible", "vessel.feasible", "vessel.neq", "vessel.ballast_speed",
               "voyage.freq", "voyage.q", "voyage.t_port_kek", "voyage.t_port_ext", "voyage.t_port", "voyage.t_fix",
               "voyage.t_sea", "voyage.rtd", "voyage.f_max", "voyage.n_ship", "voyage.utilization",
               "voyage.consumption"),
}

Value = float | list[float]
ShipUnit = Literal["ton", "TEU"]


class FeasCell(BaseModel):
    ok: bool
    reasons: list[str] = Field([], description="alasan gugur")
    notes: list[str] = Field([], description="catatan data yang tidak menggugurkan (mis. panjang dermaga kosong)")


class CalcResult(BaseModel):
    modules: list[str]
    plan_id: str | None = Field(description="rencana (kapal per flow, alat per terminal) yang dipakai")
    ship_by_flow: dict[str, str] = Field(description="kapal terpilih per flow yang dipakai")
    equipment_by_terminal: dict[str, str] = Field({}, description="alat terpilih per terminal KEK yang dipakai")
    computed: list[str] = Field(description="id variabel registry yang dihitung engine pada respons ini")
    values: dict[str, dict[str, Value]] = Field(
        description="id variabel -> kunci konteks (flow id / ship id) -> angka atau seri tahunan (indeks 0 = tahun ke-1)")
    units: dict[str, ShipUnit] = Field({}, description="satuan kapal per flow (cargo.demand_unit, payload, q)")
    reasons: dict[str, list[str]] = Field({}, description="alasan kapal terpilih gugur per flow (vessel.feasible = 0)")
    feasibility: dict[str, dict[str, FeasCell]] = Field(
        {}, description="modul voyage: kelayakan setiap kapal kompatibel per flow (flow id -> ship id -> sel)")
    warnings: list[str] = []


class CandidateRow(BaseModel):
    ship_id: str
    compatible: bool
    feasible: bool
    reasons: list[str] = Field([], description="alasan gugur")
    notes: list[str] = Field([], description="catatan data yang tidak menggugurkan")
    selected: bool = False
    values: dict[str, Value] = Field({}, description="id variabel -> angka/seri untuk flow ini dengan kapal ini")
    error: str | None = None


class CompareResult(BaseModel):
    flow_id: str
    unit: ShipUnit
    equipment_id: str | None
    rows: list[CandidateRow] = Field(description="semua kapal kasus; rantai dihitung untuk yang kompatibel")


# ─── pemilihan rencana ──────────────────────────────────────────────────────────────────────────
def resolve_plan(case: Case, plan_id: str | None, ship_override: dict[str, str] | None,
                 equip_override: dict[str, str] | None = None) -> tuple[str | None, dict[str, str], dict[str, str]]:
    """Kapal per flow & alat per terminal: plan terpilih (default plan pertama kasus) + override."""
    plan = None
    if plan_id is not None:
        plan = next((p for p in case.plans if p.id == plan_id), None)
        if plan is None:
            raise ValueError(f"plan '{plan_id}' tidak ada di kasus")
    elif case.plans:
        plan = case.plans[0]
    ships = dict(plan.ship_by_flow) if plan else {}
    ships.update(ship_override or {})
    equip = dict(plan.equipment_by_terminal) if plan else {}
    equip.update(equip_override or {})
    return (plan.id if plan else None), ships, equip


def resolve_ships(case: Case, plan_id: str | None, override: dict[str, str] | None) -> tuple[str | None, dict[str, str]]:
    pid, ships, _ = resolve_plan(case, plan_id, override)
    return pid, ships


# ─── rantai per flow ────────────────────────────────────────────────────────────────────────────
def _demand_side(case: Case, flow: CargoFlow, ship: Ship | None, series: list[float], unit: ShipUnit,
                 values: dict[str, dict[str, Value]], warnings: list[str]) -> tuple[float | None, list[float] | None]:
    """§5.1 bagian bergantung kapal: NetMax, nBox, tonPerTEU, D dalam satuan kapal."""
    t: float | None = None
    if unit == "TEU":
        cont = case.params.container
        if ship is None:
            warnings.append(f"{flow.id}: belum ada kapal terpilih; NetMax memakai payload kontainer saja")
            nm = cont.max_net_t
        else:
            cap = vessel.teu_capacity(ship, case.params)
            values.setdefault("vessel.teu_cap", {})[ship.id] = float(cap)
            nm = cargo.net_max(cont, case.params, ship.dwt_t, cap)
        if nm <= 0:
            warnings.append(f"{flow.id}: NetMax ≤ 0 untuk kapal {ship.id if ship else '-'}; kapal tidak bisa membawa muatan per TEU")
        values.setdefault("cargo.netmax", {})[flow.id] = nm
        com = next(c for c in case.commodities if c.id == flow.commodity_id)
        if com.packaging is not None:
            values.setdefault("cargo.box_per_teu", {})[flow.id] = float(cargo.box_per_teu(cont, com.packaging, nm))
        t = cargo.ton_per_teu(cont, com, nm)
        values.setdefault("cargo.ton_per_teu", {})[flow.id] = t
        if flow.unit == "ton" and t <= 0:
            warnings.append(f"{flow.id}: tonPerTEU = 0; D_TEU tidak bisa dihitung")
            return t, None
    d = cargo.demand_unit(series, flow.unit, unit, t)
    values.setdefault("cargo.demand_unit", {})[flow.id] = d
    return t, d


def voyage_chain(case: Case, flow: CargoFlow, ship: Ship, equipment_id: str | None, d_unit: list[float],
                 unit: ShipUnit, tpt: float | None) -> dict[str, Value]:
    """§5.2–5.3 untuk satu flow dengan satu kapal: nilai berkunci id registry. Tahun tanpa pelayaran = 0."""
    p = case.params
    term = voyage.terminal_of(case, flow)
    if not equipment_id:
        raise voyage.VoyageError(f"{flow.id}: belum ada alat terpilih untuk terminal {term.id}")
    equip = next((e for e in case.equipment if e.id == equipment_id), None)
    if equip is None:
        raise voyage.VoyageError(f"{flow.id}: alat '{equipment_id}' tidak ada di kasus")
    port = voyage.external_port(case, flow)
    route = next(r for r in case.routes if r.id == flow.route_id)
    feas = vessel.feasibility(case, flow, ship)
    pay = vessel.payload(ship, p, unit)
    neq = vessel.n_equipment(ship, case.equipment_rules, term.id)
    vb = vessel.ballast_speed(ship, p)
    r_kek = voyage.kek_rate(equip, flow, unit, tpt, p)
    r_ext = voyage.port_rate(port.productivity, unit, tpt, p)
    tfix = voyage.t_fix(p)
    tsea = voyage.t_sea(route, ship.speed_kn, vb)

    keys = ("voyage.freq", "voyage.q", "voyage.t_port_kek", "voyage.t_port_ext", "voyage.t_port", "voyage.t_sea",
            "voyage.rtd", "voyage.f_max", "voyage.n_ship", "voyage.utilization", "voyage.consumption")
    s: dict[str, list[float]] = {k: [] for k in keys}
    for d in d_unit:
        f = voyage.freq(d, pay)
        if f == 0:
            for k in keys:
                s[k].append(0.0)
            continue
        q = voyage.cargo_per_call(d, f, pay, p.cargo_per_call_mode)
        tk = voyage.t_port_kek(q, r_kek, neq)
        te = voyage.t_port_ext(q, r_ext)
        rt = voyage.rtd(tsea, voyage.t_port(tk, te), tfix)
        fm = voyage.f_max(p.commission_days, rt)
        ns = voyage.n_ship(f, fm)
        for k, v in (("voyage.freq", f), ("voyage.q", q), ("voyage.t_port_kek", tk), ("voyage.t_port_ext", te),
                     ("voyage.t_port", tk + te), ("voyage.t_sea", tsea), ("voyage.rtd", rt), ("voyage.f_max", fm),
                     ("voyage.n_ship", ns), ("voyage.utilization", voyage.utilization(f, ns, fm)),
                     ("voyage.consumption", voyage.consumption_days(q, d))):
            s[k].append(float(v))
    out: dict[str, Value] = {
        "vessel.payload": pay, "vessel.compatible": 1.0 if vessel.compatible(case, flow, ship) else 0.0,
        "vessel.feasible": 1.0 if feas.ok else 0.0, "vessel.neq": float(neq), "vessel.ballast_speed": vb,
        "voyage.t_fix": tfix,
    }
    out.update(s)
    return out


def _flow_unit(case: Case, flow: CargoFlow) -> ShipUnit:
    return "TEU" if flow.cargo_form in teu_forms(case) else "ton"


def _expand(mods: list[str]) -> list[str]:
    for m in mods:
        if m not in MODULES:
            raise ValueError(f"modul '{m}' belum diimplementasikan (tersedia: {', '.join(MODULES)})")
    need = set(mods)
    for m in mods:
        need.update(REQUIRES.get(m, ()))
    return [m for m in MODULES if m in need]


def calculate(case: Case, modules: list[str] | None = None, plan_id: str | None = None,
              ship_by_flow: dict[str, str] | None = None,
              equipment_by_terminal: dict[str, str] | None = None) -> CalcResult:
    mods = _expand(list(modules or MODULES))
    pid, ships_by_flow, equip_by_term = resolve_plan(case, plan_id, ship_by_flow, equipment_by_terminal)
    values: dict[str, dict[str, Value]] = {}
    units: dict[str, ShipUnit] = {}
    reasons: dict[str, list[str]] = {}
    warnings: list[str] = []
    ships = {s.id: s for s in case.ships}

    series = demand.project_flows(case)
    values["demand.base"] = {f.id: series[f.id] for f in case.flows if f.volume.mode == "independent"}
    values["demand.ratio"] = {f.id: series[f.id] for f in case.flows if f.volume.mode == "ratio"}
    for key in ("vessel.teu_cap", "cargo.netmax", "cargo.box_per_teu", "cargo.ton_per_teu", "cargo.demand_unit"):
        values[key] = {}
    for f in case.flows:
        unit = _flow_unit(case, f)
        units[f.id] = unit
        sid = ships_by_flow.get(f.id)
        ship = ships.get(sid) if sid else None
        if sid and ship is None:
            warnings.append(f"{f.id}: kapal '{sid}' tidak ada di kasus")
        tpt, d_unit = _demand_side(case, f, ship, series[f.id], unit, values, warnings)
        if "voyage" not in mods or d_unit is None:
            continue
        if ship is None:
            warnings.append(f"{f.id}: belum ada kapal terpilih; rantai pelayaran tidak dihitung")
            continue
        try:
            term = voyage.terminal_of(case, f)
            chain = voyage_chain(case, f, ship, equip_by_term.get(term.id), d_unit, unit, tpt)
        except voyage.VoyageError as e:
            warnings.append(str(e))
            continue
        for k, v in chain.items():
            key = ship.id if k == "vessel.ballast_speed" else f.id
            values.setdefault(k, {})[key] = v
        feas = vessel.feasibility(case, f, ship)
        if not feas.ok:
            reasons[f.id] = feas.reasons
            warnings.append(f"{f.id}: kapal {ship.name} gugur — {'; '.join(feas.reasons)}")

    matrix: dict[str, dict[str, FeasCell]] = {}
    if "voyage" in mods:
        for f in case.flows:
            matrix[f.id] = {}
            for sh in case.ships:
                if vessel.compatible(case, f, sh):
                    fe = vessel.feasibility(case, f, sh)
                    matrix[f.id][sh.id] = FeasCell(ok=fe.ok, reasons=fe.reasons, notes=fe.notes)

    computed = [v for m in mods for v in COMPUTES[m]]
    return CalcResult(modules=mods, plan_id=pid, ship_by_flow=ships_by_flow, equipment_by_terminal=equip_by_term,
                      computed=computed, values=values, units=units, reasons=reasons, feasibility=matrix,
                      warnings=warnings)


def compare(case: Case, flow_id: str, plan_id: str | None = None, ship_by_flow: dict[str, str] | None = None,
            equipment_by_terminal: dict[str, str] | None = None) -> CompareResult:
    """Bandingkan semua kapal kasus untuk satu flow (layar 4 & 6): kelayakan + rantai §5.1–5.3 per kapal."""
    flow = next((f for f in case.flows if f.id == flow_id), None)
    if flow is None:
        raise ValueError(f"flow '{flow_id}' tidak ada di kasus")
    _, ships_by_flow, equip_by_term = resolve_plan(case, plan_id, ship_by_flow, equipment_by_terminal)
    unit = _flow_unit(case, flow)
    series = demand.project_flows(case)[flow.id]
    term = voyage.terminal_of(case, flow)
    eq_id = equip_by_term.get(term.id)
    rows: list[CandidateRow] = []
    for ship in case.ships:
        comp = vessel.compatible(case, flow, ship)
        feas = vessel.feasibility(case, flow, ship)
        row = CandidateRow(ship_id=ship.id, compatible=comp, feasible=feas.ok, reasons=feas.reasons, notes=feas.notes,
                           selected=ships_by_flow.get(flow.id) == ship.id)
        if comp:
            vals: dict[str, dict[str, Value]] = {}
            warn: list[str] = []
            tpt, d_unit = _demand_side(case, flow, ship, series, unit, vals, warn)
            row.values = {k: v[flow.id] for k, v in vals.items() if flow.id in v}
            if d_unit is None:
                row.error = "; ".join(warn) or "D_TEU tidak bisa dihitung"
            else:
                try:
                    row.values.update(voyage_chain(case, flow, ship, eq_id, d_unit, unit, tpt))
                except voyage.VoyageError as e:
                    row.error = str(e)
        rows.append(row)
    return CompareResult(flow_id=flow.id, unit=unit, equipment_id=eq_id, rows=rows)
