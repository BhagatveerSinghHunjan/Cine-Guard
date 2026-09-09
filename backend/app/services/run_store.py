"""Run-state access over the SQLite store (app.db).

Compatibility surface for routes/services: RunNotFound, status payloads,
and validated planning inputs parsed from the stored result JSON.
"""

import json

from app import db
from app.models.schemas import (
    AnalyzeResponse,
    Recommendation,
    Risk,
    RunError,
    RunEvent,
    RunStatusResponse,
    ScreenplayAnalysis,
)


class RunNotFound(KeyError):
    pass


class RunNotReady(Exception):
    """Run exists but has no completed results to plan from."""


def _parse_result(run: dict) -> AnalyzeResponse | None:
    raw = run.get("result_json")
    if not raw:
        return None
    try:
        return AnalyzeResponse.model_validate(json.loads(raw))
    except Exception:  # noqa: BLE001 -- corrupt payload means no result
        return None


def get_run_status(run_id: str) -> RunStatusResponse:
    run = db.get_run(run_id)
    if not run:
        raise RunNotFound(f"Unknown run_id: {run_id}")
    err = None
    if run.get("error_code") or run.get("error_message"):
        err = RunError(
            code=run.get("error_code") or "FAILED",
            message=run.get("error_message") or "Run failed.",
            stage=run.get("error_stage") or "",
        )
    result = _parse_result(run)
    return RunStatusResponse(
        run_id=run["id"],
        project_id=run["project_id"],
        project_title=run["project_title"],
        status=run["status"],
        current_stage=run["current_stage"],
        progress=run["progress"],
        attempt=run["attempt"],
        started_at=run["started_at"],
        completed_at=run["completed_at"],
        created_at=run["created_at"],
        updated_at=run["updated_at"],
        error=err,
        has_results=result is not None,
        events=[RunEvent(**e) for e in run.get("events", [])],
        result=result,
    )


def get_record_for_planning(run_id: str) -> dict:
    """Validated risks/recommendations for the fix-plan engine."""
    run = db.get_run(run_id)
    if not run:
        raise RunNotFound(f"Unknown run_id: {run_id}")
    result = _parse_result(run)
    if result is None:
        raise RunNotReady(f"Run {run_id} has no completed results yet.")
    return {
        "project_title": result.project_title,
        "risks": result.risks,
        "recommendations": result.recommendations,
    }


def get_planning_inputs(run_id: str) -> tuple[str, ScreenplayAnalysis, list[Risk],
                                             list[Recommendation]]:
    """Legacy inline-planning inputs parsed from the stored result."""
    run = db.get_run(run_id)
    if not run:
        raise RunNotFound(f"Unknown run_id: {run_id}")
    result = _parse_result(run)
    if result is None:
        raise RunNotReady(f"Run {run_id} has no completed results yet.")
    return result.project_title, result.analysis, result.risks, result.recommendations
