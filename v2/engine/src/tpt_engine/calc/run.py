"""Orkestrasi kalkulasi per modul. Hasil berkunci id variabel registry (SPEC §9.3)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..domain.case import Case, teu_forms
from . import cargo, demand, vessel

Module = Literal["demand"]
MODULES: tuple[str, ...] = ("demand",)

#: modul → id variabel registry yang dihitungnya (dites terhadap registry)
COMPUTES: dict[str, tuple[str, ...]] = {
    "demand": ("demand.base", "demand.ratio", "vessel.teu_cap", "cargo.netmax", "cargo.box_per_teu",
               "cargo.ton_per_teu", "cargo.demand_unit"),
}

Value = float | list[float]


class CalcResult(BaseModel):
    modules: list[str]
    plan_id: str | None = Field(description="rencana (kapal per flow) yang dipakai untuk variabel bergantung kapal")
    ship_by_flow: dict[str, str] = Field(description="kapal terpilih per flow yang dipakai")
    computed: list[str] = Field(description="id variabel registry yang dihitung engine pada respons ini")
    values: dict[str, dict[str, Value]] = Field(
        description="id variabel -> kunci konteks (flow id / ship id) -> angka atau seri tahunan (indeks 0 = tahun ke-1)")
    units: dict[str, Literal["ton", "TEU"]] = Field({}, description="satuan cargo.demand_unit per flow")
    warnings: list[str] = []


def resolve_ships(case: Case, plan_id: str | None, override: dict[str, str] | None) -> tuple[str | None, dict[str, str]]:
    """Kapal per flow: plan terpilih (default plan pertama kasus) + override."""
    plan = None
    if plan_id is not None:
        plan = next((p for p in case.plans if p.id == plan_id), None)
        if plan is None:
            raise ValueError(f"plan '{plan_id}' tidak ada di kasus")
    elif case.plans:
        plan = case.plans[0]
    ships = dict(plan.ship_by_flow) if plan else {}
    ships.update(override or {})
    return (plan.id if plan else None), ships


def calculate(case: Case, modules: list[str] | None = None, plan_id: str | None = None,
              ship_by_flow: dict[str, str] | None = None) -> CalcResult:
    mods = list(modules or MODULES)
    for m in mods:
        if m not in MODULES:
            raise ValueError(f"modul '{m}' belum diimplementasikan (tersedia: {', '.join(MODULES)})")
    pid, ships_by_flow = resolve_ships(case, plan_id, ship_by_flow)
    values: dict[str, dict[str, Value]] = {}
    units: dict[str, Literal["ton", "TEU"]] = {}
    warnings: list[str] = []

    if "demand" in mods:
        series = demand.project_flows(case)
        values["demand.base"] = {f.id: series[f.id] for f in case.flows if f.volume.mode == "independent"}
        values["demand.ratio"] = {f.id: series[f.id] for f in case.flows if f.volume.mode == "ratio"}
        teu = teu_forms(case)
        ships = {s.id: s for s in case.ships}
        cmdty = {c.id: c for c in case.commodities}
        cont = case.params.container
        teu_cap: dict[str, Value] = {}
        nmax: dict[str, Value] = {}
        nbox: dict[str, Value] = {}
        tpt: dict[str, Value] = {}
        dunit: dict[str, Value] = {}
        for f in case.flows:
            ship_unit: Literal["ton", "TEU"] = "TEU" if f.cargo_form in teu else "ton"
            units[f.id] = ship_unit
            t: float | None = None
            if ship_unit == "TEU":
                sid = ships_by_flow.get(f.id)
                ship = ships.get(sid) if sid else None
                if ship is None:
                    warnings.append(f"{f.id}: belum ada kapal terpilih; NetMax memakai payload kontainer saja")
                    nm = cont.max_net_t
                else:
                    cap = vessel.teu_capacity(ship, case.params)
                    teu_cap[ship.id] = float(cap)
                    nm = cargo.net_max(cont, case.params, ship.dwt_t, cap)
                if nm <= 0:
                    warnings.append(f"{f.id}: NetMax ≤ 0 untuk kapal {sid}; kapal tidak bisa membawa muatan per TEU")
                nmax[f.id] = nm
                c = cmdty[f.commodity_id]
                if c.packaging is not None:
                    nbox[f.id] = float(cargo.box_per_teu(cont, c.packaging, nm))
                t = cargo.ton_per_teu(cont, c, nm)
                tpt[f.id] = t
                if f.unit == "ton" and t <= 0:
                    warnings.append(f"{f.id}: tonPerTEU = 0; D_TEU tidak bisa dihitung")
                    continue
            dunit[f.id] = cargo.demand_unit(series[f.id], f.unit, ship_unit, t)
        values.update({"vessel.teu_cap": teu_cap, "cargo.netmax": nmax, "cargo.box_per_teu": nbox,
                       "cargo.ton_per_teu": tpt, "cargo.demand_unit": dunit})

    computed = [v for m in mods for v in COMPUTES[m]]
    return CalcResult(modules=mods, plan_id=pid, ship_by_flow=ships_by_flow, computed=computed, values=values,
                      units=units, warnings=warnings)
