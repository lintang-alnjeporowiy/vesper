"""Tulis registry variabel ke web/src/mock/registry.json (dibaca UI sebagai mock sampai endpoint /registry ada).

Jalankan dari folder v2:  uv run --project engine python tools/dump_registry.py
"""

from pathlib import Path

from tpt_engine.registry import REGISTRY, to_json, topo_order

topo_order()  # gagal keras bila ada siklus
out = Path(__file__).resolve().parents[1] / "web" / "src" / "mock" / "registry.json"
out.write_text(to_json(), encoding="utf-8", newline="\n")
print(f"{len(REGISTRY)} variabel -> {out}")
