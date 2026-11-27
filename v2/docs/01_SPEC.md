# TPT Planner v2 — Spesifikasi Gambaran Besar

> Status: **DRAF 2** (2026-11-21) — hasil studi file TPT (laporan, PPT, 4 workbook Excel) dan review `apps/` (v1). Semua pertanyaan terbuka & temuan audit sudah diputuskan (§11, §13).
> Dokumen ini adalah *satu-satunya* sumber kebenaran v2. Sengaja dibuat ringkas: kalau ada yang kurang, tambahkan di sini, jangan bikin dokumen baru.
> Pendamping: [02_ROADMAP.md](02_ROADMAP.md) (tahapan + rekomendasi effort) dan [../blueprint/index.html](../blueprint/index.html) (peta variabel + peta layar interaktif).

---

## 1. Apa yang dibangun

**Aplikasi perencanaan transportasi laut untuk Kawasan Ekonomi/Industri (KEK/KI):** dari data soal (tenant, muatan, pelabuhan asal/tujuan, kandidat kapal, alat bongkar muat, kondisi perairan) aplikasi menghitung — dan bisa mengoptimasi — **armada kapal per rute** dan **kebutuhan terminal khusus (TERSUS/TUKS) di KEK** selama periode tinjauan (default 20 tahun), dengan biaya yang bisa dilacak sampai ke rumus dan input asalnya.

Satu kalimat produk:

> *"Excel TPT, tapi setiap angka bisa diklik untuk melihat dari mana asalnya, setiap parameter bisa digeser untuk melihat dampaknya, dan optimasinya dijamin optimum global."*

Tiga cara pakai yang harus didukung oleh **engine yang sama**:

| Mode | Pengguna memilih | Aplikasi menghitung |
|---|---|---|
| **Manual** | kapal per rute, alat B/M per terminal, trestle/keruk | seluruh rantai: frekuensi → armada → biaya → tambatan → investasi → unit cost |
| **Bandingkan** | satu rute | semua kandidat kapal feasible untuk rute itu, berdampingan (melihat trade-off) |
| **Optimasi** | objektif + batasan | kombinasi keputusan dengan total biaya minimum, plus penjelasan "kenapa" |

---

## 2. Pelajaran dari v1 dan prinsip v2

### 2.1 Diagnosis v1 (`apps/`)

v1 secara konsep domain sebenarnya cukup lengkap (dokumen `apps/docs/*` ~28.000 baris), tapi arah pengerjaannya membuat inti produk tidak pernah terlihat:

1. **Backend/database-first.** 6 fase habis untuk PostgreSQL + Alembic + CRUD (project, scenario, commodity, tenant, cargo flow, port, route, bathymetry, vessel). Satu-satunya hasil kalkulasi yang terlihat baru proyeksi demand. Rantai inti (frekuensi → armada → biaya → terminal → optimasi) belum ada.
2. **Navigasi berorientasi data master, bukan alur pengerjaan TPT.** Kapal & pelabuhan eksternal jadi halaman global di luar studi kasus; tab skenario berisi hal yang tidak ada di soal ("Simulasi Jaringan", "Finansial & Tarif") sementara langkah yang ada di soal (pemilihan alat B/M, fasilitas perairan, trestle vs keruk, staging investasi) belum punya tempat yang jelas.
3. **Interaksi antar variabel tidak kelihatan.** UI-nya form + tabel CRUD. Padahal nilai utama aplikasi ini justru "geser satu parameter → lihat efek berantai".
4. **Spesifikasi terlalu besar dan generik** ("professional planning platform"), sehingga agen cenderung membangun infrastruktur, bukan model TPT.
5. **Terikat environment NixOS** (`nix develop`, path `/home/...`) — tidak jalan di mesin Windows ini.

### 2.2 Prinsip v2

| # | Prinsip | Konsekuensi |
|---|---|---|
| P1 | **UI-first dengan placeholder.** Semua layar dibuat dulu dengan data contoh (kasus K15 Batam) dan angka dummy yang ditandai jelas. | Bentuk produk & alur disepakati sebelum engine ditulis. |
| P2 | **Satu dokumen kasus (Case) = satu file JSON.** Tidak ada database di awal. | Tidak ada CRUD/backend sampai benar-benar perlu. Import/export file. |
| P3 | **Engine murni (pure functions) di Python**, dipanggil UI lewat API tipis (FastAPI). Input Case → output lengkap per tahun. | Mudah dites (pytest), dekat dengan ekosistem data (openpyxl, HiGHS); tanpa database. |
| P4 | **Setiap variabel terdaftar di Registry** (id, label, satuan, rumus, dependensi, asal sheet Excel). | Peta variabel, panel "kenapa angka ini?", dan audit jadi otomatis. |
| P5 | **Golden test terhadap Excel K15** untuk bagian yang tidak terdampak temuan audit; bagian yang dikoreksi (§11) dites dengan hitungan tangan dan selisihnya vs Excel dijelaskan. **Tidak ada mode "kompatibel Excel".** | Kepercayaan terhadap angka tanpa membawa bug lama. |
| P6 | **Optimasi = koefisien hasil engine + solver MILP.** Bukan GA/Evolver. | Optimum global terjamin & bisa dijelaskan. |
| P7 | **Ikuti alur pengerjaan TPT** (Gambar 3-1 laporan K15): Muatan → Kapal → Operasi → Biaya → Terminal → Investasi → Optimasi. | Navigasi = urutan berpikir mahasiswa/perencana. |

---

## 3. Domain dalam satu halaman

```mermaid
flowchart LR
  subgraph Soal
    T[Tenant] --> FI[Muatan inbound<br/>komoditas, POL, vol awal, maks, growth, thn mulai]
    FI -->|rasio konversi| FO[Muatan outbound<br/>komoditas, POD]
  end
  FI & FO --> D[Proyeksi demand 20 th<br/>ton / TEU]
  D --> FREQ[Frekuensi & cargo per call]
  K[Kandidat kapal<br/>payload, Vs, T, LOA, GT, daya, SFOC, TCH] --> FEAS{Kompatibel &<br/>feasible?}
  P[Pelabuhan asal/tujuan<br/>draft, LOA maks, prod. B/M, jarak] --> FEAS
  FEAS --> FREQ
  FREQ --> RTD[Sea time + port time = RTD]
  A[Alat B/M KEK<br/>harga, prod., radius] --> RTD
  RTD --> N[Jumlah kapal]
  N & RTD --> SC[Biaya pelayaran<br/>BBM, TCH, pelabuhan]
  RTD --> BERTH[Tambatan & BOR KEK]
  D --> STOR[Penyimpanan<br/>CY, gudang, silo, tangki]
  K --> WATER[Fasilitas perairan<br/>kapal terbesar → kedalaman]
  B[Batimetri tapak KEK] --> DEV{Trestle vs keruk}
  WATER --> DEV
  BERTH & STOR & DEV & A --> INV[Investasi bertahap]
  SC & INV --> UC[Total cost → unit cost → PV → anuitas]
  UC --> OPT((Optimasi))
```

**Aliran muatan (flow)** adalah unit utama perhitungan: `tenant × arah (inbound/outbound) × komoditas`. Kasus K15 punya 10 flow (5 tenant × in/out). Setiap flow punya rute ke KEK, satu bentuk muatan, dan (dalam mode manual) satu kapal terpilih.

**Bentuk muatan (cargo form):** `CC` curah cair · `CK` curah kering · `PK` petikemas · `GC` general cargo. **Tipe kapal** adalah daftar per kasus (default: tanker, bulk carrier, kapal petikemas, general cargo, **LCT/tongkang**) dengan matriks kompatibilitas bentuk muatan × tipe kapal yang bisa diedit (mis. pelat baja → GC, petikemas, atau LCT).

**Armada homogen:** satu flow dilayani satu kapal terpilih (jumlah unitnya bisa >1). **Rute bolak-balik:** inbound `A-K-A`, outbound `K-F-K`; struktur data rute disiapkan supaya rute segitiga `A-K-F` bisa ditambahkan nanti.

**Terminal di KEK** dikelompokkan: **Multipurpose (MP)** melayani PK + GC + CK (HMC), **Curah cair (CC)** = jetty + MLA. Pengelompokan ini harus bisa diubah per kasus.

---

## 4. Kontrak data (isi file Case)

Semua input yang ada di Excel, dikelompokkan. Kolom "Asal" = sheet sumber di workbook K15 (kecuali disebut lain).

### 4.1 Kasus & parameter global — sheet `Model` (blok asumsi), `Investasi`
| Field | Contoh K15 | Catatan |
|---|---|---|
| nama KEK, lokasi, pelabuhan KEK | KI Batam, Batu Ampar | |
| periode tinjauan, tahun dasar | 20 th | |
| AT, WT, IT (jam/call) | 2, 2, 2 | K15 memakai total 6 jam/call |
| hari kerja/th, jam kerja/hari | 365, 24 | |
| commission days kapal/th | 365 | |
| BOR maks | 70 % | |
| MCR | 80 % | |
| % konsumsi ME/AE di laut/pelabuhan | ME laut 1, ME port 0, AE laut 0, AE port 1 | |
| harga & berat jenis BBM | MFO 18.600 Rp/l (890 kg/m³), HSD 24.000 Rp/l (832 kg/m³) | |
| jenis BBM per mesin | ME = HSD, AE = HSD | parameter (A6); K15 memakai AE = MFO |
| rasio V_ballast / Vs | 100 % | parameter global, bisa dioverride per kapal (A5); K15 memakai 130 % |
| α payload · α batas berat per TEU | 85 % DWT · 90 % DWT | dua parameter terpisah (A8) |
| kapasitas TEU default | ⌊0,85 · DWT / 20 t⌋ | dua parameter; dipakai bila `ships[].teu_capacity` kosong |
| rasio dermaga / LOA minimum | 85 % | kapal layak bila dermaga terpanjang ≥ 85 % LOA |
| kurs USD | 15.521 | |
| WACC / discount rate | 10 % | |
| eskalasi harga satuan/th | infra 1 %, alat 1 % (`Investasi!C15`, `C21`) | `escalation_infra/equipment`; dipakai hanya bila `apply_escalation` (default mati seperti Excel, A27; Tahap 8b) |
| horizon staging | pendek 1–5, menengah 6–10, panjang 11–20 | PM 51/2015 |
| masa konstruksi, lookahead | 1 th (`Investasi!C13`), tambatan 7 th, penyimpanan 5 th | tahun bangun = tahun pakai − masa konstruksi (A26) |
| pola bangun investasi | per tahap | `plans[].staging`: `phase` (default) \| `incremental` (Tahap 8b) |

### 4.2 Tenant & aliran muatan — sheet `Muatan`, `Proyeksi Muatan`
| Field | Contoh |
|---|---|
| tenant: nama, bidang | PT. Damai Sejahtera, makanan |
| flow inbound: komoditas, bentuk muatan, POL, vol awal, vol maks, satuan (ton/TEU), growth/th, tahun mulai | Jagung karung, GC, Badas, 3.000.000 t, 7.900.000 t, 5 %, th-1 |
| flow outbound: komoditas, bentuk muatan, POD, **aturan volume** | Tepung jagung, PK, Bangkok |
| aturan volume outbound | (a) rasio berat thd inbound (85 %, 55 %, 0,3 t NPI/t nikel), (b) rasio TEU (1 TEU Al = 2 TEU baja ringan), (c) volume sendiri |
| satu tenant boleh punya >1 flow per arah | K24: HSD + Avtur |

### 4.3 Komoditas & konversi ton↔TEU — sheet `Muatan`
massa jenis, stowage factor, kemasan (dimensi & berat per karung/kardus/batang, isi per kemasan), dimensi & tare petikemas 20'/40', rasio 20'/40'. Turunan: **ton per TEU** (lihat §5.1).

### 4.4 Pelabuhan eksternal (asal/tujuan) — sheet `Data Pelabuhan`, `Rute`
nama, negara, jenis terminal, **kedalaman/draft maks**, LOA maks, **produktivitas B/M** dengan mode input per pelabuhan — *total per kapal* (t/j atau TEU/j) **atau** *per alat × jumlah alat* (A3), komoditas yang dilayani, **jarak ke KEK (NM)**, AT/WT/IT khusus (opsional), tarif pelabuhan (§4.8).

**Dermaga vs LOA:** dermaga boleh lebih pendek dari kapal; kapal layak bila `dermaga terpanjang ≥ berth_loa_min_ratio · LOA` (default 85 %, wajar terutama untuk dermaga dolphin 1 dermaga 1 kapal). `max_loa_m` hanya diisi bila ada batas LOA eksplisit.

### 4.5 Tapak TERSUS di KEK — sheet `Trestle`, `Fasilitas Perairan`
profil batimetri (jarak dari garis pantai → kedalaman) dengan sumber `survei | peta_navigasi | dummy` (K15: dummy yang dikunci ke angka K15, siap diganti), harga satuan trestle (Rp/m²), keruk (Rp/m³), dermaga MP (Rp/m²), jetty CC, lebar tambatan, panjang unit tambatan (MP 300 m; CC sesuai jetty), tata letak tambatan `berth_layout` (`quay` dermaga menerus | `jetty` satu kapal satu jetty; Tahap 7a).

Perairan (Tahap 8a): lebar trestle **per terminal** `terminals[].trestle_width_m` (K15: MP 40 m `Trestle!C51`, CC 1,5 m `C60`); `trestle` = tinggi, `max_length_m` **opsional** (kosong = tanpa batas; K15 tidak punya batas — `Trestle!C50` = 500 m adalah x* batimetri dummy), `unit_price_key`; `trestle_dredge` = panjang trestle opsi trestle + keruk (K15 250 m, `C69`) + `unit_price_key` (kedalaman di ujung trestle dibaca dari batimetri, bukan diisi); kondisi perairan `waterside` (angin, arus melintang/memanjang, gelombang, eksposur, kemampuan manuver, SBNP, dasar laut, kemiringan alur, **kelas kecepatan kapal** `ship_speed_class` `cepat | sedang | lambat` (K15 `L6` = sedang), jumlah jalur, alur panjang, frekuensi tinggi, kapal tunda, faktor kedalaman ÷ draft, **batas kedalaman** opsional `max_depth_m` (Tahap 8b: kapal dengan faktor · T > batas gugur di kelayakan; K15 kosong)). Opsi perairan rencana `plans[].waterside_mode` (`trestle | mixed | dredge`) dan fraksi trestle θ `plans[].trestle_fraction` (opsional, menggantikan panjang trestle opsi campuran dengan θ · x*).

Investasi (Tahap 8b): `terminals[].berth_price_key` = kunci `unit_prices` harga tambatan (K15 MP `dermaga_multipurpose` Rp/m, CC `jetty_curah_cair` Rp/unit); basis harga dibaca dari kolom satuan: m → tambatan × panjang unit, m² → × lebar dermaga juga, lainnya per tambatan/jetty.

### 4.6 Kandidat kapal — sheet `Data Kapal`, `TCH`
| Field | Catatan |
|---|---|
| tipe kapal | dari daftar tipe kapal kasus (termasuk LCT/tongkang) |
| IMO, nama, klasifikasi | |
| LPP, LOA, B, T, H | T → draft check; LOA → panjang tambatan & jumlah alat |
| Vs, V ballast | V ballast = rasio global × Vs (default 100 %), atau diisi per kapal |
| DWT, payload (ton) / kapasitas TEU, GT | payload default = α · DWT; kapasitas TEU diisi manual bila data riil diketahui, kosong = rumus parameter |
| daya ME, daya AE | AE default 50 % ME |
| SFOC ME/AE | lookup dari rentang daya (tabel di sheet `Data Kapal`) |
| **TCH** | regresi linier `TCH/hari = a·ukuran + b` per tipe kapal (ukuran = DWT atau TEU), dari tabel tarif charter |

### 4.7 Alat bongkar muat — sheet `Alat BM`
nama (Liebherr LHM 180…600, EMCO Wheaton / Shanghai Eminent MLA), tipe (HMC/MLA/…), harga, **produktivitas per bentuk muatan** (GC t/j, PK box/j, CK t/j, CC t/j), radius jangkauan (m). Aturan jumlah alat per tambatan dari LOA (K15: <90 m→1, 90–160→2, 160–180→3, 180–350→4).

### 4.8 Tarif pelabuhan — sheet `Biaya Pelabuhan`
per pelabuhan (termasuk KEK): labuh (per GT per kunjungan; dalam/luar negeri), pandu (tetap + variabel per GT per gerakan), tambat (per GT per etmal; beton/dolphin), tunda (per GT range), bongkar muat (per ton / per TEU).

### 4.9 Parameter penyimpanan — sheet `Fasilitas Daratan`
per komoditas: dwelling time (hari), tinggi tumpukan/ratio, YOR/occupancy, f_area, f_bulk, A_TEU, kapasitas silo/tangki, porsi inbound yang masuk penyimpanan (K21: 50 %) dan outbound (100 %). Alat lapangan per bentuk muatan dengan `role` (`yard` = alat penumpukan, `transport` = truk dermaga–lapangan, Tahap 8a: `productivity` = muatan per rit (box/rit atau ton/rit, satuan harus sejalan dengan produktivitas alat B/M), `params.speed_kmh`, `params.unload_min` = waktu bongkar di lapangan (kosong → dari produktivitas alat lapangan bentuk muatan itu, mis. RTG); K15: truk petikemas 1 box/rit, truk curah & GC 25 t/rit, 15 km/jam, bongkar 3 menit). Acuan K15 = sheet `Fasilitas Daratan` (dirujuk `Investasi` & `Rangkuman`); `Fasilitas Daratan Rata2` tidak dirujuk sheet mana pun dan bukan acuan (keputusan Tahap 7b: 6 tier, f_area curah 1,5, tanpa faktor bruto 1,3, dozer 20 t/jam).

Harga penyimpanan (Tahap 8b, keputusan pengguna: harga = parameter yang bisa diganti): `container_yard.unit_price_key`, `general_cargo.unit_price_key`, `dry_bulk.unit_price_key` (menggantikan `silo_price_usd`), `liquid.unit_price_key`, `liquid.pipe_price_key` → kunci `unit_prices`. Bawaan K15 mengikuti Excel: CY `lapangan_penumpukan_petikemas`, GC `lapangan_penumpukan_general_cargo` (gudang dihargai sebagai lapangan GC), silo **`tanki_curah_cair`** (Excel memakai harga tangki; harga silo spesifikasi `Fasilitas Daratan!AC144` tersedia sebagai `unit_prices.silo`), tangki `tanki_curah_cair`, pipa `pipa`. Alat lapangan & truk memakai `unit_price_key` masing-masing; truk curah & truk GC = `headtruck` (Excel tidak menghargai truk, A25).

---

## 5. Rantai kalkulasi (kanonis)

Setiap baris tabel di bawah = satu variabel di registry (`engine/src/tpt_engine/registry.py`, §9.3); id registry dipakai UI untuk jejak.

Notasi: flow `f`, tahun `t`, kapal `k`, alat `e`, terminal `τ ∈ {MP, CC}`. Semua output per tahun kecuali disebut lain. ⌈·⌉ = ROUNDUP, ⌊·⌋ = ROUNDDOWN.

### 5.1 Demand & konversi muatan
| Variabel | Rumus | Asal |
|---|---|---|
| `D[f,t]` demand | 0 jika t < t₀; `V₀` di t₀; `min(Dmax, D[t-1]·(1+g))` | Proyeksi Muatan |
| outbound | `r · D_in[t]` (aturan volume §4.2) | Proyeksi Muatan |
| `nBox` per TEU | `min(⌊Lc/l⌋·⌊Wc/w⌋·⌊Hc/h⌋, ⌊NetMax/w_box⌋)` | Muatan |
| `tonPerTEU` | `nBox · w_box` bila ada data kemasan; selain itu `Vc/SF` (atau `Vc·ρ`); selalu ≤ `NetMax` | Muatan |
| `NetMax` | `min(payload kontainer, 0,9·DWT_k / TEU_k − tare)` → **bergantung kapal** | Muatan |
| `D_TEU` | `⌈D_ton / tonPerTEU⌉`; flow yang sudah dalam TEU: `⌈D⌉` — dibulatkan **sekali**, setelah proyeksi kontinu (A12) | Proyeksi Muatan |

**Implementasi Tahap 4 (2026-11-22)** — `tpt_engine/calc/demand.py` (`demand_base`, `demand_ratio`, `project_flows`), `calc/cargo.py` (`net_max`, `box_per_teu`, `ton_per_teu`, `demand_unit`), `calc/vessel.py` (`teu_capacity`, didahulukan dari Tahap 5 karena dipakai NetMax), orkestrasi `calc/run.py` (`calculate(case, modules, plan_id, ship_by_flow)`). Variabel bergantung kapal memakai kapal per flow dari plan (default plan pertama kasus) + override dari UI. `D` disimpan kontinu dalam satuan flow; `V₀` ikut dibatasi `Dmax`; rantai flow rasio boleh bertingkat (siklus ditolak). Kemasan dimuat sesuai orientasi input (tanpa rotasi). Validasi K15 (`tests/test_calc_demand.py`): 6 flow ton & proyeksi out.fantasi = Excel persis; tonPerTEU tepung jagung/terigu/aluminium = Excel; selisih hanya A12 (out.damai th-1 +1 TEU, in/out.fantasi ≤ 6 TEU). Baja ringan: Excel memakai SF 0,6 (`Muatan!C75`, tidak ada di kasus) → 9,749 t/TEU; engine dari kemasan batang → 2.156 batang = 9,745 t/TEU (tidak di golden; flow TEU sehingga tak memengaruhi D).

### 5.2 Kandidat & kelayakan kapal
| Variabel | Rumus |
|---|---|
| `payload[k]` | GC/CK/CC: `α·DWT` (α 0,85–0,9), opsional dibatasi volume ruang muat/SF; PK: `teu_capacity` atau `⌊0,85·DWT / 20⌋` (cek `TEU·tonPerTEU ≤ 0,9·DWT`) |
| `compatible[f,k]` | tipe kapal k ∈ tipe yang diizinkan untuk bentuk muatan f (matriks, bisa diedit) |
| `feasible[f,k]` | compatible ∧ `T_k ≤ draft pelabuhan eksternal` ∧ `dermaga terpanjang ≥ 0,85·LOA_k` ∧ `LOA_k ≤ max_loa` (bila diisi) ∧ (opsional) `T_k·(1+UKC) ≤ kedalaman rencana KEK` |
| `nEq[k]` | jumlah alat/tambatan dari tabel rentang LOA |
| `reach_ok[k,e]` | radius alat ≥ kebutuhan jangkauan (≈ B kapal + margin) — **ditunda ke Tahap 7** (margin belum ada di kasus) |

**Implementasi Tahap 5 (2026-11-22)** — `calc/vessel.py`: `payload` (TEU = kapasitas TEU efektif; ton = isian atau α·DWT; cek berat per TEU sudah dijamin NetMax §5.1), `compatible`, `feasibility` (per pelabuhan eksternal di rute: draft, dermaga terpanjang ≥ rasio·LOA, LOA maks; panjang dermaga kosong → LOA tidak dicek, dicatat sebagai *notes*; kedalaman KEK tidak membatasi karena dirancang mengikuti kapal di Tahap 8), `n_equipment` (rentang `[min, max)`, di atas rentang terakhir = rentang terakhir, dibatasi `max_per_berth` terminal), `ballast_speed`. Kecepatan = Vs kapal; keputusan kecepatan (dv.speed, I2) **ditunda** (keputusan pengguna).

### 5.3 Operasi pelayaran — sheet `Model` baris 28–235
| Variabel | Rumus | Satuan |
|---|---|---|
| `F_req` frekuensi | `⌈D / payload⌉` | call/th |
| `q` cargo per call | mode *full-load*: `payload`; mode *interval*: `D / F` | ton/TEU |
| `tPortKEK` | `q / (prod_e,form · nEq) / 24` | hari/call |
| `tPortExt` | `q / prodTotal_port / 24`; `prodTotal` = angka total per kapal **atau** `prod_per_alat · nAlat_port`, sesuai mode input pelabuhan (A3) | hari/call |
| `tFix` | `(AT+WT+IT)/24` | hari/call |
| `tSea` | `(jarak/Vs + jarak/V_ballast) / 24` | hari/call |
| `RTD` | `tSea + tPortKEK + tPortExt + tFix` | hari |
| `F_max` per kapal | `⌊CD / RTD⌋` (K15 memakai ⌈⌉ — temuan audit) | call/kapal/th |
| `N_ship` | `⌈F_req / F_max⌉` | unit |
| `lamaKonsumsi` | `q / (D/365)` | hari stok per pengapalan |
| utilisasi kapal (metrik) | `F_req / (N_ship · F_max)` | – |

**Implementasi Tahap 5 (2026-11-22)** — `calc/voyage.py` + `run.voyage_chain`. Terminal flow = terminal KEK yang melayani bentuk muatannya; alat = `plan.equipment_by_terminal` (+ override). Arah: inbound = bongkar di KEK / muat di asal, outbound sebaliknya (`ProdRate.unload/load`). Laju dikonversi ke satuan kapal: box/j → TEU/j lewat `share_20ft` (TEU per box = s + 2(1−s); K15 = 1), t/j ↔ TEU/j lewat tonPerTEU. Pelabuhan eksternal = ujung non-KEK leg bermuatan; `tSea` = Σ leg (Vs bila bermuatan, V ballast bila kosong). `tFix` sekali per call. Tahun tanpa demand: semua seri 0 (seperti Excel). Excel menyimpan port time sebagai hari/tahun (`Model!M68`, `M82`) dan `tFix` di dalam port time per call (`M182`); engine hari/call. Validasi (`tests/test_calc_voyage.py`, `tests/excel_k15.py`, `tools/diff_k15.py`): tiruan rumus Excel mereproduksi golden K15 persis (10 flow × 11 seri × 20 th), dan tiruan yang sama + koreksi A1, A2, A3, A5, A10, A13 + D_TEU engine (A12) = engine persis → setiap selisih vs Excel terjelaskan. Contoh tahun pertama: jumlah kapal berubah di in.baru (4→5, A5), out.damai & out.fantasi (3→4, A3), out.esa (2→1, A2), out.baru (3→4, A10).

### 5.4 Biaya pelayaran — sheet `Model` 246–338, `TCH`, `Biaya Pelabuhan`
| Variabel | Rumus |
|---|---|
| BBM ME | `P_ME · MCR · SFOC_ME · tSea·24 · F · %ME_laut` (+ porsi di pelabuhan) → liter via berat jenis → × harga; **F = frekuensi aktual** (A9), jenis BBM = parameter (default HSD) |
| BBM AE | `P_AE · SFOC_AE · (tPort+tFix)·24 · F · %AE_port` → liter → × harga; jenis BBM = parameter (default HSD) |
| Voyage cost | BBM ME + BBM AE |
| TCH | `(a_tipe·ukuran_k + b_tipe) · kurs · CD · N_ship` |
| Biaya pelabuhan | `F · Σ_{pelabuhan∈{ext, KEK}} [labuh(GT) + pandu(GT, gerakan) + tambat(GT, etmal) + tunda(GT) + B/M(q)]` |
| **Shipping cost** | voyage + TCH + biaya pelabuhan (+ CHC bila dipisah) |
| biaya pelayaran per satuan (metrik) | `shipping cost / D`, satuan flow (A7) — kolom Rp/t layar 6–7 |

**Implementasi Tahap 6 (2026-11-22)** — `calc/shipcost.py` + `run.cost_chain`; modul API `shipcost` (menarik `voyage`, `demand`).
- **BBM:** `P · MCR · SFOC · 24 · (tSea · porsi laut + (tPort + tFix) · porsi pelabuhan) · F ÷ berat jenis`, satu rumus untuk ME dan AE — MCR = faktor beban kedua mesin (K15: porsi ME laut 1/pelabuhan 0, AE laut 0/pelabuhan 1 → identik dengan Excel, yang mengalikan MCR ke AE). SFOC dari rentang daya (rentang terakhir dengan `min_kw ≤ P`, seperti MATCH Excel), P_AE default 50 % P_ME. Berat jenis & harga dari `params.fuels` sesuai `me_fuel`/`ae_fuel` (A6, default HSD). F = frekuensi aktual (A9).
- **TCH:** regresi linier kuadrat terkecil per tipe kapal (= SLOPE/INTERCEPT Excel); ukuran = DWT, atau kapasitas TEU efektif untuk tipe `size_basis = teu`; biaya = tarif · kurs · CD · N_ship. Tipe dengan < 2 titik tarif (LCT) → galat data. Tarif TCH & SFOC = Excel untuk ke-41 kapal (dites).
- **Biaya pelabuhan per call** (keputusan pengguna 2026-11-22): labuh/GT per kunjungan; pandu & tunda `(tetap + var·GT) × 2 gerakan` (masuk + keluar; tunda per rentang GT); tambat `tarif/GT/etmal · GT · ⌈tPortExt⌉ etmal` (lama sandar di pelabuhan itu, dibulatkan ke etmal); B/M `q × tarif per ton` (atau per TEU untuk petikemas) **masuk** shipping cost. Pelabuhan luar negeri memakai kolom USD × kurs (A14). TERSUS KEK `port_charges = none` → 0; bila `tariff`, kelas `kek_site.tariff_class`, dalam negeri, beton, lama sandar `⌈tPortKEK⌉`. Biaya per tahun = per call × F (A11). Rincian per komponen ikut di respons (`port_breakdown`).
- **Validasi:** tiruan rumus Excel (`tests/excel_k15.py`) mereproduksi golden BBM, TCH, biaya pelabuhan, shipping cost persis (toleransi 1e-6 karena konstanta liter/ton Excel dibulatkan) dan tiruan + koreksi A6, A9, A11, A14, A15 (+ koreksi Tahap 5) = engine persis; hitungan tangan in.damai (Badas, dalam negeri) & out.damai (Bangkok, luar negeri).

### 5.5 Terminal KEK: tambatan, BOR, alat — sheet `Model` 104–152, 361–377
| Variabel | Rumus |
|---|---|
| `shipDays[f]` | `F · (tPortKEK + IT)` — bongkar muat + idle time di tambatan; AT & WT tidak menempati tambatan (A17) |
| `berthDaysReq[f]` | dermaga menerus (`berth_layout = quay`): `⌈shipDays · LOA_k / L_unit,τ⌉`; jetty: `⌈shipDays⌉` (satu kapal satu jetty, A16) |
| `nBerth[τ]` | `⌈Σ_f∈τ berthDaysReq / (BOR_max · WD)⌉`, tidak pernah turun (tambatan yang sudah dibangun tetap ada) |
| `BOR[τ]` | `Σ berthDaysReq / (nBerth · WD)` (= `Σ shipDays / (nBerth · (Σ shipDays / Σ berthDaysReq) · WD)` Excel) |
| panjang dermaga | `nBerth[τ] · L_unit,τ` (jetty: panjang platform per jetty) |
| `nAlat[τ]` | `nBerth[τ] · nEq(kapal terpanjang yang melayani τ tahun itu, kumulatif)`; penambahan per tahun |

**Implementasi Tahap 7a (2026-11-23)** — `calc/terminal.py` + `run.terminal_chain`; modul API `terminal` (menarik `voyage`, `demand`), nilai per flow (`terminal.ship_days`, `terminal.berth_days`) dan per terminal (`terminal.n_berth`, `bor`, `berth_length`, `n_equip`, kunci = id terminal). Input baru `kek_site.terminals[].berth_layout` (`quay | jetty`; K15: MP quay, CC jetty). Keputusan pengguna: shipDays + IT (A17), jetty satu kapal satu jetty (A16). Kebutuhan per tahun saja; jadwal bangun dengan masa konstruksi & lookahead (`horizon.construction_lead_years`, `berth_lookahead_years`) dipindah ke §5.8 (Tahap 8). Validasi: tiruan Excel `excel_terminal` = golden `Model!K101:AD363` (ship-days, berth-days, tambatan, BOR, alat MP/CC) dan tiruan + koreksi (A2, A10, A16, A17 di atas koreksi flow) = engine; hitungan tangan MP tahun 8. Penyimpanan (§5.6) = Tahap 7b (lihat §5.6).

### 5.6 Penyimpanan — sheet `Fasilitas Daratan`
| Fasilitas | Rumus (Q = porsi masuk · D per flow, TEU untuk petikemas; Tdw = lama konsumsi tahun itu) |
|---|---|
| Lapangan penumpukan PK | `A = (1 + porsi kosong) · Q_TEU · Tdw · A_TEU / (365 · H_ratio · YOR)`; ground slot `= (1 + porsi kosong) · Q·Tdw / (365 · H_ratio · YOR · tier maks)` |
| Gudang/lapangan GC | `A = Q · Tdw · f_area · f_bulk / (365 · ρ · H · SOR)` |
| Curah kering (silo; lapangan alternatif) | `V_silo = faktor bruto · Q·Tdw·Rc / (365·ρ·SOR)`, `nSilo = ⌈V / (cap · rasio isi)⌉`; lapangan `A = f_area · V_netto / H` |
| Curah cair (tangki) | `V = Q · Tdw / (365 · ρ · occupancy)` per produk, `nTangki = ⌈V/cap⌉` per produk |
| Alat lapangan (`role = yard`) | `⌈Σ_bentuk Q (petikemas × (1 + porsi kosong)) / (produktivitas · utilisasi · WD · jam/hari)⌉` — satu armada per bentuk muatan |
| Truk dermaga–lapangan (`role = transport`, Tahap 8a) | per alat B/M `⌈siklus / t_muat⌉`, `t_muat = 60 · muatan per rit / laju alat B/M` (bongkar untuk inbound, muat untuk outbound; maks antar flow aktif), `siklus = t_muat + 2 · jarak / kecepatan · 60 + t_bongkar lapangan` [menit]; × alat B/M aktif `min(nAlat[τ], nEq_maks · ⌈Σ shipDays bentuk itu / WD⌉)`; jarak = panjang trestle desain terminal (opsi rencana); tidak pernah turun (A25) |
| Pipa dermaga–tangki (`storage.pipeline`, Tahap 8b) | per flow curah cair sejak pertama aktif: `trestle desain terminal + LOA kapal flow · jetty[τ]` (aturan `Fasilitas Daratan!F239:F240`; Excel memakai trestle opsi keruk 250 m, A30); tidak pernah turun |

Dengan Tdw = lama konsumsi = `q / (D/365)`, stok `Q · Tdw / 365` = **satu muatan per call**: luas/volume mengikuti ukuran kapal (I1), bukan langsung demand. Kapasitas terpasang per fasilitas (kunci `total`) = Σ flow, tidak pernah turun.

**Implementasi Tahap 7b (2026-11-23)** — `calc/storage.py` + `run.storage_chain`; modul API `storage` (menarik `voyage`, `demand`). Variabel per flow + kunci `total` per fasilitas: `storage.dwell`, `throughput`, `cy`, `cy_slots`, `gc`, `bulk`, `bulk_area`, `silos`, `liquid`, `tanks`; `storage.yard_equipment` berkunci id alat (RTG, forklift, dozer). Input baru `storage.yard_equipment[].role` (`yard | transport`). Keputusan (opsi rekomendasi, pengguna melanjutkan tanpa memilih): golden = sheet `Fasilitas Daratan`; dwell per tahun (A18); alat lapangan satu armada per bentuk muatan (A19); truk ditunda ke Tahap 8 (jarak dermaga–lapangan = panjang trestle; rumus truk Excel memakai satuan keliru — produktivitas box/jam ÷ 60 dianggap menit). Kekeliruan Excel tanpa dampak angka K15 (tidak diberi ID): luas petikemas kosong = salinan luas full (`F29:F32`, porsi kosong `F37` tidak dipakai; K15 = 100 %), `F48` memakai dwell outbound untuk kosong inbound tahun ke-1 (muatan 0), `F233` memakai kapasitas tangki RBD untuk CPO (sama 20.000 m³). Validasi: tiruan Excel `excel_storage` = golden `Fasilitas Daratan` (dwell, luas CY, ground slot, RTG full/kosong per flow, silo, gudang, tangki, forklift, dozer; 20 th) dan tiruan + koreksi (A12, A13, A18, A19, A20) = engine untuk setiap variabel & kunci; hitungan tangan stok = satu pengapalan; forklift & dozer = Excel persis. Investasi penyimpanan (termasuk temuan baris `Investasi!N78` yang memakai penambahan, bukan total luas gudang) = Tahap 8.

### 5.7 Fasilitas perairan & trestle vs keruk — sheet `Fasilitas Perairan`, `Trestle`
**Kapal penentu (governing vessel)** = per terminal per tahun: LOA, B, dan T **masing-masing** maksimum kumulatif kapal rencana flow aktif (F > 0) di terminal itu; kunci `site` = semua terminal, dipakai alur & kolam putar (A21).

| Variabel | Rumus |
|---|---|
| kedalaman perlu `D[τ]` | `faktor · T[τ]` (K15: 1,5 T, `waterside.depth_factor_of_draft`) |
| lebar alur | 1 jalur `Wm + ΣWa + 2Wb`; 2 jalur `2(Wm + ΣWa) + 2Wb + Ws`, kelipatan B kapal penentu tapak. Tabel PIANC (`Fasilitas Perairan!B11:G84`, konstanta engine): Wm dari kemampuan manuver; Wa dari kelas kecepatan, angin, arus melintang & memanjang, gelombang, SBNP, dasar laut dan kedalaman (keduanya 0 bila h ≥ 1,5 T); Wb dari kemiringan alur; Ws dari kecepatan (A22) |
| panjang alur | alur panjang 2L (frekuensi tinggi) / 1,5L; pendek 1,5L / L |
| pintu masuk, jarak henti, kolam putar, radius labuh | `1 LOA`, `7 LOA`, diameter `2 LOA` dengan kapal tunda / `4 LOA` tanpa, luas `π(D/2)²` (A23), `L + 6D` |
| `x*[τ]` | jarak pertama dari pantai dengan batimetri ≥ `D[τ]` (interpolasi linier); tidak tercapai → peringatan, opsi trestle & campuran tidak layak |
| kolam tambat | panjang per tambatan: dermaga menerus = panjang unit, jetty = `1,175 LOA`; lebar `1,5 B` kapal penentu terminal (A24) |
| opsi **trestle** | trestle `x*`, tanpa keruk |
| opsi **trestle + keruk** (`mixed`) | trestle `min(L_opsi, x*)` (`trestle_dredge.trestle_length_m`) atau `θ · x*` bila `plans[].trestle_fraction` diisi; keruk kolam tambat `nBerth · panjang · lebar · (D − kedalaman di ujung trestle)` |
| opsi **keruk** (`dredge`) | tambatan di garis pantai (trestle 0), keruk kolam tambat dari kedalaman batimetri di 0 m |
| biaya dasar | `panjang trestle · lebar trestle terminal · Rp/m² + volume keruk · Rp/m³`, harga tahun dasar (eskalasi & jadwal bangun di §5.8); trestle > `max_length_m` → opsi tidak layak |

**Implementasi Tahap 8a (2026-11-24)** — `calc/waterside.py` (tabel PIANC & fungsi per baris) + `run.waterside_chain`, `run.truck_chain`; modul API `waterside` (menarik `demand`, `voyage`, `terminal`): 18 variabel `waterside.*` berkunci terminal (`MP`, `CC`) atau `site`, plus `storage.trucks` berkunci id alat transport (butuh panjang trestle). Respons menambah `waterside_options` (ketiga opsi: panjang trestle, θ, kedalaman ujung, luas trestle, volume keruk, biaya per terminal & total, layak/alasan, `selected`), `governing_ships` (terminal | site → loa/beam/draft → id kapal akhir horizon) dan `channel_parts` (komponen lebar alur).
- **Keputusan pengguna (2026-11-24):** kapal penentu per terminal per tahun mengikuti rencana kapal (A21); keruk hanya kolam tambat seperti Excel — alur & kolam putar dicatat sebagai dimensi tanpa biaya; truk = truk per alat × alat B/M aktif (A25); alokasi biaya bersama berbasis pemakaian (§13 no. 9, diterapkan Tahap 8c).
- **Semantik desain:** perairan dirancang untuk kebutuhan **akhir horizon** dan ada sejak tahun pertama terminal punya tambatan; seri `trestle_len`, `tip_depth`, `pocket_*` konstan sejak tahun itu, `dredge_vol` dan `cost` mengikuti jumlah tambatan tahun itu (keadaan terpasang, bukan penambahan — penambahan & jadwal di 8b). Variabel `waterside.*` mengikuti opsi rencana `plans[].waterside_mode`; engine tidak memilih otomatis — UI menandai opsi termurah, pemilihan otomatis = `dv.waterside` di optimizer (Tahap 9).
- **Kasus:** input baru `terminals[].trestle_width_m`, `trestle.unit_price_key`, `trestle_dredge.unit_price_key`, `waterside.ship_speed_class`; `trestle.max_length_m` jadi opsional; dihapus `trestle.width_mp_m/width_jetty_m`, `trestle_dredge.trestle_width_m/existing_depth_m`. Truk diekstrak ulang dari `Fasilitas Daratan` (tambah truk GC).
- **Validasi:** tiruan Excel `excel_waterside` = golden 49 sel `Fasilitas Perairan`/`Trestle` (termasuk volume keruk per fase dan biaya opsi terpilih `Model!K395` Rp 415 M), `excel_trucks` = golden truk `Fasilitas Daratan!F118:F217`; tiruan + koreksi A21–A25 (di atas koreksi flow & terminal) = engine untuk setiap variabel, kunci, opsi, dan truk. Hitungan tangan: x* CC = 541,4 m, lebar alur 9,4 B = 402,3 m, kolam putar π · 255², volume keruk opsi campuran. I8 didemokan di test (batimetri lebih dalam → lebih murah; kedalaman tak tercapai → trestle tidak layak; panjang maks). K15 terkoreksi (opsi rencana trestle penuh): trestle penuh Rp 416,2 M, trestle + keruk Rp 339,0 M, keruk penuh Rp 245,2 M (tiruan Excel: 415 / 602,3 / 192,8 M); truk PK 33 → 132, GC 24, CK 24 sejak th-8 (Excel 6 / 6 / 0 tetap 20 th). Laporan: `tools/diff_k15.py` bagian perairan & truk.

### 5.8 Investasi & staging — sheet `Investasi`, `Model` 361–400
Investasi = **penambahan kapasitas terpasang × harga satuan × faktor eskalasi**, dicatat di **tahun bangun**. Kebutuhan terpasang per tahun datang dari modul hulu (tidak pernah turun): `terminal.n_berth`, `terminal.n_equipment`, total `storage.cy / gc / silos / tanks`, `storage.yard_equipment`, `storage.trucks`, `storage.pipeline`.

| Pola (`plans[].staging`) | Aturan (lead = `construction_lead_years`) |
|---|---|
| `phase` (default, seperti Excel) | tiap tahap `horizon.phases` (s, e) dibangun di th `s − lead` sebanyak `maks(need[s..e]) − terpasang`; lookahead tidak dipakai |
| `incremental` | bila `need[t] > terpasang`, dibangun di th `t − lead` sampai `maks(need[t .. t+N−1])`; N = `berth_lookahead_years` (tambatan, alat B/M, perairan) atau `storage_lookahead_years` (penyimpanan, alat lapangan, truk, pipa) |

| Variabel (`invest.*`, seri per tahun bangun) | Kunci · kuantitas × harga |
|---|---|
| `invest.berth` | terminal · tambatan ditambah × basis harga `berth_price_key` (m / m² / unit, §4.5) |
| `invest.handling` | id alat B/M · alat ditambah × `price_usd` × kurs (e alat) |
| `invest.waterside` | terminal · trestle opsi rencana dibangun **penuh** (desain akhir horizon) bersama tambatan pertama terminal; keruk kolam tambat per tambatan ditambah = `Δtambatan · volume keruk desain / tambatan akhir`, langsung ke kedalaman desain akhir |
| `invest.storage` | `cy`, `gc` (m²), `bulk` (silo), `liquid` (tangki) · penambahan × `unit_price_key` fasilitas |
| `invest.pipeline` | flow curah cair · Δ panjang pipa × `pipe_price_key` |
| `invest.yard_equipment` | id alat lapangan & truk · Δ unit × `unit_price_key` (e alat) |
| `invest.total` | `total` · Σ semua item per tahun bangun |

- **Eskalasi** (A27): faktor `(1 + e)^t` bila `params.apply_escalation`, t = tahun bangun, th 0 = tahun harga satuan; e infra untuk tambatan, perairan, penyimpanan & pipa, e alat untuk alat B/M, alat lapangan & truk. Default mati (K15 = Excel).
- **Seri & PV:** indeks 0 = th `1 − lead` (K15: th 0; respons `invest_start_year`), panjang `T + lead`. Tiap `waterside_options[]` dilengkapi `build_year` (trestle per terminal), `invest_total` (terjadwal) dan `pv = Σ I[t] / (1 + r)^t` ke th 0 dengan `discount_rate` (I9); UI menandai opsi termurah menurut PV.
- **Implementasi Tahap 8b (2026-11-27)** — `calc/invest.py` (`schedule`, `escalation`, `costed`, `price_basis`, `berth_quantity`, `pipe_length`, `present_value`) + `run.pipeline_chain`, `run.invest_chain`; modul API `invest` (menarik `demand`, `voyage`, `terminal`, `storage`, `waterside`); `storage.pipeline` ikut modul `waterside` (butuh trestle desain). Keputusan pengguna (2026-11-27): kedua pola bangun, default per tahap; keruk ikut tambatan sampai kedalaman akhir, trestle penuh bersama tambatan pertama; tahun bangun = tahun pakai − masa konstruksi untuk semua komponen; eskalasi = opsi, default mati (saklar layar 1 & 9); batas kedalaman opsional; harga per fasilitas bisa diganti (silo bawaan harga tangki seperti Excel); GC = harga lapangan GC, truk curah & GC = headtruck.
- **Validasi:** tiruan Excel `excel_invest` = golden `Model!K369:AF395` (22 kolom th −1..20: alat lapangan, pipa, alat B/M, penyimpanan, dermaga MP, jetty CC, trestle) beserta luas GC `Investasi!N78` dan panjang pipa; tiruan + koreksi A26, A28, A29, A30 (di atas koreksi hulu) = engine untuk setiap variabel & kunci, dan PV opsi perairan. Hitungan tangan: tambatan MP ke-3 dipakai th-14 → dibangun th 10 (per tahap) / th 13 (saat dibutuhkan); lookahead & masa konstruksi; eskalasi; diskonto I9; truk & pipa; batas kedalaman. K15 terkoreksi Σ investasi nominal **Rp 3.540,5 M** (tiruan Excel Rp 3.238,2 M): RTG 1.316 → 1.596 M dan CY 1.224,8 → 934,5 M (hulu A18/A19), GC 4,5 → 55,0 M (A28), pipa 4,6 → 7,5 M (A30), dermaga MP th −1 → th 0 (A26), trestle Rp 415 M di th −1 → MP th 0 + CC th 10 (A29), truk baru PK 158,4 / CK 28,8 / GC 28,8 M (A25). PV opsi: trestle penuh Rp 406,3 M, trestle + keruk 281,3 M, keruk penuh 146,8 M. Laporan: `tools/diff_k15.py` bagian investasi.

Tahap 8 dipecah (2026-11-24): **8a** perairan (§5.7), **8b** investasi & staging (bagian ini, selesai 2026-11-27), **8c** agregasi & objektif (§5.9, layar 9).

### 5.9 Agregasi & objektif — sheet `Model` 398–408
| Variabel | Rumus (K15) |
|---|---|
| `TC[t]` total cost | Σ shipping cost + investasi (K15: investasi awal dibagi 20 lalu ditambahkan tiap tahun) |
| **NPV total cost** | `Σ_t TC[t] / (1+r)^t` → **objektif default v2** |
| `UC[t]` unit cost | **dipisah per satuan** (A7): `Rp/ton` untuk flow bersatuan ton, `Rp/TEU` untuk flow petikemas — tidak ada satu angka gabungan. Biaya bersama dialokasikan ke flow **berbasis pemakaian** (§13 no. 9), diterapkan di Tahap 8c |
| `PV_UC[t]`, anuitas | `UC[t] / (1+r)^t`, `PMT(r, 20, Σ PV_UC)` per kelompok satuan — metrik laporan (cara K15) |

---

## 6. Model optimasi

### 6.1 Formulasi
**Sets:** F flow, K kapal, E alat, T tahun, τ terminal, M mode pengembangan (trestle/keruk/campuran).

**Variabel keputusan**
| Var | Domain | Arti |
|---|---|---|
| `y[f,k]` | {0,1} | kapal k melayani flow f |
| `z[τ,e]` | {0,1} | alat e dipakai di terminal τ |
| `w[m]` | {0,1} (atau θ ∈ [0,1]) | mode pengembangan perairan |
| `nBerth[τ,t]`, `nAlat[τ,t]` | integer | turunan, bisa dijadikan variabel |
| *(opsional)* `s[f,v]` | {0,1} | level kecepatan (slow steaming, catatan K21 "Vs dikurangi biar BBM murah") |
| *(nanti)* armada campuran | integer | >1 tipe kapal per flow |

**Batasan inti:** `Σ_k y[f,k] = 1` · `y[f,k] = 0` jika tidak feasible · `Σ_e z[τ,e] = 1` · alat kompatibel dengan semua bentuk muatan di τ · kedalaman perlu ≥ `T_k·(1+c)·y[f,k]` · BOR ≤ BOR_max (lewat `nBerth` integer) · jangkauan alat ≥ kebutuhan · *(opsional)* interval layanan ≤ lama konsumsi / kapasitas penyimpanan.

**Objektif (bisa dipilih):** **min NPV total cost (default)** · min unit cost. Karena unit cost dipisah Rp/ton dan Rp/TEU, objektif unit cost butuh aturan agregasi (bobot per kelompok atau leksikografis) — diputuskan di Tahap 9.

### 6.2 Strategi penyelesaian
Kopling antar flow hanya lewat (a) alat B/M di terminal (mempengaruhi port time semua flow di τ), (b) kapal penentu (kedalaman → biaya trestle/keruk), (c) jumlah tambatan bersama. Maka:

1. **Engine memprakalkulasi** koefisien biaya & berth-days untuk setiap kombinasi `(f, k, e_τ(f), [v])` — semua nonlinearitas (ROUNDUP, lookup, TCH) selesai di sini.
2. **MILP (HiGHS via `highspy`)** memilih kombinasi dengan variabel biner `x[f,k,e]`, level kedalaman diskret (big-M), dan `nBerth` integer. Ukuran K15: ~10 flow × ≤15 kapal × 10 alat → ribuan biner, kecil untuk HiGHS.
3. **Enumerasi pembanding** (outer: alat × mode × level draft; inner: argmin per flow) untuk validasi & penjelasan.
4. **Bukti konvergensi:** callback HiGHS merekam `(waktu, incumbent, dual bound, gap)` setiap kali solusi membaik / log MIP; layar 10 menggambar incumbent (turun) dan batas bawah (naik) terhadap waktu sampai gap 0 % (pengganti grafik iterasi Evolver; keputusan Milestone A 2026-11-22).
5. **Penjelasan:** untuk tiap flow tampilkan 3 kandidat terbaik + selisih biaya + batasan yang aktif ("kapal X lebih murah tapi draft 12,9 m > 11,5 m Badas").

Ini menggantikan Solver/Evolver (GA) di Excel yang tidak menjamin optimum global.

---

## 7. Interaksi yang WAJIB terlihat di UI

Ini daftar "cerita" yang harus bisa dialami pengguna — dasar desain layar dan uji penerimaan:

| # | Geser/ubah | Efek berantai yang harus terlihat |
|---|---|---|
| I1 | Kapal lebih besar | payload ↑ → frekuensi ↓ → biaya pelabuhan per tahun ↓ · TCH/hari ↑, BBM/hari ↑ · draft/LOA ↑ → bisa gugur di pelabuhan asal · kedalaman KEK ↑ → trestle/keruk ↑ · LOA ↑ → alat per tambatan ↑ · lama konsumsi ↑ → penyimpanan ↑ |
| I2 | Kecepatan | RTD ↓ → jumlah kapal ↓ · BBM ↑ |
| I3 | Alat B/M lebih produktif | port time ↓ → RTD ↓ & berth-days ↓ → tambatan ↓ · harga alat ↑ |
| I4 | Growth / volume maks / tahun mulai | demand per tahun → kapan tambah kapal, tambatan, alat (staging) |
| I5 | Rasio konversi in→out, ton/TEU | volume outbound & jumlah TEU → frekuensi outbound |
| I6 | BOR maks, hari kerja | jumlah tambatan & panjang dermaga |
| I7 | Harga BBM, kurs, tarif pelabuhan | komposisi biaya & bisa mengubah kapal optimum |
| I8 | Batimetri / clearance | trestle vs keruk berpindah |
| I9 | Discount rate | PV & anuitas, preferensi investasi awal vs bertahap |

Pola UI pendukung: **slider/what-if** di samping hasil, **badge delta** (angka berubah berapa vs baseline), **panel jejak** (klik angka → rumus + input + turunan), **grafik trade-off** (unit cost vs ukuran kapal per rute).

---

## 8. Peta layar (UI-first)

Shell: sidebar kiri = langkah pengerjaan (1–10, dengan status ✓/⚠/placeholder) · bar atas = pemilih kasus + skenario + tombol hitung/optimasi · laci kanan = tab **Jejak** (selalu tersedia) | **Review** (catatan koreksi Milestone A, lihat di bawah) | **Pengaturan** (setelan tampilan per pengguna, disimpan di localStorage browser; wadah semua pengaturan berikutnya).

| # | Layar | Isi utama | Interaksi kunci |
|---|---|---|---|
| 0 | **Beranda** | daftar kasus, kasus contoh (K15 Batam, K21 Gresik, K24 Palu), import/export | buka/duplikat kasus |
| 1 | **Soal & Asumsi** | identitas KEK, periode, parameter global (§4.1), tarif | ubah parameter → badge "perlu hitung ulang" |
| 2 | **Tenant & Muatan** | tabel tenant; flow in/out; aturan konversi; kalkulator ton/TEU; grafik proyeksi 20 th | I4, I5 |
| 3 | **Pelabuhan & Rute** | pelabuhan asal/tujuan (draft, LOA, prod.), jarak; peta skematik; tapak KEK + profil batimetri | I8 |
| 4 | **Kapal** | database kandidat per tipe; matriks kompatibilitas bentuk muatan × tipe kapal; filter feasibility per flow (alasan gugur); grafik regresi TCH | lihat kenapa kapal gugur |
| 5 | **Alat B/M** | database alat; produktivitas per bentuk muatan; aturan alat/tambatan dari LOA | I3 |
| 6 | **Armada & Operasi** | per flow: pilih kapal (manual) → kartu rantai frekuensi → port time → sea time → RTD → jumlah kapal; slider tahun; **tabel bandingkan kandidat** + grafik unit cost vs ukuran | I1, I2 |
| 7 | **Biaya Pelayaran** | BBM, TCH, biaya pelabuhan, shipping cost per flow per tahun; komposisi (stacked) | I7 |
| 8 | **Terminal KEK** | tambatan MP/CC & BOR per tahun; jumlah alat; penyimpanan per komoditas; truk dermaga–lapangan; kapal penentu & kedalaman perlu; alur & kolam; trestle vs keruk (grafik batimetri + garis kedalaman perlu per terminal + x*, tiga opsi); staging | I6, I8 |
| 9 | **Investasi & Ringkasan Biaya** | jadwal investasi per tahun; total cost; unit cost; PV; anuitas | I9 |
| 10 | **Optimasi** | objektif, variabel yang dioptimasi, batasan on/off → jalankan → hasil vs manual, penjelasan per flow | P6 |
| 11 | **Skenario & Laporan** | bandingkan skenario (KPI berdampingan), sensitivitas (tornado), rangkuman ala sheet `Rangkuman`, export Excel/PDF | |
| 12 | **Peta variabel** (grup sidebar *Telusur*) | graf seluruh registry: kolom input kiri, lajur per modul, posisi horizontal = tingkat dependensi; input ringkas (per entitas) / rinci (per atribut); filter *hanya rantai terpilih*, cari; kanvas **seret = geser, roda = zoom di titik kursor, klik ganda = perbesar**, tombol −/%/+/*Paskan* (20–200 %), simpul terpilih di luar layar digeser ke tengah; tombol **Ruang**: sembunyikan menu kiri (hanya di layar ini) dan tutup laci (memilih simpul tidak membuka laci yang sudah ditutup); tombol I1–I9 | klik simpul → sorot hulu/hilir + laci jejak |

**Konvensi visual (wireframe 2a, `design/wireframe-2a.fig`, draf menunggu review):**
- Kanvas 1440 px: bar atas 56 px · sidebar 240 px · konten 880 px · laci jejak 320 px (selalu terbuka di wireframe). Sidebar, bar atas, laci jejak = komponen OpenPencil.
- **Gaya (2026-11-21, keputusan pengguna + TasteSkill):** palet datar hitam `#000000`, biru `#56BDCC`, hijau `#90B148`, merah `#AA3A36` di atas putih; netral pendukung `#EEEEEE` (permukaan), `#DEDEDE` (garis rambut), `#555555` (teks sekunder). Tanpa bayangan dan gradien; sudut 2 px (badge) / 4 px (tombol, input); bagian dipisah garis rambut, bukan kartu berbingkai di atas latar abu. Font Chivo (teks) + Chivo Mono (semua angka & kode), bobot 400/500 saja, huruf kalimat, minimum 13 px; judul layar 32, judul bagian 20, judul kartu 16/500, teks 14–16, label 13/500 abu, angka KPI mono 28.
- Peran warna: hitam = teks, tombol utama, langkah aktif, simpul hasil akhir · biru = input yang bisa diedit (penanda kotak 6 px), isi slider, baris terpilih, seri data utama · hijau = `dihitung`, layak, input lengkap, delta membaik · merah = gugur, asumsi, perlu hitung ulang, nilai yang melanggar batas, delta memburuk. Biru & hijau kontrasnya ±2:1 di atas putih → hanya sebagai bidang/penanda dengan teks hitam; merah boleh jadi teks.
- Badge angka: `placeholder` abu `#EEEEEE` (angka placeholder ditulis `#555`) · `dihitung` bidang hijau · `input` bidang biru · `asumsi` bingkai merah · `gugur · <alasan>` bidang merah teks putih · `≠ Excel · A#` bingkai hitam. Bentuk muatan = kode mono berbingkai (CC/CK/PK/GC), bukan warna.
- Layar 6: kandidat gugur tetap tampil (redup + alasan), kelayakan = draft ≤ draft maks pelabuhan & LOA ≤ dermaga ÷ 0,85. Rantai hitung tampil sebagai simpul yang bisa diklik → laci jejak.
- Pola semua layar: label langkah mono (`06 · hasil`), judul 32, satu kalimat 16; bagian dipisah garis rambut; nilai input ditandai kotak biru di kepala kolom atau di samping angka; angka hasil abu + badge `placeholder` sampai engine tersambung; baris terpilih = latar `#EEEEEE` + garis biru kiri 3 px.
- Layar 0: kasus aktif + daftar kasus (K21/K24 "belum diekstrak") + import JSON/Excel. Layar 1: identitas, horizon & fase, parameter global dua kolom, contoh status "diubah", tabel asumsi. Layar 3: tabel 10 pelabuhan (LOA maks = dermaga ÷ 0,85 sebagai turunan), batang jarak rute, tapak & kondisi perairan. Layar 4: matriks bentuk muatan × tipe kapal, regresi TCH, tab per tipe kapal dengan kelayakan per pelabuhan. Layar 5: tabel HMC & MLA, aturan alat/tambatan dari LOA, what-if produktivitas (I3).
- Layar 7: slider I7, KPI, batang komposisi TCH/BBM/pelabuhan per flow, rincian per tahun (badge A11). Layar 9: KPI (NPV biaya total = objektif bawaan), slider discount (I9), jadwal investasi bertumpuk, tabel item investasi. Layar 10: objektif, variabel keputusan (§6.1), sakelar batasan, tombol jalankan, tabel hasil vs manual + batasan aktif, tiga kandidat terbaik per flow. Layar 11: tabel skenario berdampingan, tornado sensitivitas, isi ekspor.
- **Review Milestone A batch 1** (2026-11-22): layar 1 — judul kelompok parameter tebal + garis hitam; judul layar menjadi *Soal & parameter*; tabel asumsi & celah data = **panduan development** (disembunyikan bawaan, ditampilkan lewat Pengaturan → *Catatan development*), bukan saklar model. Layar 3 — tabel **Tarif pelabuhan per kelas** (utama, I–V; tab kapal luar/dalam negeri; labuh, pandu tetap/variabel, tambat beton/dolphin, B/M per ton/TEU; tunda per rentang GT per kelas), semua bisa diedit; kelas tiap pelabuhan tetap di tabel pelabuhan. Layar 5 — rentang LOA → alat per tambatan dan batas maksimum alat per terminal bisa diedit; tombol *Tambah alat* (HMC/MLA, id `eq.baru_*`, nama/harga/produktivitas bisa diedit, bisa dihapus). Layar 7 — sumbu nilai berskala dengan satuan di grafik komposisi; pemilih flow (tenant · arah) untuk rincian per tahun; tabel **biaya pelabuhan per call** per komponen (placeholder). Layar 9 — grafik biaya per tahun menumpuk biaya pelayaran + investasi (sumbu Y Rp miliar, sumbu X tahun operasi). Layar 10 — grafik **konvergensi solver** (§6.2 butir 4). Grafik batang/kolom kini bisa menampilkan sumbu dengan satuan (`xUnit`/`yUnit`).
- Layar 3–4 · **Satuan & isian tabel** (2026-11-22): setiap kepala kolom angka memuat satuannya (`Draft maks, m`, `Dermaga terpanjang, m`, `Kecepatan, knot`, `DWT, t`, …). Tabel pelabuhan memuat kolom **Jarak ke KEK, NM** yang bisa diedit (= `routes[].legs[].distance_nm` rute yang menyinggahi pelabuhan itu; pola round trip → kedua leg diisi sama, tanda ≠ bila data pergi/pulang berbeda); grafik batang jarak di bawahnya hanya visualisasi. Tabel kapal memuat kolom **IMO** (`ships[].imo`, tidak dipakai hitungan; digit periksa IMO divalidasi, merah bila salah, tautan ↗ ke MarineTraffic untuk verifikasi). Titik **TCH pasar** diisi per tipe kapal di layar 4 (`ship_types[].tch_points`: kelas pasar | ukuran DWT/TEU | USD/hari, tambah/hapus, min. 2 untuk regresi); TCH tiap kapal = regresi linier titik-titik itu terhadap DWT/TEU kapal (Tahap 6).
- Layar 3 · **Profil batimetri tapak** (2026-11-21): tabel isian *jarak dari pantai (m) | kedalaman (m LWS, positif ke bawah)* = `kek_site.bathymetry`, dengan pilihan sumber (survei / peta navigasi / dummy), tambah/hapus titik (min. 2), **tempel dua kolom dari Excel** (baris judul dilewati, kedalaman negatif dibaca positif), baris merah + tombol *Urutkan* bila jarak tidak naik (syarat validator `Case`). Di sampingnya grafik profil berskala jarak sebenarnya (`BathyProfile`): muka air, area air biru muda, garis dasar biru, garis putus-putus merah = kedalaman perlu per terminal dari engine (Tahap 8a; satu garis placeholder bila API mati), garis hitam = x* per terminal dan ujung trestle opsi trestle + keruk; titik baris yang disorot ditebalkan. Grafik yang sama dipakai di layar 8.
- Layar 8: kartu per terminal (MP, CC) + grid staging per tahun (kotak hitam = tahun bangun) + tabel penyimpanan + profil batimetri dengan opsi trestle vs trestle+keruk.
- Layar 8 · **perairan (Tahap 8a, 2026-11-24):** tabel *Kapal penentu & kedalaman perlu* (MP, CC, tapak: kapal, LOA, B, T, kedalaman perlu, x*, tahun mulai; nilai desain akhir horizon); *Alur & kolam (PIANC)* (lebar alur + komponen Wm/Wa/Wb/Ws dan rincian Wa, panjang alur, pintu masuk, jarak henti, kolam putar Ø & ha, radius labuh); profil batimetri; tiga kartu opsi **Trestle penuh | Trestle + keruk | Keruk penuh** (per terminal: trestle panjang × lebar, kedalaman ujung, volume keruk, biaya; biaya dasar total; badge *termurah*, *tidak layak* + alasan, selisih % terhadap opsi rencana; tombol *Pakai di rencana* mengubah `plans[0].waterside_mode`; PV tetap placeholder sampai 8b). Truk tampil di tabel penyimpanan per fasilitas dan tabel kebutuhan 20 th.
- Layar 8 · **investasi (Tahap 8b, 2026-11-27):** kartu opsi perairan menampilkan PV th 0 (r = discount rate), nilai terjadwal dan tahun bangun trestle per terminal; *termurah* dan selisih % menurut PV. Tabel penyimpanan: kolom *Investasi Σ · tahun bangun* (fasilitas, alat lapangan & truk, pipa CC). Tabel kebutuhan 20 th menambah baris panjang pipa per flow CC.
- Layar 9 · **jadwal investasi (Tahap 8b):** blok *Pola bangun & harga* — tab pola bangun (`plans[0].staging`: per tahap | saat dibutuhkan), masa konstruksi & dua lookahead (bisa diedit), saklar eskalasi (`params.apply_escalation`, juga di layar 1) + laju eskalasi; slider discount rate kini mengubah input (PV opsi perairan). Grafik biaya per tahun menumpuk biaya pelayaran (Σ flow) + investasi infrastruktur / alat / penyimpanan dari th `invest_start_year`; tabel *Jadwal investasi* (item × tahun bangun, Rp miliar, semua sel bisa ditelusuri) dan tabel *Item investasi* (kategori, tahun bangun, Σ nominal) berbadge `dihitung`. KPI investasi Σ dihitung; total cost, anuitas, NPV tetap placeholder (8c). Layar 3: baris tapak menampilkan lebar trestle per terminal, tinggi & panjang maks trestle, panjang trestle opsi trestle + keruk.

**Jejak & peta variabel (Tahap 3, 2026-11-21):**
- Angka yang bisa ditelusuri = garis bawah titik-titik abu (`Tv` di `web/src/components/trace.tsx`); klik → laci jejak. Angka aktif dibingkai biru 2 px. Semua angka hasil dan input yang tampil di layar 6–9 bisa diklik.
- Laci jejak (dari registry): konteks (flow · kapal · tahun / terminal), label, nilai (input = nilai kasus aktif, hitam; turunan = placeholder abu), badge jenis, simbol + id, **keterangan singkat apa variabel ini**, chip **Tampil di layar** (klik = pindah layar), rumus atau `case_path`, SPEC §, sel Excel; daftar **Dihitung dari** (klik = telusuri ke hulu, konteks tetap), chip **Dipakai untuk menghitung**, keterangan juga muncul sebagai tooltip di angka, masukan, dan simpul peta; jumlah hulu/hilir, tombol "Buka di peta", tombol ← riwayat; catatan `≠ Excel · A#` dari ringkasan audit di registry. Tab Pengaturan bisa menyembunyikan keterangan, catatan ≠ Excel, catatan "tidak ada temuan audit" (bawaan: **tersembunyi**), dan catatan nilai placeholder.
- **Review Milestone A** (2026-11-22): catatan koreksi `{screen, varId?, topic, text, done}` dengan topik nama / keterangan / rumus / dependensi / satuan / data / tampilan / lainnya. Dicatat dari tab Jejak (*Catat koreksi* → terkait variabel yang dilihat) atau tab Review (catatan layar aktif, opsional dikaitkan ke variabel jejak). Tab Review: progres layar ditinjau (x/13, centang per layar), filter layar ini / terbuka / semua, tandai selesai, hapus, *Salin semua (Markdown)*. Sidebar menampilkan jumlah catatan terbuka dan ✓ per layar. Disimpan di localStorage dan, saat dev server berjalan, disinkronkan ke **`v2/review/notes.json`** (plugin Vite `/__review`, GET/POST; versi lebih baru menang) supaya agen bisa membaca dan menerapkan koreksi ke registry/SPEC lalu menandainya selesai.
- Peta variabel: simpul input = penanda kotak biru; keputusan = bingkai putus-putus hitam; turunan/metrik = bingkai garis rambut; objektif = bidang hitam. Sorot: **hulu = bidang biru** (sisi biru 2 px), **hilir = bidang `#EEEEEE` + bingkai hitam** (sisi hitam), terpilih = bingkai biru 2 px, lainnya redup 30 %.

Setiap layar di tahap UI-first menampilkan data K15 (dari JSON contoh) dan angka hasil berlabel **`placeholder`** sampai engine modul itu tersambung (lalu label berubah jadi **`dihitung`** + bisa dilacak).

---

## 9. Arsitektur v2

### 9.1 Stack (diputuskan: React + engine Python, tanpa DB)
| Lapisan | Pilihan | Alasan |
|---|---|---|
| Desain UI | **OpenPencil** via MCP (`D:\LAH\TPT\.mcp.json`) | wireframe Tahap 2a, review lewat komentar kanvas |
| UI | **React + TypeScript + Vite**, Tailwind | ringan, jalan di Windows tanpa Nix |
| State UI | Zustand (atau Context) — `Case` + `Scenario` aktif + hasil hitung terakhir | |
| Grafik | Recharts / ECharts | proyeksi, trade-off, batimetri |
| Peta variabel | React Flow (atau SVG custom) | graf dependensi dari Registry |
| API | **FastAPI**, tipis: `/cases`, `/calculate`, `/compare`, `/optimize`, `/registry` | satu proses lokal |
| Engine | **Python murni** (`tpt_engine`), model data **Pydantic** | satu sumber kebenaran rumus; dites pytest |
| Optimizer | **HiGHS** via `highspy` | MILP optimum global |
| Tipe bersama | OpenAPI dari FastAPI → `openapi-typescript` | tipe TS di UI selalu sinkron dengan Pydantic |
| Persistensi | file JSON kasus di `v2/cases/` (+ upload/download) | tanpa database |
| Excel | openpyxl (ekstraksi K15; import workbook nanti) | |
| Lingkungan | `uv` (Python 3.13) + Node | keduanya sudah ada di mesin ini |

Selama Tahap 2–3 (UI placeholder) web membaca JSON kasus langsung sebagai mock, jadi UI bisa jalan tanpa backend.

**API (Tahap 4, keputusan pengguna 2026-11-22):**
- **Dev:** FastAPI (`uv run --project engine uvicorn tpt_api.app:app`, :8000, konfigurasi `api` di `.claude/launch.json`) berdampingan dengan Vite; Vite mem-proxy `/api` → :8000 (`TPT_API_URL` untuk mengganti target). Semua rute di bawah `/api`; Tahap 13 FastAPI juga menyajikan build web di origin yang sama.
- **Rute:** `GET /api/health`, `GET /api/cases` (file `cases/*.json` + status validasi), `GET /api/cases/{id}`, `POST /api/calculate`, `POST /api/compare` (Tahap 5).
- **`/calculate`:** request `{case, modules: ["demand"], plan_id?, ship_by_flow?}` — kasus aktif dikirim utuh (termasuk editan UI, tanpa state server). Respons **berkunci id registry**: `{modules, plan_id, ship_by_flow, computed: [id…], values: {id: {flow|ship: angka | seri[20]}}, units: {flow: ton|TEU}, warnings}`. `computed` = daftar variabel yang dihitung engine → UI mengganti badge `placeholder` dengan `dihitung`. Modul yang belum ada → 422. Tahap 8a: modul `waterside` (menarik `terminal`); variabel berkunci id terminal atau `site` (lingkup `site×year`), `storage.trucks` dihitung modul ini; respons menambah `waterside_options`, `governing_ships`, `channel_parts`. Tahap 7b: modul `storage` (menarik `voyage`); variabel penyimpanan berkunci flow + `total`, alat lapangan berkunci id alat. Tahap 7a: modul `terminal` (menarik `voyage`); variabel terminal berkunci id terminal (`MP`, `CC`). Tahap 6: modul `shipcost` (menarik `voyage`), respons menambah `port_breakdown` (flow → komponen → seri Rp/call); `/compare` ikut menghitung biaya tiap kandidat (kolom Rp/satuan layar 6). Tahap 5: modul `voyage` (menarik `demand`), request menerima `equipment_by_terminal`, respons menambah `equipment_by_terminal`, `reasons` (alasan kapal terpilih gugur) dan `feasibility` (flow → kapal kompatibel → `{ok, reasons, notes}`, dipakai layar 4).
- **`/compare` (keputusan pengguna 2026-11-22):** request `{case, flow_id, plan_id?, ship_by_flow?, equipment_by_terminal?}` → `{flow_id, unit, equipment_id, rows: [{ship_id, compatible, feasible, reasons, notes, selected, values: {id registry: angka | seri}, error}]}` untuk semua kapal kasus; rantai §5.1–5.3 dihitung untuk yang kompatibel (termasuk yang gugur, agar posisinya terlihat). Dipanggil hanya oleh layar 6 (`useCompare`), bukan setiap /calculate.
- **Web memilih mock vs API otomatis:** `useEngineSync` (dipasang di App) mengirim kasus ke `/calculate` dengan debounce 300 ms setiap kali kasus/kapal terpilih berubah (dan saat Hitung ulang); bila API tak terjangkau, angka kembali ke placeholder dengan catatan "API tidak aktif" dan dicoba lagi tiap 5 detik. Kasus awal tetap dibundel dari `cases/k15-batam.json` agar UI terbuka tanpa API; `registry.json` tetap mock sampai `/registry`.
- **Tipe:** `tools/export_openapi.py` → `web/src/api/openapi.json` → `npm --prefix web run gen:api` (openapi-typescript, dipasang terpisah di `web/tools/gen-api` karena butuh TypeScript 5 sedangkan web TypeScript 7) → `src/api/openapi.ts`; `src/api/case.ts` hanya alias `components['schemas'][…]`. FastAPI memakai `separate_input_output_schemas=False` agar satu tipe per model. Test gagal bila `openapi.json` basi. Database hanya dipertimbangkan bila nanti butuh multi-user — **bukan** di roadmap ini. Kode v1 tidak dibuang; boleh jadi referensi.

### 9.2 Struktur folder
```
v2/
├─ docs/            01_SPEC.md, 02_ROADMAP.md
├─ blueprint/       index.html (peta variabel & layar, statis)
├─ design/          wireframe-2a.fig (OpenPencil, Tahap 2a), _preview/ (PNG pratinjau)
├─ cases/           k15-batam.json, case.schema.json  ← satu file = satu kasus
├─ engine/          (proyek uv)
│  ├─ src/tpt_engine/domain/     model Pydantic Case/Scenario, satuan
│  ├─ src/tpt_engine/calc/       demand, cargo, vessel, voyage, shipping_cost,
│  │                             terminal, storage, waterside, investment, aggregate
│  ├─ src/tpt_engine/registry.py, trace.py
│  ├─ src/tpt_engine/optimizer/  candidates, enumerate, milp (highspy)
│  ├─ src/tpt_api/               FastAPI (app.py; rute /api/*)
│  └─ tests/                     unit + golden K15
├─ web/             (Vite) src/api (openapi.json → openapi.ts via openapi-typescript, case.ts alias tipe, client.ts), src/screens/S00..S12,
│                   src/components (ui, shell, trace), src/charts, src/lib (case, format, registry),
│                   src/mock (case + placeholders + registry.json), src/store.ts (Zustand)
└─ tools/           extract_k15.py (pemetaan sel khusus K15), export_schema.py, dump_registry.py (registry → web/src/mock/registry.json),
                    export_openapi.py (OpenAPI → web/src/api/openapi.json), check.ps1 (semua cek), dev.ps1 (jalankan API + web lokal),
                    diff_k15.py (laporan selisih engine vs Excel K15 per flow + penyebab, memakai engine/tests/excel_k15.py)
```

### 9.3 Registry & jejak (inti "interaksi variabel")
```python
@dataclass(frozen=True)
class VarDef:
    id: str                    # "voyage.rtd"
    label: str                 # "Round Trip Days"
    unit: str                  # "hari"
    scope: str                 # "global" | "flow" | "flow×year" | "terminal×year" | ...
    kind: str                  # "input" | "derived" | "decision" | "objective"
    formula: str               # teks rumus untuk ditampilkan
    deps: tuple[str, ...]      # id variabel lain
    excel_ref: str | None = None   # "Model!M195"
```
Registry diekspos lewat `/registry`; hasil `/calculate` membawa nilai + `deps` aktual → UI menggambar graf, menyorot hulu/hilir, dan menampilkan "kenapa angka ini".

**Implementasi Tahap 3 (2026-11-21)** — `engine/src/tpt_engine/registry.py`, 173 variabel (100 input, 4 keputusan, 64 turunan, 4 metrik, 1 objektif):
- `VarDef` ditambah: `impl` (Tahap 4: fungsi engine `"modul:fungsi"` di bawah `tpt_engine.calc`, dari `IMPL`; dites dapat diimpor dan sama dengan `calc.run.COMPUTES`), `section` (§ SPEC), `audit` (ID A1–A25), `case_path` (input), `screens` (layar tempat tampil), `symbol`, `note`, `desc` (keterangan 1–2 kalimat untuk pengguna, di `registry_desc.py`; test mewajibkan setiap variabel punya). `kind` ditambah **`metric`** = angka laporan yang tidak dipakai variabel lain (utilisasi, Rp/t pelayaran, BOR realisasi, anuitas).
- Id: input `in.<entitas>.<atribut>`, keputusan `dv.*`, objektif `obj.npv`; turunan `<modul>.<nama>` dengan modul = file `calc/` (demand, cargo, vessel, voyage, shipcost, terminal, storage, waterside, invest, agg).
- **Input per atribut** (keputusan pengguna): satu simpul per field `Case` yang dipakai rumus; `case_path` memakai `nama[kunci]` untuk elemen list yang dipilih konteks (flow, ship, port, route, terminal, equip, …). Tampilan graf bisa meringkasnya per entitas (17 kelompok).
- Turunan = satu per baris rumus §5; beberapa baris dipecah agar jejak berguna (BBM liter vs Rp, port time KEK/ext/total, biaya pelabuhan per call vs per tahun, V ballast/daya AE/SFOC/kapasitas TEU efektif) dan beberapa ditambah: utilisasi, Rp/t pelayaran, alat lapangan, investasi total.
- Ringkasan temuan audit (`AUDIT`) dan interaksi I1–I9 (`INTERACTIONS`, titik awal penelusuran) ikut di registry.
- Test (`engine/tests/test_registry.py`): id unik, deps ada, **tanpa siklus** (Kahn + test deteksi), **tanpa simpul yatim** (input selalu dipakai, turunan selalu punya masukan, hanya metric/objective boleh jadi ujung), semua simpul mencapai metric/objective, objektif dipengaruhi keempat keputusan, §4.1–4.9 & §5.1–5.9 tercakup, `case_path` ada di model `Case`, `web/src/mock/registry.json` sinkron.
- Web membaca `registry.json` (hasil `tools/dump_registry.py`) sebagai mock sampai `/registry` ada. Graf: **SVG custom** (keputusan pengguna; tanpa dependensi baru). Tata letak = lajur per modul (baris) × tingkat dependensi (kolom, `depth`), karena ±70 dependensi berada di dalam modul yang sama sehingga kolom-per-modul tidak bisa mengalir kiri→kanan.

---

## 10. Data referensi

Semua file di bawah ada di `referensi/<kasus>/` (di luar git — milik kelompok lain).

| Kasus | File | Peran |
|---|---|---|
| **K15 — KI Batam** (Febiola & Yudho, 2024) | `TPT_Kelompok 15 Revisi 02-Januari-2025.xlsx`, laporan & PPT K15 | **kasus utama**: contoh data UI + golden test |
| K21 — KI Gresik (2023) | `KELOMPOK 21_…_Perhitungan.xlsx`, laporan, PPT | uji kedua; sumber ide trestle vs keruk, objektif NPV, catatan kelas |
| K24 — KEK Palu (Primo, 2024) | `Perencanaan Transportasi Laut Kelompok 24 (2).xlsx`, PPT PRIMO | uji ketiga; payload volume-limited, θ trestle, 2 komoditas per tenant |
| K7 — Impor jagung hub-spoke | `K7_TPT SOLVER (1).xlsx` | **varian lain** (hub & feeder + penjadwalan harian) → di luar cakupan awal |

---

## 11. Temuan audit Excel K15 & keputusan

Semua temuan sudah diputuskan (tabel keputusan di bawah). Engine v2 **hanya** mengimplementasikan versi terkoreksi; tidak ada flag kompatibel Excel.

| # | Lokasi | Temuan | Dampak |
|---|---|---|---|
| A1 | `Model!M208` dst. | `F_max = ROUNDUP(365/RTD)` — seharusnya ROUNDDOWN | jumlah kapal bisa kurang 1 |
| A2 | `Model!M89`, `M91` (cabang non-PK) | `N48/$DD19*$CI15` → waktu muat **dikali** jumlah alat, bukan dibagi | port time GC/CC outbound di KEK membengkak (×16 untuk 4 alat) |
| A3 | `Model!M82` | waktu muat di pelabuhan asal memakai jumlah alat KEK (`CI8`) × produktivitas pelabuhan | tergantung arti "produktivitas pelabuhan" (per alat atau total?) |
| A4 | `Proyeksi Muatan!H12…`, `O14…` | cek batas maks memakai sel tetap (`$G$12`, `$I$13`) bukan nilai tahun sebelumnya | batas maks tidak bekerja benar (kebetulan tidak terlampaui) |
| A5 | `Data Kapal!L` | V ballast = 130 % Vs | sea time balik terlalu cepat? |
| A6 | `Model!M247/M273` | BBM ME dihitung sebagai HSD, AE sebagai MFO | biasanya kebalikannya |
| A7 | `Model!K404` | unit cost membagi biaya dengan muatan campuran ton & TEU | unit cost tidak sebanding antar tahun |
| A8 | `Muatan!AD`, `Data Kapal!N` | payload 85 % DWT di satu tempat, 90 % di tempat lain | konsistensi |
| A9 | `Model!M247`, `M260` | BBM dihitung dari `F_max × N_ship` voyage (AETOS th-1: 65 × 2 = 130), bukan frekuensi aktual (92) | biaya BBM ±40 % lebih tinggi |
| A10 | `Model!CI8:CI17` | jumlah alat/tambatan di-XLOOKUP dengan **nama alat** ("Alat 7") ke tabel rentang LOA → selalu 4 | aturan LOA→alat tidak pernah aktif |
| A11 | `Biaya Pelabuhan!E71:E128` | biaya pelabuhan berupa **nilai statis** (tidak ikut berubah saat kapal diganti) dan dihitung dengan voyage maks per kapal (65), bukan frekuensi aktual (92) | optimasi Evolver tidak "melihat" biaya pelabuhan; in.damai th-1 dihitung 65 call, seharusnya 92 (kurang ±30 %) |
| A12 | `Proyeksi Muatan!G20:Z24`, `J5…`, `Model!N9` | pembulatan TEU tidak seragam: tahun-1 `ROUNDDOWN` (G20), tahun lain `ROUNDUP`; TEU inbound (fantasi) dibulatkan lalu **dikompounding**; outbound TEU tidak dibulatkan (224.972,8 TEU) | out.damai th-1 kurang 1 TEU; in.fantasi naik ≤ 6 TEU sebelum batas (ditemukan Tahap 4) |
| A13 | `Model!M350:AF359` | lama konsumsi = `ROUNDUP(payload / (D/365))` — memakai payload (bukan muatan per call aktual) dan dibulatkan ke hari | lama konsumsi naik ≤ 1 hari (dwelling time penyimpanan, Tahap 7) (ditemukan Tahap 5) |
| A14 | `Biaya Pelabuhan!E71:AF142` | pilihan tarif membandingkan label `"Dalam Negeri"`/`"Luar Negeri"` dengan `"Dalam"`/`"Luar"` → tidak pernah sama, semua pelabuhan kena tarif **dalam negeri**; baris pandu out.adi (`E93:AF93`) kolomnya terbalik sehingga hanya itu yang memakai tarif luar negeri; tarif labuh luar negeri kelas utama kosong | biaya pelabuhan luar negeri (Visakhapatnam, Melbourne, Bangkok, Kobe, Chennai) jauh terlalu rendah (ditemukan Tahap 6) |
| A15 | `Biaya Pelabuhan!E84…E133` | pandu & tunda dihitung 1 gerakan per call; biaya tetap tunda **tidak dikali frekuensi** (urutan operasi `tetap + var·GT·F`); tambat dikali seluruh port time per call (bongkar muat KEK + asal + AT/WT/IT) | pandu/tunda kurang ±½, tambat bergantung port time KEK yang tidak relevan (ditemukan Tahap 6) |
| A16 | `Model!M106:AF115` | cek label `"CC"` berth-days memakai referensi relatif (`L107` → bergeser ke sel tahun) sehingga mulai tahun ke-2 jetty CC dibagi **300 m** (unit MP), baris pertama memakai `$L$106` absolut; rumus aslinya `LOA / 40 m` membuat satu tanker 174 m menempati ±4,4 jetty | berth-days & BOR jetty CC terlalu rendah (ditemukan Tahap 7a) |
| A17 | `Model!M68:AF91` | ship-days KEK hanya waktu bongkar muat; idle time di tambatan tidak dihitung | berth-days & BOR sedikit terlalu rendah (ditemukan Tahap 7a) |
| A18 | `Fasilitas Daratan!F14:Y16`, `F132`, `F173:F175`, `F224:F225` | dwelling time = `AVERAGE` lama konsumsi 20 tahun **termasuk tahun tanpa muatan** (CPO 0,8 hr padahal 1,5–1,9 hr saat aktif); in.fantasi per tahun kecuali `F13`, `J13`, `O13` = MAX blok tahun 1–5 / 6–10 / 11–20 | penyimpanan curah cair & kering terlalu kecil; luas CY & gudang tumbuh dengan demand sehingga lebih besar di akhir horizon (ditemukan Tahap 7b) |
| A19 | `Fasilitas Daratan!F69:Y115` | RTG dihitung per tenant dan per full/kosong, masing-masing `ROUNDUP`, produktivitas di-hardcode beda per tenant (in.fantasi 4, out.damai 8 full / 12 kosong, lainnya 5 TEU/jam) | jumlah RTG th-1 12 vs 22 (ditemukan Tahap 7b) |
| A20 | `Fasilitas Daratan!F226:F227` | densitas CPO & RBD olein di tangki = 0,9 tetap, tidak memakai data `Muatan` (0,909; 0,91) | volume tangki ±1 % terlalu besar (ditemukan Tahap 7b) |
| A21 | `Fasilitas Perairan!C4:C6`, `K18`; `Trestle!C50`, `C59` | satu kapal penentu = LOA terbesar (ALS CERES), B & T diambil dari kapal itu, untuk kedua terminal dan 20 tahun; tanker THEA di jetty CC (T 14,918 m) lebih dalam | kedalaman CC 21,3 m, seharusnya 22,4 m; trestle CC 500 m, seharusnya 541 m; tahun-tahun awal ikut kapal terbesar 20 th (ditemukan Tahap 8a) |
| A22 | `Fasilitas Perairan!G18`, `G58`, `K14` | Wa kecepatan = 0,1 · Vs (knot) dari baris "cepat" padahal kelas kecepatan sedang (`L6`); Wa dasar laut 0,1 B walau h = 1,5 T; alur 1 jalur hanya satu Wb | lebar alur 2 jalur 415,9 m, seharusnya 402,3 m (ditemukan Tahap 8a) |
| A23 | `Fasilitas Perairan!K37` | luas kolam putar dari diameter 1,5 LOA padahal asumsinya kapal dibantu tunda (diameter 2 LOA, `K35`) | luas 114.909 m², seharusnya 204.282 m² (ditemukan Tahap 8a) |
| A24 | `Trestle!C70`, `C79`, `C73`, `C82`, `C30`, `C105:N107` | opsi trestle + keruk: lebar trestle MP & jetty 50 m (trestle penuh 40 m & 1,5 m); kedalaman ujung trestle sel tetap 10 m, bukan dari batimetri; kolam keruk jetty 40 m × 1,5 B kapal MP | biaya opsi campuran Rp 602,3 M, seharusnya Rp 339,0 M → lebih murah daripada trestle penuh (ditemukan Tahap 8a) |
| A25 | `Fasilitas Daratan!F118:F125`, `F156:F163`, `F208:F217` | truk: produktivitas box/jam ÷ 60 dipakai sebagai menit, jarak sekali jalan, waktu di dermaga dihitung dua kali, jarak = trestle opsi keruk 250 m, jumlah untuk satu alat tetap 20 th, tidak masuk investasi | truk PK 6, seharusnya 33–132; GC 6 → 24; CK 0 → 24 (ditemukan Tahap 8a) |
| A26 | `Investasi!N..AG` (SUM per fase), `Model!K369:AF395`, `Investasi!C13` | pengadaan per fase di kolom th 0/5/10 dengan jendela tak seragam: dermaga MP di th −1 untuk penambahan th 0–6, 7–11, 11–21 (th 11 dihitung dua kali), jetty CC dan kolom batas silo/pipa terhitung dua kali; masa konstruksi `C13` tidak dirujuk | dermaga & trestle setahun terlalu awal; potensi hitung ganda bila kebutuhan naik di tahun batas (K15 tanpa dampak nilai) (ditemukan Tahap 8b) |
| A27 | `Investasi!C15`, `C21` | eskalasi harga infra & alat (1 %/th) tidak dirujuk sel mana pun | investasi tahap menengah/panjang memakai harga tahun dasar (ditemukan Tahap 8b) |
| A28 | `Investasi!N78` | luas GC = baris **penambahan** `Fasilitas Daratan!F193:F195`, lalu diselisihkan lagi (penambahan negatif) | investasi gudang GC Rp 4,5 M, seharusnya Rp 55,0 M (ditemukan Tahap 8b) |
| A29 | `Trestle!C92:N110`, `Model!K395` | trestle penuh kedua terminal seluruhnya di th −1 (jetty CC baru dipakai th-13); `K395` hanya mengambil bagian th −1 opsi terpilih (fase keruk th 5 & 10 hilang); "PV" dan "Total PV" tidak didiskon | perbandingan opsi perairan tidak memakai nilai waktu uang; trestle CC 13 th terlalu awal (ditemukan Tahap 8b) |
| A30 | `Fasilitas Daratan!F239:F240` | panjang pipa CC = trestle opsi keruk 250 m (`Trestle!C69`) + LOA × jetty walau rencana trestle penuh | pipa 4,6 → 7,5 M (ditemukan Tahap 8b) |

Verifikasi: dengan rumus di atas (termasuk A1, A9, A10), rantai AETOS tahun-1 rute Badas mereproduksi `Model!M338` = Rp 734,3 M persis — lihat tab 3 blueprint.

### Keputusan (2026-11-21)
| # | Keputusan | Perilaku engine v2 |
|---|---|---|
| A1 | **ROUNDDOWN** | `F_max = ⌊CD / RTD⌋` |
| A2 | **dibagi** jumlah alat | `t = q / (prod · nEq) / 24` untuk semua bentuk muatan |
| A9 | **frekuensi aktual** | BBM dihitung dari `F` voyage, bukan `F_max · N_ship` |
| A10 | **dari LOA** | `nEq` = tabel rentang LOA kapal terpilih |
| A3 | **input per pelabuhan** | tiap pelabuhan memilih mode produktivitas: *total per kapal* atau *per alat × jumlah alat* |
| A4 | **diperbaiki** (jelas bug) | batas maks dicek terhadap nilai tahun sebelumnya: `min(Dmax, D[t−1]·(1+g))` |
| A5 | **parameter, default 100 %** | `V_ballast = rasio · Vs`, rasio global bisa dioverride per kapal |
| A6 | **ME & AE = HSD, sebagai parameter** | jenis BBM per mesin bisa dipilih; default keduanya HSD |
| A7 | **dipisah per satuan** | unit cost Rp/ton dan Rp/TEU terpisah; objektif default NPV total cost |
| A8 | **dua parameter** (default saya, bisa diubah) | α payload = 85 % DWT; α batas berat per TEU = 90 % DWT |
| A11 | **dihitung dari tarif × frekuensi aktual** (sejalan A9) | jasa labuh/pandu/tambat/tunda/B-M dari `tariffs` × `F`; TERSUS KEK tanpa jasa kepelabuhanan (`kek_site.port_charges = "none"`) |
| A12 | **⌈·⌉ sekali** (jelas bug, sejalan rumus §5.1) | proyeksi kontinu dalam satuan flow; `D_TEU = ⌈D_ton/tonPerTEU⌉` atau `⌈D⌉` di semua tahun |
| A13 | **ikut rumus §5.3** (q / (D/365), kontinu) | pembulatan hari, bila perlu, diputuskan di penyimpanan (Tahap 7) |
| A14 | **tarif sesuai jenis pelabuhan** (jelas bug) | luar negeri = kolom USD × kurs, dalam negeri = kolom Rp; satu rumus untuk semua komponen |
| A15 | **2 gerakan, tambat ⌈tPortExt⌉ etmal, tunda tetap per call** (keputusan pengguna 2026-11-22) | pandu & tunda × 2 (masuk + keluar); tambat dari lama sandar di pelabuhan itu dibulatkan ke etmal; B/M tetap masuk shipping cost |
| A16 | **jetty: satu kapal satu jetty** (keputusan pengguna 2026-11-23) | berth-days jetty = ⌈shipDays⌉; faktor LOA/L_unit hanya untuk dermaga menerus (`berth_layout`) |
| A17 | **shipDays = F · (tPortKEK + IT)** (keputusan pengguna 2026-11-23) | AT (approach) dan WT (menunggu di luar) tidak menempati tambatan |
| A18 | **dwell per tahun = lama konsumsi tahun itu** (2026-11-23, opsi rekomendasi) | stok = satu pengapalan; luas mengikuti muatan per call |
| A19 | **satu armada alat lapangan per bentuk muatan** (2026-11-23, opsi rekomendasi) | `⌈Σ Q / kapasitas⌉`, satu produktivitas per jenis alat (RTG 5 TEU/jam) |
| A20 | **densitas dari data komoditas** (jelas bug) | `commodities[].density_t_m3` |
| A21 | **per terminal, per tahun** (keputusan pengguna 2026-11-24) | LOA, B, T maks kumulatif kapal rencana per terminal; `site` untuk alur & kolam putar; desain = kebutuhan akhir horizon |
| A22 | **baris tabel PIANC sesuai kondisi** (jelas bug) | Wa kecepatan dari `ship_speed_class`; Wa dasar laut & kedalaman 0 bila h ≥ 1,5 T; 1 jalur `Wm + ΣWa + 2Wb` |
| A23 | **diameter kolam putar sesuai kapal tunda** (jelas bug) | luas `π(D/2)²`, D = 2 LOA (tunda) / 4 LOA |
| A24 | **lebar trestle per terminal, kedalaman ujung dari batimetri, kolam jetty dari kapal CC** (jelas bug) | satu lebar trestle per terminal untuk semua opsi; kolam jetty 1,175 LOA × 1,5 B kapal penentu CC |
| A25 | **truk per alat × alat B/M aktif** (keputusan pengguna 2026-11-24) | siklus menit pergi-pulang, jarak = trestle desain, tidak pernah turun; investasi truk di Tahap 8b |
| A26 | **tahun bangun = awal tahap (atau tahun pakai) − masa konstruksi** (keputusan pengguna 2026-11-27) | jendela tahap `horizon.phases` seragam untuk semua komponen; `plans[].staging` per tahap (default) atau saat dibutuhkan |
| A27 | **opsi, default mati** (keputusan pengguna 2026-11-27) | `params.apply_escalation`; harga tahun bangun = harga dasar × (1 + e)^t |
| A28 | **luas terpasang** (jelas bug) | investasi GC = penambahan luas GC terpasang × harga lapangan GC |
| A29 | **trestle bersama tambatan pertama, keruk per tambatan, PV didiskon** (keputusan pengguna 2026-11-27) | trestle penuh per terminal di tahun bangun tambatan pertamanya; keruk kolam tambat ikut penambahan tambatan sampai kedalaman akhir; PV ke th 0 dengan I9 |
| A30 | **trestle desain opsi rencana** (jelas bug) | pipa = trestle desain terminal CC + LOA × jetty, per flow sejak aktif |

**Data kasus:** celah data & asumsi ekstraksi K15 (batimetri, dermaga eksisting, mode produktivitas pelabuhan, batas LOA, kapasitas TEU, dll.) dicatat di `cases/k15-batam.json → assumptions`, bukan di dokumen ini.

**Konsekuensi untuk golden test:** angka K15 yang terdampak A1–A3, A5, A6, A9–A30 (port time, RTD, jumlah kapal, BBM, biaya pelabuhan, pembulatan TEU, lama konsumsi, berth-days, BOR, penyimpanan, RTG, perairan, truk, jadwal & nilai investasi) tidak akan sama dengan Excel. Bagian itu dites dengan hitungan tangan; laporan validasi mencatat selisih per flow vs Excel beserta penyebabnya (Tahap 5: `tools/diff_k15.py`).

---

## 12. Di luar cakupan (sekarang) & ekstensi nanti
- Varian hub-and-spoke / feeder multi-port (K7) dan rute segitiga asal→KEK→tujuan (disebut di laporan K15 tapi Excel memakai rute bolak-balik terpisah; struktur data sudah disiapkan).
- Armada campuran (>1 tipe kapal per flow).
- UI dua bahasa (v2 berbahasa Indonesia saja).
- Simulasi penjadwalan harian & inventori (K7 `Penjadwalan`).
- Layout AutoCAD (cukup ringkasan dimensi), analisis lingkungan/oseanografi.
- Multi-user, login, server.
- Perhitungan jarak otomatis dari peta.
- Kecocokan alat B/M per bentuk muatan di dermaga MP (mis. GC pakai HMC, CK pakai grab/conveyor) — sekarang semua muatan MP memakai HMC; dicatat dari review Milestone A (2026-11-22).

---

## 13. Keputusan (dulu pertanyaan terbuka) — 2026-11-21
| # | Topik | Keputusan |
|---|---|---|
| 1 | Kasus utama | **K15 KI Batam** (data contoh UI + golden test); K21 & K24 di Tahap 12 |
| 2 | Objektif | **bisa dipilih, default NPV total cost**; unit cost (Rp/ton & Rp/TEU terpisah) sebagai alternatif |
| 3 | Bug Excel | **langsung versi terkoreksi**, tanpa flag kompatibel Excel (§11) |
| 4 | Armada | **homogen dulu**; campuran = ekstensi |
| 5 | Rute | **bolak-balik dulu** (A-K-A, K-F-K); data rute siap untuk segitiga |
| 6 | Stack | **React (Vite) + engine Python (FastAPI), tanpa DB** (§9) |
| 7 | LCT | **ya** — daftar tipe kapal & matriks kompatibilitas bisa diedit per kasus |
| 8 | Bahasa UI | **Indonesia**, istilah teknis tetap (RTD, BOR, TCH, DWT, LOA) |
| 9 | Alokasi biaya bersama ke flow (2026-11-24, keputusan pengguna) | **berbasis pemakaian**: biaya pelayaran langsung per flow; dermaga/jetty, alat B/M, dan trestle/keruk per terminal dibagi menurut berth-days flow; penyimpanan & alat lapangan per fasilitas menurut arus Q; alur & kolam putar (bila nanti diberi biaya) menurut jumlah call. Diterapkan di Tahap 8c (unit cost per satuan) |

Belum diputuskan (dijadwalkan): agregasi objektif unit cost (Tahap 9).
