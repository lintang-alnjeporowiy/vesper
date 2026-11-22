"""§5.1 Demand — proyeksi volume per flow per tahun (sheet `Proyeksi Muatan`).

Indeks tahun: elemen ke-0 = tahun ke-1. Nilai dalam satuan definisi flow (`CargoFlow.unit`), tanpa pembulatan;
pembulatan ke TEU utuh dilakukan sekali di `cargo.demand_unit` (A12).
"""

from __future__ import annotations

from ..domain.case import CargoFlow, Case, VolumeIndependent, VolumeRatio


def demand_base(start_year: int, initial: float, maximum: float, growth_rate: float, years: int) -> list[float]:
    """`demand.base` — D[t] = 0 bila t < t₀; V₀ di t₀; min(Dmax, D[t−1]·(1+g)).

    A4 (diperbaiki): batas maks dicek terhadap nilai tahun sebelumnya, bukan sel tetap tahun pertama.
    V₀ juga dibatasi Dmax agar input yang tidak konsisten (V₀ > Dmax) tidak melampaui batas.
    """
    out: list[float] = []
    prev = 0.0
    for t in range(1, years + 1):
        if t < start_year:
            d = 0.0
        elif t == start_year:
            d = min(maximum, initial)
        else:
            d = min(maximum, prev * (1.0 + growth_rate))
        out.append(d)
        prev = d
    return out


def demand_ratio(basis: list[float], ratio: float) -> list[float]:
    """`demand.ratio` — D_out[t] = r · D_acuan[t] (aturan volume §4.2; tahun mulai, laju & batas ikut acuan)."""
    return [ratio * d for d in basis]


def project_flows(case: Case) -> dict[str, list[float]]:
    """D[f,t] untuk semua flow (flow rasio dihitung setelah acuannya; rantai rasio diperbolehkan)."""
    years = case.horizon.years
    by_id: dict[str, CargoFlow] = {f.id: f for f in case.flows}
    out: dict[str, list[float]] = {}

    def solve(fid: str, stack: tuple[str, ...] = ()) -> list[float]:
        if fid in out:
            return out[fid]
        if fid in stack:
            raise ValueError(f"rantai flow rasio melingkar: {' -> '.join((*stack, fid))}")
        v = by_id[fid].volume
        if isinstance(v, VolumeIndependent):
            s = demand_base(v.start_year, v.initial, v.maximum, v.growth_rate, years)
        else:
            assert isinstance(v, VolumeRatio)
            s = demand_ratio(solve(v.basis_flow_id, (*stack, fid)), v.ratio)
        out[fid] = s
        return s

    for f in case.flows:
        solve(f.id)
    return out
