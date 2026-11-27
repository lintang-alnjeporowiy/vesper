"""§5.8 Investasi & staging (Tahap 8b).

Keputusan pengguna (2026-11-27):
- pola bangun = rencana `plans[].staging`: `phase` (default, seperti Excel) — tiap tahap `horizon.phases` dibangun di
  tahun (awal tahap − masa konstruksi) untuk kebutuhan maksimum tahap itu; `incremental` — saat kebutuhan tahun t
  melampaui kapasitas terpasang, dibangun di tahun (t − masa konstruksi) untuk kebutuhan maksimum N tahun ke depan
  (`berth_lookahead_years` untuk tambatan, alat B/M & perairan; `storage_lookahead_years` untuk penyimpanan, alat
  lapangan, truk & pipa).
- tahun bangun = tahun pakai − `horizon.construction_lead_years` untuk semua komponen (Excel: dermaga & trestle di th −1,
  alat & penyimpanan di th 0, jendela tahap tidak seragam dan sebagian kolom batas terhitung dua kali, A26).
- perairan: trestle per terminal dibangun penuh (desain akhir horizon) bersama tambatan pertama terminal itu; keruk
  kolam tambat mengikuti penambahan tambatan, langsung sampai kedalaman desain akhir horizon (A29).
- escalation = opsi `params.apply_escalation` (default mati, seperti Excel; A27): harga tahun bangun t = harga dasar ×
  (1 + e)^t, t = tahun bangun (th 0 = tahun harga satuan), e infra untuk tambatan, trestle/keruk, penyimpanan & pipa,
  e alat untuk alat B/M, alat lapangan & truk.

Seri investasi berindeks tahun bangun: indeks 0 = tahun `1 − masa konstruksi` (K15: th 0), panjang `T + masa
konstruksi`; PV didiskon ke th 0: `Σ I[t] / (1 + r)^t`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from ..domain.case import KekTerminal

Staging = Literal["phase", "incremental"]
Category = Literal["infra", "equipment"]
EPS = 1e-9


def schedule(need: Sequence[float], mode: Staging, phases: Sequence[tuple[int, int]], lead: int,
             lookahead: int) -> dict[int, float]:
    """Penambahan kapasitas per tahun bangun dari kebutuhan terpasang per tahun (`need[i]` = tahun i+1).

    phase: tiap tahap (s, e) dibangun di th s − lead sebanyak maks(need[s..e]) − kapasitas terpasang.
    incremental: bila need[t] > kapasitas, dibangun di th t − lead sampai maks(need[t .. t+N−1]), N = lookahead (≥ 1).
    """
    n = len(need)
    out: dict[int, float] = {}
    cap = 0.0

    def add(year: int, target: float) -> None:
        nonlocal cap
        if target > cap + EPS:
            out[year] = out.get(year, 0.0) + target - cap
            cap = target

    if mode == "phase":
        for s, e in sorted(phases):
            if s > n:
                continue
            add(s - lead, max(need[s - 1: min(e, n)]))
        if n and need[-1] > cap + EPS:  # tahun di luar semua tahap (validator Case mencegahnya)
            add(n - lead, need[-1])
    else:
        span = max(1, lookahead)
        for t in range(1, n + 1):
            if need[t - 1] > cap + EPS:
                add(t - lead, max(need[t - 1: min(n, t - 1 + span)]))
    return out


def escalation(year: int, rate: float, apply: bool) -> float:
    """Faktor harga tahun bangun: (1 + e)^t bila eskalasi diterapkan, selain itu 1 (harga tahun dasar)."""
    return (1.0 + rate) ** year if apply else 1.0


def series(items: dict[int, float], start_year: int, length: int) -> list[float]:
    """Nilai per tahun bangun → seri berindeks `start_year` (indeks 0)."""
    out = [0.0] * length
    for y, v in items.items():
        out[y - start_year] += v
    return out


def costed(adds: dict[int, float], unit_price: float, rate: float, apply: bool) -> dict[int, float]:
    """Penambahan × harga satuan × faktor eskalasi tahun bangun."""
    return {y: a * unit_price * escalation(y, rate, apply) for y, a in adds.items()}


def price_basis(unit: str) -> Literal["m", "m2", "unit"]:
    """Basis harga satuan dari kolom satuan unit_prices: m² (juga 'm2', 'm^2', sel rusak 'm�') | m | unit."""
    u = unit.strip().lower()
    if u.startswith("m") and len(u) > 1 and u[1] in "²2^�":
        return "m2"
    return "m" if u == "m" else "unit"


def berth_quantity(n_added: float, term: KekTerminal, unit: str) -> float:
    """Kuantitas harga tambatan menurut satuan harga: m = tambatan × panjang unit, m² = × lebar dermaga juga,
    unit = jumlah tambatan/jetty (K15: dermaga MP Rp/m, jetty CC Rp/unit)."""
    basis = price_basis(unit)
    if basis == "unit":
        return n_added
    length = n_added * term.berth_unit_length_m
    return length * term.berth_width_m if basis == "m2" else length


def pipe_length(trestle_m: float, loa_m: float, n_berth: float) -> float:
    """Panjang pipa dermaga–tangki per produk curah cair = trestle terminal + LOA kapal × jumlah jetty (aturan Excel
    `Fasilitas Daratan!F239:F240`; Excel memakai trestle opsi keruk 250 m walau rencana trestle penuh, A30)."""
    return trestle_m + loa_m * n_berth if n_berth else 0.0


def present_value(by_year: dict[int, float], rate: float) -> float:
    """PV ke th 0: Σ I[t] / (1 + r)^t."""
    return sum(v / (1.0 + rate) ** y for y, v in by_year.items())
