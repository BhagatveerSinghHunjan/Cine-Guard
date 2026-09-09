"""Analyze / plan endpoint validation tests (async run contract)."""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import wait_for_run

client = TestClient(app)

SAMPLE = """MY SHORT FILM

INT. WAREHOUSE - NIGHT

JACK enters with a gun. A car chase erupts outside as rain hammers the roof.

EXT. ROOFTOP - DAY

JILL rigs an explosion for the stunt team. A helicopter circles.
"""


def test_analyze_rejects_missing_text():
    r = client.post("/api/analyze", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_rejects_empty_text():
    r = client.post("/api/analyze", json={"screenplay_text": ""})
    assert r.status_code == 422


def test_analyze_accepts_and_completes_minimal_text():
    r = client.post("/api/analyze", json={"screenplay_text": "INT. ROOM - DAY\nJON walks in."})
    assert r.status_code == 202
    body = r.json()
    assert body["run_id"].startswith("run-")
    assert body["status"] == "queued"

    status = wait_for_run(client, body["run_id"])
    assert status["status"] == "completed"
    assert status["has_results"] is True
    result = status["result"]
    assert "analysis" in result
    assert "risks" in result
    assert "readiness" in result
    assert isinstance(result["readiness"]["score"], (int, float))


def test_analyze_structured_and_scored():
    r = client.post("/api/analyze", json={"screenplay_text": SAMPLE, "project_title": "Demo"})
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "completed"
    body = status["result"]
    assert body["project_title"] == "Demo"
    assert len(body["analysis"]["scenes"]) >= 2
    # stunt/helicopter sample must produce at least one risk, honestly derived
    assert len(body["risks"]) >= 1
    assert 0 <= body["readiness"]["score"] <= 100
    # real persisted events with timestamps, in order
    seqs = [e["seq"] for e in status["events"]]
    assert seqs == sorted(seqs) and len(seqs) > 0
    assert all(e["ts"] for e in status["events"])


def test_plan_accepts_empty_risks():
    r = client.post("/api/plan", json={"risks": []})
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["readiness_score"] == 100.0


def test_plan_validation_bad_severity():
    r = client.post(
        "/api/plan",
        json={
            "risks": [
                {
                    "id": "R-1",
                    "category": "stunt",
                    "severity": "extreme",
                    "title": "t",
                    "description": "d",
                }
            ]
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
