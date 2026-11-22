"""Tulis skema OpenAPI FastAPI ke web/src/api/openapi.json (sumber `npm --prefix web run gen:api`).

Jalankan dari folder v2:  uv run --project engine python tools/export_openapi.py
"""

import json
from pathlib import Path

from tpt_api.app import app

out = Path(__file__).resolve().parents[1] / "web" / "src" / "api" / "openapi.json"
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"OpenAPI -> {out}")
