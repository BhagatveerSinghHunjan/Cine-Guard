"""Orchestration for the full intelligence workflow.

SCREENPLAY → EXTRACTION → RESEARCH PLANNER → PARALLEL → EVIDENCE
→ RISK REASONING → DETERMINISTIC SCORING → RECOMMENDATIONS → RUN STATE

Stages are REAL backend work, persisted per run with events:
queued → analyzing_screenplay → researching → reasoning_risks
→ building_plan → completed | failed.

- Gemini configured → real extraction + real risk reasoning.
- Not configured → deterministic heuristic fallback (offline-safe).
- Research degrades honestly without a key (no fake citations) and
  never fails the analysis when the provider errors.
- Readiness is ALWAYS backend-calculated, never model-invented.
"""

import logging
import threading

from app import db
from app.config import get_settings
from app.models.schemas import ProductionPlan, ScreenplayAnalysis
from app.services.fixplan import build_fix_plan
from app.services.gemini_extraction import (
    GeminiNotConfigured,
    InputTooLargeError,
    chunk_screenplay,
    extract_heuristic_fallback,
    extract_with_gemini,
)
from app.services.readiness import score_readiness
from app.tools.planning_tools import build_plan
from app.tools.research_tools import build_research_notes, run_research
from app.tools.risk_tools import (
    assess_risks,
    build_dependency_edges,
    count_by_severity,
    derive_unknowns,
    generate_recommendations,
)

log = logging.getLogger("cineguard.analysis")

# Stage → progress mapping. Progress is derived from completed stages only.
_STAGES = [
    "analyzing_screenplay",
    "researching",
    "reasoning_risks",
    "building_plan",
]
_STAGE_PROGRESS = {
    "queued": 0,
    "analyzing_screenplay": 15,
    "researching": 40,
    "reasoning_risks": 65,
    "building_plan": 85,
    "completed": 100,
    "failed": 0,
}


def _emit(run_id: str, event_type: str, message: str, metadata: dict | None = None) -> None:
    db.add_event(run_id, event_type, message, metadata or {})


def _set_stage(run_id: str, stage: str) -> None:
    db.update_run(run_id, status=stage, current_stage=stage,
                  progress=_STAGE_PROGRESS.get(stage, 0))


def submit_analysis(
    screenplay_text: str,
    project_title: str | None = None,
    project_id: str | None = None,
    background: bool = True,
) -> dict:
    """Validate input, persist a queued run, and start background execution."""
    settings = get_settings()
    text = (screenplay_text or "").strip()
    if not text:
        raise ValueError("screenplay_text must not be empty")
    # Explicit guardrail (Pydantic max_length also enforces at the boundary).
    chunk_screenplay(text, settings.max_screenplay_chars)

    title = (project_title or "").strip() or "Untitled"
    project = db.get_or_create_project(title, project_id)
    run = db.create_run(project["id"], text, title)
    db.add_event(run["id"], "run_queued", "Analysis queued",
                 {"project_id": project["id"]})
    if background:
        thread = threading.Thread(target=execute_run, args=(run["id"],), daemon=True)
        thread.start()
    return {"run_id": run["id"], "project_id": project["id"], "status": "queued"}


def execute_run(run_id: str) -> None:
    """Run the staged pipeline, persisting stage + events. Never raises."""
    try:
        _run_pipeline(run_id)
    except (InputTooLargeError, ValueError) as exc:
        _fail(run_id, "analyzing_screenplay", "BAD_INPUT", str(exc))
    except Exception:
        log.exception("run %s failed unexpectedly", run_id)
        _fail(run_id, _current_stage_safe(run_id), "ANALYSIS_FAILED",
              "Analysis failed unexpectedly — retry or simplify the input.")


def _current_stage_safe(run_id: str) -> str:
    try:
        run = db.get_run(run_id)
        return (run or {}).get("current_stage") or "analyzing_screenplay"
    except Exception:  # noqa: BLE001 -- best-effort stage lookup
        return "analyzing_screenplay"


def _fail(run_id: str, stage: str, code: str, message: str) -> None:
    try:
        db.add_event(run_id, "run_failed", message, {"stage": stage, "code": code})
    except Exception:  # noqa: BLE001 -- failure path must not raise
        log.warning("could not persist failure event for run %s", run_id)
    try:
        db.fail_run(run_id, stage, code, message)
    except Exception:  # noqa: BLE001 -- failure path must not raise
        log.warning("could not persist failure state for run %s", run_id)


def _run_pipeline(run_id: str) -> None:
    from app.services.gemini_extraction import (
        GeminiAPIError,
        GeminiAuthError,
        GeminiTimeoutError,
        GeminiValidationError,
    )

    settings = get_settings()
    run = db.get_run(run_id)
    if not run:
        return
    text = run["screenplay_text"]
    title = run["project_title"]
    db.add_event(run_id, "screenplay_received",
                 f"Screenplay received ({len(text):,} characters)",
                 {"chars": len(text), "attempt": run.get("attempt", 1)})

    # ── Stage 1: screenplay analysis ──
    _set_stage(run_id, "analyzing_screenplay")
    warnings: list[str] = []
    source = "heuristic"
    model = ""
    try:
        analysis: ScreenplayAnalysis = extract_with_gemini(text, title)
        source = "gemini"
        model = settings.gemini_model
        _emit(run_id, "screenplay_parsed", "Screenplay parsed with Gemini extraction",
              {"source": source, "model": model})
    except GeminiNotConfigured:
        analysis = extract_heuristic_fallback(text, title)
        warnings = ["Gemini not configured — local heuristic extraction used."]
        _emit(run_id, "screenplay_parsed", "Screenplay parsed with local heuristics",
              {"source": source})
    except (GeminiAuthError, GeminiTimeoutError, GeminiAPIError, GeminiValidationError) as exc:
        log.warning("run %s extraction failed: %s", run_id, type(exc).__name__)
        _fail(run_id, "analyzing_screenplay", _gemini_code(exc), _gemini_user_message(exc))
        return
    _emit(run_id, "scenes_extracted", f"{len(analysis.scenes)} scene(s) extracted",
          {"scenes": len(analysis.scenes)})
    _emit(run_id, "dependencies_identified",
          f"{len(analysis.production_dependencies)} production dependencie(s) identified",
          {"dependencies": len(analysis.production_dependencies)})

    # ── Stage 2: research ──
    _set_stage(run_id, "researching")
    try:
        research, research_extra_notes = run_research(
            analysis, on_event=lambda t, m, md: _emit(run_id, t, m, md))
    except Exception:  # noqa: BLE001 -- research never fails the run
        log.warning("research stage failed; continuing without evidence")
        research, research_extra_notes = [], ["External research errored — continuing without evidence."]
        _emit(run_id, "research_errored", "Research provider errored — continuing without evidence", {})

    # ── Stage 3: risk reasoning ──
    _set_stage(run_id, "reasoning_risks")
    if source == "gemini":
        from app.services.gemini_risk import reason_risks_with_gemini

        _emit(run_id, "risk_analysis_started", "Risk reasoning with Gemini", {})
        try:
            reasoned = reason_risks_with_gemini(analysis, research)
            risks = reasoned.risks
            dependencies = reasoned.dependencies
            recommendations = reasoned.recommendations
        except GeminiNotConfigured:
            risks = assess_risks(analysis)
            dependencies = build_dependency_edges(risks)
            recommendations = generate_recommendations(risks)
            warnings.append("Risk reasoning fell back to local heuristics.")
            _emit(run_id, "risk_analysis_started", "Risk reasoning with local heuristics", {})
        except (GeminiAuthError, GeminiTimeoutError, GeminiAPIError,
                GeminiValidationError) as exc:
            log.warning("run %s risk reasoning failed: %s", run_id, type(exc).__name__)
            _fail(run_id, "reasoning_risks", _gemini_code(exc), _gemini_user_message(exc))
            return
    else:
        _emit(run_id, "risk_analysis_started", "Risk reasoning with local heuristics", {})
        risks = assess_risks(analysis)
        dependencies = build_dependency_edges(risks)
        recommendations = generate_recommendations(risks)
    if not analysis.unknowns:
        analysis.unknowns = derive_unknowns(analysis)
    if not analysis.unknowns:
        analysis.unknowns = derive_unknowns(analysis)
    by_sev = count_by_severity(risks)
    _emit(run_id, "risks_detected",
          f"{len(risks)} risk(s) detected "
          f"({by_sev.get('critical', 0)} critical, {by_sev.get('high', 0)} high)",
          {"total": len(risks), **by_sev})
    _emit(run_id, "dependency_graph_built",
          f"{len(dependencies)} risk dependencie(s) mapped", {"edges": len(dependencies)})

    # ── Stage 4: scoring + recommendations ──
    _set_stage(run_id, "building_plan")
    notes = build_research_notes(analysis) + research_extra_notes
    readiness = score_readiness(risks)
    _emit(run_id, "readiness_calculated",
          f"Readiness {readiness.score:.1f} ({readiness.status.value}) — deterministic scoring",
          {"score": readiness.score, "status": readiness.status.value})
    _emit(run_id, "recommendations_created",
          f"{len(recommendations)} recommendation(s) created",
          {"recommendations": len(recommendations)})

    from app.models.schemas import AnalyzeResponse

    result = AnalyzeResponse(
        project_title=analysis.project_title,
        run_id=run_id,
        analysis=analysis,
        risks=risks,
        dependencies=dependencies,
        recommendations=recommendations,
        research=research,
        readiness=readiness,
        research_notes=notes,
        readiness_score=readiness.score,
        risk_counts=by_sev,
        analysis_source=source,
        extraction_model=model,
        extraction_warnings=warnings,
    )

    db.complete_run(run_id, result.model_dump(mode="json"))
    db.add_event(run_id, "run_completed",
                 f"Analysis completed — readiness {readiness.score:.1f}",
                 {"score": readiness.score})


def _gemini_user_message(exc: Exception) -> str:
    """Fixed user-facing messages — originals stay server-side only."""
    from app.services.gemini_extraction import (
        GeminiAuthError,
        GeminiTimeoutError,
        GeminiValidationError,
    )

    if isinstance(exc, GeminiAuthError):
        return "Gemini authentication failed on the server."
    if isinstance(exc, GeminiTimeoutError):
        return "Gemini request timed out — retry shortly."
    if isinstance(exc, GeminiValidationError):
        return "Gemini returned unusable output — retry or simplify the input."
    return "Gemini request failed — retry shortly."


def _gemini_code(exc: Exception) -> str:
    from app.services.gemini_extraction import (
        GeminiAuthError,
        GeminiTimeoutError,
        GeminiValidationError,
    )

    if isinstance(exc, GeminiAuthError):
        return "GEMINI_AUTH"
    if isinstance(exc, GeminiTimeoutError):
        return "GEMINI_TIMEOUT"
    if isinstance(exc, GeminiValidationError):
        return "GEMINI_OUTPUT"
    return "GEMINI_ERROR"


def run_full_analysis(
    screenplay_text: str, project_title: str | None = None
) -> dict:
    """Synchronous convenience: submit + execute inline, return result dict.

    Used by tests and the local smoke test. Production HTTP path uses
    submit_analysis (background) + GET /api/runs/{id} (poll).
    """
    submitted = submit_analysis(screenplay_text, project_title, background=False)
    execute_run(submitted["run_id"])
    run = db.get_run(submitted["run_id"])
    if not run or run["status"] != "completed":
        err = (run or {}).get("error_message") or "Analysis failed."
        raise RuntimeError(err)
    import json

    from app.models.schemas import AnalyzeResponse

    # Revalidate into models so callers get the same object shapes as before.
    parsed = AnalyzeResponse.model_validate(json.loads(run["result_json"]))
    return {
        "run_id": parsed.run_id,
        "project_title": parsed.project_title,
        "analysis": parsed.analysis,
        "risks": parsed.risks,
        "dependencies": parsed.dependencies,
        "recommendations": parsed.recommendations,
        "research": parsed.research,
        "readiness": parsed.readiness,
        "research_notes": parsed.research_notes,
        "readiness_score": parsed.readiness_score,
        "risk_counts": parsed.risk_counts,
        "analysis_source": parsed.analysis_source,
        "extraction_model": parsed.extraction_model,
        "extraction_warnings": parsed.extraction_warnings,
    }


def run_fix_plan(run_id: str, selected_ids: list[str]) -> dict:
    """Build a deterministic mitigation plan for a stored completed run."""
    from app.services.run_store import get_record_for_planning

    record = get_record_for_planning(run_id)
    from app.services.readiness import score_readiness as _score

    current = _score(record["risks"])
    fix_plan = build_fix_plan(record["risks"], record["recommendations"], selected_ids or [])
    db.add_event(
        run_id, "plan_generated",
        f"Fix plan built: {len(fix_plan.actions)} action(s), "
        f"projected readiness {fix_plan.projected_readiness.score:.1f}",
        {"actions": len(fix_plan.actions),
         "projected": fix_plan.projected_readiness.score},
    )
    return {
        "run_id": run_id,
        "project_title": record["project_title"],
        "fix_plan": fix_plan,
        "affected_risks": fix_plan.affected_risk_ids,
        "projected_readiness": fix_plan.projected_readiness,
        "current_readiness": current,
    }


def run_planning(
    analysis: ScreenplayAnalysis | None, risks: list | None
) -> ProductionPlan:
    return build_plan(analysis, risks or [])
