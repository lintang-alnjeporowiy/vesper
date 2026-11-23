"""§5.6 Penyimpanan: dwell time, arus masuk, luas CY / gudang GC, silo, tangki, alat lapangan.

Acuan K15: sheet `Fasilitas Daratan` (dirujuk Investasi & Rangkuman). Keputusan Tahap 7b (2026-11-23):
- dwell time per tahun = lama konsumsi tahun itu (`voyage.consumption`, A13 terkoreksi); Excel merata-rata 20 tahun
  termasuk tahun tanpa muatan (A18).
- alat lapangan (RTG, forklift, dozer) satu armada per bentuk muatan: ⌈Σ arus / kapasitas⌉ dengan satu produktivitas
  per jenis alat; Excel membulatkan per tenant & per full/kosong dengan produktivitas RTG berbeda per tenant (A19).
- densitas curah cair dari data komoditas; Excel memakai 0,9 tetap (A20).
- kapasitas terpasang (total per fasilitas) tidak pernah turun; jadwal pengadaan & lookahead di §5.8 (Tahap 8).
- truk (role `transport`) dihitung di Tahap 8 bersama panjang trestle.
"""

from __future__ import annotations

from ..domain.case import (
    ContainerYardParams,
    DryBulkStorageParams,
    GeneralCargoStorageParams,
    LiquidStorageParams,
    YardEquipment,
)
from .cargo import ceil_

DAYS = 365.0  # hari kalender: stok rata-rata = Q · Tdw / 365 (sama dengan dasar lama konsumsi)
#: bentuk muatan → fasilitas penyimpanan (bentuk ber-TEU → container yard `cy`)
FACILITY = {"GC": "gc", "CK": "bulk", "CC": "liquid"}
TOTAL = "total"  # kunci kapasitas terpasang (Σ flow, tidak pernah turun) di variabel per fasilitas


def throughput(demand_unit: float, share: float) -> float:
    """`storage.throughput` — Q = porsi masuk penyimpanan · D (satuan flow untuk penyimpanan: TEU untuk PK, ton lainnya)."""
    return share * demand_unit


def dwell(consumption_days: float, mode: str, fixed_days: float | None) -> float:
    """`storage.dwell` — lama konsumsi tahun itu (mode from_consumption) atau isian tetap per komoditas."""
    if mode == "fixed":
        return float(fixed_days or 0.0)
    return consumption_days


def cy_area(q_teu: float, tdw: float, cy: ContainerYardParams) -> float:
    """`storage.cy` — (1 + porsi kosong) · Q · Tdw · A_TEU / (365 · H_ratio · YOR) [m²]."""
    return (1.0 + cy.empty_share) * q_teu * tdw * cy.area_per_teu_m2 / (DAYS * cy.height_ratio * cy.yor_max)


def ground_slots(q_teu: float, tdw: float, cy: ContainerYardParams) -> float:
    """`storage.cy_slots` — (1 + porsi kosong) · Q · Tdw / (365 · H_ratio · YOR · tier maks) [ground slot]."""
    return (1.0 + cy.empty_share) * q_teu * tdw / (DAYS * cy.height_ratio * cy.yor_max * cy.max_tiers)


def gc_area(q_t: float, tdw: float, density: float, gc: GeneralCargoStorageParams) -> float:
    """`storage.gc` — Q · Tdw · f_area · f_bulk / (365 · ρ · H · SOR) [m²]."""
    return q_t * tdw * gc.f_area * gc.f_bulk / (DAYS * density * gc.stack_height_m * gc.sor_max)


def bulk_net_volume(q_t: float, tdw: float, density: float, db: DryBulkStorageParams) -> float:
    """Volume netto curah kering: Q · Tdw · Rc / (365 · ρ · SOR) [m³]."""
    return q_t * tdw * db.capacity_ratio / (DAYS * density * db.sor_max)


def bulk_volume(q_t: float, tdw: float, density: float, db: DryBulkStorageParams) -> float:
    """`storage.bulk` — volume penyimpanan curah kering = faktor bruto · volume netto [m³]."""
    return db.gross_volume_factor * bulk_net_volume(q_t, tdw, density, db)


def bulk_area(q_t: float, tdw: float, density: float, db: DryBulkStorageParams) -> float:
    """`storage.bulk_area` — lapangan curah (alternatif silo): f_area · V_netto / H [m²]."""
    return db.f_area * bulk_net_volume(q_t, tdw, density, db) / db.stack_height_m


def silos(volume_m3: float, db: DryBulkStorageParams) -> int:
    """`storage.silos` — ⌈V / (kapasitas silo · rasio isi)⌉; 0 bila kasus tanpa silo."""
    if volume_m3 <= 0 or not db.silo_capacity_m3:
        return 0
    return ceil_(volume_m3 / (db.silo_capacity_m3 * db.silo_fill_ratio))


def liquid_volume(q_t: float, tdw: float, density: float, lq: LiquidStorageParams) -> float:
    """`storage.liquid` — Q · Tdw / (365 · ρ · okupansi) [m³]."""
    return q_t * tdw / (DAYS * density * lq.occupancy)


def tanks(volume_m3: float, lq: LiquidStorageParams) -> int:
    """`storage.tanks` — ⌈V / kapasitas tangki⌉ per produk (produk berbeda tidak berbagi tangki)."""
    return ceil_(volume_m3 / lq.tank_capacity_m3) if volume_m3 > 0 else 0


def yard_equipment(q_total: float, eq: YardEquipment, hours: float) -> int:
    """`storage.yard_equipment` — ⌈Σ arus / (produktivitas · utilisasi · jam kerja per tahun)⌉."""
    return ceil_(q_total / (eq.productivity * eq.utilization * hours)) if q_total > 0 else 0
