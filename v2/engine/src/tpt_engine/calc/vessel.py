"""§5.2 Kandidat & kelayakan kapal (sheet `Data Kapal`, `Model` baris 24–39, `Model!CF34:CI37`).

Kecepatan = Vs kapal (dv.speed belum diaktifkan); cek jangkauan alat (`vessel.reach_ok`) menyusul di Tahap 7.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..domain.case import KEK, CargoFlow, Case, EquipmentRules, ExternalPort, GlobalParams, Ship


def teu_capacity(ship: Ship, params: GlobalParams) -> int:
    """`vessel.teu_cap` — TEU_k isian; bila kosong ⌊rasio · DWT / berat nominal per TEU⌋."""
    if ship.teu_capacity is not None:
        return ship.teu_capacity
    return math.floor(params.teu_capacity_dwt_ratio * ship.dwt_t / params.teu_nominal_weight_t + 1e-9)


def payload(ship: Ship, params: GlobalParams, ship_unit: str) -> float:
    """`vessel.payload` — muatan per call maksimum dalam satuan kapal.

    Satuan TEU (petikemas): kapasitas TEU efektif. Batas berat per TEU sudah dijamin NetMax (§5.1:
    tonPerTEU ≤ α·DWT/TEU − tare), jadi TEU·tonPerTEU ≤ α·DWT selalu terpenuhi.
    Satuan ton: payload isian, bila kosong α·DWT (A8: α = payload_dwt_ratio, default 0,85).
    """
    if ship_unit == "TEU":
        return float(teu_capacity(ship, params))
    if ship.payload_t is not None:
        return ship.payload_t
    return params.payload_dwt_ratio * ship.dwt_t


def compatible(case: Case, flow: CargoFlow, ship: Ship) -> bool:
    """`vessel.compatible` — tipe kapal k ∈ tipe yang diizinkan untuk bentuk muatan flow (matriks kasus)."""
    return ship.ship_type in case.compatibility.get(flow.cargo_form, [])


def route_ports(case: Case, flow: CargoFlow) -> list[ExternalPort]:
    """Pelabuhan eksternal yang disinggahi rute flow (urut kemunculan, tanpa duplikat)."""
    route = next(r for r in case.routes if r.id == flow.route_id)
    ports = {p.id: p for p in case.ports}
    seen: list[str] = []
    for leg in route.legs:
        for pid in (leg.origin, leg.destination):
            if pid != KEK and pid not in seen:
                seen.append(pid)
    return [ports[p] for p in seen]


def _n(x: float) -> str:
    """Angka untuk teks alasan, gaya Indonesia (koma desimal)."""
    return f"{x:g}".replace(".", ",")


@dataclass
class Feasibility:
    ok: bool
    reasons: list[str] = field(default_factory=list)  # alasan gugur (kosong bila layak)
    notes: list[str] = field(default_factory=list)  # catatan data (tidak menggugurkan)


def feasibility(case: Case, flow: CargoFlow, ship: Ship) -> Feasibility:
    """`vessel.feasible` — compatible ∧ T_k ≤ draft maks ∧ dermaga terpanjang ≥ rasio·LOA_k ∧ LOA_k ≤ LOA maks,
    untuk setiap pelabuhan eksternal di rute ∧ faktor · T_k ≤ batas kedalaman rencana KEK (bila diisi, Tahap 8b);
    tanpa batas, perairan KEK dirancang mengikuti kapal (Tahap 8a)."""
    r: list[str] = []
    notes: list[str] = []
    if not compatible(case, flow, ship):
        r.append(f"tipe {ship.ship_type} tidak boleh membawa {flow.cargo_form}")
    ratio = case.params.berth_loa_min_ratio
    for p in route_ports(case, flow):
        if ship.draft_m > p.max_draft_m + 1e-9:
            r.append(f"draft {_n(ship.draft_m)} m > {_n(p.max_draft_m)} m di {p.name}")
        if p.longest_berth_m is not None:
            if p.longest_berth_m + 1e-9 < ratio * ship.loa_m:
                r.append(f"dermaga {p.name} {_n(p.longest_berth_m)} m < {_n(ratio)}·LOA {_n(ship.loa_m)} m")
        else:
            notes.append(f"panjang dermaga {p.name} belum ada datanya (LOA tidak dicek)")
        if p.max_loa_m is not None and ship.loa_m > p.max_loa_m + 1e-9:
            r.append(f"LOA {_n(ship.loa_m)} m > batas {_n(p.max_loa_m)} m di {p.name}")
    w = case.kek_site.waterside
    if w.max_depth_m is not None and w.depth_factor_of_draft * ship.draft_m > w.max_depth_m + 1e-9:
        r.append(f"kedalaman perlu {_n(round(w.depth_factor_of_draft * ship.draft_m, 2))} m > batas KEK "
                 f"{_n(w.max_depth_m)} m")
    return Feasibility(ok=not r, reasons=r, notes=notes)


def n_equipment(ship: Ship, rules: EquipmentRules, terminal_id: str) -> int:
    """`vessel.neq` — alat per tambatan dari tabel rentang LOA (A10), dibatasi batas per terminal.

    Rentang [min, max): LOA tepat di batas masuk rentang atas; di atas rentang terakhir memakai rentang terakhir.
    """
    bands = sorted(rules.loa_bands, key=lambda b: b.loa_min_m)
    n = bands[-1].per_berth
    for b in bands:
        if ship.loa_m >= b.loa_min_m and (b.loa_max_m is None or ship.loa_m < b.loa_max_m):
            n = b.per_berth
            break
    cap = rules.max_per_berth.get(terminal_id)
    return min(n, cap) if cap else n


def ballast_speed(ship: Ship, params: GlobalParams) -> float:
    """`vessel.ballast_speed` — V_ballast isian; bila kosong rasio · Vs (A5: default 100 %)."""
    if ship.ballast_speed_kn is not None:
        return ship.ballast_speed_kn
    return params.ballast_speed_ratio * ship.speed_kn
