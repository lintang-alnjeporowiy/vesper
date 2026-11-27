"""Orkestrasi kalkulasi per modul. Hasil berkunci id variabel registry (SPEC §9.3).

Modul: `demand` (§5.1) → `voyage` (§5.2–5.3) → `shipcost` (§5.4) · `terminal` (§5.5) · `storage` (§5.6) ·
`waterside` (§5.7 + truk & pipa dermaga–lapangan, menarik `terminal`) → `invest` (§5.8, menarik terminal, storage,
waterside); modul menarik modul yang dibutuhkannya. Variabel bergantung kapal/alat memakai rencana kasus
(default plan pertama) + override dari UI.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..domain.case import CargoFlow, Case, Plan, Ship, teu_forms
from . import cargo, demand, invest, shipcost, storage, terminal, vessel, voyage, waterside

Module = Literal["demand", "voyage", "shipcost", "terminal", "storage", "waterside", "invest"]
MODULES: tuple[str, ...] = ("demand", "voyage", "shipcost", "terminal", "storage", "waterside", "invest")
REQUIRES: dict[str, tuple[str, ...]] = {"voyage": ("demand",), "shipcost": ("demand", "voyage"),
                                        "terminal": ("demand", "voyage"), "storage": ("demand", "voyage"),
                                        "waterside": ("demand", "voyage", "terminal"),
                                        "invest": ("demand", "voyage", "terminal", "storage", "waterside")}

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
    "storage": ("storage.dwell", "storage.throughput", "storage.cy", "storage.cy_slots", "storage.gc", "storage.bulk",
                "storage.bulk_area", "storage.silos", "storage.liquid", "storage.tanks", "storage.yard_equipment"),
    "waterside": ("waterside.gov_loa", "waterside.gov_beam", "waterside.gov_draft", "waterside.depth_req",
                  "waterside.channel_width", "waterside.channel_length", "waterside.entrance_width",
                  "waterside.stopping_distance", "waterside.turning_basin", "waterside.turning_area",
                  "waterside.anchorage_radius", "waterside.x_star", "waterside.trestle_len", "waterside.tip_depth",
                  "waterside.pocket_length", "waterside.pocket_width", "waterside.dredge_vol", "waterside.cost",
                  "storage.trucks", "storage.pipeline"),
    "invest": ("invest.berth", "invest.handling", "invest.waterside", "invest.storage", "invest.pipeline",
               "invest.yard_equipment", "invest.total"),
}
#: variabel investasi: seri per tahun bangun, indeks 0 = `CalcResult.invest_start_year`
INVEST_VARS = set(COMPUTES["invest"])
#: variabel berkunci id terminal KEK (bukan flow)
TERMINAL_KEYED = {"terminal.n_berth", "terminal.bor", "terminal.berth_length", "terminal.n_equip"}
#: variabel penyimpanan per fasilitas: kunci flow + `total` (kapasitas terpasang, tidak pernah turun)
STORAGE_FACILITY_VARS = {"cy": ("storage.cy", "storage.cy_slots"), "gc": ("storage.gc",),
                         "bulk": ("storage.bulk", "storage.bulk_area", "storage.silos"),
                         "liquid": ("storage.liquid", "storage.tanks")}
PORT_PARTS = ("labuh", "pandu", "tambat", "tunda", "bm")
#: variabel perairan berkunci id terminal dan/atau `site` (alur & kolam bersama); `storage.trucks` berkunci id alat
WATERSIDE_SITE = {"waterside.channel_width", "waterside.channel_length", "waterside.entrance_width",
                  "waterside.stopping_distance", "waterside.turning_basin", "waterside.turning_area",
                  "waterside.anchorage_radius"}
GOV_DIMS = (("loa", "loa_m"), ("beam", "beam_m"), ("draft", "draft_m"))

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
    waterside_options: list[WatersideOption] = Field(
        [], description="modul waterside: trestle penuh / trestle + keruk / keruk dengan biaya dasar (I8)")
    governing_ships: dict[str, dict[str, str]] = Field(
        {}, description="modul waterside: terminal | site → dimensi (loa, beam, draft) → kapal yang menentukan nilai "
                        "akhir horizon")
    channel_parts: dict[str, list[float]] = Field(
        {}, description="modul waterside: komponen lebar alur site (wm, wa_*, wa, wb, ws), seri tahunan m")
    invest_start_year: int = Field(1, description="modul invest: tahun bangun indeks 0 seri invest.* (= 1 − masa "
                                                  "konstruksi; K15: 0); seri lain mulai tahun ke-1")
    warnings: list[str] = []


class WatersideOption(BaseModel):
    """Satu opsi perairan (desain akhir horizon per terminal, harga satuan tahun dasar)."""

    mode: Literal["trestle", "mixed", "dredge"]
    selected: bool = Field(description="opsi rencana (plans[].waterside_mode) yang dipakai variabel waterside.*")
    feasible: bool
    reasons: list[str] = Field([], description="alasan opsi tidak layak (x* tidak tercapai / melebihi panjang maks)")
    trestle_len: dict[str, float] = Field({}, description="terminal → panjang trestle, m")
    theta: dict[str, float] = Field({}, description="terminal → panjang trestle / x*")
    tip_depth: dict[str, float] = Field({}, description="terminal → kedalaman eksisting di ujung trestle, m")
    trestle_area: dict[str, float] = Field({}, description="terminal → luas trestle, m²")
    dredge_vol: dict[str, float] = Field({}, description="terminal → volume keruk kolam tambat akhir horizon, m³")
    cost_trestle: dict[str, float] = Field({}, description="terminal → biaya trestle, Rp")
    cost_dredge: dict[str, float] = Field({}, description="terminal → biaya keruk, Rp")
    cost: float = Field(0.0, description="Σ biaya dasar semua terminal, Rp")
    build_year: dict[str, int] = Field({}, description="modul invest: terminal → tahun bangun trestle (tambatan pertama)")
    invest_total: float = Field(0.0, description="modul invest: Σ investasi terjadwal (trestle + keruk bertahap, "
                                                 "eskalasi bila diterapkan), Rp")
    pv: float = Field(0.0, description="modul invest: PV investasi terjadwal ke th 0 dengan discount rate, Rp")


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


def storage_chain(case: Case, d_unit: dict[str, list[float]], chains: dict[str, tuple[Ship, dict[str, Value]]],
                  warnings: list[str]) -> dict[str, dict[str, Value]]:
    """§5.6 dari D satuan flow (`d_unit`, TEU untuk PK) dan lama konsumsi per flow (`chains`). Nilai per flow + kunci
    `total` per fasilitas (Σ flow, tidak pernah turun); alat lapangan berkunci id alat."""
    sp = case.storage
    p = case.params
    n_years = case.horizon.years
    teu = teu_forms(case)
    com = {c.id: c for c in case.commodities}
    out: dict[str, dict[str, Value]] = {k: {} for k in COMPUTES["storage"]}
    sums: dict[str, list[float]] = {v: [0.0] * n_years for vs in STORAGE_FACILITY_VARS.values() for v in vs}
    q_form: dict[str, list[float]] = {}
    for f in case.flows:
        d = d_unit.get(f.id)
        if d is None:
            continue
        fac = "cy" if f.cargo_form in teu else storage.FACILITY.get(f.cargo_form)
        if fac is None:
            warnings.append(f"{f.id}: bentuk muatan {f.cargo_form} tidak punya fasilitas penyimpanan (§5.6)")
            continue
        if sp.dwell_time_mode == "fixed":
            if f.commodity_id not in sp.fixed_dwell_days:
                warnings.append(f"{f.id}: dwell time tetap untuk komoditas {f.commodity_id} belum diisi; penyimpanan "
                                "tidak dihitung")
                continue
            cons = [0.0] * n_years
        else:
            ch = chains.get(f.id)
            if ch is None:
                warnings.append(f"{f.id}: lama konsumsi belum dihitung (rantai pelayaran gagal); penyimpanan tidak dihitung")
                continue
            cons_v = ch[1]["voyage.consumption"]
            assert isinstance(cons_v, list)
            cons = cons_v
        rho = com[f.commodity_id].density_t_m3
        if fac != "cy" and not rho:
            warnings.append(f"{f.id}: densitas komoditas {f.commodity_id} kosong; penyimpanan tidak dihitung")
            continue
        share = sp.inbound_share if f.direction == "inbound" else sp.outbound_share
        q = [storage.throughput(x, share) for x in d]
        tdw = [storage.dwell(c, sp.dwell_time_mode, sp.fixed_dwell_days.get(f.commodity_id)) if x > 0 else 0.0
               for c, x in zip(cons, q, strict=True)]
        out["storage.throughput"][f.id] = q
        out["storage.dwell"][f.id] = tdw
        per: dict[str, list[float]] = {}
        if fac == "cy":
            per["storage.cy"] = [storage.cy_area(a, t, sp.container_yard) for a, t in zip(q, tdw, strict=True)]
            per["storage.cy_slots"] = [storage.ground_slots(a, t, sp.container_yard) for a, t in zip(q, tdw, strict=True)]
            qe = [a * (1.0 + sp.container_yard.empty_share) for a in q]  # alat lapangan menangani full + kosong
        elif fac == "gc":
            assert rho
            per["storage.gc"] = [storage.gc_area(a, t, rho, sp.general_cargo) for a, t in zip(q, tdw, strict=True)]
            qe = q
        elif fac == "bulk":
            assert rho
            vol = [storage.bulk_volume(a, t, rho, sp.dry_bulk) for a, t in zip(q, tdw, strict=True)]
            per["storage.bulk"] = vol
            per["storage.bulk_area"] = [storage.bulk_area(a, t, rho, sp.dry_bulk) for a, t in zip(q, tdw, strict=True)]
            per["storage.silos"] = [float(storage.silos(v, sp.dry_bulk)) for v in vol]
            qe = q
        else:
            assert rho
            vol = [storage.liquid_volume(a, t, rho, sp.liquid) for a, t in zip(q, tdw, strict=True)]
            per["storage.liquid"] = vol
            per["storage.tanks"] = [float(storage.tanks(v, sp.liquid)) for v in vol]
            qe = q
        for k, s in per.items():
            out[k][f.id] = s
            sums[k] = [a + b for a, b in zip(sums[k], s, strict=True)]
        acc = q_form.setdefault(f.cargo_form, [0.0] * n_years)
        q_form[f.cargo_form] = [a + b for a, b in zip(acc, qe, strict=True)]
    for k, s in sums.items():
        out[k][storage.TOTAL] = terminal.never_decrease(s)
    hours = p.working_days_per_year * p.working_hours_per_day
    for eq in sp.yard_equipment:
        if eq.role != "yard":
            continue
        qf = q_form.get(eq.cargo_form, [0.0] * n_years)
        out["storage.yard_equipment"][eq.id] = terminal.never_decrease(
            [float(storage.yard_equipment(x, eq, hours)) for x in qf])
    return out


def _price(case: Case, key: str, warnings: list[str]) -> float:
    up = next((u for u in case.unit_prices if u.key == key), None)
    if up is None:
        warnings.append(f"harga satuan '{key}' tidak ada di unit_prices; biaya dihitung 0")
        return 0.0
    return up.price_rp


def waterside_chain(case: Case, chains: dict[str, tuple[Ship, dict[str, Value]]],
                    term_vals: dict[str, dict[str, Value]], plan: Plan | None,
                    warnings: list[str]) -> tuple[dict[str, dict[str, Value]], list[WatersideOption],
                                                  dict[str, dict[str, str]], dict[str, list[float]]]:
    """§5.7 dari kapal aktif per terminal (`chains`) dan jumlah tambatan (`term_vals`). Kebutuhan per tahun (kapal
    penentu, kedalaman, x*, alur & kolam) dan desain opsi rencana (trestle, keruk, biaya dasar) per terminal."""
    site = case.kek_site
    w = site.waterside
    bathy = site.bathymetry
    n = case.horizon.years
    flows = {f.id: f for f in case.flows}
    out: dict[str, dict[str, Value]] = {k: {} for k in COMPUTES["waterside"] if k != "storage.trucks"}
    active: dict[str, list[list[Ship]]] = {t.id: [[] for _ in range(n)] for t in site.terminals}
    for fid, (ship, ch) in chains.items():
        freq = ch["voyage.freq"]
        assert isinstance(freq, list)
        tid = voyage.terminal_of(case, flows[fid]).id
        for y, fq in enumerate(freq):
            if fq:
                active[tid][y].append(ship)
    active[waterside.SITE] = [[s for t in site.terminals for s in active[t.id][y]] for y in range(n)]
    gov_ships: dict[str, dict[str, str]] = {}
    for key, by_year in active.items():
        for dim, attr in GOV_DIMS:
            out[f"waterside.gov_{dim}"][key] = waterside.governing([[getattr(s, attr) for s in ys] for ys in by_year])
        every = [s for ys in by_year for s in ys]
        if every:
            gov_ships[key] = {dim: max(every, key=lambda s, a=attr: getattr(s, a)).id for dim, attr in GOV_DIMS}
        drafts = out["waterside.gov_draft"][key]
        assert isinstance(drafts, list)
        out["waterside.depth_req"][key] = [waterside.depth_required(t, w.depth_factor_of_draft) for t in drafts]

    def col(var: str, key: str) -> list[float]:
        v = out[var][key]
        assert isinstance(v, list)
        return v

    loa, beam, dep = col("waterside.gov_loa", waterside.SITE), col("waterside.gov_beam", waterside.SITE), \
        col("waterside.depth_req", waterside.SITE)
    site_vals = {
        "waterside.channel_width": [waterside.channel_width(b, w) for b in beam],
        "waterside.channel_length": [waterside.channel_length(x, w) for x in loa],
        "waterside.entrance_width": [waterside.entrance_width(x) for x in loa],
        "waterside.stopping_distance": [waterside.stopping_distance(x) for x in loa],
        "waterside.turning_basin": [waterside.turning_basin(x, w.tug_assisted) for x in loa],
        "waterside.anchorage_radius": [waterside.anchorage_radius(x, d) for x, d in zip(loa, dep, strict=True)],
    }
    site_vals["waterside.turning_area"] = [waterside.turning_area(d) for d in site_vals["waterside.turning_basin"]]
    for k, v in site_vals.items():
        out[k][waterside.SITE] = v
    parts: dict[str, list[float]] = {}
    for b in beam:
        for k, v in waterside.channel_components(b, w).items():
            parts.setdefault(k, []).append(v)

    mode = plan.waterside_mode if plan else "trestle"
    theta = plan.trestle_fraction if plan else None
    p_tr = _price(case, site.trestle.unit_price_key, warnings)
    p_dr = _price(case, site.trestle_dredge.unit_price_key, warnings)
    options = {m: WatersideOption(mode=m, selected=m == mode, feasible=True) for m in waterside.OPTIONS}
    for t in site.terminals:
        dreq = col("waterside.depth_req", t.id)
        nb = term_vals["terminal.n_berth"].get(t.id)
        assert isinstance(nb, list)
        xs = [waterside.x_star(bathy, d) for d in dreq]
        if any(x is None for x in xs):
            warnings.append(f"{t.id}: kedalaman perlu {max(dreq):.1f} m tidak tercapai di profil batimetri "
                            f"(terdalam {max(b.depth_m for b in bathy):.1f} m); x* tidak dihitung")
        else:
            out["waterside.x_star"][t.id] = [float(x) for x in xs if x is not None]
        used = [any(v > 0 for v in nb[: y + 1]) for y in range(n)]
        if not any(used):
            continue
        d_des = dreq[-1]
        xs_des = waterside.x_star(bathy, d_des)
        loa_des, beam_des = col("waterside.gov_loa", t.id)[-1], col("waterside.gov_beam", t.id)[-1]
        pl, pw = waterside.pocket_length(t, loa_des), waterside.pocket_width(beam_des)
        chosen: tuple[float, float] | None = None
        for m, opt in options.items():
            ln = waterside.trestle_length(m, xs_des, site.trestle_dredge.trestle_length_m, theta)
            if ln is None:
                opt.feasible = False
                opt.reasons.append(f"{t.id}: kedalaman perlu {d_des:.1f} m tidak tercapai di profil batimetri")
                continue
            if site.trestle.max_length_m is not None and ln > site.trestle.max_length_m + 1e-9:
                opt.feasible = False
                opt.reasons.append(f"{t.id}: trestle {ln:.0f} m > panjang maks {site.trestle.max_length_m:.0f} m")
            tip = waterside.depth_at(bathy, ln)
            area = ln * t.trestle_width_m
            vol = waterside.dredge_volume(nb[-1], pl, pw, d_des, tip)
            opt.trestle_len[t.id], opt.tip_depth[t.id], opt.trestle_area[t.id] = ln, tip, area
            if xs_des:
                opt.theta[t.id] = ln / xs_des
            opt.dredge_vol[t.id] = vol
            opt.cost_trestle[t.id], opt.cost_dredge[t.id] = area * p_tr, vol * p_dr
            opt.cost += waterside.cost(area, p_tr, vol, p_dr)
            if m == mode:
                chosen = (ln, tip)
        if chosen is None:
            warnings.append(f"{t.id}: opsi perairan '{mode}' tidak bisa dihitung; desain trestle/keruk dilewati")
            continue
        ln, tip = chosen
        area = ln * t.trestle_width_m
        vol = [waterside.dredge_volume(b, pl, pw, d_des, tip) for b in nb]
        out["waterside.trestle_len"][t.id] = [ln if u else 0.0 for u in used]
        out["waterside.tip_depth"][t.id] = [tip if u else 0.0 for u in used]
        out["waterside.pocket_length"][t.id] = [pl if u else 0.0 for u in used]
        out["waterside.pocket_width"][t.id] = [pw if u else 0.0 for u in used]
        out["waterside.dredge_vol"][t.id] = vol
        out["waterside.cost"][t.id] = [waterside.cost(area if u else 0.0, p_tr, v, p_dr) for u, v in zip(used, vol, strict=True)]
    return out, list(options.values()), gov_ships, parts


def truck_chain(case: Case, chains: dict[str, tuple[Ship, dict[str, Value]]], term_vals: dict[str, dict[str, Value]],
                trestle_len: dict[str, Value], equip_by_term: dict[str, str],
                warnings: list[str]) -> dict[str, Value]:
    """`storage.trucks` per alat transport: truk per alat B/M × alat B/M aktif untuk bentuk muatannya; jarak =
    panjang trestle desain terminal (opsi rencana)."""
    sp = case.storage
    p = case.params
    n = case.horizon.years
    teu_box = p.container.share_20ft + 2 * (1 - p.container.share_20ft)
    flows = {f.id: f for f in case.flows}
    out: dict[str, Value] = {}
    for eq in sp.yard_equipment:
        if eq.role != "transport":
            continue
        term = next((t for t in case.kek_site.terminals if eq.cargo_form in t.cargo_forms), None)
        crane = next((e for e in case.equipment if e.id == equip_by_term.get(term.id, "")), None) if term else None
        rate = crane.productivity.get(eq.cargo_form) if crane else None
        if term is None or crane is None or rate is None:
            warnings.append(f"{eq.id}: alat B/M terminal untuk {eq.cargo_form} tidak ditemukan; truk tidak dihitung")
            continue
        if eq.productivity_unit.startswith("box") != (rate.unit == "box/h"):
            warnings.append(f"{eq.id}: satuan muatan per rit ({eq.productivity_unit}) tidak sesuai produktivitas alat "
                            f"B/M ({rate.unit}); truk tidak dihitung")
            continue
        speed = eq.params.get("speed_kmh")
        if not speed:
            warnings.append(f"{eq.id}: params.speed_kmh kosong; truk tidak dihitung")
            continue
        yard_min = eq.params.get("unload_min")
        if yard_min is None:
            ye = next((e for e in sp.yard_equipment if e.role == "yard" and e.cargo_form == eq.cargo_form), None)
            if ye is None:
                warnings.append(f"{eq.id}: params.unload_min kosong dan tidak ada alat lapangan {eq.cargo_form}; "
                                "waktu bongkar di lapangan = 0")
                yard_min = 0.0
            else:
                cap_y = eq.productivity * (teu_box if eq.productivity_unit.startswith("box") and
                                           ye.productivity_unit.upper().startswith("TEU") else 1.0)
                yard_min = 60.0 * cap_y / ye.productivity
        tl = trestle_len.get(term.id)
        dist_km = max(tl) / 1000.0 if isinstance(tl, list) and tl else 0.0
        n_eq_t = term_vals["terminal.n_equip"][term.id]
        assert isinstance(n_eq_t, list)
        fids = [fid for fid in chains if flows[fid].cargo_form == eq.cargo_form]
        res: list[float] = []
        for y in range(n):
            act = []
            for fid in fids:
                freq = chains[fid][1]["voyage.freq"]
                assert isinstance(freq, list)
                if freq[y]:
                    act.append(fid)
            if not act:
                res.append(0.0)
                continue
            per = 0
            neq = 0
            sd = 0.0
            for fid in act:
                ship = chains[fid][0]
                r = rate.unload if flows[fid].direction == "inbound" else rate.load
                per = max(per, storage.trucks_per_crane(*storage.truck_cycle(eq.productivity, r, dist_km, speed, yard_min)))
                neq = max(neq, vessel.n_equipment(ship, case.equipment_rules, term.id))
                sdv = term_vals["terminal.ship_days"][fid]
                assert isinstance(sdv, list)
                sd += sdv[y]
            cr = storage.active_cranes(n_eq_t[y], neq, sd, p.working_days_per_year)
            res.append(storage.trucks(per, cr))
        out[eq.id] = terminal.never_decrease(res)
    return out


def pipeline_chain(case: Case, chains: dict[str, tuple[Ship, dict[str, Value]]], term_vals: dict[str, dict[str, Value]],
                   trestle_len: dict[str, Value]) -> dict[str, Value]:
    """`storage.pipeline` per flow curah cair: trestle desain terminal + LOA kapal × jumlah jetty, sejak flow pertama
    aktif; tidak pernah turun."""
    flows = {f.id: f for f in case.flows}
    out: dict[str, Value] = {}
    for fid, (ship, ch) in chains.items():
        if storage.FACILITY.get(flows[fid].cargo_form) != "liquid":
            continue
        tid = voyage.terminal_of(case, flows[fid]).id
        tl = trestle_len.get(tid)
        tr = max(tl) if isinstance(tl, list) and tl else 0.0
        nb, freq = term_vals["terminal.n_berth"][tid], ch["voyage.freq"]
        assert isinstance(nb, list) and isinstance(freq, list)
        used = [any(f > 0 for f in freq[: y + 1]) for y in range(len(freq))]
        out[fid] = terminal.never_decrease([invest.pipe_length(tr, ship.loa_m, b) if u else 0.0
                                            for u, b in zip(used, nb, strict=True)])
    return out


def invest_chain(case: Case, values: dict[str, dict[str, Value]], plan: Plan | None, options: list[WatersideOption],
                 equip_by_term: dict[str, str], warnings: list[str]) -> tuple[dict[str, dict[str, Value]], int]:
    """§5.8 jadwal investasi dari kebutuhan terpasang per tahun (tambatan, alat, penyimpanan, alat lapangan, truk,
    pipa) dan opsi perairan. Mengembalikan nilai `invest.*` (seri per tahun bangun) dan tahun indeks 0. Melengkapi
    `options` dengan tahun bangun, investasi terjadwal dan PV per opsi."""
    h, p = case.horizon, case.params
    lead = h.construction_lead_years
    start, length = 1 - lead, h.years + lead
    mode = plan.staging if plan else "phase"
    phases = [(ph.start_year, ph.end_year) for ph in h.phases]
    sp = case.storage
    out: dict[str, dict[str, Value]] = {k: {} for k in COMPUTES["invest"]}
    total: dict[int, float] = {}

    def need(var: str, key: str) -> list[float] | None:
        v = values.get(var, {}).get(key)
        return v if isinstance(v, list) else None

    def sched(seq: list[float], look: int) -> dict[int, float]:
        return invest.schedule(seq, mode, phases, lead, look)

    def put(var: str, key: str, by_year: dict[int, float]) -> None:
        out[var][key] = invest.series(by_year, start, length)
        for y, v in by_year.items():
            total[y] = total.get(y, 0.0) + v

    def price(key: str | None, what: str) -> float | None:
        if key is None:
            warnings.append(f"{what}: kunci harga satuan kosong; tidak diinvestasikan")
            return None
        return _price(case, key, warnings)

    e_inf, e_eq, apply = p.escalation_infra, p.escalation_equipment, p.apply_escalation
    terms = {t.id: t for t in case.kek_site.terminals}
    berth_adds: dict[str, dict[int, float]] = {}
    for tid, t in terms.items():
        nb = need("terminal.n_berth", tid)
        if nb is None:
            continue
        adds = sched(nb, h.berth_lookahead_years)
        berth_adds[tid] = adds
        up = next((u for u in case.unit_prices if u.key == t.berth_price_key), None)
        pr = price(t.berth_price_key, f"tambatan {tid}")
        if pr is not None:
            unit = up.unit if up else "unit"
            put("invest.berth", tid, invest.costed({y: invest.berth_quantity(a, t, unit) for y, a in adds.items()}, pr,
                                                   e_inf, apply))
        ne = need("terminal.n_equip", tid)
        crane = next((e for e in case.equipment if e.id == equip_by_term.get(tid, "")), None)
        if ne is not None and crane is not None:
            put("invest.handling", tid, invest.costed(sched(ne, h.berth_lookahead_years), crane.price_usd * p.usd_rate,
                                                      e_eq, apply))

    # perairan: trestle bersama tambatan pertama terminal, keruk kolam tambat per tambatan yang ditambahkan
    p_tr = _price(case, case.kek_site.trestle.unit_price_key, warnings)
    p_dr = _price(case, case.kek_site.trestle_dredge.unit_price_key, warnings)
    for opt in options:
        for tid, adds in berth_adds.items():
            if tid not in opt.trestle_area or not adds:
                continue
            nb = need("terminal.n_berth", tid)
            assert nb is not None
            y0 = min(adds)
            per_berth = opt.dredge_vol.get(tid, 0.0) / nb[-1] if nb[-1] else 0.0
            by: dict[int, float] = {y0: opt.trestle_area[tid] * p_tr * invest.escalation(y0, e_inf, apply)}
            for y, a in adds.items():
                by[y] = by.get(y, 0.0) + a * per_berth * p_dr * invest.escalation(y, e_inf, apply)
            opt.build_year[tid] = y0
            opt.invest_total += sum(by.values())
            opt.pv += invest.present_value(by, p.discount_rate)
            if opt.selected:
                put("invest.waterside", tid, by)

    # penyimpanan (kapasitas terpasang total per fasilitas)
    fac_price = {"cy": (("storage.cy",), sp.container_yard.unit_price_key),
                 "gc": (("storage.gc",), sp.general_cargo.unit_price_key),
                 "bulk": (("storage.silos",), sp.dry_bulk.unit_price_key),
                 "liquid": (("storage.tanks",), sp.liquid.unit_price_key)}
    for fac, (vars_, key) in fac_price.items():
        seq = need(vars_[0], storage.TOTAL)
        if seq is None or not any(seq):
            continue
        pr = price(key, f"penyimpanan {fac}")
        if pr is not None:
            put("invest.storage", fac, invest.costed(sched(seq, h.storage_lookahead_years), pr, e_inf, apply))
    for fid, seq in values.get("storage.pipeline", {}).items():
        if not isinstance(seq, list) or not any(seq):
            continue
        pr = price(sp.liquid.pipe_price_key, f"pipa {fid}")
        if pr is not None:
            put("invest.pipeline", fid, invest.costed(sched(seq, h.storage_lookahead_years), pr, e_inf, apply))
    # alat lapangan & truk
    for eq in sp.yard_equipment:
        seq = need("storage.yard_equipment" if eq.role == "yard" else "storage.trucks", eq.id)
        if seq is None or not any(seq):
            continue
        pr = price(eq.unit_price_key, f"alat lapangan {eq.id}")
        if pr is not None:
            put("invest.yard_equipment", eq.id, invest.costed(sched(seq, h.storage_lookahead_years), pr, e_eq, apply))
    out["invest.total"][storage.TOTAL] = invest.series(total, start, length)
    return out, start


SHIP_KEYED ={"vessel.ballast_speed", "vessel.ae_kw", "vessel.sfoc_me", "vessel.sfoc_ae", "shipcost.tch_rate"}


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
    if "storage" in mods:
        d_unit = {k: v for k, v in values["cargo.demand_unit"].items() if isinstance(v, list)}
        values.update(storage_chain(case, d_unit, chains, warnings))
    w_opts: list[WatersideOption] = []
    gov: dict[str, dict[str, str]] = {}
    ch_parts: dict[str, list[float]] = {}
    plan = next((x for x in case.plans if x.id == pid), None)
    if "waterside" in mods:
        w_vals, w_opts, gov, ch_parts = waterside_chain(case, chains, values, plan, warnings)
        values.update(w_vals)
        values["storage.trucks"] = truck_chain(case, chains, values, w_vals["waterside.trestle_len"], equip_by_term,
                                               warnings)
        values["storage.pipeline"] = pipeline_chain(case, chains, values, w_vals["waterside.trestle_len"])
    inv_start = 1
    if "invest" in mods:
        i_vals, inv_start = invest_chain(case, values, plan, w_opts, equip_by_term, warnings)
        values.update(i_vals)

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
                      port_breakdown=breakdown, waterside_options=w_opts, governing_ships=gov, channel_parts=ch_parts,
                      invest_start_year=inv_start, warnings=warnings)


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
