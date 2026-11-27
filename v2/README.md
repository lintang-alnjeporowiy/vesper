# Vesper (v2)

Kode **Vesper**: restart proyek modernisasi model TPT (Perencanaan Transportasi Laut) dengan pendekatan **UI-first + placeholder**.

| File | Isi |
|---|---|
| [docs/01_SPEC.md](docs/01_SPEC.md) | gambaran besar: domain, kontrak data, rantai kalkulasi, optimasi, peta layar, arsitektur, temuan audit Excel, pertanyaan terbuka |
| [docs/02_ROADMAP.md](docs/02_ROADMAP.md) | 14 tahap + rekomendasi effort/model per tahap |
| [blueprint/index.html](blueprint/index.html) | buka di browser: peta variabel interaktif, peta layar, prototipe rantai hitung 1 rute (cocok dengan Excel K15) |
| [cases/k15-batam.json](cases/k15-batam.json) | input kasus K15 (divalidasi oleh `cases/case.schema.json` / model Pydantic) |
| [engine/](engine/README.md) | engine Python (uv): model data `Case`, test, data pembanding Excel |
| [web/](web/src/App.tsx) | UI React (Tahap 2b): `npm --prefix web run dev`, data dari `cases/k15-batam.json`, hasil masih placeholder |
| [design/](design/wireframe-2a.fig) | wireframe OpenPencil (Tahap 2a) + pratinjau PNG |
| [tools/](tools/extract_k15.py) | ekstraksi workbook K15, export JSON Schema |

`../apps/` = v1 (referensi saja, tidak dilanjutkan). Bahan asli TPT ada di `../referensi/` (tidak masuk git).
