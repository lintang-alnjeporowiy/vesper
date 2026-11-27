# tpt-engine

Engine Python Vesper (lihat `../docs/01_SPEC.md`). Saat ini (Tahap 1) berisi kontrak data `Case`.

Perintah (dari folder `v2/`):

```powershell
uv run --project engine pytest engine/tests -q
uv run --project engine python tools/extract_k15.py "../referensi/K15/TPT_Kelompok 15 Revisi 02-Januari-2025.xlsx"
uv run --project engine python tools/export_schema.py
```

- `src/tpt_engine/domain/case.py` — model Pydantic `Case` + validasi integritas.
- `../cases/k15-batam.json` — input kasus K15 (hasil ekstraksi, setiap angka punya `refs` ke sel Excel).
- `tests/golden/k15_excel.json` — nilai Excel K15 sebagai pembanding (`affected_by` = temuan audit SPEC §11).
