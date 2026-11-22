"""§5.3 Operasi pelayaran — sheet `Model` baris 28–235 (versi terkoreksi A1, A2, A3, A5, A10).

Semua fungsi per call / per tahun dalam satuan kapal (ton atau TEU). Excel menyimpan port time sebagai hari/tahun
(`Model!M68`, `M82`); engine menyimpan hari/call (× F = hari/tahun).
"""

from __future__ import annotations

import math

from ..domain.case import (
    KEK,
    CargoFlow,
    Case,
    Equipment,
    ExternalPort,
    GlobalParams,
    KekTerminal,
    PortProductivity,
    Route,
)
from .cargo import ceil_, floor_


class VoyageError(ValueError):
    """Data kasus tidak cukup untuk menghitung rantai pelayaran flow (alat/pelabuhan/satuan)."""


def terminal_of(case: Case, flow: CargoFlow) -> KekTerminal:
    """Terminal KEK yang melayani bentuk muatan flow."""
    for t in case.kek_site.terminals:
        if flow.cargo_form in t.cargo_forms:
            return t
    raise VoyageError(f"{flow.id}: tidak ada terminal KEK untuk bentuk muatan {flow.cargo_form}")


def external_port(case: Case, flow: CargoFlow) -> ExternalPort:
    """Pelabuhan asal (inbound) / tujuan (outbound): ujung non-KEK leg bermuatan yang menyinggung KEK."""
    route = next(r for r in case.routes if r.id == flow.route_id)
    ports = {p.id: p for p in case.ports}
    for leg in route.legs:
        if not leg.laden:
            continue
        if flow.direction == "inbound" and leg.destination == KEK and leg.origin != KEK:
            return ports[leg.origin]
        if flow.direction == "outbound" and leg.origin == KEK and leg.destination != KEK:
            return ports[leg.destination]
    other = [leg.origin for leg in route.legs if leg.origin != KEK]
    if not other:
        raise VoyageError(f"{flow.id}: rute {route.id} tidak menyinggahi pelabuhan eksternal")
    return ports[other[0]]


def teu_per_box(params: GlobalParams) -> float:
    """TEU per box petikemas: porsi box 20' (1 TEU) dan 40' (2 TEU). K15: semua 20' → 1."""
    s = params.container.share_20ft
    return s + 2.0 * (1.0 - s)


def rate_to_ship_unit(value: float, unit: str, ship_unit: str, tpt: float | None, params: GlobalParams) -> float:
    """Ubah laju bongkar muat ke satuan kapal per jam (t/h atau TEU/h)."""
    if unit == "t/h":
        if ship_unit == "ton":
            return value
        if not tpt:
            raise VoyageError("laju t/h untuk muatan TEU butuh tonPerTEU")
        return value / tpt
    teu_h = value * teu_per_box(params) if unit == "box/h" else value  # box/h atau TEU/h
    if ship_unit == "TEU":
        return teu_h
    if not tpt:
        raise VoyageError(f"laju {unit} untuk muatan ton butuh tonPerTEU")
    return teu_h * tpt


def kek_rate(equipment: Equipment, flow: CargoFlow, ship_unit: str, tpt: float | None, params: GlobalParams) -> float:
    """Produktivitas satu alat KEK untuk bentuk & arah muatan flow (bongkar = inbound, muat = outbound)."""
    pr = equipment.productivity.get(flow.cargo_form)
    if pr is None:
        raise VoyageError(f"{flow.id}: alat {equipment.name} tidak punya produktivitas {flow.cargo_form}")
    v = pr.unload if flow.direction == "inbound" else pr.load
    return rate_to_ship_unit(v, pr.unit, ship_unit, tpt, params)


def port_rate(prod: PortProductivity, ship_unit: str, tpt: float | None, params: GlobalParams) -> float:
    """A3: produktivitas total per kapal di pelabuhan eksternal — angka total, atau per alat × jumlah alat."""
    v = prod.value * (prod.equipment_count or 1) if prod.mode == "per_equipment" else prod.value
    return rate_to_ship_unit(v, prod.unit, ship_unit, tpt, params)


def freq(demand: float, payload: float) -> int:
    """`voyage.freq` — F_req = ⌈D / payload⌉ (0 bila tidak ada demand)."""
    if demand <= 0:
        return 0
    return ceil_(demand / payload)


def cargo_per_call(demand: float, f: int, payload: float, mode: str) -> float:
    """`voyage.q` — interval: D / F (K15); full_load: payload."""
    if f == 0:
        return 0.0
    return payload if mode == "full_load" else demand / f


def t_port_kek(q: float, rate_per_equipment: float, n_eq: int) -> float:
    """`voyage.t_port_kek` — q / (prod_e,form · nEq) / 24 [hari/call]. A2: dibagi jumlah alat untuk semua bentuk;
    A10: nEq dari rentang LOA kapal."""
    return q / (rate_per_equipment * n_eq) / 24.0


def t_port_ext(q: float, rate_total: float) -> float:
    """`voyage.t_port_ext` — q / prodTotal_port / 24 [hari/call] (A3: tanpa jumlah alat KEK)."""
    return q / rate_total / 24.0


def t_port(t_kek: float, t_ext: float) -> float:
    """`voyage.t_port` — tPortKEK + tPortExt [hari/call] (tanpa tFix)."""
    return t_kek + t_ext


def t_fix(params: GlobalParams) -> float:
    """`voyage.t_fix` — (AT + WT + IT) / 24 [hari/call]."""
    return (params.at_hours + params.wt_hours + params.it_hours) / 24.0


def t_sea(route: Route, vs: float, vb: float) -> float:
    """`voyage.t_sea` — Σ jarak leg / (Vs bila bermuatan, V_ballast bila kosong) / 24 [hari/call]."""
    return sum(leg.distance_nm / (vs if leg.laden else vb) for leg in route.legs) / 24.0


def rtd(t_sea_d: float, t_port_d: float, t_fix_d: float) -> float:
    """`voyage.rtd` — RTD = tSea + tPortKEK + tPortExt + tFix [hari]."""
    return t_sea_d + t_port_d + t_fix_d


def f_max(commission_days: float, rtd_d: float) -> int:
    """`voyage.f_max` — ⌊CD / RTD⌋ (A1: Excel ROUNDUP)."""
    return floor_(commission_days / rtd_d) if rtd_d > 0 else 0


def n_ship(f: int, fmax: int) -> int:
    """`voyage.n_ship` — ⌈F / F_max⌉; 0 bila tidak ada pelayaran."""
    if f == 0:
        return 0
    if fmax <= 0:
        raise VoyageError("RTD melebihi hari operasi: satu kapal tidak sanggup satu voyage per tahun")
    return math.ceil(f / fmax)


def utilization(f: int, ns: int, fmax: int) -> float:
    """`voyage.utilization` — F / (N_ship · F_max)."""
    return f / (ns * fmax) if ns and fmax else 0.0


def consumption_days(q: float, demand: float) -> float:
    """`voyage.consumption` — q / (D / 365): hari stok yang dibawa satu pengapalan."""
    return q / (demand / 365.0) if demand > 0 else 0.0
