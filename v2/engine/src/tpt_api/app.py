"""FastAPI TPT Planner v2 — Tahap 4: daftar kasus & kalkulasi modul demand.

Semua rute di bawah `/api` (dev: Vite mem-proxy `/api` → :8000; Tahap 13: FastAPI juga menyajikan build web).
Skema OpenAPI → `web/src/api/openapi.ts` lewat `tools/export_openapi.py` + `npm run gen:api`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from tpt_engine.calc.run import CalcResult, Module, calculate
from tpt_engine.domain import Case, load_case

CASES_DIR = Path(os.environ.get("TPT_CASES_DIR") or Path(__file__).resolve().parents[3] / "cases")

app = FastAPI(
    title="TPT Planner v2 API",
    version="0.4.0",
    description="Engine perencanaan transportasi laut (TPT). Hasil /calculate berkunci id variabel registry.",
    separate_input_output_schemas=False,
)


class CaseSummary(BaseModel):
    id: str = Field(description="nama file tanpa .json")
    name: str
    location: str | None = None
    status: Literal["siap", "tidak_valid"]
    error: str | None = None


class CalcRequest(BaseModel):
    case: Case = Field(description="kasus aktif (termasuk editan di UI)")
    modules: list[Module] = Field(["demand"], description="modul engine yang dihitung")
    plan_id: str | None = Field(None, description="rencana kapal per flow; default plan pertama kasus")
    ship_by_flow: dict[str, str] | None = Field(None, description="override kapal per flow di atas plan")


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    modules: list[str]


def _case_files() -> list[Path]:
    return sorted(p for p in CASES_DIR.glob("*.json") if not p.name.endswith(".schema.json"))


@app.get("/api/health", response_model=Health, tags=["meta"])
def health() -> Health:
    from tpt_engine.calc.run import MODULES

    return Health(version=app.version, modules=list(MODULES))


@app.get("/api/cases", response_model=list[CaseSummary], tags=["cases"])
def list_cases() -> list[CaseSummary]:
    out: list[CaseSummary] = []
    for p in _case_files():
        try:
            c = load_case(p)
            out.append(CaseSummary(id=p.stem, name=c.meta.name, location=c.meta.location, status="siap"))
        except (ValidationError, ValueError) as e:
            out.append(CaseSummary(id=p.stem, name=p.stem, status="tidak_valid", error=str(e).splitlines()[0]))
    return out


@app.get("/api/cases/{case_id}", response_model=Case, tags=["cases"])
def get_case(case_id: str) -> Case:
    p = CASES_DIR / f"{case_id}.json"
    if "/" in case_id or "\\" in case_id or not p.is_file():
        raise HTTPException(404, f"kasus '{case_id}' tidak ditemukan")
    return load_case(p)


@app.post("/api/calculate", response_model=CalcResult, tags=["calc"])
def post_calculate(req: CalcRequest) -> CalcResult:
    try:
        return calculate(req.case, list(req.modules), plan_id=req.plan_id, ship_by_flow=req.ship_by_flow)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e)) from e
