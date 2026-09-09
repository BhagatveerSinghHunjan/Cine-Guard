"""Step 4 tests — Gemini extraction pipeline (no real API key required)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.services.analysis_service as svc
from app.main import app
from app.models.schemas import (
    CharacterDetail,
    ComplexityLevel,
    EvidenceLevel,
    InitialConcern,
    InteriorExterior,
    LocationDetail,
    ProjectInfo,
    Scene,
    ScreenplayAnalysis,
)
from app.services.gemini_extraction import (
    GeminiAPIError,
    GeminiAuthError,
    GeminiValidationError,
    InputTooLargeError,
    _strip_fences,
    chunk_screenplay,
)
from tests.helpers import wait_for_run

FIXTURE = Path(__file__).parent / "fixtures" / "sample_screenplay.txt"
client = TestClient(app, raise_server_exceptions=False)


def _gemini_style_analysis() -> ScreenplayAnalysis:
    return ScreenplayAnalysis(
        project_title="Neon Harbor",
        project=ProjectInfo(
            title="Neon Harbor", genre="action", estimated_complexity=ComplexityLevel.high
        ),
        genre="action",
        estimated_complexity=ComplexityLevel.high,
        scenes=[
            Scene(
                scene_number=1,
                heading="INT. WAREHOUSE - NIGHT",
                interior_or_exterior=InteriorExterior.interior,
                location="WAREHOUSE",
                time_of_day="Night",
                characters=["Jack", "Mara"],
                description="Jack and Mara argue beside guns and a ZestPop fridge.",
                production_requirements=["gun", "rain"],
                evidence_level=EvidenceLevel.explicit,
            ),
            Scene(
                scene_number=2,
                heading="EXT. PIER 9 - NIGHT",
                interior_or_exterior=InteriorExterior.exterior,
                location="PIER 9",
                time_of_day="Night",
                characters=["Mara", "Jack"],
                description="Truck chase and stunt on a storm-soaked pier.",
                production_requirements=["chase", "storm"],
                evidence_level=EvidenceLevel.explicit,
            ),
        ],
        characters=["Jack", "Mara", "Jill"],
        characters_detailed=[
            CharacterDetail(name="Jack", scenes_present=[1, 2]),
            CharacterDetail(name="Mara", scenes_present=[1, 2]),
        ],
        locations=["WAREHOUSE", "PIER 9"],
        locations_detailed=[LocationDetail(name="PIER 9", scenes=[2])],
        props=["gun"],
        vehicles=["truck"],
        brands=["ZestPop"],
        music=["song"],
        stunts=["chase"],
        vfx_requirements=[],
        weather_dependencies=["rain", "storm"],
        time_dependencies=["midnight"],
        special_equipment=["boat"],
        permits_or_clearances=["stunt permit"],
        production_dependencies=["gun", "truck", "chase"],
        initial_concerns=[
            InitialConcern(
                title="Night stunt in storm",
                description="Chase on wet pier at night.",
                category="stunt",
                scene_numbers=[2],
                evidence_level=EvidenceLevel.explicit,
                recommendation="Add safety day.",
            )
        ],
    )


# 1. Schema validation ───────────────────────────────────────
def test_evidence_enums_and_detail_models():
    s = Scene(scene_number=1)
    assert s.interior_or_exterior == InteriorExterior.unknown
    assert s.evidence_level == EvidenceLevel.explicit
    c = CharacterDetail(name="Mara")
    assert c.scenes_present == []
    assert c.evidence_level == EvidenceLevel.explicit


def test_rejects_unknown_evidence():
    with pytest.raises(ValidationError):
        Scene(scene_number=1, evidence_level="guessed")  # type: ignore


# 2/3. Empty + invalid input ─────────────────────────────────
def test_empty_screenplay_rejected():
    with pytest.raises(ValueError):
        svc.run_full_analysis("   ")


def test_over_limit_raises_not_truncates():
    with pytest.raises(InputTooLargeError):
        chunk_screenplay("x" * 50, 10)


def test_api_rejects_oversized_payload():
    big = "INT. ROOM - DAY\n" + ("x " * 100_000)
    assert len(big) > 200_000
    r = client.post("/api/analyze", json={"screenplay_text": big})
    assert r.status_code == 422


def test_strip_fences():
    assert _strip_fences("```json\n{\"a\":1}\n```") == '{"a":1}'


# 4. Mocked Gemini success ───────────────────────────────────
def test_mocked_gemini_success(monkeypatch):
    monkeypatch.setattr(svc, "extract_with_gemini", lambda t, p=None: _gemini_style_analysis())
    result = svc.run_full_analysis(FIXTURE.read_text(), "Neon Harbor")
    assert result["analysis_source"] == "gemini"
    analysis = result["analysis"]
    assert len(analysis.scenes) == 2
    assert "truck" in analysis.vehicles
    assert analysis.initial_concerns[0].evidence_level == EvidenceLevel.explicit


def test_api_returns_structured_gemini_payload(monkeypatch):
    monkeypatch.setattr(svc, "extract_with_gemini", lambda t, p=None: _gemini_style_analysis())
    r = client.post(
        "/api/analyze",
        json={"screenplay_text": FIXTURE.read_text(), "project_title": "Neon Harbor"},
    )
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "completed"
    body = status["result"]
    assert body["analysis_source"] == "gemini"
    assert body["analysis"]["genre"] == "action"
    assert body["analysis"]["special_equipment"] == ["boat"]
    assert body["analysis"]["initial_concerns"][0]["title"] == "Night stunt in storm"
    assert body["analysis"]["scenes"][0]["interior_or_exterior"] == "interior"


# 5/6. Malformed output + failures ───────────────────────────
def test_gemini_validation_error_fails_run_with_code(monkeypatch):
    def boom(t, p=None):
        raise GeminiValidationError("bad json")

    monkeypatch.setattr(svc, "extract_with_gemini", boom)
    r = client.post("/api/analyze", json={"screenplay_text": FIXTURE.read_text()})
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "failed"
    assert status["error"]["code"] == "GEMINI_OUTPUT"
    assert status["error"]["stage"] == "analyzing_screenplay"
    assert status["has_results"] is False


def test_configured_gemini_failure_surfaces_without_secrets(monkeypatch):
    import app.services.gemini_extraction as gx

    monkeypatch.setattr(gx, "is_gemini_available", lambda: True)

    def boom(t, p=None):
        raise GeminiAPIError("upstream exploded for SECRET-KEY-abc123")

    monkeypatch.setattr(svc, "extract_with_gemini", boom)
    # Simulate configured path by calling the Gemini branch directly:
    with pytest.raises(GeminiAPIError):
        svc.extract_with_gemini("INT. ROOM - DAY\nHi.")
    # And the persisted failure must use the fixed safe message, never echoing secrets:
    r = client.post("/api/analyze", json={"screenplay_text": "INT. ROOM - DAY\nHi there."})
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "failed"
    assert status["error"]["message"] == "Gemini request failed — retry shortly."
    assert "SECRET-KEY" not in status["error"]["message"]
    assert "abc123" not in status["error"]["message"]


def test_gemini_auth_fails_run_with_503_code(monkeypatch):
    def boom(*a, **k):
        raise GeminiAuthError("bad key")

    monkeypatch.setattr(svc, "extract_with_gemini", boom)
    r = client.post("/api/analyze", json={"screenplay_text": "INT. ROOM - DAY\nHi there."})
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "failed"
    assert status["error"]["code"] == "GEMINI_AUTH"
