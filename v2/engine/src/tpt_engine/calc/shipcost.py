"""§5.4 Biaya pelayaran — sheet `Model` 246–338, `TCH`, `Biaya Pelabuhan` (versi terkoreksi A6, A9, A11, A14, A15).

Satuan: liter/th, Rp/th, Rp/call. Frekuensi = frekuensi aktual F (A9, A11).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..domain.case import ExternalPort, Fuel, GlobalParams, PowerBand, Ship, ShipType, TariffBook, TariffClassRow

MOVES_PER_CALL = 2  # pandu & tunda: masuk + keluar (keputusan pengguna 2026-11-22, A15)


class CostError(ValueError):
    """Data kasus tidak cukup untuk menghitung biaya (TCH, tarif, BBM)."""


# ─── kapal: daya & SFOC ─────────────────────────────────────────────────────────────────────────
def ae_kw(ship: Ship, params: GlobalParams) -> float:
    """`vessel.ae_kw` — P_AE isian; bila kosong rasio · P_ME (K15: 50 %)."""
    return ship.ae_kw if ship.ae_kw is not None else params.ae_me_power_ratio * ship.me_kw


def sfoc_from_bands(power_kw: float, bands: list[PowerBand]) -> float:
    """Rentang daya → SFOC (g/kWh): rentang terakhir dengan min_kw ≤ P (seperti MATCH ≤ di Excel)."""
    hit = [b for b in sorted(bands, key=lambda b: b.min_kw) if b.min_kw <= power_kw + 1e-9]
    if not hit:
        raise CostError(f"tidak ada rentang SFOC untuk {power_kw:g} kW")
    return hit[-1].sfoc_g_kwh


def sfoc(ship: Ship, params: GlobalParams) -> tuple[float, float]:
    """`vessel.sfoc` — (SFOC ME, SFOC AE) g/kWh: isian kapal, bila kosong dari tabel rentang daya."""
    me = ship.sfoc_me_g_kwh if ship.sfoc_me_g_kwh is not None else sfoc_from_bands(ship.me_kw, params.sfoc_me_bands)
    ae = ship.sfoc_ae_g_kwh if ship.sfoc_ae_g_kwh is not None else sfoc_from_bands(ae_kw(ship, params), params.sfoc_ae_bands)
    return me, ae


# ─── BBM ────────────────────────────────────────────────────────────────────────────────────────
def fuel_of(params: GlobalParams, code: str) -> Fuel:
    f = next((x for x in params.fuels if x.code == code), None)
    if f is None:
        raise CostError(f"jenis BBM '{code}' tidak ada di parameter")
    return f


def fuel_litres(power_kw: float, sfoc_g_kwh: float, mcr: float, t_sea: float, t_port_call: float,
                share_sea: float, share_port: float, freq: float, density_kg_m3: float) -> float:
    """`shipcost.fuel_me_l` / `shipcost.fuel_ae_l` — liter/th:
    P · MCR · SFOC · 24 · (tSea · porsi laut + (tPort + tFix) · porsi pelabuhan) · F ÷ berat jenis.
    A9: F = frekuensi aktual (Excel: F_max · N_ship). MCR = faktor beban mesin, untuk ME dan AE
    (K15: porsi ME laut 1, pelabuhan 0; AE laut 0, pelabuhan 1 — sama dengan Excel)."""
    tonnes = power_kw * mcr * sfoc_g_kwh / 1e6 * 24.0 * (t_sea * share_sea + t_port_call * share_port) * freq
    return tonnes * 1e6 / density_kg_m3  # t → kg (×1000) → m³ (÷ρ) → l (×1000)


def fuel_cost(litres: float, fuel: Fuel) -> float:
    """`shipcost.fuel_me` / `shipcost.fuel_ae` — liter × harga (A6: jenis BBM per mesin = parameter, default HSD)."""
    return litres * fuel.price_rp_per_l


# ─── TCH ────────────────────────────────────────────────────────────────────────────────────────
def tch_regression(stype: ShipType) -> tuple[float, float]:
    """(slope a, intercept b) regresi linier kuadrat terkecil TCH USD/hari = a · ukuran + b (Excel SLOPE/INTERCEPT)."""
    pts = stype.tch_points
    if len(pts) < 2:
        raise CostError(f"tipe kapal {stype.code}: butuh ≥ 2 titik tarif charter untuk regresi TCH")
    n = len(pts)
    mx = sum(p.size for p in pts) / n
    my = sum(p.usd_per_day for p in pts) / n
    sxx = sum((p.size - mx) ** 2 for p in pts)
    if sxx == 0:
        raise CostError(f"tipe kapal {stype.code}: ukuran titik tarif charter semuanya sama")
    a = sum((p.size - mx) * (p.usd_per_day - my) for p in pts) / sxx
    return a, my - a * mx


def tch_rate(stype: ShipType, size: float) -> float:
    """`shipcost.tch_rate` — USD/hari = a_tipe · ukuran_k + b_tipe (ukuran = DWT atau kapasitas TEU sesuai tipe)."""
    a, b = tch_regression(stype)
    return a * size + b


def tch_cost(rate_usd_day: float, usd_rate: float, commission_days: float, n_ship: float) -> float:
    """`shipcost.tch` — Rp/th = tarif · kurs · CD · N_ship."""
    return rate_usd_day * usd_rate * commission_days * n_ship


# ─── biaya pelabuhan ────────────────────────────────────────────────────────────────────────────
@dataclass
class PortCall:
    """Biaya satu call di satu pelabuhan (Rp)."""
    labuh: float = 0.0
    pandu: float = 0.0
    tambat: float = 0.0
    tunda: float = 0.0
    bm: float = 0.0

    @property
    def total(self) -> float:
        return self.labuh + self.pandu + self.tambat + self.tunda + self.bm

    def as_dict(self) -> dict[str, float]:
        return {"labuh": self.labuh, "pandu": self.pandu, "tambat": self.tambat, "tunda": self.tunda, "bm": self.bm,
                "total": self.total}


def tariff_row(book: TariffBook, cls: str) -> TariffClassRow:
    row = next((c for c in book.classes if c.tariff_class == cls), None)
    if row is None:
        raise CostError(f"kelas tarif '{cls}' tidak ada di buku tarif")
    return row


def tug_band(book: TariffBook, gt: float) -> int:
    """Indeks rentang GT tunda: rentang terakhir dengan gt_min ≤ GT (Excel XLOOKUP …, -1)."""
    idx = [i for i, b in enumerate(book.tug_gt_bands) if b.gt_min <= gt + 1e-9]
    if not idx:
        raise CostError(f"tidak ada rentang GT tunda untuk {gt:g} GT")
    return idx[-1]


def port_call_cost(book: TariffBook, cls: str, foreign: bool, berth_type: str, gt: float, berth_days: float,
                   q: float, ship_unit: str, usd_rate: float) -> PortCall:
    """`shipcost.port_call` — satu call di satu pelabuhan.

    labuh = tarif/GT · GT (per kunjungan); pandu = (tetap + var·GT) · 2 gerakan; tambat = tarif/GT/etmal · GT ·
    ⌈lama sandar⌉ etmal; tunda = (tetap + var·GT) · 2 gerakan (rentang GT); B/M = q · tarif per ton atau per TEU.
    A14: tarif luar negeri dipakai untuk pelabuhan luar negeri (Excel selalu memakai dalam negeri).
    A15: 2 gerakan, tambat dari lama sandar di pelabuhan itu dibulatkan ke etmal, tunda tetap ikut per call.
    """
    r = tariff_row(book, cls)
    fx = usd_rate if foreign else 1.0
    labuh = (r.labuh_foreign_usd_per_gt if foreign else r.labuh_domestic_rp_per_gt) * fx * gt
    if foreign:
        pandu_1 = (r.pandu_foreign_fixed_usd + r.pandu_foreign_var_usd_per_gt * gt) * fx
    else:
        pandu_1 = r.pandu_domestic_fixed_rp + r.pandu_domestic_var_rp_per_gt * gt
    tambat_rate = (r.tambat_foreign_usd_per_gt_etmal if foreign else r.tambat_domestic_rp_per_gt_etmal)[berth_type] * fx
    etmal = math.ceil(berth_days - 1e-9) if berth_days > 0 else 0
    tug = r.tug[tug_band(book, gt)]
    if foreign:
        tunda_1 = (tug.fixed_foreign_usd + tug.var_foreign_usd_per_gt * gt) * fx
    else:
        tunda_1 = tug.fixed_domestic_rp + tug.var_domestic_rp_per_gt * gt
    if ship_unit == "TEU":
        rate = r.bm_foreign_rp_per_teu if foreign else r.bm_domestic_rp_per_teu
        if rate is None:
            raise CostError(f"kelas tarif '{cls}': tarif B/M per TEU {'luar' if foreign else 'dalam'} negeri kosong")
    else:
        rate = r.bm_foreign_rp_per_ton if foreign else r.bm_domestic_rp_per_ton
    return PortCall(labuh=labuh, pandu=pandu_1 * MOVES_PER_CALL, tambat=tambat_rate * gt * etmal,
                    tunda=tunda_1 * MOVES_PER_CALL, bm=q * rate)


def ext_port_call(book: TariffBook, port: ExternalPort, gt: float, t_port_ext: float, q: float, ship_unit: str,
                  usd_rate: float) -> PortCall:
    """Biaya satu call di pelabuhan asal/tujuan (kelas, dalam/luar negeri, jenis tambatan dari data pelabuhan)."""
    return port_call_cost(book, port.tariff_class, port.kind == "foreign", port.berth_type, gt, t_port_ext, q,
                          ship_unit, usd_rate)


def unit_cost(total: float, demand_flow_unit: float) -> float:
    """`shipcost.unit` — shipping cost / D dalam satuan flow (Rp/t atau Rp/TEU, A7)."""
    return total / demand_flow_unit if demand_flow_unit > 0 else 0.0
