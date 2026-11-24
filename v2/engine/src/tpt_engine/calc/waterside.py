"""§5.7 Fasilitas perairan & trestle vs keruk (Tahap 8a).

Keputusan pengguna (2026-11-24):
- kapal penentu per terminal (MP, CC) per tahun: T, LOA, B maksimum masing-masing atas kapal terpilih flow yang aktif
  tahun itu di terminal itu, kumulatif (tidak turun); alur & kolam bersama (`site`) memakai semua terminal. Excel
  memakai satu kapal ber-LOA terbesar untuk seluruh KEK dan 20 tahun, B & T diambil dari kapal itu (A21).
- desain trestle/keruk = kebutuhan akhir horizon per terminal, ada sejak tahun pertama terminal dipakai; jadwal bangun
  & eskalasi di §5.8 (Tahap 8b).
- lingkup keruk = kolam tambat saja (lingkup Excel): panjang kolam × 1,5 B × (kedalaman perlu − kedalaman di ujung
  trestle); kolam jetty = 1,175 LOA kapal CC per jetty (Excel: panjang unit 40 m × lebar kapal MP, A24).

Lebar alur memakai tabel koefisien (kelipatan B) sheet `Fasilitas Perairan!B11:G84` (PIANC) dengan baris dipilih dari
kondisi perairan kasus; Excel memakai Vs (knot) untuk Wa kecepatan, Wa dasar laut walau h = 1,5 T, dan satu Wb pada
alur 1 jalur (A22). Kolam putar dengan kapal tunda = 2 LOA, luas dari diameter itu (Excel: 1,5 LOA, A23).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..domain.case import BathyPoint, KekTerminal, WatersideConditions

SITE = "site"  # kunci alur & kolam bersama (semua terminal)
OPTIONS = ("trestle", "mixed", "dredge")

# ─── tabel lebar alur (kelipatan B): {kelas kecepatan: (perairan terbuka, terlindungi)} ─────────────────────────────
Pair = tuple[float, float]
WM = {"baik": 1.3, "sedang": 1.5, "buruk": 1.8}  # B12:C14 (Wm menurut manuver kapal)
WA_SPEED: dict[str, Pair] = {"cepat": (0.1, 0.0), "sedang": (0.0, 0.0), "lambat": (0.0, 0.0)}  # B18:E20
#: (batas atas, inklusif?) → koefisien; band terakhir tanpa batas atas
WA_WIND: tuple[tuple[float, bool, dict[str, Pair]], ...] = (  # B21:E30 (knot)
    (15.0, False, {"cepat": (0.1, 0.0), "sedang": (0.2, 0.0), "lambat": (0.3, 0.0)}),
    (33.0, True, {"cepat": (0.3, 0.0), "sedang": (0.4, 0.0), "lambat": (0.5, 0.0)}),
    (math.inf, True, {"cepat": (0.6, 0.0), "sedang": (0.7, 0.0), "lambat": (1.1, 0.0)}),
)
_ZERO = {"cepat": (0.0, 0.0), "sedang": (0.0, 0.0), "lambat": (0.0, 0.0)}
WA_CROSS: tuple[tuple[float, bool, dict[str, Pair]], ...] = (  # B31:E40 (knot)
    (0.2, False, _ZERO),
    (0.5, False, {"cepat": (0.2, 0.1), "sedang": (0.3, 0.2), "lambat": (0.3, 0.3)}),
    (1.5, True, {"cepat": (0.5, 0.4), "sedang": (0.7, 0.6), "lambat": (1.0, 0.8)}),
    (math.inf, True, {"cepat": (0.5, 0.0), "sedang": (0.7, 0.0), "lambat": (1.0, 0.0)}),
)
WA_LONG: tuple[tuple[float, bool, dict[str, Pair]], ...] = (  # B41:E48 (knot)
    (1.5, False, _ZERO),
    (3.0, False, {"cepat": (0.0, 0.0), "sedang": (0.1, 0.0), "lambat": (0.2, 0.0)}),
    (math.inf, True, {"cepat": (0.1, 0.0), "sedang": (0.2, 0.0), "lambat": (0.4, 0.0)}),
)
WA_WAVE: tuple[tuple[float, bool, Pair], ...] = ((1.0, True, (0.0, 0.0)), (3.0, False, (0.5, 0.0)),
                                                 (math.inf, True, (1.0, 0.0)))  # B49:E52 (m)
WA_NAV: dict[str, Pair] = {"sangat_baik": (0.0, 0.0), "baik": (0.2, 0.0), "cukup": (0.4, 0.0)}  # B53:E56
WA_BOTTOM: dict[str, Pair] = {"tanah_lunak": (0.1, 0.0), "tanah_keras": (0.2, 0.0)}  # B57:E61, hanya bila h < 1,5 T
WA_DEPTH: tuple[tuple[float, Pair], ...] = ((1.5, (0.0, 0.0)), (1.25, (0.1, 0.2)), (0.0, (0.2, 0.4)))  # B62:E65 (h/T ≥)
WB: dict[str, dict[str, float]] = {  # B69:G78 (sama untuk terbuka & terlindungi)
    "landai": {"cepat": 0.2, "sedang": 0.1, "lambat": 0.0},
    "sedang": {"cepat": 0.7, "sedang": 0.5, "lambat": 0.3},
    "curam": {"cepat": 1.3, "sedang": 1.0, "lambat": 0.5},
}
WS: dict[str, Pair] = {"cepat": (2.0, 1.8), "sedang": (1.6, 1.4), "lambat": (1.2, 1.0)}  # B81:G84

# ─── faktor dimensi kolam (Fasilitas Perairan!K29:L50, nilai K15) ───────────────────────────────────────────────────
ENTRANCE_LOA = 1.0  # pintu masuk 0,7–1 LOA (K29)
STOPPING_LOA = 7.0  # jarak henti 7–8 LOA (K32)
TURNING_LOA_TUG = 2.0  # kolam putar dengan kapal tunda (K35)
TURNING_LOA_FREE = 4.0  # tanpa kapal tunda & bow thruster (K34)
BERTH_AREA_LOA = 1.175  # panjang area sandar (K40)
BERTH_AREA_BEAM = 1.5  # lebar area sandar (K42)
ANCHOR_DEPTH_K = 6.0  # radius labuh L + 6D, perjangkaran baik (L50)


class WatersideError(ValueError):
    pass


def _band(table, x: float):
    for top, incl, val in table:
        if x < top or (incl and x <= top):
            return val
    return table[-1][2]


def _col(pair: Pair, exposure: str) -> float:
    return pair[0] if exposure == "terbuka" else pair[1]


# ─── kapal penentu & kedalaman ──────────────────────────────────────────────────────────────────────────────────────
def governing(dims_by_year: Sequence[Sequence[float]]) -> list[float]:
    """`waterside.gov_loa|gov_beam|gov_draft` — maksimum atas kapal yang aktif tiap tahun, kumulatif (tidak turun)."""
    out: list[float] = []
    m = 0.0
    for dims in dims_by_year:
        m = max([m, *dims])
        out.append(m)
    return out


def depth_required(draft_m: float, factor: float) -> float:
    """`waterside.depth_req` — faktor × T kapal penentu [m LWS] (K15: 1,5 T)."""
    return factor * draft_m


# ─── alur & kolam (site) ────────────────────────────────────────────────────────────────────────────────────────────
def channel_components(beam_m: float, w: WatersideConditions) -> dict[str, float]:
    """Komponen lebar alur [m]: Wm, Wa per faktor, ΣWa, Wb, Ws. Wa dasar laut & kedalaman alur nol bila h ≥ 1,5 T."""
    sp, ex = w.ship_speed_class, w.exposure
    h_t = w.depth_factor_of_draft
    parts = {
        "wm": WM[w.maneuverability],
        "wa_speed": _col(WA_SPEED[sp], ex),
        "wa_wind": _col(_band(WA_WIND, w.wind_kn)[sp], ex),
        "wa_cross_current": _col(_band(WA_CROSS, w.cross_current_kn)[sp], ex),
        "wa_long_current": _col(_band(WA_LONG, w.longitudinal_current_kn)[sp], ex),
        "wa_wave": _col(_band(WA_WAVE, w.wave_height_m), ex),
        "wa_nav_aids": _col(WA_NAV[w.nav_aids], ex),
        "wa_bottom": 0.0 if h_t >= 1.5 else _col(WA_BOTTOM[w.seabed], ex),
        "wa_depth": _col(next(p for lim, p in WA_DEPTH if h_t >= lim), ex),
        "wb": WB[w.channel_slope][sp],
        "ws": _col(WS[sp], ex),
    }
    out = {k: v * beam_m for k, v in parts.items()}
    out["wa"] = sum(v for k, v in out.items() if k.startswith("wa_"))
    return out


def channel_width(beam_m: float, w: WatersideConditions) -> float:
    """`waterside.channel_width` — 1 jalur Wm + ΣWa + 2Wb; 2 jalur 2(Wm + ΣWa) + 2Wb + Ws [m] (A22)."""
    if beam_m <= 0:
        return 0.0
    c = channel_components(beam_m, w)
    if w.lanes == 1:
        return c["wm"] + c["wa"] + 2 * c["wb"]
    return 2 * (c["wm"] + c["wa"]) + 2 * c["wb"] + c["ws"]


def channel_length(loa_m: float, w: WatersideConditions) -> float:
    """`waterside.channel_length` — alur panjang: 2L (frekuensi tinggi) / 1,5L; pendek: 1,5L / L [m]."""
    if w.long_channel:
        return (2.0 if w.high_frequency else 1.5) * loa_m
    return (1.5 if w.high_frequency else 1.0) * loa_m


def entrance_width(loa_m: float) -> float:
    """`waterside.entrance_width` — lebar pintu masuk = 1 LOA [m]."""
    return ENTRANCE_LOA * loa_m


def stopping_distance(loa_m: float) -> float:
    """`waterside.stopping_distance` — jarak henti = 7 LOA [m]."""
    return STOPPING_LOA * loa_m


def turning_basin(loa_m: float, tug_assisted: bool) -> float:
    """`waterside.turning_basin` — diameter kolam putar: 2 LOA dengan kapal tunda, 4 LOA tanpa [m]."""
    return (TURNING_LOA_TUG if tug_assisted else TURNING_LOA_FREE) * loa_m


def turning_area(diameter_m: float) -> float:
    """`waterside.turning_area` — π · (D/2)² [m²] (A23: Excel memakai D = 1,5 LOA)."""
    return math.pi * (diameter_m / 2) ** 2


def anchorage_radius(loa_m: float, depth_m: float) -> float:
    """`waterside.anchorage_radius` — L + 6D (labuh bebas berputar, perjangkaran baik) [m]."""
    return loa_m + ANCHOR_DEPTH_K * depth_m if loa_m else 0.0


# ─── batimetri, trestle, keruk (per terminal) ───────────────────────────────────────────────────────────────────────
def depth_at(bathy: Sequence[BathyPoint], x_m: float) -> float:
    """Kedalaman eksisting pada jarak x dari pantai (interpolasi linier; di luar profil = titik ujung)."""
    if x_m <= bathy[0].distance_m:
        return bathy[0].depth_m
    for a, b in zip(bathy, bathy[1:], strict=False):
        if x_m <= b.distance_m:
            return a.depth_m + (b.depth_m - a.depth_m) * (x_m - a.distance_m) / (b.distance_m - a.distance_m)
    return bathy[-1].depth_m


def x_star(bathy: Sequence[BathyPoint], depth_m: float) -> float | None:
    """`waterside.x_star` — jarak pertama dari pantai dengan kedalaman ≥ kedalaman perlu (interpolasi linier);
    None bila profil tidak pernah mencapainya."""
    if depth_m <= 0 or bathy[0].depth_m >= depth_m:
        return bathy[0].distance_m if depth_m > 0 else 0.0
    for a, b in zip(bathy, bathy[1:], strict=False):
        if b.depth_m >= depth_m:
            return a.distance_m + (b.distance_m - a.distance_m) * (depth_m - a.depth_m) / (b.depth_m - a.depth_m)
    return None


def trestle_length(mode: str, xs: float | None, fixed_m: float, theta: float | None) -> float | None:
    """`waterside.trestle_len` — trestle: x*; mixed: θ · x* (θ dari rencana) atau panjang opsi keruk (≤ x*);
    dredge: 0 (tambatan di garis pantai). None bila trestle penuh tidak mungkin (x* tidak tercapai)."""
    if mode == "dredge":
        return 0.0
    if mode == "trestle":
        return xs
    if theta is not None and xs is not None:
        return theta * xs
    return fixed_m if xs is None else min(fixed_m, xs)


def pocket_length(term: KekTerminal, loa_m: float) -> float:
    """`waterside.pocket_length` — panjang kolam tambat per tambatan: dermaga menerus = panjang unit; jetty =
    1,175 LOA kapal penentu terminal (satu kapal satu jetty, A24)."""
    return term.berth_unit_length_m if term.berth_layout == "quay" else BERTH_AREA_LOA * loa_m


def pocket_width(beam_m: float) -> float:
    """`waterside.pocket_width` — lebar kolam tambat / area sandar = 1,5 B kapal penentu [m]."""
    return BERTH_AREA_BEAM * beam_m


def dredge_volume(n_berth: float, length_m: float, width_m: float, depth_req_m: float, tip_depth_m: float) -> float:
    """`waterside.dredge_vol` — nBerth · panjang · lebar kolam tambat · (kedalaman perlu − kedalaman di ujung trestle)."""
    return n_berth * length_m * width_m * max(0.0, depth_req_m - tip_depth_m)


def cost(trestle_area_m2: float, price_trestle: float, dredge_m3: float, price_dredge: float) -> float:
    """`waterside.cost` — biaya dasar (harga satuan tahun dasar, tanpa eskalasi & jadwal): luas trestle · Rp/m² +
    volume keruk · Rp/m³."""
    return trestle_area_m2 * price_trestle + dredge_m3 * price_dredge


@dataclass
class OptionDesign:
    """Desain satu opsi perairan untuk satu terminal (nilai akhir horizon)."""

    trestle_len: float
    tip_depth: float
    trestle_area: float
    dredge_vol: float
    cost_trestle: float
    cost_dredge: float
