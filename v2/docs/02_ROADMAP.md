# TPT Planner v2 — Roadmap & Rekomendasi Effort

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
- **Keputusan di tahap ini:** aturan alokasi biaya bersama (investasi terminal) ke flow untuk unit cost per satuan (Rp/ton, Rp/TEU).
- **DoD:** investasi per komponen cocok Excel untuk input yang sama; NPV total cost dan unit cost per satuan dihitung; layar 8–9 hidup; I8, I9 bisa didemokan.

> **MILESTONE C — rantai manual lengkap.** Semua badge `placeholder` di layar 1–9 hilang; setiap selisih vs Excel K15 tercatat penyebabnya.

### Tahap 9 — Optimizer · 🔴🔴
- prakalkulasi koefisien `(flow, kapal, alat[, kecepatan])`; enumerasi pembanding; model MILP (`highspy`, endpoint `/optimize`) dengan level draft & nBerth integer; penjelasan (top-3 per flow, batasan aktif); layar 10.
- **Keputusan di tahap ini:** agregasi objektif unit cost (bobot per kelompok satuan atau leksikografis); default tetap NPV total cost.
- **DoD:** pada K15, NPV solusi optimizer ≤ NPV solusi Evolver bila keduanya dihitung dengan engine v2; enumerasi & MILP sepakat pada instance kecil; waktu < beberapa detik.
- **Kenapa 🔴🔴:** formulasi, linearisasi, dan verifikasi optimum.

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
- [ ] Milestone A — (2026-11-22, berjalan) alat review di UI: tab **Review** di laci kanan + tombol *Catat koreksi* per variabel, centang layar ditinjau, sinkron ke `v2/review/notes.json` (lihat SPEC §8). Alur: pengguna klik-tembus layar 0 → 12 dan mencatat koreksi; agen membaca `notes.json`, menerapkan ke registry/SPEC/UI, menandai catatan selesai. Selesai bila 13/13 layar ditinjau dan tidak ada catatan terbuka.
