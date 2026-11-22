"""§5.2 Kapal — sementara hanya kapasitas TEU efektif (dibutuhkan NetMax di §5.1). Sisanya Tahap 5."""

from __future__ import annotations

import math

from ..domain.case import GlobalParams, Ship


def teu_capacity(ship: Ship, params: GlobalParams) -> int:
    """`vessel.teu_cap` — TEU_k isian; bila kosong ⌊rasio · DWT / berat nominal per TEU⌋."""
    if ship.teu_capacity is not None:
        return ship.teu_capacity
    return math.floor(params.teu_capacity_dwt_ratio * ship.dwt_t / params.teu_nominal_weight_t + 1e-9)
