"""Health / status endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "cineguard-backend"


def test_api_status_has_workflow_and_no_secrets():
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert "workflow" in body
    assert "integrations" in body
    raw = r.text
    assert "sk-" not in raw.lower()
    # keys must never leak values; mode is honest about live vs not-configured
    assert body["integrations"]["parallel_mode"] in ("live", "not-configured")
