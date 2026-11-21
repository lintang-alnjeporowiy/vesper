"""Tulis JSON Schema model Case ke cases/case.schema.json (dipakai editor & web untuk validasi/autocomplete).

Jalankan dari folder v2:  uv run --project engine python tools/export_schema.py
"""

import json
from pathlib import Path

from tpt_engine.domain import case_json_schema

out = Path(__file__).resolve().parents[1] / "cases" / "case.schema.json"
out.write_text(json.dumps(case_json_schema(), ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
print(f"schema -> {out}")
