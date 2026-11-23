# TPT Planner — panduan agen

Proyek ini memodernisasi model optimasi (MILP) tugas **Perencanaan Transportasi Laut (TPT)**, Teknik Transportasi Laut ITS, menjadi aplikasi untuk merencanakan armada kapal per rute dan terminal khusus (TERSUS) di kawasan industri/KEK.
Pengguna adalah alumni TPT dan menguasai domainnya. **Jawab dalam Bahasa Indonesia**; istilah teknis tetap (RTD, BOR, TCH, DWT, LOA, GT).

## Mulai dari sini
- `v2/docs/01_SPEC.md` — **satu-satunya sumber kebenaran**: domain, kontrak data, rumus, arsitektur, keputusan (§11 audit Excel, §13). Baca hanya bagian yang relevan dengan tugas.
- `v2/docs/02_ROADMAP.md` — tahapan, rekomendasi effort per tahap, dan **Progres** (lihat tahap berikutnya di sana).
- `v2/blueprint/index.html` — peta variabel, peta layar, prototipe rantai hitung 1 rute.

## Struktur
- `v2/cases/k15-batam.json` — input kasus utama (K15, KI Batam); skema `v2/cases/case.schema.json`. Celah data & asumsi ada di field `assumptions`.
- `v2/engine/` — engine Python 3.13 (uv + Pydantic, lint ruff). Dari folder `v2/`: `uv run --project engine pytest engine/tests -q`. Pakai `uv` (sudah di PATH); `python` di PATH hanya stub Windows Store.
- `v2/tools/extract_k15.py` — membuat ulang kasus & data pembanding dari Excel K15; `v2/tools/export_schema.py` — JSON Schema.
- `v2/tools/diff_k15.py` — laporan selisih engine vs Excel K15 per flow + penyebab audit (tiruan rumus Excel di `v2/engine/tests/excel_k15.py`; dites: tiruan = golden, tiruan + koreksi = engine).
- `v2/engine/src/tpt_engine/registry.py` — registry variabel (rumus, deps, Excel) untuk jejak & peta variabel; setelah mengubahnya jalankan `uv run --project engine python tools/dump_registry.py` (dari `v2/`) — test gagal bila `web/src/mock/registry.json` basi.
- `v2/engine/src/tpt_api/` — FastAPI (Tahap 4): `/api/cases`, `/api/calculate` (hasil berkunci id registry). Jalankan konfigurasi "api" di `.claude/launch.json` (uvicorn :8000); Vite mem-proxy `/api`.
- `v2/web/` — UI React + Vite + Tailwind + Zustand (Tahap 2b). Jalankan sendiri API + web: `powershell -File v2\tools\dev.ps1` (opsi `-WebPort`, `-ApiPort`, `-NoApi`, `-NoBrowser`; Ctrl+C menghentikan keduanya), atau konfigurasi "api" + "web" di `.claude/launch.json`; cek: `npm --prefix v2/web run build`. Angka yang dihitung engine datang dari `/api/calculate` (badge `dihitung`, kembali ke placeholder bila API mati); sisanya dummy di `v2/web/src/mock/placeholders.ts`.
- `v2/review/notes.json` — catatan koreksi Milestone A dari tab Review di UI (disinkronkan dev server). Terapkan catatan terbuka ke registry/SPEC/UI, lalu set `done: true` (perbarui `updated`).
- `apps/` — v1, **hanya referensi**; jangan diubah kecuali diminta. Repo git tersendiri; di-gitignore.
- `referensi/K15|K21|K24|K7/` — bahan asli TPT milik kelompok lain (xlsx/pdf/pptx): K15 (utama), K21 & K24 (uji lanjutan), K7 (varian hub-spoke, di luar cakupan). **Di-gitignore; jangan pernah di-commit.**
- `arsip/` — catatan lama era v1 (21 Juli) dan file lepas; di-gitignore.
- Repo git di root (`main`); `.gitignore` juga mengecualikan semua `*.xlsx/*.pdf/*.pptx`, `.claude/skills/`, `node_modules/`, `.venv/`.

## Lingkungan dev
- Butuh: Node (npm), `uv`, git. Instalasi bersih + semua cek: `powershell -File v2\tools\check.ps1 -Install`; tanpa `-Install` hanya menjalankan cek (ruff, pytest, tsc, oxlint, vite build). **Jalankan sebelum menyelesaikan tugas yang mengubah kode.**
- Tipe TS dibuat ulang setelah model Pydantic/API berubah (dari `v2/`): `uv run --project engine python tools/export_openapi.py` lalu `npm --prefix web run gen:api` (openapi-typescript di `web/tools/gen-api`, dipasang `check.ps1 -Install`); `tools/export_schema.py` untuk `case.schema.json`. Test gagal bila `web/src/api/openapi.json` basi.
- Line ending LF (`.gitattributes`, `.editorconfig`); skrip `.ps1` CRLF. Penulis file Python memakai `newline="\n"`.

## Aturan kerja
1. Keputusan baru → perbarui `01_SPEC.md` dan Progres di `02_ROADMAP.md`. Jangan membuat dokumen baru.
2. Angka hasil yang belum dihitung engine wajib berlabel `placeholder`.
3. Engine hanya mengimplementasikan versi terkoreksi (tanpa mode kompatibel Excel); setiap selisih vs Excel dijelaskan dengan ID temuan audit A1–A20.
4. Satu tahap (atau sub-tahap) per sesi; akhiri dengan memperbarui Progres.

## OpenPencil (desain UI, Tahap 2a)
- Server MCP `openpencil` terdaftar di `.mcp.json`. Aplikasi OpenPencil harus sudah terbuka sebelum sesi dimulai, kalau tidak tool-nya tidak tersedia.
- Jangan pernah menampilkan atau menyalin token dari `%LOCALAPPDATA%\OpenPencil\mcp.json`.
- Wireframe: satu halaman per layar SPEC §8 + satu halaman komponen bersama; isi dengan data `k15-batam.json`; pengguna mengoreksi lewat komentar di kanvas.
