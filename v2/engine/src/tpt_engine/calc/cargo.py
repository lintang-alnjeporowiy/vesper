"""§5.1 Konversi muatan ton ↔ TEU (sheet `Muatan`) dan demand dalam satuan kapal.

NetMax bergantung kapal (A8: α batas berat per TEU), sehingga tonPerTEU & D_TEU dihitung per (flow, kapal terpilih).
"""

from __future__ import annotations

import math

from ..domain.case import Commodity, ContainerSpec, GlobalParams, Packaging

EPS = 1e-9


def floor_(x: float) -> int:
    """⌊x⌋ yang tahan galat floating point."""
    return math.floor(x + EPS)


def ceil_(x: float) -> int:
    """⌈x⌉ yang tahan galat floating point (104 000,000 000 1 tetap 104 000)."""
    return math.ceil(x - EPS * max(1.0, abs(x)))


def net_max(container: ContainerSpec, params: GlobalParams, dwt_t: float, teu_cap: int) -> float:
    """`cargo.netmax` — NetMax = min(payload kontainer, α·DWT_k / TEU_k − tare) [t/TEU] (A8: α = teu_weight_dwt_ratio)."""
    by_ship = params.teu_weight_dwt_ratio * dwt_t / teu_cap - container.tare_t
    return min(container.max_net_t, by_ship)


def container_volume(container: ContainerSpec) -> float:
    """Vc — volume dalam petikemas 20 ft [m³]."""
    return container.inner_length_m * container.inner_width_m * container.inner_height_m


def box_per_teu(container: ContainerSpec, pack: Packaging, netmax: float) -> int:
    """`cargo.box_per_teu` — nBox = min(⌊Lc/l⌋·⌊Wc/w⌋·⌊Hc/h⌋, ⌊NetMax / w_box⌋) (orientasi kemasan sesuai input)."""
    geo = (floor_(container.inner_length_m / pack.length_m) * floor_(container.inner_width_m / pack.width_m)
           * floor_(container.inner_height_m / pack.height_m))
    by_weight = floor_(netmax / (pack.weight_kg / 1000.0))
    return max(0, min(geo, by_weight))


def ton_per_teu(container: ContainerSpec, commodity: Commodity, netmax: float) -> float:
    """`cargo.ton_per_teu` — nBox · w_box bila ada data kemasan; selain itu Vc/SF (atau Vc·ρ); selalu ≤ NetMax."""
    if commodity.packaging is not None:
        return box_per_teu(container, commodity.packaging, netmax) * commodity.packaging.weight_kg / 1000.0
    vc = container_volume(container)
    if commodity.stowage_factor_m3_t:
        return max(0.0, min(netmax, vc / commodity.stowage_factor_m3_t))
    if commodity.density_t_m3:
        return max(0.0, min(netmax, vc * commodity.density_t_m3))
    return max(0.0, netmax)


def demand_unit(demand: list[float], flow_unit: str, ship_unit: str, tpt: float | None) -> list[float]:
    """`cargo.demand_unit` — demand dalam satuan kapal.

    - satuan kapal TEU, flow dalam ton: D_TEU = ⌈D_ton / tonPerTEU⌉
    - satuan kapal TEU, flow dalam TEU: ⌈D⌉ (TEU utuh)
    - satuan kapal ton: D apa adanya
    A12: pembulatan ⌈·⌉ diterapkan seragam di semua tahun, sekali, setelah proyeksi (Excel: ROUNDDOWN di tahun-1,
    ROUNDUP di tahun lain; proyeksi TEU inbound dibulatkan lalu dikompounding; outbound TEU tidak dibulatkan).
    """
    if ship_unit == "ton":
        return list(demand)
    if flow_unit == "TEU":
        return [float(ceil_(d)) for d in demand]
    if not tpt or tpt <= 0:
        raise ValueError("tonPerTEU harus > 0 untuk mengonversi ton ke TEU")
    return [float(ceil_(d / tpt)) for d in demand]
