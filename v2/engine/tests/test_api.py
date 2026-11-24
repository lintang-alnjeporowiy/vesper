"""Tahap 4 — fondasi API: /cases, /calculate (modul demand), skema OpenAPI web sinkron."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tpt_api.app import app

V2 = Path(__file__).resolve().parents[2]
CASE = json.loads((V2 / "cases" / "k15-batam.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and "demand" in r.json()["modules"]


def test_list_and_get_case(client):
    items = client.get("/api/cases").json()
    k15 = next(i for i in items if i["id"] == "k15-batam")
    assert k15["status"] == "siap"
    assert client.get("/api/cases/k15-batam").json()["meta"]["id"] == CASE["meta"]["id"]
    assert client.get("/api/cases/tidak-ada").status_code == 404


def test_calculate_demand(client):
    r = client.post("/api/calculate", json={"case": CASE, "modules": ["demand"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan_id"] == "k15-excel"
    assert "cargo.demand_unit" in body["computed"]
    assert body["values"]["cargo.demand_unit"]["out.baru"][7] == 303031
    assert body["units"]["out.damai"] == "TEU" and body["units"]["in.damai"] == "ton"


def test_calculate_reflects_edits(client):
    """Editan UI (laju pertumbuhan) dikirim dalam kasus → hasil berubah."""
    edited = json.loads(json.dumps(CASE))
    f = next(x for x in edited["flows"] if x["id"] == "in.damai")
    f["volume"]["growth_rate"] = 0.10
    body = client.post("/api/calculate", json={"case": edited}).json()
    assert body["values"]["demand.base"]["in.damai"][1] == pytest.approx(3_300_000)


def test_calculate_voyage_and_compare(client):
    body = client.post("/api/calculate", json={"case": CASE, "modules": ["voyage"]}).json()
    assert body["modules"] == ["demand", "voyage"] and body["values"]["voyage.n_ship"]["in.damai"][0] == 2
    cmp = client.post("/api/compare", json={"case": CASE, "flow_id": "in.damai"})
    assert cmp.status_code == 200, cmp.text
    rows = {r["ship_id"]: r for r in cmp.json()["rows"]}
    assert rows["ship.aetos"]["selected"] and rows["ship.aetos"]["feasible"]
    assert client.post("/api/compare", json={"case": CASE, "flow_id": "x"}).status_code == 422


def test_calculate_errors(client):
    assert client.post("/api/calculate", json={"case": CASE, "modules": ["invest"]}).status_code == 422
    assert client.post("/api/calculate", json={"case": CASE, "plan_id": "x"}).status_code == 422


def test_openapi_snapshot_in_sync():
    """web/src/api/openapi.json harus sama dengan skema app (jalankan tools/export_openapi.py + npm run gen:api)."""
    snap = V2 / "web" / "src" / "api" / "openapi.json"
    assert json.loads(snap.read_text(encoding="utf-8")) == json.loads(json.dumps(app.openapi())), \
        "openapi.json basi: jalankan `uv run --project engine python tools/export_openapi.py` lalu `npm --prefix web run gen:api`"
