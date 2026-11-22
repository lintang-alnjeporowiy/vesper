"""FastAPI TPT Planner v2 — daftar kasus, kalkulasi per modul (demand, voyage), bandingkan kandidat kapal.

Semua rute di bawah `/api` (dev: Vite mem-proxy `/api` → :8000; Tahap 13: FastAPI juga menyajikan build web).
Skema OpenAPI → `web/src/api/openapi.ts` lewat `tools/export_openapi.py` + `npm run gen:api`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError

from tpt_engine.calc.run import MODULES, CalcResult, CompareResult, Module, calculate, compare
from tpt_engine.domain import Case, load_case

CASES_DIR = Path(os.environ.get("TPT_CASES_DIR") or Path(__file__).resolve().parents[3] / "cases")

app = FastAPI(
    title="TPT Planner v2 API",
    version="0.5.0",
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
    modules: list[Module] = Field(list(MODULES), description="modul engine yang dihitung (dependensi ikut)")
    plan_id: str | None = Field(None, description="rencana kapal & alat; default plan pertama kasus")
    ship_by_flow: dict[str, str] | None = Field(None, description="override kapal per flow di atas plan")
    equipment_by_terminal: dict[str, str] | None = Field(None, description="override alat per terminal KEK di atas plan")


class CompareRequest(BaseModel):
    case: Case = Field(description="kasus aktif (termasuk editan di UI)")
    flow_id: str
    plan_id: str | None = None
    ship_by_flow: dict[str, str] | None = None
    equipment_by_terminal: dict[str, str] | None = None


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
    modules: list[str]


def _case_files() -> list[Path]:
    return sorted(p for p in CASES_DIR.glob("*.json") if not p.name.endswith(".schema.json"))


@app.get("/api/health", response_model=Health, tags=["meta"])
def health() -> Health:
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
        return calculate(req.case, list(req.modules), plan_id=req.plan_id, ship_by_flow=req.ship_by_flow,
                         equipment_by_terminal=req.equipment_by_terminal)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e)) from e


@app.post("/api/compare", response_model=CompareResult, tags=["calc"])
def post_compare(req: CompareRequest) -> CompareResult:
    """Semua kapal kandidat untuk satu flow: kelayakan + alasan gugur + rantai §5.1–5.3 (layar 4 & 6)."""
    try:
        return compare(req.case, req.flow_id, plan_id=req.plan_id, ship_by_flow=req.ship_by_flow,
                       equipment_by_terminal=req.equipment_by_terminal)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e)) from e
