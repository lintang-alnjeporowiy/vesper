"""Orkestrasi kalkulasi per modul. Hasil berkunci id variabel registry (SPEC §9.3).

Modul: `demand` (§5.1) → `voyage` (§5.2–5.3) → `shipcost` (§5.4) · `terminal` (§5.5); modul menarik modul yang
dibutuhkannya. Variabel bergantung kapal/alat memakai rencana kasus
(default plan pertama) + override dari UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..domain.case import CargoFlow, Case, Ship, teu_forms
from . import cargo, demand, shipcost, terminal, vessel, voyage

Module = Literal["demand", "voyage", "shipcost", "terminal"]
MODULES: tuple[str, ...] = ("demand", "voyage", "shipcost", "terminal")
REQUIRES: dict[str, tuple[str, ...]] = {"voyage": ("demand",), "shipcost": ("demand", "voyage"),
                                        "terminal": ("demand", "voyage")}

#: modul → id variabel registry yang dihitungnya (dites terhadap registry)
COMPUTES: dict[str, tuple[str, ...]] = {
    "demand": ("demand.base", "demand.ratio", "vessel.teu_cap", "cargo.netmax", "cargo.box_per_teu",
               "cargo.ton_per_teu", "cargo.demand_unit"),
    "voyage": ("vessel.payload", "vessel.compatible", "vessel.feasible", "vessel.neq", "vessel.ballast_speed",
               "voyage.freq", "voyage.q", "voyage.t_port_kek", "voyage.t_port_ext", "voyage.t_port", "voyage.t_fix",
               "voyage.t_sea", "voyage.rtd", "voyage.f_max", "voyage.n_ship", "voyage.utilization",
               "voyage.consumption"),
    "shipcost": ("vessel.ae_kw", "vessel.sfoc_me", "vessel.sfoc_ae", "shipcost.fuel_me_l", "shipcost.fuel_ae_l",
                 "shipcost.fuel_me", "shipcost.fuel_ae", "shipcost.voyage", "shipcost.tch_rate", "shipcost.tch",
                 "shipcost.port_call", "shipcost.port", "shipcost.total", "shipcost.unit"),
    "terminal": ("terminal.ship_days", "terminal.berth_days", "terminal.n_berth", "terminal.bor",
                 "terminal.berth_length", "terminal.n_equip"),
}
#: variabel berkunci id terminal KEK (bukan flow)
TERMINAL_KEYED = {"terminal.n_berth", "terminal.bor", "terminal.berth_length", "terminal.n_equip"}
PORT_PARTS = ("labuh", "pandu", "tambat", "tunda", "bm")

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
    port_breakdown: dict[str, dict[str, list[float]]] = Field(
        {}, description="modul shipcost: biaya pelabuhan per call per komponen (labuh, pandu, tambat, tunda, bm; "
                        "ext + KEK) per flow, seri tahunan Rp/call")
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


def cost_chain(case: Case, flow: CargoFlow, ship: Ship, ch: dict[str, Value], unit: ShipUnit,
               d_flow: list[float]) -> tuple[dict[str, Value], dict[str, list[float]]]:
    """§5.4 untuk satu flow dengan satu kapal, dari hasil `voyage_chain` (`ch`). Mengembalikan nilai berkunci id
    registry dan rincian biaya pelabuhan per call per komponen. `d_flow` = demand dalam satuan flow (A7)."""
    p = case.params
    ae = shipcost.ae_kw(ship, p)
    s_me, s_ae = shipcost.sfoc(ship, p)
    f_me, f_ae = shipcost.fuel_of(p, p.me_fuel), shipcost.fuel_of(p, p.ae_fuel)
    stype = next(t for t in case.ship_types if t.code == ship.ship_type)
    size = float(vessel.teu_capacity(ship, p)) if stype.size_basis == "teu" else ship.dwt_t
    rate = shipcost.tch_rate(stype, size)
    port = voyage.external_port(case, flow)
    kek = case.kek_site
    book = case.tariffs

    keys = ("shipcost.fuel_me_l", "shipcost.fuel_ae_l", "shipcost.fuel_me", "shipcost.fuel_ae", "shipcost.voyage",
            "shipcost.tch", "shipcost.port_call", "shipcost.port", "shipcost.total", "shipcost.unit")
    s: dict[str, list[float]] = {k: [] for k in keys}
    parts: dict[str, list[float]] = {k: [] for k in PORT_PARTS}

    def col(k: str) -> list[float]:
        v = ch[k]
        assert isinstance(v, list)
        return v

    freq, q, tk, te, tsea, ns = (col(k) for k in ("voyage.freq", "voyage.q", "voyage.t_port_kek", "voyage.t_port_ext",
                                                    "voyage.t_sea", "voyage.n_ship"))
    tfix = ch["voyage.t_fix"]
    assert isinstance(tfix, float)
    for y, f in enumerate(freq):
        if f == 0:
            for k in keys:
                s[k].append(0.0)
            for k in PORT_PARTS:
                parts[k].append(0.0)
            continue
        t_call = tk[y] + te[y] + tfix
        me_l = shipcost.fuel_litres(ship.me_kw, s_me, p.mcr, tsea[y], t_call, p.fuel_share_me_sea, p.fuel_share_me_port,
                                    f, f_me.density_kg_m3)
        ae_l = shipcost.fuel_litres(ae, s_ae, p.mcr, tsea[y], t_call, p.fuel_share_ae_sea, p.fuel_share_ae_port, f,
                                    f_ae.density_kg_m3)
        me_rp, ae_rp = shipcost.fuel_cost(me_l, f_me), shipcost.fuel_cost(ae_l, f_ae)
        tch = shipcost.tch_cost(rate, p.usd_rate, p.commission_days, ns[y])
        call = shipcost.ext_port_call(book, port, ship.gt, te[y], q[y], unit, p.usd_rate)
        if kek.port_charges == "tariff" and kek.tariff_class:
            k_call = shipcost.port_call_cost(book, kek.tariff_class, False, "beton", ship.gt, tk[y], q[y], unit,
                                             p.usd_rate)
            for k in PORT_PARTS:
                setattr(call, k, getattr(call, k) + getattr(k_call, k))
        port_yr = call.total * f
        total = me_rp + ae_rp + tch + port_yr
        for k, v in (("shipcost.fuel_me_l", me_l), ("shipcost.fuel_ae_l", ae_l), ("shipcost.fuel_me", me_rp),
                     ("shipcost.fuel_ae", ae_rp), ("shipcost.voyage", me_rp + ae_rp), ("shipcost.tch", tch),
                     ("shipcost.port_call", call.total), ("shipcost.port", port_yr), ("shipcost.total", total),
                     ("shipcost.unit", shipcost.unit_cost(total, d_flow[y]))):
            s[k].append(float(v))
        for k in PORT_PARTS:
            parts[k].append(float(getattr(call, k)))
    out: dict[str, Value] = {"vessel.ae_kw": ae, "vessel.sfoc_me": s_me, "vessel.sfoc_ae": s_ae, "shipcost.tch_rate": rate}
    out.update(s)
    return out, parts


def terminal_chain(case: Case, chains: dict[str, tuple[Ship, dict[str, Value]]]) -> dict[str, dict[str, Value]]:
    """§5.5 dari hasil `voyage_chain` per flow (`chains`: flow id → (kapal, rantai)). Nilai per flow (ship-days,
    berth-days) dan per terminal (tambatan, BOR, panjang, alat)."""
    p = case.params
    it = p.it_hours / p.working_hours_per_day
    n_years = case.horizon.years
    out: dict[str, dict[str, Value]] = {k: {} for k in COMPUTES["terminal"]}
    flows = {f.id: f for f in case.flows}
    for term in case.kek_site.terminals:
        tot = [0.0] * n_years
        neq = [0.0] * n_years
        for fid, (ship, ch) in chains.items():
            if voyage.terminal_of(case, flows[fid]).id != term.id:
                continue
            freq, tk = ch["voyage.freq"], ch["voyage.t_port_kek"]
            assert isinstance(freq, list) and isinstance(tk, list)
            sd = [terminal.ship_days(f, t, it) for f, t in zip(freq, tk, strict=True)]
            bd = [float(terminal.berth_days(x, ship.loa_m, term)) for x in sd]
            out["terminal.ship_days"][fid] = sd
            out["terminal.berth_days"][fid] = bd
            n_eq = vessel.n_equipment(ship, case.equipment_rules, term.id)
            for y in range(n_years):
                tot[y] += bd[y]
                if freq[y]:
                    neq[y] = max(neq[y], n_eq)
        nb = terminal.n_berth(tot, p.bor_max, p.working_days_per_year)
        neq_c = terminal.never_decrease(neq)
        out["terminal.n_berth"][term.id] = nb
        out["terminal.bor"][term.id] = [terminal.bor(b, n, p.working_days_per_year) for b, n in zip(tot, nb, strict=True)]
        out["terminal.berth_length"][term.id] = [terminal.berth_length(n, term) for n in nb]
        out["terminal.n_equip"][term.id] = [terminal.n_equip(n, int(e)) for n, e in zip(nb, neq_c, strict=True)]
    return out


SHIP_KEYED = {"vessel.ballast_speed", "vessel.ae_kw", "vessel.sfoc_me", "vessel.sfoc_ae", "shipcost.tch_rate"}


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
    breakdown: dict[str, dict[str, list[float]]] = {}
    warnings: list[str] = []
    ships = {s.id: s for s in case.ships}
    chains: dict[str, tuple[Ship, dict[str, Value]]] = {}

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
        if "shipcost" in mods:
            try:
                costs, parts = cost_chain(case, f, ship, chain, unit, series[f.id])
            except shipcost.CostError as e:
                warnings.append(f"{f.id}: {e}")
            else:
                chain = {**chain, **costs}
                breakdown[f.id] = parts
        chains[f.id] = (ship, chain)
        for k, v in chain.items():
            key = ship.id if k in SHIP_KEYED else f.id
            values.setdefault(k, {})[key] = v
        feas = vessel.feasibility(case, f, ship)
        if not feas.ok:
            reasons[f.id] = feas.reasons
            warnings.append(f"{f.id}: kapal {ship.name} gugur — {'; '.join(feas.reasons)}")

    if "terminal" in mods:
        values.update(terminal_chain(case, chains))

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
                      port_breakdown=breakdown, warnings=warnings)


def compare(case: Case, flow_id: str, plan_id: str | None = None, ship_by_flow: dict[str, str] | None = None,
            equipment_by_terminal: dict[str, str] | None = None) -> CompareResult:
    """Bandingkan semua kapal kasus untuk satu flow (layar 4 & 6): kelayakan + rantai §5.1–5.4 per kapal."""
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
                    ch = voyage_chain(case, flow, ship, eq_id, d_unit, unit, tpt)
                    row.values.update(ch)
                    costs, _ = cost_chain(case, flow, ship, ch, unit, series)
                    row.values.update(costs)
                except (voyage.VoyageError, shipcost.CostError) as e:
                    row.error = str(e)
        rows.append(row)
    return CompareResult(flow_id=flow.id, unit=unit, equipment_id=eq_id, rows=rows)
