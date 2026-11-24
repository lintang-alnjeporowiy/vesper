"""Kontrak data v2: satu `Case` = seluruh INPUT satu studi kasus TPT.

Aturan:
- Hanya input. Nilai turunan (payload dari DWT, ton/TEU dari kemasan, tarif TCH dari regresi,
  SFOC dari rentang daya, dst.) dihitung engine, bukan disimpan di sini — kecuali sebagai override.
- Setiap record punya `refs` (nama field -> sel Excel asal) dan `note` opsional.
- Referensi antar record memakai `id` string.
- Satuan ditulis di nama field (`_m`, `_kn`, `_t`, `_rp`, `_usd`, ...) dan di metadata JSON Schema.

Lihat docs/01_SPEC.md §4 (kontrak data) dan §11/§13 (keputusan).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1"
KEK = "KEK"  # id khusus untuk titik KEK di rute


def F(default=..., *, unit: str | None = None, desc: str | None = None, **kw):
    """Field dengan satuan & deskripsi (muncul di JSON Schema, dipakai UI)."""
    extra = {"unit": unit} if unit else None
    return Field(default, description=desc, json_schema_extra=extra, **kw)


class Rec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refs: dict[str, str] = F({}, desc="nama field -> sel Excel asal, mis. {'dwt_t': 'Data Kapal!M4'}")
    note: str | None = None


Rate = Annotated[float, Field(ge=0, le=1)]
Pos = Annotated[float, Field(gt=0)]
NonNeg = Annotated[float, Field(ge=0)]

# --------------------------------------------------------------------------------------------
# Meta & horizon
# --------------------------------------------------------------------------------------------


class CaseMeta(Rec):
    id: str
    name: str
    kek_name: str = F(desc="nama kawasan, mis. 'KI Batam'")
    kek_port_name: str = F(desc="nama pelabuhan/TERSUS di KEK")
    location: str | None = None
    description: str | None = None
    source_files: list[str] = []
    extracted_at: str | None = None


class Phase(Rec):
    name: str
    start_year: int = F(ge=1)
    end_year: int = F(ge=1)


class Horizon(Rec):
    years: int = F(20, ge=1, le=60, unit="th", desc="periode tinjauan")
    phases: list[Phase] = F(desc="tahap perencanaan (pendek/menengah/panjang)")
    construction_lead_years: int = F(1, ge=0, unit="th", desc="masa konstruksi sebelum dipakai")
    berth_lookahead_years: int = F(7, ge=0, unit="th", desc="dermaga dibangun untuk kebutuhan N tahun ke depan")
    storage_lookahead_years: int = F(5, ge=0, unit="th", desc="penyimpanan dibangun untuk kebutuhan N tahun ke depan")


# --------------------------------------------------------------------------------------------
# Parameter global
# --------------------------------------------------------------------------------------------


class Fuel(Rec):
    code: str
    name: str
    price_rp_per_l: Pos = F(unit="Rp/l")
    density_kg_m3: Pos = F(unit="kg/m³")


class PowerBand(Rec):
    min_kw: NonNeg = F(unit="kW")
    max_kw: float | None = F(None, unit="kW", desc="None = tanpa batas atas")
    sfoc_g_kwh: Pos = F(unit="g/kWh")


class ContainerSpec(Rec):
    inner_length_m: Pos = F(unit="m")
    inner_width_m: Pos = F(unit="m")
    inner_height_m: Pos = F(unit="m")
    tare_t: Pos = F(unit="ton")
    max_gross_t: Pos = F(unit="ton")
    max_net_t: Pos = F(unit="ton")
    share_20ft: Rate = F(1.0, desc="porsi petikemas 20' (sisanya 40')")


class GlobalParams(Rec):
    at_hours: NonNeg = F(unit="jam/call", desc="approach time")
    wt_hours: NonNeg = F(unit="jam/call", desc="waiting time")
    it_hours: NonNeg = F(unit="jam/call", desc="idle time")
    working_days_per_year: Pos = F(unit="hari")
    working_hours_per_day: Pos = F(unit="jam")
    commission_days: Pos = F(unit="hari/th", desc="hari operasi kapal per tahun")
    bor_max: Rate = F(desc="berth occupancy ratio maksimum")
    mcr: Rate = F(desc="maximum continuous rating mesin")
    fuel_share_me_sea: Rate
    fuel_share_me_port: Rate
    fuel_share_ae_sea: Rate
    fuel_share_ae_port: Rate
    fuels: list[Fuel]
    me_fuel: str = F(desc="kode BBM mesin induk (A6)")
    ae_fuel: str = F(desc="kode BBM mesin bantu (A6)")
    sfoc_me_bands: list[PowerBand]
    sfoc_ae_bands: list[PowerBand]
    ae_me_power_ratio: Rate = F(0.5, desc="daya AE default bila data kapal kosong")
    usd_rate: Pos = F(unit="Rp/USD")
    discount_rate: Rate = F(desc="WACC")
    escalation_infra: NonNeg = F(unit="/th", desc="kenaikan harga satuan infrastruktur")
    escalation_equipment: NonNeg = F(unit="/th", desc="kenaikan harga alat")
    ballast_speed_ratio: Pos = F(1.0, desc="V_ballast / Vs default (A5)")
    payload_dwt_ratio: Rate = F(desc="α payload: payload = α·DWT (A8)")
    teu_weight_dwt_ratio: Rate = F(desc="α batas berat per TEU: NetMax = α·DWT/TEU − tare (A8)")
    teu_capacity_dwt_ratio: Rate = F(desc="kapasitas TEU default = ⌊rasio·DWT / berat nominal per TEU⌋")
    teu_nominal_weight_t: Pos = F(unit="ton/TEU", desc="berat nominal per TEU untuk kapasitas TEU default")
    berth_loa_min_ratio: Pos = F(desc="kapal layak bila dermaga terpanjang ≥ rasio × LOA (mis. 0,85)")
    cargo_per_call_mode: Literal["interval", "full_load"] = F(
        "interval", desc="interval: q = D/F (K15); full_load: q = payload")
    container: ContainerSpec


# --------------------------------------------------------------------------------------------
# Muatan
# --------------------------------------------------------------------------------------------


class CargoForm(Rec):
    code: str = F(desc="CC, CK, PK, GC, …")
    name: str
    default_unit: Literal["ton", "TEU"]


class TchPoint(Rec):
    label: str | None = None
    size: Pos = F(desc="DWT atau TEU sesuai size_basis")
    usd_per_day: Pos = F(unit="USD/hari")


class ShipType(Rec):
    code: str
    name: str
    size_basis: Literal["dwt", "teu"] = F(desc="ukuran untuk regresi TCH")
    tch_points: list[TchPoint] = F([], desc="tabel tarif charter pasar; engine membuat regresi linier")


class Packaging(Rec):
    kind: str = F(desc="karung, kardus, batang, pelat, …")
    length_m: Pos = F(unit="m")
    width_m: Pos = F(unit="m")
    height_m: Pos = F(unit="m")
    weight_kg: Pos = F(unit="kg", desc="berat per kemasan")
    pieces_per_pack: int | None = F(None, ge=1)


class Commodity(Rec):
    id: str
    name: str
    cargo_form: str
    density_t_m3: float | None = F(None, gt=0, unit="t/m³")
    stowage_factor_m3_t: float | None = F(None, gt=0, unit="m³/t")
    packaging: Packaging | None = None


class Tenant(Rec):
    id: str
    name: str
    sector: str | None = None


class VolumeIndependent(Rec):
    mode: Literal["independent"] = "independent"
    start_year: int = F(ge=1, unit="th-ke")
    initial: Pos = F(desc="volume tahun mulai, satuan = unit flow")
    maximum: Pos = F(desc="batas volume")
    growth_rate: NonNeg = F(unit="/th")


class VolumeRatio(Rec):
    mode: Literal["ratio"] = "ratio"
    basis_flow_id: str = F(desc="flow acuan (biasanya inbound tenant yang sama)")
    ratio: Pos = F(desc="volume = ratio × volume flow acuan (awal & maks); growth & tahun mulai ikut acuan")


Volume = Annotated[VolumeIndependent | VolumeRatio, Field(discriminator="mode")]


class CargoFlow(Rec):
    id: str
    tenant_id: str
    direction: Literal["inbound", "outbound"]
    commodity_id: str
    cargo_form: str
    unit: Literal["ton", "TEU"] = F(desc="satuan definisi volume")
    route_id: str
    volume: Volume


# --------------------------------------------------------------------------------------------
# Pelabuhan & rute
# --------------------------------------------------------------------------------------------


class PortProductivity(Rec):
    mode: Literal["total", "per_equipment"] = F(desc="A3: total per kapal, atau per alat × jumlah alat")
    value: Pos
    unit: Literal["t/h", "TEU/h"]
    equipment_count: int | None = F(None, ge=1, desc="wajib bila mode per_equipment")


class ExternalPort(Rec):
    id: str
    name: str
    country: str | None = None
    kind: Literal["domestic", "foreign"]
    terminal_type: str | None = None
    max_draft_m: Pos = F(unit="m", desc="kedalaman/draft maksimum yang diizinkan")
    max_loa_m: float | None = F(None, gt=0, unit="m", desc="batas LOA eksplisit bila diketahui; None = tidak ada")
    longest_berth_m: float | None = F(
        None, gt=0, unit="m", desc="dermaga terpanjang; batasan: ≥ params.berth_loa_min_ratio × LOA. None = tidak dicek")
    productivity: PortProductivity
    tariff_class: Literal["utama", "1", "2", "3", "4", "5"]
    berth_type: Literal["beton", "dolphin"]


class Leg(Rec):
    origin: str = F(desc="id pelabuhan atau 'KEK'")
    destination: str
    distance_nm: Pos = F(unit="NM")
    laden: bool = F(desc="True = bermuatan (Vs), False = ballast")


class Route(Rec):
    id: str
    name: str
    pattern: Literal["round_trip", "triangle"] = "round_trip"
    legs: list[Leg] = F(min_length=2)


class KekTerminal(Rec):
    id: str
    name: str
    cargo_forms: list[str]
    berth_unit_length_m: Pos = F(unit="m")
    berth_width_m: Pos = F(unit="m")
    equipment_kind: str = F(desc="HMC, MLA, …")
    berth_layout: Literal["quay", "jetty"] = F(
        "quay", desc="quay = dermaga menerus (berth-days ∝ LOA / panjang unit); jetty = satu kapal satu jetty")
    trestle_width_m: Pos = F(unit="m", desc="lebar trestle dari pantai ke tambatan terminal ini (MP: jalan truk; "
                                             "jetty: pipa + catwalk), sama untuk semua opsi perairan")


class BathyPoint(Rec):
    distance_m: NonNeg = F(unit="m", desc="jarak dari garis pantai")
    depth_m: NonNeg = F(unit="m LWS")


class TrestleSpec(Rec):
    max_length_m: float | None = F(None, gt=0, unit="m", desc="batas fisik panjang trestle; kosong = tanpa batas "
                                                               "(trestle penuh gugur bila x* melebihi batas)")
    height_m: Pos = F(unit="m")
    unit_price_key: str = F("trestle", desc="kunci harga satuan trestle (Rp/m²) di unit_prices")


class TrestleDredgeSpec(Rec):
    trestle_length_m: Pos = F(unit="m", desc="panjang trestle opsi trestle + keruk per terminal (dibatasi x*); "
                                              "plans[].trestle_fraction θ, bila diisi, menggantikannya dengan θ · x*")
    unit_price_key: str = F("dredging", desc="kunci harga satuan pengerukan (Rp/m³) di unit_prices")


class WatersideConditions(Rec):
    wind_kn: NonNeg = F(unit="knot")
    cross_current_kn: NonNeg = F(unit="knot")
    longitudinal_current_kn: NonNeg = F(unit="knot")
    wave_height_m: NonNeg = F(unit="m")
    exposure: Literal["terbuka", "terlindungi"]
    maneuverability: Literal["baik", "sedang", "buruk"]
    nav_aids: Literal["sangat_baik", "baik", "cukup"]
    seabed: Literal["tanah_lunak", "tanah_keras"]
    channel_slope: Literal["landai", "sedang", "curam"]
    ship_speed_class: Literal["cepat", "sedang", "lambat"] = F(
        "sedang", desc="kelas kecepatan kapal di alur (menentukan Wa kecepatan, angin, arus, Wb, Ws)")
    lanes: Literal[1, 2] = 2
    long_channel: bool = F(False, desc="alur relatif panjang (menentukan rumus panjang alur)")
    high_frequency: bool = F(True, desc="frekuensi kapal tinggi (menentukan rumus panjang alur)")
    tug_assisted: bool = True
    depth_factor_of_draft: Pos = F(desc="kedalaman perlu = faktor × T kapal penentu (K15: 1,5)")


class KekSite(Rec):
    name: str
    terminals: list[KekTerminal]
    bathymetry: list[BathyPoint]
    bathymetry_source: Literal["survei", "peta_navigasi", "dummy"] = F(
        "dummy", desc="asal profil batimetri; 'dummy' = data contoh yang harus diganti")
    trestle: TrestleSpec
    trestle_dredge: TrestleDredgeSpec
    waterside: WatersideConditions
    port_charges: Literal["none", "tariff"] = F("none", desc="TERSUS milik sendiri: tanpa jasa kepelabuhanan")
    tariff_class: Literal["utama", "1", "2", "3", "4", "5"] | None = None


# --------------------------------------------------------------------------------------------
# Kapal & alat
# --------------------------------------------------------------------------------------------


class Ship(Rec):
    id: str
    name: str
    ship_type: str
    imo: str | None = None
    classification: str | None = None
    lpp_m: float | None = F(None, gt=0, unit="m")
    loa_m: Pos = F(unit="m")
    beam_m: Pos = F(unit="m")
    draft_m: Pos = F(unit="m")
    depth_m: float | None = F(None, gt=0, unit="m", desc="tinggi geladak H")
    speed_kn: Pos = F(unit="knot")
    ballast_speed_kn: float | None = F(None, gt=0, unit="knot", desc="None = Vs × ballast_speed_ratio")
    dwt_t: Pos = F(unit="ton")
    payload_t: float | None = F(None, gt=0, unit="ton", desc="override; None = payload_dwt_ratio × DWT")
    teu_capacity: int | None = F(
        None, ge=1, unit="TEU",
        desc="override bila data riil diketahui; None = ⌊teu_capacity_dwt_ratio·DWT / teu_nominal_weight_t⌋")
    gt: Pos = F(unit="GT")
    me_kw: Pos = F(unit="kW")
    ae_kw: float | None = F(None, gt=0, unit="kW")
    sfoc_me_g_kwh: float | None = F(None, gt=0, unit="g/kWh", desc="override; None = dari rentang daya")
    sfoc_ae_g_kwh: float | None = F(None, gt=0, unit="g/kWh")


class ProdRate(Rec):
    unload: Pos
    load: Pos
    unit: Literal["t/h", "box/h"]


class Equipment(Rec):
    id: str
    name: str
    kind: str = F(desc="HMC, MLA, …")
    terminal_id: str
    price_usd: Pos = F(unit="USD")
    productivity: dict[str, ProdRate] = F(desc="kode bentuk muatan -> laju")
    reach_m: float | None = F(None, gt=0, unit="m")
    lift_t: float | None = F(None, gt=0, unit="ton")
    in_reference_model: bool = F(True, desc="False = ada di data, tapi tidak dipakai model Excel")


class LoaBand(Rec):
    loa_min_m: NonNeg = F(unit="m")
    loa_max_m: float | None = F(None, unit="m")
    per_berth: int = F(ge=1)


class EquipmentRules(Rec):
    loa_bands: list[LoaBand] = F(desc="A10: jumlah alat per tambatan dari LOA kapal")
    max_per_berth: dict[str, int] = F(desc="terminal_id -> batas alat per tambatan")


# --------------------------------------------------------------------------------------------
# Tarif pelabuhan
# --------------------------------------------------------------------------------------------


class TugTariff(Rec):
    fixed_foreign_usd: NonNeg = F(unit="USD/gerakan")
    var_foreign_usd_per_gt: NonNeg = F(unit="USD/GT")
    fixed_domestic_rp: NonNeg = F(unit="Rp/gerakan")
    var_domestic_rp_per_gt: NonNeg = F(unit="Rp/GT")


class TariffClassRow(Rec):
    tariff_class: Literal["utama", "1", "2", "3", "4", "5"]
    labuh_foreign_usd_per_gt: NonNeg = F(unit="USD/GT/kunjungan")
    labuh_domestic_rp_per_gt: NonNeg = F(unit="Rp/GT/kunjungan")
    pandu_foreign_fixed_usd: NonNeg = F(unit="USD/gerakan")
    pandu_foreign_var_usd_per_gt: NonNeg = F(unit="USD/GT/gerakan")
    pandu_domestic_fixed_rp: NonNeg = F(unit="Rp/gerakan")
    pandu_domestic_var_rp_per_gt: NonNeg = F(unit="Rp/GT/gerakan")
    tambat_foreign_usd_per_gt_etmal: dict[Literal["beton", "dolphin"], NonNeg]
    tambat_domestic_rp_per_gt_etmal: dict[Literal["beton", "dolphin"], NonNeg]
    bm_foreign_rp_per_ton: NonNeg = F(unit="Rp/ton")
    bm_foreign_rp_per_teu: float | None = F(None, ge=0, unit="Rp/TEU")
    bm_domestic_rp_per_ton: NonNeg = F(unit="Rp/ton")
    bm_domestic_rp_per_teu: float | None = F(None, ge=0, unit="Rp/TEU")
    tug: list[TugTariff] = F(desc="satu entri per rentang GT (urutan = tug_gt_bands)")


class GtBand(Rec):
    gt_min: NonNeg
    gt_max: float | None = None


class TariffBook(Rec):
    classes: list[TariffClassRow]
    tug_gt_bands: list[GtBand]


# --------------------------------------------------------------------------------------------
# Penyimpanan, harga satuan
# --------------------------------------------------------------------------------------------


class ContainerYardParams(Rec):
    area_per_teu_m2: Pos = F(unit="m²/TEU")
    height_ratio: Rate = F(desc="rasio tinggi rata-rata / rencana")
    yor_max: Rate
    max_tiers: int = F(ge=1)
    empty_share: NonNeg = F(desc="porsi petikemas kosong terhadap isi")


class GeneralCargoStorageParams(Rec):
    f_area: Pos
    f_bulk: Pos
    stack_height_m: Pos = F(unit="m")
    sor_max: Rate


class DryBulkStorageParams(Rec):
    f_area: Pos
    capacity_ratio: Pos = F(desc="Rc")
    stack_height_m: Pos = F(unit="m")
    sor_max: Rate
    gross_volume_factor: Pos = F(1.0, desc="volume bruto = faktor × netto")
    silo_capacity_m3: float | None = F(None, gt=0, unit="m³")
    silo_fill_ratio: Rate = 0.8
    silo_price_usd: float | None = F(None, gt=0, unit="USD/unit")


class LiquidStorageParams(Rec):
    occupancy: Rate
    tank_capacity_m3: Pos = F(unit="m³")


class YardEquipment(Rec):
    id: str
    name: str
    cargo_form: str
    role: Literal["yard", "transport"] = F(
        "yard", desc="yard = alat penumpukan (jumlah dari arus/kapasitas, §5.6); transport = angkutan dermaga–lapangan "
                     "(truk per alat B/M × alat aktif, jarak = panjang trestle, §5.6; params speed_kmh, unload_min)")
    productivity: Pos = F(desc="yard: produktivitas per jam; transport: muatan per rit (box atau ton)")
    productivity_unit: str = F(desc="yard: TEU/jam, ton/jam, …; transport: box/rit, ton/rit")
    utilization: Rate
    unit_price_key: str | None = F(None, desc="kunci di unit_prices")
    params: dict[str, float] = {}


class StorageParams(Rec):
    dwell_time_mode: Literal["from_consumption", "fixed"] = F(
        "from_consumption", desc="K15: dwelling time = lama konsumsi per pengapalan")
    fixed_dwell_days: dict[str, float] = F({}, desc="commodity_id -> hari (mode fixed)")
    inbound_share: Rate = F(1.0, desc="porsi muatan inbound yang masuk penyimpanan")
    outbound_share: Rate = 1.0
    container_yard: ContainerYardParams
    general_cargo: GeneralCargoStorageParams
    dry_bulk: DryBulkStorageParams
    liquid: LiquidStorageParams
    yard_equipment: list[YardEquipment] = []


class UnitPrice(Rec):
    key: str
    label: str
    unit: str
    price_rp: NonNeg = F(unit="Rp")
    category: str | None = None
    year: int | None = None


# --------------------------------------------------------------------------------------------
# Rencana (keputusan) & asumsi
# --------------------------------------------------------------------------------------------


class Plan(Rec):
    id: str
    name: str
    description: str | None = None
    ship_by_flow: dict[str, str] = F(desc="flow_id -> ship_id")
    equipment_by_terminal: dict[str, str] = F(desc="terminal_id -> equipment_id")
    waterside_mode: Literal["trestle", "dredge", "mixed"] = F(
        desc="trestle = trestle penuh sampai x*; mixed = trestle + keruk; dredge = tambatan di garis pantai + keruk")
    trestle_fraction: float | None = F(None, ge=0, le=1, desc="θ opsi mixed: panjang trestle = θ · x* per terminal "
                                                              "(kosong = kek_site.trestle_dredge.trestle_length_m)")


class Assumption(Rec):
    id: str
    topic: str
    text: str
    status: Literal["dari_excel", "asumsi", "perlu_konfirmasi", "dikonfirmasi"]


# --------------------------------------------------------------------------------------------
# Case
# --------------------------------------------------------------------------------------------


class Case(Rec):
    schema_version: str = SCHEMA_VERSION
    meta: CaseMeta
    horizon: Horizon
    params: GlobalParams
    cargo_forms: list[CargoForm]
    ship_types: list[ShipType]
    compatibility: dict[str, list[str]] = F(desc="kode bentuk muatan -> kode tipe kapal yang boleh")
    commodities: list[Commodity]
    tenants: list[Tenant]
    flows: list[CargoFlow]
    ports: list[ExternalPort]
    routes: list[Route]
    kek_site: KekSite
    ships: list[Ship]
    equipment: list[Equipment]
    equipment_rules: EquipmentRules
    tariffs: TariffBook
    storage: StorageParams
    unit_prices: list[UnitPrice]
    plans: list[Plan] = []
    assumptions: list[Assumption] = []

    # ---- lookup helpers ----
    def by_id(self, collection: str) -> dict:
        key = "code" if collection in ("cargo_forms", "ship_types", "fuels") else "id"
        items = self.params.fuels if collection == "fuels" else getattr(self, collection)
        return {getattr(x, key): x for x in items}

    # ---- integrity ----
    @model_validator(mode="after")
    def _integrity(self) -> Case:
        errors: list[str] = []
        err = errors.append

        def unique(name: str, items, key="id"):
            seen: set[str] = set()
            for it in items:
                k = getattr(it, key)
                if k in seen:
                    err(f"{name}: id ganda '{k}'")
                seen.add(k)
            return seen

        forms = unique("cargo_forms", self.cargo_forms, "code")
        types = unique("ship_types", self.ship_types, "code")
        fuels = unique("params.fuels", self.params.fuels, "code")
        comms = unique("commodities", self.commodities)
        tenants = unique("tenants", self.tenants)
        flows = unique("flows", self.flows)
        ports = unique("ports", self.ports)
        routes = unique("routes", self.routes)
        ships = unique("ships", self.ships)
        equips = unique("equipment", self.equipment)
        terms = unique("kek_site.terminals", self.kek_site.terminals)
        unique("plans", self.plans)
        unique("assumptions", self.assumptions)
        unique("unit_prices", self.unit_prices, "key")
        classes = {c.tariff_class for c in self.tariffs.classes}

        p = self.params
        for f in (p.me_fuel, p.ae_fuel):
            if f not in fuels:
                err(f"params: BBM '{f}' tidak ada di params.fuels")
        for name, bands in (("sfoc_me_bands", p.sfoc_me_bands), ("sfoc_ae_bands", p.sfoc_ae_bands)):
            if not bands or bands[0].min_kw > 0:
                err(f"params.{name}: rentang harus mulai dari 0 kW")

        # horizon
        covered = set()
        for ph in self.horizon.phases:
            if ph.end_year < ph.start_year:
                err(f"horizon: tahap '{ph.name}' berakhir sebelum mulai")
            covered |= set(range(ph.start_year, ph.end_year + 1))
        if covered != set(range(1, self.horizon.years + 1)):
            err("horizon: tahap tidak menutup tahun 1..years tepat satu kali")

        # compatibility
        for form, tlist in self.compatibility.items():
            if form not in forms:
                err(f"compatibility: bentuk muatan '{form}' tidak dikenal")
            for t in tlist:
                if t not in types:
                    err(f"compatibility[{form}]: tipe kapal '{t}' tidak dikenal")

        # commodities
        for c in self.commodities:
            if c.cargo_form not in forms:
                err(f"commodity {c.id}: bentuk muatan '{c.cargo_form}' tidak dikenal")

        # terminals
        served: dict[str, str] = {}
        for t in self.kek_site.terminals:
            for form in t.cargo_forms:
                if form not in forms:
                    err(f"terminal {t.id}: bentuk muatan '{form}' tidak dikenal")
                if form in served:
                    err(f"bentuk muatan '{form}' dilayani dua terminal ({served[form]}, {t.id})")
                served[form] = t.id
        bathy = self.kek_site.bathymetry
        if any(b.distance_m <= a.distance_m for a, b in zip(bathy, bathy[1:])):
            err("kek_site.bathymetry: jarak harus naik")
        if self.kek_site.port_charges == "tariff" and self.kek_site.tariff_class not in classes:
            err("kek_site: port_charges='tariff' butuh tariff_class yang ada di tariffs")

        # ports & routes
        for pt in self.ports:
            if pt.tariff_class not in classes:
                err(f"port {pt.id}: kelas tarif '{pt.tariff_class}' tidak ada di tariffs")
            if pt.productivity.mode == "per_equipment" and not pt.productivity.equipment_count:
                err(f"port {pt.id}: mode per_equipment butuh equipment_count")
        nodes = ports | {KEK}
        for r in self.routes:
            touched = set()
            for lg in r.legs:
                for n in (lg.origin, lg.destination):
                    if n not in nodes:
                        err(f"route {r.id}: titik '{n}' tidak dikenal")
                    touched.add(n)
            if KEK not in touched:
                err(f"route {r.id}: harus melewati KEK")
            if r.legs[0].origin != r.legs[-1].destination:
                err(f"route {r.id}: rute harus kembali ke titik awal")

        # ships & equipment
        for s in self.ships:
            if s.ship_type not in types:
                err(f"ship {s.id}: tipe '{s.ship_type}' tidak dikenal")
        for e in self.equipment:
            if e.terminal_id not in terms:
                err(f"equipment {e.id}: terminal '{e.terminal_id}' tidak dikenal")
            for form in e.productivity:
                if form not in forms:
                    err(f"equipment {e.id}: bentuk muatan '{form}' tidak dikenal")
        bands = self.equipment_rules.loa_bands
        for a, b in zip(bands, bands[1:]):
            if a.loa_max_m is None or abs(a.loa_max_m - b.loa_min_m) > 1e-9:
                err("equipment_rules.loa_bands: rentang LOA harus bersambung")
        for t in self.equipment_rules.max_per_berth:
            if t not in terms:
                err(f"equipment_rules.max_per_berth: terminal '{t}' tidak dikenal")

        # flows
        flow_map = {f.id: f for f in self.flows}
        ships_by_type: dict[str, int] = {}
        for s in self.ships:
            ships_by_type[s.ship_type] = ships_by_type.get(s.ship_type, 0) + 1
        comm_map = {c.id: c for c in self.commodities}
        for f in self.flows:
            if f.tenant_id not in tenants:
                err(f"flow {f.id}: tenant '{f.tenant_id}' tidak dikenal")
            if f.commodity_id not in comms:
                err(f"flow {f.id}: komoditas '{f.commodity_id}' tidak dikenal")
            if f.route_id not in routes:
                err(f"flow {f.id}: rute '{f.route_id}' tidak dikenal")
            if f.cargo_form not in forms:
                err(f"flow {f.id}: bentuk muatan '{f.cargo_form}' tidak dikenal")
            elif f.cargo_form not in served:
                err(f"flow {f.id}: bentuk muatan '{f.cargo_form}' tidak dilayani terminal KEK mana pun")
            if not any(ships_by_type.get(t, 0) for t in self.compatibility.get(f.cargo_form, [])):
                err(f"flow {f.id}: tidak ada kandidat kapal yang kompatibel dengan '{f.cargo_form}'")
            if f.cargo_form in teu_forms(self) and f.unit == "ton":
                c = comm_map.get(f.commodity_id)
                if c and not (c.packaging or c.stowage_factor_m3_t):
                    err(f"flow {f.id}: muatan PK bersatuan ton butuh kemasan/SF untuk konversi ton→TEU")
            if isinstance(f.volume, VolumeRatio):
                b = flow_map.get(f.volume.basis_flow_id)
                if b is None:
                    err(f"flow {f.id}: flow acuan '{f.volume.basis_flow_id}' tidak dikenal")
                elif isinstance(b.volume, VolumeRatio):
                    err(f"flow {f.id}: flow acuan harus bervolume independen")
            elif f.volume.start_year > self.horizon.years:
                err(f"flow {f.id}: tahun mulai di luar periode tinjauan")
            elif f.volume.maximum < f.volume.initial:
                err(f"flow {f.id}: volume maks < volume awal")

        # plans
        for pl in self.plans:
            for fid, sid in pl.ship_by_flow.items():
                if fid not in flows:
                    err(f"plan {pl.id}: flow '{fid}' tidak dikenal")
                if sid not in ships:
                    err(f"plan {pl.id}: kapal '{sid}' tidak dikenal")
            for tid, eid in pl.equipment_by_terminal.items():
                if tid not in terms:
                    err(f"plan {pl.id}: terminal '{tid}' tidak dikenal")
                if eid not in equips:
                    err(f"plan {pl.id}: alat '{eid}' tidak dikenal")

        if errors:
            raise ValueError("Case tidak valid:\n- " + "\n- ".join(errors))
        return self


def teu_forms(case: Case) -> set[str]:
    """Bentuk muatan yang diangkut dalam TEU (default_unit = TEU)."""
    return {c.code for c in case.cargo_forms if c.default_unit == "TEU"}
