# Vesper (TPT Planner v2) — Roadmap & Rekomendasi Effort

> Pendamping [01_SPEC.md](01_SPEC.md). Urutan: **UI dulu (placeholder) → engine per modul (tervalidasi Excel) → optimasi → skenario & laporan.**
> Setiap tahap kecil, menghasilkan sesuatu yang bisa diklik, dan punya *Definition of Done* (DoD).

## Legenda effort

| Tanda | Kapan | Rekomendasi model / effort |
|---|---|---|
| 🔴 **Tinggi** | keputusan arsitektur, membaca & menerjemahkan rumus Excel yang rumit, desain optimasi, debugging angka yang tidak cocok | model teratas (yang kamu pakai sekarang) dengan effort **high** (🔴🔴 = **xhigh/max**) |
| 🟠 **Sedang** | implementasi modul yang rumusnya sudah jelas di SPEC, layar dengan logika | model teratas effort **medium**, atau model menengah (mis. Sonnet) effort **high** |
| 🟢 **Rendah** | layout/styling, boilerplate, CRUD tabel, export, perapihan | model menengah/ringan effort **medium/low** |

Aturan praktis: **kalau tahap itu menyentuh "angka benar atau salah", pakai 🔴.** Kalau hanya "tampilan benar atau salah", 🟠/🟢 cukup.

---

## Peta tahapan

```
Tahap 0  Spesifikasi & keputusan ............................. 🔴🔴  ← sekarang
Tahap 1  Kontrak data + kasus contoh K15 + golden data ....... 🔴
Tahap 2  2a wireframe OpenPencil → 2b shell UI + 12 layar ..... 🟠 (styling 🟢)
Tahap 3  Registry variabel + panel jejak + peta variabel ..... 🔴
         ── MILESTONE A: bentuk produk disepakati ──
Tahap 4  Engine 1 — demand & konversi muatan ................. 🟠
Tahap 5  Engine 2 — kelayakan kapal & operasi pelayaran ...... 🔴
Tahap 6  Engine 3 — biaya pelayaran .......................... 🟠→🔴 (tarif pelabuhan)
         ── MILESTONE B: armada & biaya pelayaran "dihitung" ──
Tahap 7  Engine 4 — terminal KEK (tambatan, BOR, alat, storage) 🔴
Tahap 8  Engine 5 — perairan, trestle/keruk, investasi, UC/PV . 🔴
         ── MILESTONE C: rantai manual lengkap, validasi K15 selesai ──
Tahap 9  Optimizer (prakalkulasi + MILP HiGHS + penjelasan) .. 🔴🔴
         ── MILESTONE D: optimasi ≥ hasil Evolver K15 ──
Tahap 10 Skenario, what-if delta, sensitivitas ............... 🟠
Tahap 11 Import/export Excel, rangkuman & laporan ............ 🟢→🟠
Tahap 12 Validasi kasus K21 & K24, generalisasi .............. 🔴
Tahap 13 Polishing & paket jalan-lokal ....................... 🟢
```

---

## Detail tahapan

### Tahap 0 — Spesifikasi & keputusan · 🔴🔴
- **Tujuan:** gambaran besar disepakati sebelum kode.
- **Deliverable:** `01_SPEC.md`, `02_ROADMAP.md`, `blueprint/index.html`, keputusan SPEC §11 & §13.
- **DoD:** ✅ selesai 2026-11-21 — semua pertanyaan terbuka & temuan audit diputuskan.
- **Kenapa 🔴🔴:** semua tahap lain mewarisi keputusan di sini.

### Tahap 1 — Kontrak data + kasus contoh · 🔴
- **Tujuan:** satu file JSON yang memuat seluruh input kasus K15.
- **Deliverable:**
  - `engine/` (proyek uv) dengan `tpt_engine/domain/case.py` — model **Pydantic** `Case` (§4 SPEC, termasuk daftar tipe kapal + matriks kompatibilitas, mode produktivitas pelabuhan, parameter BBM/ballast/α) + satuan; export JSON Schema.
  - `tools/extract_k15.py` — membaca workbook K15 → `cases/k15-batam.json` (input) dan `engine/tests/golden/k15-*.json` (nilai antara Excel: proyeksi, tarif TCH, port time, RTD, jumlah kapal, biaya, tambatan, investasi) — dipakai sebagai pembanding, bukan kebenaran mutlak (bug §11).
- **DoD:** `cases/k15-batam.json` lolos validasi Pydantic; setiap field punya `excel_ref`; golden data berisi minimal 1 flow per bentuk muatan.
- **Kenapa 🔴:** salah bentuk data = refactor di semua layar & engine. Ekstraksi butuh penilaian (sel mana yang input, mana turunan).

### Tahap 2 — Wireframe & shell UI dengan placeholder · 🟠 (styling 🟢)
- **Tujuan:** seluruh alur aplikasi bisa dilihat lalu diklik dengan data K15 dan angka dummy.

**2a — Wireframe di OpenPencil** (MCP `openpencil`, aplikasi harus terbuka)
- 1 halaman per layar SPEC §8 (0–11) + 1 halaman komponen bersama (shell: sidebar langkah, bar kasus/skenario, laci jejak, kartu angka berbadge `placeholder`/`dihitung`, tabel, slot grafik).
- Isi memakai data nyata dari `cases/k15-batam.json` (nama tenant, kapal, pelabuhan, parameter); angka hasil = placeholder.
- Mulai dari layar inti dulu (6 Armada & Operasi, 2 Tenant & Muatan, 8 Terminal KEK), minta review, baru layar lain.
- Kamu memberi koreksi lewat komentar di kanvas OpenPencil; agen membaca & menindaklanjuti (`get_comments`).
- **DoD 2a:** 12 layar + komponen disetujui; koreksi besar dicatat di SPEC §8.

**2b — Implementasi React**
- **Deliverable:** scaffold `web/` Vite + React + TS + Tailwind yang membaca `cases/k15-batam.json` langsung sebagai mock (belum perlu backend); shell (sidebar langkah, bar kasus/skenario, laci jejak); layar 0–11 (SPEC §8) dengan tabel/kartu/grafik berisi data JSON + angka berlabel `placeholder`.
- **Bisa dipecah** per kelompok layar (paralel): {0,1,2} · {3,4,5} · {6,7} · {8,9} · {10,11}.
- **DoD 2b:** semua layar terbuka tanpa error dan sesuai wireframe 2a; setiap angka hasil berbadge `placeholder`; edit input di layar 1–5 tersimpan ke state.
- **Catatan:** `get_jsx` OpenPencil bisa jadi titik awal komponen; jangan sentuh rumus.

### Tahap 3 — Registry variabel + jejak + peta variabel · 🔴
- **Tujuan:** "interaksi antar variabel" jadi fitur nyata sejak awal.
- **Deliverable:** `tpt_engine/registry.py` (semua variabel §5 SPEC: id, label, satuan, rumus, deps, excel_ref) + skrip dump ke JSON untuk mock web; komponen **TraceDrawer** (klik angka → rumus, input, turunan); layar **Peta Variabel** (graf, sorot hulu/hilir) — masih nilai placeholder.
- **DoD:** setiap angka di layar 6–9 bisa diklik dan menunjukkan rumus & dependensinya; graf tidak ada simpul yatim.
- **Kenapa 🔴:** ini tulang punggung arsitektur engine & UI.

> **MILESTONE A — bentuk produk disepakati.** Kamu klik-tembus semua layar, beri koreksi; SPEC diperbarui. Baru lanjut ke engine.

### Tahap 4 — Engine 1: demand & konversi · 🟠
- proyeksi (growth, cap A4 diperbaiki, tahun mulai), aturan outbound, kalkulator ton/TEU, `D_TEU`.
- **Plus fondasi API:** FastAPI minimal (`/cases`, `/calculate`), generate tipe TS dengan `openapi-typescript`, web berpindah dari mock ke API untuk layar 2. (🟠)
- **DoD:** pytest proyeksi K15 cocok Excel (cap tidak terlampaui di K15, jadi A4 tidak mengubah angka); layar 2 berbadge `dihitung`.

### Tahap 5 — Engine 2: kelayakan kapal & operasi · 🔴
- payload efektif, kompatibilitas, feasibility (draft/LOA) + alasan gugur, nEq dari LOA, frekuensi, port time (KEK & eksternal), sea time, RTD, F_max, jumlah kapal, lama konsumsi.
- Layar 4 & 6 hidup: pilih kapal manual + **tabel bandingkan kandidat** + grafik trade-off.
- **DoD:** untuk kapal terpilih K15, angka per tahun cocok dengan hitungan tangan; **laporan selisih vs Excel** per flow dengan penyebab (A1, A2, A3, A5, A10).
- **Kenapa 🔴:** banyak detail Excel (pembulatan, cabang PK vs non-PK, mode produktivitas pelabuhan) dan setiap selisih harus bisa dijelaskan.

### Tahap 6 — Engine 3: biaya pelayaran · 🟠→🔴
- BBM ME/AE, TCH (regresi per tipe), tarif pelabuhan (labuh, pandu, tambat, tunda, B/M) kedua ujung.
- **DoD:** tarif TCH & biaya pelabuhan cocok Excel untuk input yang sama; BBM sesuai hitungan tangan (A6 HSD, A9 frekuensi aktual) dengan selisih vs Excel terjelaskan; layar 7 hidup.
- 🔴 untuk sub-bagian tarif pelabuhan (sheet `Biaya Pelabuhan` 158 baris, banyak lookup GT).

> **MILESTONE B — armada & biaya pelayaran dihitung.** Interaksi I1, I2, I7 bisa didemokan.

### Tahap 7 — Engine 4: terminal KEK · 🔴
- shipDays, berthDaysReq, nBerth & BOR per terminal per tahun, panjang dermaga, jumlah alat & penambahan; penyimpanan (CY, gudang, silo, tangki).
- **DoD:** golden tambatan/BOR/alat/luas penyimpanan K15 lulus; layar 8 (bagian darat) hidup; I3, I6 bisa didemokan.

### Tahap 8 — Engine 5: perairan, investasi, agregasi · 🔴
- kapal penentu, kedalaman perlu, dimensi alur/kolam; batimetri → trestle vs keruk (dan θ campuran); investasi bertahap + escalation; total cost, unit cost (satuan seragam), PV, anuitas / NPV.
- **Keputusan di tahap ini:** aturan alokasi biaya bersama (investasi terminal) ke flow untuk unit cost per satuan (Rp/ton, Rp/TEU) — diputuskan 2026-11-24: berbasis pemakaian (SPEC §13 no. 9).
- **Dipecah (2026-11-24):** **8a** perairan — kapal penentu, kedalaman perlu, alur & kolam, batimetri → trestle / trestle + keruk / keruk, truk dermaga–lapangan (🔴, selesai); **8b** investasi & staging — dermaga MP, jetty CC, trestle/keruk, alat B/M, penyimpanan (lookahead `FD!F196`), truk & pipa CC, masa konstruksi & lookahead tambatan, escalation, temuan `Investasi!N78` (🔴, selesai); **8c** agregasi — TC, NPV total cost, UC per satuan dengan alokasi berbasis pemakaian, PV_UC & anuitas, layar 9 (🟠→🔴).
- **DoD:** investasi per komponen cocok Excel untuk input yang sama; NPV total cost dan unit cost per satuan dihitung; layar 8–9 hidup; I8, I9 bisa didemokan.

> **MILESTONE C — rantai manual lengkap.** Semua badge `placeholder` di layar 1–9 hilang; setiap selisih vs Excel K15 tercatat penyebabnya.

### Tahap 9 — Optimizer · 🔴🔴
- prakalkulasi koefisien `(flow, kapal, alat[, kecepatan])`; enumerasi pembanding; model MILP (`highspy`, endpoint `/optimize`) dengan level draft & nBerth integer; penjelasan (top-3 per flow, batasan aktif); layar 10.
- **Keputusan di tahap ini:** agregasi objektif unit cost (bobot per kelompok satuan atau leksikografis); default tetap NPV total cost.
- **DoD:** pada K15, NPV solusi optimizer ≤ NPV solusi Evolver bila keduanya dihitung dengan engine v2; enumerasi & MILP sepakat pada instance kecil; waktu < beberapa detik.
- **Kenapa 🔴🔴:** formulasi, linearisasi, dan verifikasi optimum.
- **Masukan dari telusur engine (2026-11-27, cek di awal tahap):**
  1. Koefisien jangan diambil dari `compare()` (`calc/run.py`) begitu saja: ia berhenti di §5.4. Biaya terminal, penyimpanan, dan perairan (§5.5–5.7) bergantung pada gabungan kapal per terminal, bukan per flow, sehingga tidak linear per baris `(flow, kapal)`.
  2. `calculate()` melewati flow yang gagal (kapal tak ada / `VoyageError`) hanya dengan `warnings`. Bila optimizer memakainya, kombinasi gagal bisa tampak murah karena biayanya hilang; perlakukan sebagai tak layak.
  3. `compare()` tetap menghitung kapal yang `compatible` tapi gugur kelayakan (`feasible=False`). Batasan MILP memakai `feasible`, bukan `compatible`.

> **MILESTONE D — optimasi terjamin.**

### Tahap 10 — Skenario & sensitivitas · 🟠
- skenario = override parameter atas kasus; perbandingan KPI berdampingan; badge delta vs baseline; tornado (±x % per parameter).

### Tahap 11 — Import/export & laporan · 🟢→🟠
- export JSON/Excel hasil; rangkuman ala sheet `Rangkuman`; cetak/PDF. (Import workbook Excel mahasiswa = 🟠, karena layout tiap kelompok beda.)

### Tahap 12 — Validasi K21 & K24 · 🔴
- jadikan kasus contoh kedua & ketiga; temukan asumsi yang ternyata spesifik K15 (payload volume-limited, θ trestle, 2 komoditas/tenant, objektif NPV); generalisasi engine.

### Tahap 13 — Polishing & deployment · 🟢
- aksesibilitas, responsif, dark mode; satu perintah untuk menjalankan lokal (FastAPI menyajikan build web), panduan instalasi di Windows.

---

## Aturan kerja agen untuk v2
1. **Satu tahap = satu sesi kerja** (atau sub-bagian tahap). Mulai sesi dengan membaca SPEC bagian terkait saja.
2. **Tidak membuat dokumen baru.** Keputusan baru → perbarui `01_SPEC.md` (dan centang tahap di sini).
3. **Angka harus dites.** Setiap fungsi engine punya test; tahap engine tidak selesai sebelum golden test relevan lulus.
4. **Placeholder harus jujur.** Angka yang belum dihitung engine wajib berbadge `placeholder`.
5. **Jangan sentuh `apps/` (v1)** kecuali diminta; v1 hanya referensi.

## Progres
- [x] Tahap 0 — SPEC (draf 2), ROADMAP, blueprint; keputusan §11 & §13 masuk (2026-11-21)
- [x] Tahap 1 — `Case` Pydantic (44 tipe), `cases/k15-batam.json` (10 flow, 41 kapal, 11 alat, 10 pelabuhan, 68 harga satuan, 11 asumsi tercatat), `cases/case.schema.json`, golden `engine/tests/golden/k15_excel.json` (10 flow × 21 seri × 20 th + terminal/investasi/agregat); 19 test lulus (2026-11-21). Temuan baru A11 (dikonfirmasi: tarif × frekuensi aktual). Keputusan data: batimetri dummy terkunci ke K15, greenfield, produktivitas pelabuhan total per kapal, dermaga ≥ 85 % LOA, kapasitas TEU = parameter/isian manual.
- [ ] Tahap 2
  - [~] 2a — `design/wireframe-2a.fig`: halaman komponen bersama + layar inti 6, 2, 8 (data K15, hasil = placeholder estimasi kasar); 4 komentar review di kanvas; konvensi visual dicatat di SPEC §8 (2026-11-21). Gaya dirombak ke palet datar pengguna + TasteSkill (Chivo/Chivo Mono, garis rambut, tanpa kartu berbayang); komponen & layar 2/6/8 dibangun ulang, langkah aktif sidebar kini benar per layar (2026-11-21). Gaya disetujui pengguna; layar 0, 1, 3, 4, 5, 7, 9, 10, 11 ditambahkan → 12 layar + komponen lengkap, pratinjau PNG di `design/_preview/` (2026-11-21). Review isi ditunda pengguna. **Berikutnya:** review isi semua layar lewat komentar kanvas (`get_comments`) → revisi → setujui 2a → Tahap 2b. Catatan: isi laci jejak di layar 2/8 masih contoh RTD layar 6; ekspor PNG OpenPencil gagal ("No visible nodes"), pratinjau dibuat lewat ekspor SVG → Edge headless.
  - [x] 2b (dicoba pengguna di browser: OK, 2026-11-21) — `web/` Vite 8 + React 19 + TS + Tailwind v4 + Zustand: shell (sidebar langkah, bar kasus/tahun/hitung ulang, laci jejak yang bisa diklik dari rantai hitung), 12 layar sesuai wireframe 2a, data dari `cases/k15-batam.json`; tipe `src/api/case.ts` di-generate dari `case.schema.json` (json2ts) sampai API ada; semua angka hasil terkumpul di `src/mock/placeholders.ts` dan berbadge `placeholder`. Edit input layar 1–5 (parameter, volume/rasio flow, pelabuhan, kapal, alat) tersimpan di store, ditandai "diubah", bar atas menghitung "perlu hitung ulang"; Hitung ulang menjadikannya baseline (engine belum ada). `tsc -b`, `vite build`, oxlint lulus; 12 layar dibuka tanpa error konsol (2026-11-21). Dev server: `.claude/launch.json` "web" atau `npm --prefix v2/web run dev`. **Belum:** review pengguna terhadap 2a/2b; grafik masih div sederhana (Recharts/ECharts saat data engine nyata); kelayakan kapal di layar 4/6 dihitung sementara di UI (`feasibilityMock`) sampai Tahap 5.
- [x] Tahap 3 (2026-11-21) — `tpt_engine/registry.py`: 173 variabel (input per atribut dengan `case_path`, keputusan, turunan per baris §5, metrik, objektif NPV) + ringkasan audit A1–A11 + interaksi I1–I9; 11 test registry (tanpa siklus, tanpa yatim, path Case valid, JSON sinkron) → 31 test lulus. `tools/dump_registry.py` → `web/src/mock/registry.json` (menggantikan `TRACES` statis; `placeholders.ts` kini hanya berisi nilai contoh `PH_SAMPLE`). Laci jejak membaca registry: rumus/sumber, masukan (nilai input dari kasus aktif, turunan placeholder), dipakai oleh, hulu/hilir, riwayat ←, catatan `≠ Excel`. Semua angka layar 6–9 bisa diklik (komponen `Tv`). Layar 12 **Peta variabel** (SVG custom, lajur modul × tingkat dependensi, input ringkas/rinci, sorot hulu biru/hilir abu, rantai terpilih, cari, zoom, I1–I9). Keputusan pengguna: input per atribut, SVG custom, langkah 12 di sidebar; dicatat di SPEC §8, §9.2, §9.3 + baris tambahan §5. `check.ps1` lulus; diverifikasi di browser (tanpa error konsol). Tambahan (permintaan pengguna sebelum Milestone A): setiap variabel punya keterangan singkat (`registry_desc.py`, dites lengkap) yang tampil di laci jejak + tooltip, laci menampilkan layar tempat variabel tampil (bisa diklik), label bagian diganti "Dihitung dari" / "Dipakai untuk menghitung"; 32 test lulus. Laci kanan kini bertab **Jejak variabel | Pengaturan** (setelan tampilan disimpan di browser; catatan "tidak ada temuan audit" disembunyikan secara bawaan). Batimetri tapak kini bisa diisi sebagai tabel di layar 3 (tambah/hapus titik, tempel dari Excel, cek urutan jarak) dengan grafik profil berskala yang juga dipakai layar 8. Review pengguna 2026-11-22: satuan di semua kepala kolom layar 3–4, kolom IMO (validasi digit periksa + tautan verifikasi), editor titik TCH per tipe di layar 4, kolom jarak rute yang bisa diedit di tabel pelabuhan, peta variabel bisa diseret/di-zoom (roda, klik ganda, Paskan) dan dilebarkan (sembunyikan menu kiri, tutup laci tanpa dibuka ulang saat memilih simpul). **Berikutnya:** Milestone A — klik-tembus semua layar + peta variabel, koreksi nama/keterangan/rumus/dependensi variabel, lalu Tahap 4.
- [x] Milestone A — (2026-11-22) alat review di UI: tab **Review** di laci kanan + tombol *Catat koreksi* per variabel, centang layar ditinjau, sinkron ke `v2/review/notes.json` (lihat SPEC §8). Alur: pengguna klik-tembus layar 0 → 12 dan mencatat koreksi; agen membaca `notes.json`, menerapkan ke registry/SPEC/UI, menandai catatan selesai. Selesai bila 13/13 layar ditinjau dan tidak ada catatan terbuka. Batch 1 (8 catatan, layar 1/3/4/5/7/9/10) diterapkan 2026-11-22 setelah konfirmasi: asumsi = panduan development, tarif per kelas + rincian per call, konvergensi incumbent + bound vs waktu; kecocokan alat per muatan di MP masuk §12 (lanjutan). Pengguna memutuskan lanjut ke Tahap 4 setelah batch 1 (2026-11-22); tab Review tetap dipakai untuk koreksi berikutnya.
- [x] Tahap 4 (2026-11-22) — Engine 1 demand & konversi + fondasi API. `notes.json`: 0 catatan terbuka saat mulai. Keputusan pengguna: proxy Vite `/api` → uvicorn :8000 (konfigurasi `api` di launch.json), respons `/calculate` berkunci id registry, web otomatis memakai API (debounce 300 ms, fallback placeholder + coba lagi tiap 5 dtk bila API mati), paket sesuai SPEC §9.2 (`calc/` + `tpt_api/`) — dicatat di SPEC §9.1–9.3. Engine: `calc/demand.py`, `calc/cargo.py`, `calc/vessel.py` (kapasitas TEU), `calc/run.py`; registry `impl` menunjuk fungsi engine untuk 7 variabel §5.1 (+ `vessel.teu_cap`). **Temuan baru A12** (pembulatan TEU tak seragam di `Proyeksi Muatan`) → engine ⌈·⌉ sekali; SPEC §5.1 & §11. DoD: proyeksi 6 flow ton + out.fantasi = Excel persis; tonPerTEU 3 komoditas golden = Excel; selisih lain hanya A12 (out.damai th-1 1 TEU, fantasi ≤ 6 TEU), A4 dites tetapi tidak aktif di K15. API: `GET /api/health|cases|cases/{id}`, `POST /api/calculate`; `tools/export_openapi.py` → `web/src/api/openapi.json` → `npm run gen:api` (openapi-typescript di `web/tools/gen-api`, TS 5 terpisah dari TS 7 web) → `openapi.ts`; `case.ts` kini alias tipe OpenAPI (json2ts dilepas). Web: layar 2 — kolom D th-N, kalkulator ton↔TEU per flow (NetMax kapal terpilih, kemasan/TEU, t/TEU, D_TEU), grafik proyeksi, semua berbadge `dihitung · engine`; laci jejak menampilkan nilai engine + badge `dihitung`; bar atas menampilkan status engine; layar 0 membaca daftar kasus dari `/api/cases`. 62 test lulus, `check.ps1` lulus; diverifikasi di browser (nilai cocok Excel, edit laju → angka berubah, API dimatikan → placeholder, API hidup lagi → pulih otomatis). Peluncur lokal `tools/dev.ps1` (API uvicorn di latar + Vite, buka browser, Ctrl+C menghentikan keduanya; diuji di port 8001/5175). Commit `5c63025`.
- [x] Tahap 5 (2026-11-22) — Engine 2 kelayakan kapal & operasi pelayaran. Keputusan pengguna: endpoint `/api/compare` untuk tabel kandidat, laporan selisih = test tiruan Excel + `tools/diff_k15.py`, kecepatan (dv.speed, I2) dan `reach_ok` **ditunda** — dicatat di SPEC §5.2, §5.3, §9.1. Engine: `calc/vessel.py` (payload, kompatibilitas, kelayakan + alasan gugur, nEq dari LOA, V ballast), `calc/voyage.py` (F, q, port time KEK/asal, tFix, tSea, RTD, F_max ⌊⌋, jumlah kapal, utilisasi, lama konsumsi), `run.voyage_chain` + `compare`; registry `impl` untuk 17 variabel §5.2–5.3 (semua kecuali `vessel.reach_ok`). **Temuan baru A13** (lama konsumsi Excel = ⌈payload/(D/365)⌉) → engine ikut rumus §5.3. DoD: hitungan tangan in.damai th-1 (AETOS: F 92, RTD 7,249, F_max 50, 2 kapal) dan out.damai PK lulus; **laporan selisih**: tiruan rumus Excel (`engine/tests/excel_k15.py`) = golden persis (10 flow × 11 seri × 20 th), tiruan + koreksi A1/A2/A3/A5/A10/A13 + D_TEU engine = engine persis; `tools/diff_k15.py` mencetak Excel vs v2 per flow per seri dengan efek koreksi berurutan (A12 → A3 → A10 → A2 → A5 → A1 → A13). API: modul `voyage`, `equipment_by_terminal`, `reasons`, matriks `feasibility`, `POST /api/compare`. Web: layar 6 — rantai hitung 11 simpul per flow/tahun dari engine, KPI utilisasi & lama konsumsi, tabel kandidat (payload, F, RTD, F_max, jumlah kapal, status + alasan gugur) dan grafik jumlah kapal vs DWT, semua `dihitung`; biaya tetap placeholder (tahap 6). Layar 4 — kolom kelayakan per pelabuhan dari engine (`feasibilityMock` & mock armada dihapus). 100 test lulus; diverifikasi di browser (in.damai th-10: 143 call, RTD 7,25, 3 kapal; ganti kapal → rantai & tabel berubah; out.damai PK; layar 4). Commit `f4e048e`.
- [x] Tahap 6 (2026-11-22) — Engine 3 biaya pelayaran. Keputusan pengguna: pandu & tunda 2 gerakan per call, tambat = ⌈port time asal/tujuan⌉ etmal, B/M masuk shipping cost — dicatat di SPEC §5.4 & §11. Engine: `calc/shipcost.py` (daya AE, SFOC, BBM liter & Rp, regresi TCH, biaya TCH, biaya pelabuhan per call per komponen, unit cost), `run.cost_chain`; registry `vessel.sfoc` dipecah jadi `vessel.sfoc_me`/`vessel.sfoc_ae`, input baru `in.param.fuel_density`, `impl` untuk semua variabel §5.4 (175 variabel). **Temuan baru A14** (tarif dalam/luar negeri tidak pernah cocok → semua pelabuhan tarif dalam negeri; pandu out.adi terbalik) dan **A15** (1 gerakan, tunda tetap tidak dikali frekuensi, tambat × seluruh port time). DoD: SFOC & TCH per tahun = Excel untuk ke-41 kapal, regresi TCH = SLOPE/INTERCEPT Excel; hitungan tangan BBM, TCH, biaya pelabuhan dalam negeri (in.damai/Badas) & luar negeri (out.damai/Bangkok); tiruan Excel = golden dan tiruan + koreksi (A6, A9, A11, A14, A15) = engine untuk 19 seri × 10 flow × 20 th; `tools/diff_k15.py` diperluas ke seri biaya. API: modul `shipcost`, `port_breakdown`, `/compare` dengan biaya. Web: layar 7 hidup (slider harga HSD & kurs langsung mengubah input → engine, KPI, komposisi per flow, grafik biaya per tahun TCH/BBM/pelabuhan, rincian per tahun per flow, biaya pelabuhan per call per komponen); layar 6 KPI shipping cost & Rp/satuan, kolom Rp/satuan kandidat, grafik biaya per satuan vs DWT. 113 test lulus; diverifikasi di browser (total th-10 Rp 16,41 T; HSD 30.000 → Rp 18,68 T; rincian per call in.damai cocok hitungan tangan). Commit `d6a34f1`.
- [x] Tahap 7a (2026-11-23) — Engine 4 terminal KEK bagian tambatan (Tahap 7 dipecah: 7a tambatan/BOR/alat, 7b penyimpanan). Keputusan pengguna: shipDays = F · (tPortKEK + IT) (A17), jetty CC satu kapal satu jetty (A16), kebutuhan tambatan per tahun tidak pernah turun; jadwal bangun (lead/lookahead) ke Tahap 8. **Temuan baru A16** (cek label CC relatif bergeser → jetty dibagi 300 m; rumus aslinya LOA/40 m) dan **A17** (ship-days tanpa IT). Engine: `calc/terminal.py`, `run.terminal_chain`, modul API `terminal`; input baru `kek_site.terminals[].berth_layout` (quay/jetty); registry `impl` untuk 6 variabel §5.5, `in.term.layout` (176 variabel). DoD: tiruan Excel `excel_terminal` = golden ship-days/berth-days/tambatan/BOR/alat MP & CC 20 th, tiruan + koreksi = engine, hitungan tangan MP th-8; `tools/diff_k15.py` menambah bagian terminal. I6 & I3 didemokan di test (BOR maks 0,5 → tambatan lebih banyak; alat 2× lebih produktif → berth-days turun). Web layar 8: kartu MP/CC per tahun tinjau (berth-days, tambatan, alat, BOR vs maks, panjang dermaga), slider BOR maks & hari kerja langsung mengubah input, tabel pemakaian tambatan per flow, tabel kebutuhan tambatan & alat 20 th dari engine. 121 test lulus; diverifikasi di browser (th-10 MP 435 berth-days, 2 tambatan, BOR 60 %; BOR maks 50 % → MP 4 tambatan di th-16). **Berikutnya:** Tahap 7b — penyimpanan (CY, gudang, silo, tangki, alat lapangan; golden `Fasilitas Daratan Rata2` perlu diekstrak). Commit `3dd4391`.
- [x] Tahap 7b (2026-11-23) — Engine 4 terminal KEK bagian penyimpanan. Keputusan (opsi rekomendasi; pengguna melanjutkan tanpa memilih di dialog): golden = sheet `Fasilitas Daratan` (dirujuk Investasi & Rangkuman; `Rata2` tidak dirujuk sheet mana pun) → parameter kasus diekstrak ulang (6 tier, f_area curah 1,5, faktor bruto 1,0, dozer 20 t/jam); dwell per tahun = lama konsumsi tahun itu (A18) sehingga stok = satu pengapalan; alat lapangan satu armada per bentuk muatan (A19); truk ditunda ke Tahap 8. **Temuan baru A18** (dwell = rata-rata 20 th termasuk tahun nol), **A19** (RTG per tenant, produktivitas di-hardcode 4/8/12/5), **A20** (densitas tangki 0,9 tetap). Engine: `calc/storage.py`, `run.storage_chain`, modul API `storage`; input baru `storage.yard_equipment[].role`; registry `impl` untuk 11 variabel §5.6 (181 variabel). DoD: tiruan Excel `excel_storage` = golden `Fasilitas Daratan` (semua baris, 20 th), tiruan + koreksi = engine untuk setiap variabel & kunci, hitungan tangan stok = satu pengapalan, forklift & dozer = Excel persis; `tools/diff_k15.py` menambah bagian penyimpanan. I1 didemokan di test (kapal lebih besar → gudang lebih luas). Web layar 8: tabel penyimpanan per fasilitas (kebutuhan, alat lapangan; biaya placeholder Tahap 8), tabel per flow (arus, muatan/call, dwell, kebutuhan), baris CY/gudang/silo/tangki/RTG/dozer/forklift di tabel kebutuhan 20 th. 128 test lulus; diverifikasi di browser (th-10: CY 466.575 m² / 5.184 slot / 78 RTG, gudang 27.444 m² / 69 forklift, 9 silo / 40 dozer). **Berikutnya:** Tahap 8 — perairan, investasi (termasuk staging penyimpanan, truk, temuan `Investasi!N78`), agregasi. Commit `18081a1`.
- [x] Tahap 8a (2026-11-24) — Engine 5 bagian perairan (Tahap 8 dipecah: 8a perairan, 8b investasi & staging, 8c agregasi). Keputusan pengguna: kapal penentu per terminal per tahun mengikuti rencana kapal (A21); truk = truk per alat × alat B/M aktif (A25); keruk hanya kolam tambat seperti Excel (alur & kolam putar = dimensi tanpa biaya; rekomendasi saya keruk alur juga, tidak dipilih); alokasi biaya bersama berbasis pemakaian (SPEC §13 no. 9, diterapkan 8c). **Temuan baru A21** (satu kapal penentu ALS CERES untuk kedua terminal & 20 th → kedalaman CC 21,3 m, seharusnya 22,4 m), **A22** (Wa kecepatan dari baris "cepat", Wa dasar laut walau h = 1,5 T, 1 jalur satu Wb → alur 415,9 vs 402,3 m), **A23** (luas kolam putar dari 1,5 LOA walau dibantu tunda), **A24** (opsi trestle + keruk: lebar trestle 50 m untuk MP & jetty, kedalaman ujung sel tetap, kolam jetty dari kapal MP → Rp 602 M, seharusnya 339 M), **A25** (truk: box/jam ÷ 60 dianggap menit, jarak sekali jalan, 6 truk tetap 20 th). Engine: `calc/waterside.py` (tabel PIANC sebagai konstanta), `run.waterside_chain` + `run.truck_chain`, modul API `waterside` (respons + `waterside_options`, `governing_ships`, `channel_parts`); kasus: lebar trestle per terminal, `trestle.max_length_m` opsional (`Trestle!C50` ternyata x*, bukan batas), `ship_speed_class`, truk diekstrak ulang dari `Fasilitas Daratan` (+ truk GC); registry 18 variabel `waterside.*` + `storage.trucks` (194 variabel). DoD: tiruan Excel `excel_waterside` = golden 49 sel `Fasilitas Perairan`/`Trestle` (termasuk biaya opsi terpilih `Model!K395` Rp 415 M) dan `excel_trucks` = golden truk; tiruan + koreksi A21–A25 = engine untuk setiap variabel, kunci, opsi, truk; hitungan tangan (x* CC 541,4 m, alur 9,4 B, kolam putar π·255², volume keruk). I8 didemokan di test (batimetri lebih dalam → lebih murah; kedalaman tak tercapai → trestle tidak layak + peringatan; panjang maks). `tools/diff_k15.py` menambah bagian perairan & truk. Web: layar 8 — tabel kapal penentu & kedalaman perlu (MP, CC, tapak), alur & kolam (komponen Wm/Wa/Wb/Ws), profil batimetri dengan garis kedalaman perlu per terminal + x*, tiga kartu opsi (biaya dasar, termurah, selisih % vs rencana, tombol *Pakai di rencana*), truk di tabel penyimpanan & kebutuhan 20 th; layar 3 — editor batimetri memakai garis engine, baris tapak trestle per terminal; PV & investasi tetap placeholder. 137 test lulus, `check.ps1` lulus; diverifikasi di browser (trestle penuh Rp 416,2 M, trestle + keruk Rp 339,0 M −19 %, keruk penuh Rp 245,2 M −41 % termurah; pindah ke keruk penuh → truk PK th-20 132 → 96 karena jarak 0 m). **Berikutnya:** Tahap 8b — investasi & staging: dermaga MP/jetty CC dengan masa konstruksi & lookahead, alat B/M, trestle/keruk dari `waterside.cost` (catatan awal untuk dicek: Excel tampaknya tidak menerapkan escalation dan "Total PV" sheet `Trestle` tidak didiskonto), penyimpanan dengan lookahead `FD!F196` dan temuan `Investasi!N78`, investasi truk & pipa CC; layar 9 bagian jadwal investasi.
- [x] Tahap 8b (2026-11-27) — Investasi & staging. Keputusan pengguna: kedua pola bangun lewat `plans[].staging` (default `phase` per tahap, opsi `incremental` saat dibutuhkan dengan lookahead); keruk kolam tambat ikut penambahan tambatan sampai kedalaman akhir, trestle penuh bersama tambatan pertama tiap terminal; tahun bangun = tahun pakai − masa konstruksi untuk semua komponen; eskalasi = opsi `params.apply_escalation`, default mati (saklar layar 1 & 9, `harga × (1 + e)^t`); batas kedalaman KEK opsional `waterside.max_depth_m` (kapal gugur di kelayakan); harga tambatan & penyimpanan = kunci `unit_prices` yang bisa diganti (`berth_price_key`, `unit_price_key`, `pipe_price_key`; silo bawaan harga tangki seperti Excel, `unit_prices.silo` dari `FD!AC144` tersedia); GC = harga lapangan GC, truk curah & GC = headtruck. **Temuan baru A26** (jendela SUM per fase tak seragam, dermaga & trestle di th −1, kolom batas terhitung dua kali, masa konstruksi `C13` tidak dirujuk), **A27** (eskalasi `C15`/`C21` tidak dirujuk), **A28** (`Investasi!N78` GC dari baris penambahan → Rp 4,5 M, seharusnya 55,0 M), **A29** (trestle kedua terminal di th −1, `K395` hanya bagian th −1, "Total PV" tidak didiskon), **A30** (pipa CC dari trestle opsi keruk 250 m). Engine: `calc/invest.py`, `run.pipeline_chain` (`storage.pipeline`, modul `waterside`) + `run.invest_chain`, modul API `invest` (7 variabel `invest.*` berseri tahun bangun, `invest_start_year`; `waterside_options[]` + `build_year`, `invest_total`, `pv`); registry 201 variabel (+ `dv.staging`, input eskalasi, batas kedalaman, kunci harga). DoD: tiruan Excel `excel_invest` = golden `Model!K369:AF395` (th −1..20) + luas GC `N78` + panjang pipa; tiruan + koreksi A26, A28–A30 = engine untuk setiap variabel & kunci dan PV opsi; hitungan tangan (staging, lookahead, masa konstruksi, eskalasi, diskonto I9, truk, pipa, batas kedalaman). `tools/diff_k15.py` bagian investasi: Σ nominal Rp 3.238,2 → 3.540,5 M; PV opsi perairan trestle penuh 406,3 / trestle + keruk 281,3 / keruk penuh 146,8 M. Web: layar 8 — PV, nilai terjadwal & tahun bangun trestle di kartu opsi (termurah menurut PV), kolom investasi penyimpanan (fasilitas, alat & truk, pipa), baris pipa di kebutuhan 20 th; layar 9 — pola bangun, masa konstruksi & lookahead, saklar eskalasi, slider discount yang aktif, grafik pelayaran + investasi per kategori, tabel jadwal investasi & item (badge `dihitung`); total cost/anuitas/NPV tetap placeholder; layar 1 — saklar eskalasi. 146 test lulus, `check.ps1` lulus; diverifikasi di browser (Σ Rp 3,54 T; eskalasi hidup → 3,66 T; saat dibutuhkan → 3,69 T). **Berikutnya:** Tahap 8c — agregasi & objektif: TC per tahun (pelayaran + investasi; Excel membagi investasi awal 20), NPV total cost, UC per satuan dengan alokasi biaya bersama berbasis pemakaian (§13 no. 9), PV_UC & anuitas, KPI layar 9.
