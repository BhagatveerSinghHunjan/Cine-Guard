"""Risk reasoning layer tests — no Gemini/Parallel credentials required."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.services.analysis_service as svc
from app.main import app
from app.models.schemas import (
    EvidenceItem,
    EvidenceKind,
    RecommendationAction,
    Risk,
    RiskCategory,
    RiskConfidence,
    RiskSeverity,
    RiskStatus,
)
from app.services.fixplan import build_fix_plan
from app.services.readiness import readiness_status, risk_penalty, score_readiness
from app.tools.risk_tools import (
    build_dependency_edges,
    dedup_risks,
    generate_recommendations,
)
from tests.helpers import wait_for_run

client = TestClient(app, raise_server_exceptions=False)


def _risk(rid, sev, cat=RiskCategory.stunt, conf=RiskConfidence.high,
          scenes=None, status=RiskStatus.open, deps=None):
    return Risk(
        id=rid,
        scene_number=(scenes[0] if scenes and len(scenes) == 1 else None),
        affected_scenes=scenes or [],
        category=cat,
        severity=sev,
        title=f"{rid} title",
        description="desc",
        why_it_matters="matters",
        evidence_items=[EvidenceItem(kind=EvidenceKind.screenplay, text="quote")],
        affected_dependencies=deps or [],
        confidence=conf,
        status=status,
    )


# Classification / severity validation ───────────────────────
def test_severity_and_confidence_validation():
    with pytest.raises(ValidationError):
        Risk(id="x", category="stunt", severity="extreme", title="t", description="d")
    with pytest.raises(ValidationError):
        Risk(id="x", category="stunt", severity="high", title="t",
             description="d", confidence="certain")
    assert RiskCategory.legal.value == "legal"
    assert RiskStatus.unknown.value == "unknown"


def test_new_fields_have_safe_defaults():
    r = Risk(id="R-1", category="other", severity="low", title="t", description="d")
    assert r.why_it_matters == ""
    assert r.confidence == RiskConfidence.medium
    assert r.status == RiskStatus.open
    assert r.affected_scenes == []
    assert r.evidence_items == []


# Evidence handling ──────────────────────────────────────────
def test_heuristic_evidence_never_fabricates_research():
    risks = svc.run_full_analysis("INT. ROOM - DAY\nJON walks in.")["risks"]
    kinds = {i.kind for r in risks for i in r.evidence_items}
    assert EvidenceKind.research not in kinds


def test_mocked_parallel_evidence_mapping(monkeypatch):
    """Canned Parallel payload → structured sources; honest empty without key."""
    import json as _json
    import urllib.request as _url

    from app.models.schemas import ScreenplayAnalysis
    from app.tools.research_tools import plan_research_queries, run_research

    analysis = ScreenplayAnalysis(
        project_title="T",
        locations=["Pier 9"],
        brands=["ZestPop"],
        stunts=["chase"],
    )
    queries = plan_research_queries(analysis)
    assert 1 <= len(queries) <= 6
    assert any("Pier 9" in q.objective for q in queries)

    # No key in this env → honest not-run, zero sources.
    evidence, notes = run_research(analysis)
    assert evidence == []
    assert any("not run" in n for n in notes)

    # Live mapping with a mocked transport (no network, no key in code).
    payload = _json.dumps({"results": [{
        "url": "https://filmoffice.example/permits",
        "title": "Film Office Permits",
        "publish_date": "2025-01-01",
        "excerpts": ["Permits take 10 days."]}]}).encode()

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return payload

    monkeypatch.setattr(_url, "urlopen", lambda req, timeout=None: _Resp())
    from app.tools.research_tools import ParallelResearchProvider
    got = ParallelResearchProvider("DUMMY-KEY-FOR-TEST", max_results=5).search(queries[:1])
    assert got[0].status == "complete"
    src = got[0].sources[0]
    assert src.domain == "filmoffice.example"
    assert src.url == "https://filmoffice.example/permits"
    assert "10 days" in src.excerpt


# Dedup ──────────────────────────────────────────────────────
def test_dedup_merges_same_problem_across_scenes():
    risks = [
        _risk("R-001", RiskSeverity.medium, RiskCategory.schedule, scenes=[12]),
        _risk("R-002", RiskSeverity.medium, RiskCategory.schedule, scenes=[13]),
        _risk("R-003", RiskSeverity.medium, RiskCategory.schedule, scenes=[14]),
    ]
    for r in risks:
        r.title = "Night exterior shooting"
    out = dedup_risks(risks)
    assert len(out) == 1
    assert out[0].affected_scenes == [12, 13, 14]
    assert out[0].scene_number is None


def test_dedup_keeps_distinct_risks():
    out = dedup_risks([
        _risk("R-001", RiskSeverity.high, RiskCategory.stunt, scenes=[1]),
        _risk("R-002", RiskSeverity.high, RiskCategory.permit, scenes=[1]),
    ])
    assert len(out) == 2


# Dependencies ───────────────────────────────────────────────
def test_dependency_edges_link_shared_scenes():
    permit = _risk("R-001", RiskSeverity.high, RiskCategory.permit, scenes=[2])
    stunt = _risk("R-002", RiskSeverity.high, RiskCategory.stunt, scenes=[2])
    edges = build_dependency_edges([permit, stunt])
    assert any(e.source_risk_id == "R-001" and e.target_risk_id == "R-002"
               and e.relationship.value == "blocks" for e in edges)


def test_no_self_edges():
    edges = build_dependency_edges([_risk("R-001", RiskSeverity.low, scenes=[1])])
    assert all(e.source_risk_id != e.target_risk_id for e in edges)


# Deterministic scoring ──────────────────────────────────────
def test_scoring_deterministic_and_documented():
    risks = [_risk("R-1", RiskSeverity.critical), _risk("R-2", RiskSeverity.high)]
    a = score_readiness(risks)
    b = score_readiness(risks)
    assert a.score == b.score == 80.0  # 100 − (15 + 5)
    assert "critical=15" in a.methodology
    assert a.blockers == ["R-1", "R-2"]
    lines = {line.severity: line for line in a.penalty_breakdown}
    assert lines["critical"].penalty == 15.0
    assert lines["high"].penalty == 5.0
    assert lines["medium"].penalty == 0.0
    assert lines["critical"].count == 1 and lines["critical"].weight == 15.0
    assert sum(line.penalty for line in a.penalty_breakdown) == pytest.approx(20.0)


def test_demo_screenplay_endpoint_labels_fiction():
    r = client.get("/api/demo/screenplay")
    assert r.status_code == 200
    body = r.json()
    assert body["is_fictional"] is True
    assert "fictional" in body["note"].lower()
    assert len(body["screenplay_text"]) > 500
    assert "INT." in body["screenplay_text"]


def test_confidence_weights_penalty():
    hi = _risk("R-1", RiskSeverity.high, conf=RiskConfidence.high)
    lo = _risk("R-1", RiskSeverity.high, conf=RiskConfidence.low)
    assert risk_penalty(hi) == 5.0
    assert risk_penalty(lo) == pytest.approx(2.0)
    assert score_readiness([lo]).score > score_readiness([hi]).score


def test_mitigated_risks_score_zero():
    r = _risk("R-1", RiskSeverity.critical, status=RiskStatus.mitigated)
    assert score_readiness([r]).score == 100.0


def test_status_thresholds():
    assert readiness_status(100).value == "READY"
    assert readiness_status(80).value == "READY"
    assert readiness_status(79.9).value == "AT RISK"
    assert readiness_status(60).value == "AT RISK"
    assert readiness_status(59.9).value == "HIGH RISK"
    assert readiness_status(40).value == "HIGH RISK"
    assert readiness_status(39.9).value == "NOT READY"
    assert readiness_status(0).value == "NOT READY"


def test_edge_cases():
    assert score_readiness([]).score == 100.0
    assert score_readiness([]).status.value == "READY"
    lows = [_risk(f"R-{i}", RiskSeverity.low) for i in range(4)]
    assert score_readiness(lows).score == pytest.approx(98.0)  # 4 × 0.5 × 1.0
    crit = score_readiness([_risk("R-1", RiskSeverity.critical)])
    assert crit.score == 85.0 and crit.status.value == "READY"
    many = [_risk(f"R-{i}", RiskSeverity.high) for i in range(10)]
    assert score_readiness(many).score == 50.0
    assert score_readiness(many).status.value == "HIGH RISK"


# Recommendations + mitigation ───────────────────────────────
def test_recommendation_generation_actionable():
    risks = [_risk("R-1", RiskSeverity.high, RiskCategory.location, scenes=[18, 19])]
    recs = generate_recommendations(risks)
    assert len(recs) == 1
    assert recs[0].action_type == RecommendationAction.replace_location
    assert recs[0].addresses_risk_ids == ["R-1"]
    assert recs[0].priority == 2


def test_mitigation_math_and_projected_readiness():
    risks = [_risk("R-1", RiskSeverity.high, RiskCategory.stunt, scenes=[2]),
             _risk("R-2", RiskSeverity.medium, RiskCategory.brand)]
    recs = generate_recommendations(risks)
    before = score_readiness(risks).score
    plan = build_fix_plan(risks, recs, [recs[0].id])
    assert plan.projected_readiness.score > before
    # high(5.0) mitigated → only medium(2.0): 98.0
    assert plan.projected_readiness.score == pytest.approx(98.0)
    assert plan.affected_risk_ids == ["R-1"]
    assert plan.remaining_blockers == []


def test_unknown_ids_ignored_and_empty_selection():
    risks = [_risk("R-1", RiskSeverity.high)]
    recs = generate_recommendations(risks)
    plan = build_fix_plan(risks, recs, ["REC-999"])
    assert plan.actions == []
    assert plan.projected_readiness.score == score_readiness(risks).score


# API: analyze shape + plan flow ─────────────────────────────
def test_analyze_returns_full_workflow_shape():
    r = client.post("/api/analyze", json={
        "screenplay_text": "INT. WAREHOUSE - NIGHT\nJACK enters with a gun. A chase erupts as rain falls.",
        "project_title": "Shape",
    })
    assert r.status_code == 202
    status = wait_for_run(client, r.json()["run_id"])
    assert status["status"] == "completed"
    body = status["result"]
    for key in ("run_id", "project", "scenes", "characters", "locations",
                "dependencies", "research", "risks", "readiness", "recommendations"):
        assert key in body or key in body.get("analysis", {}), key
    assert body["run_id"].startswith("run-")
    assert body["readiness"]["status"] in ("READY", "AT RISK", "HIGH RISK", "NOT READY")
    assert "methodology" in body["readiness"]
    assert isinstance(body["analysis"].get("unknowns"), list)
    # No fake research without a key
    assert body["research"] == []
    for risk in body["risks"]:
        for item in risk.get("evidence_items", []):
            assert item["kind"] in ("screenplay", "inference")


def test_run_inspect_then_plan_flow():
    a = client.post("/api/analyze", json={
        "screenplay_text": "EXT. PIER 9 - NIGHT\nMARA runs. A truck chase erupts in the rain.",
    })
    assert a.status_code == 202
    run_id = a.json()["run_id"]
    status = wait_for_run(client, run_id)
    result = status["result"]
    g = client.get(f"/api/runs/{run_id}")
    assert g.status_code == 200
    assert g.json()["run_id"] == run_id
    assert g.json()["events"]
    assert client.get("/api/runs/run-nope").status_code == 404

    rec_ids = [rec["id"] for rec in result["recommendations"][:1]]
    p = client.post("/api/plan", json={
        "run_id": run_id, "selected_recommendation_ids": rec_ids})
    assert p.status_code == 200
    body = p.json()
    assert body["fix_plan"]["projected_readiness"]["score"] >= result["readiness"]["score"]
    assert body["current_readiness"]["score"] == result["readiness"]["score"]
    assert isinstance(body["fix_plan"].get("improvements"), list)
    assert "revised_plan" in body["fix_plan"] or "revised_plan" in body["plan"]
    # Legacy inline path still works
    legacy = client.post("/api/plan", json={"risks": []})
    assert legacy.status_code == 200
    assert legacy.json()["plan"]["readiness_score"] == 100.0


def test_no_secrets_in_error_paths():
    r = client.post("/api/plan", json={"run_id": "run-nope", "selected_recommendation_ids": []})
    assert r.status_code == 404
    assert "api_key" not in r.text.lower() and "GEMINI" not in r.text
