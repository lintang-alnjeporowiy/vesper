"""§5.5 Terminal KEK: ship-days, berth-days, jumlah tambatan, BOR, panjang dermaga, jumlah alat B/M.

Keputusan pengguna (Tahap 7a, 2026-11-23):
- shipDays = F · (tPortKEK + IT): waktu bongkar muat + idle time di tambatan; AT (approach) dan WT (menunggu di luar)
  tidak menempati tambatan (A17: Excel hanya bongkar muat).
- berth-days dermaga menerus (MP) = ⌈shipDays · LOA / L_unit⌉; jetty (CC) = ⌈shipDays⌉ — satu kapal satu jetty
  berapa pun LOA-nya (A16).
- nBerth per tahun = kebutuhan tahun itu, tidak pernah turun (tambatan yang sudah dibangun tetap ada); staging
  per tahap / lookahead di §5.8 (Tahap 8).
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.case import KekTerminal
from .cargo import ceil_


def ship_days(freq: float, t_port_kek: float, it_days: float) -> float:
    """`terminal.ship_days` — F · (tPortKEK + IT) [hari kapal di tambatan KEK per tahun] (A17)."""
    return freq * (t_port_kek + it_days) if freq else 0.0


def berth_days(ship_days_d: float, loa_m: float, term: KekTerminal) -> int:
    """`terminal.berth_days` — dermaga menerus: ⌈shipDays · LOA / L_unit⌉ (hari-tambatan); jetty: ⌈shipDays⌉ (A16)."""
    if ship_days_d <= 0:
        return 0
    if term.berth_layout == "jetty":
        return ceil_(ship_days_d)
    return ceil_(ship_days_d * loa_m / term.berth_unit_length_m)


def berths_required(berth_days_total: float, bor_max: float, working_days: float) -> int:
    """⌈Σ berth-days / (BOR_maks · hari kerja)⌉ — kebutuhan satu tahun."""
    return ceil_(berth_days_total / (bor_max * working_days)) if berth_days_total > 0 else 0


def never_decrease(seq: Sequence[float]) -> list[float]:
    """Seri kumulatif maksimum: kapasitas yang sudah dibangun tetap ada."""
    out: list[float] = []
    m = 0.0
    for v in seq:
        m = max(m, v)
        out.append(m)
    return out


def n_berth(berth_days_total: Sequence[float], bor_max: float, working_days: float) -> list[float]:
    """`terminal.n_berth` — kebutuhan per tahun, tidak pernah turun."""
    return never_decrease([float(berths_required(b, bor_max, working_days)) for b in berth_days_total])


def bor(berth_days_total: float, n: float, working_days: float) -> float:
    """`terminal.bor` — Σ berth-days / (nBerth · hari kerja) (= rumus SPEC dengan Σ shipDays yang saling coret)."""
    return berth_days_total / (n * working_days) if n else 0.0


def berth_length(n: float, term: KekTerminal) -> float:
    """`terminal.berth_length` — nBerth · L_unit (dermaga MP menerus; jetty: panjang platform per jetty)."""
    return n * term.berth_unit_length_m


def n_equip(n: float, neq_max: int) -> float:
    """`terminal.n_equip` — nBerth · nEq kapal terpanjang yang melayani terminal pada tahun itu."""
    return n * neq_max


def additions(seq: Sequence[float]) -> list[float]:
    """Penambahan per tahun dari seri kumulatif (tahun ke-1 = nilai awal)."""
    return [v - (seq[i - 1] if i else 0.0) for i, v in enumerate(seq)]
