"""FastAPI entry — structured JSON only, tolerant validation.

Single consistent error envelope everywhere:
  {"error": {"code": "CODE", "message": "human text", "details": {...}}}
Never stack traces, never secrets.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import db
from app.agents.root_agent import describe_workflow
from app.config import get_settings
from app.models.schemas import (
    AnalyzeRequest,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    ProjectSummary,
    RetryAccepted,
    RunAccepted,
    RunStatusResponse,
    RunSummary,
)
from app.services.analysis_service import (
    execute_run,
    run_fix_plan,
    run_planning,
    submit_analysis,
)
from app.services.gemini_extraction import (
    GeminiAPIError,
    GeminiAuthError,
    GeminiTimeoutError,
    GeminiValidationError,
)
from app.services.run_store import RunNotFound, RunNotReady, get_planning_inputs, get_run_status

log = logging.getLogger("cineguard")
settings = get_settings()


def _err(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _validate_startup_config() -> None:
    """Log production-readiness gaps at startup. Names only — never values."""
    s = get_settings()
    missing = []
    if not s.gemini_api_key and not s.google_cloud_project:
        missing.append("GEMINI_API_KEY (or GOOGLE_CLOUD_PROJECT for Vertex)")
    if not s.parallel_api_key:
        missing.append("PARALLEL_API_KEY")
    if not s.database_url:
        missing.append("DATABASE_URL")
    if missing:
        log.warning(
            "production config incomplete — running degraded: missing %s",
            ", ".join(missing),
        )
    else:
        log.info("production config complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_startup_config()
    db.migrate()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_err("VALIDATION_ERROR", "Request failed validation.",
                     {"fields": exc.errors()}),
    )


@app.exception_handler(ValueError)
async def value_handler(_: Request, exc: ValueError):
    # InputTooLargeError subclasses ValueError → 400 with actionable message.
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_err("BAD_INPUT", str(exc)),
    )


def _safe_error(code: str, message: str, http: int) -> JSONResponse:
    """Guaranteed secret-free error envelope."""
    return JSONResponse(status_code=http, content=_err(code, message))


@app.exception_handler(GeminiAuthError)
async def gemini_auth_handler(_: Request, exc: GeminiAuthError):
    log.warning("gemini auth failure")
    return _safe_error(
        "GEMINI_AUTH",
        "Gemini authentication failed on the server — check GEMINI_API_KEY / project.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.exception_handler(GeminiTimeoutError)
async def gemini_timeout_handler(_: Request, exc: GeminiTimeoutError):
    return _safe_error("GEMINI_TIMEOUT", "Gemini request timed out — retry shortly.", 504)


@app.exception_handler(GeminiValidationError)
async def gemini_validation_handler(_: Request, exc: GeminiValidationError):
    return _safe_error(
        "GEMINI_OUTPUT",
        "Gemini returned unusable output — retry or simplify the input.",
        status.HTTP_502_BAD_GATEWAY,
    )


@app.exception_handler(GeminiAPIError)
async def gemini_api_handler(_: Request, exc: GeminiAPIError):
    return _safe_error(
        "GEMINI_ERROR", "Gemini request failed — retry shortly.", status.HTTP_502_BAD_GATEWAY
    )


@app.exception_handler(RunNotFound)
async def run_not_found_handler(_: Request, exc: RunNotFound):
    return _safe_error("RUN_NOT_FOUND", "Unknown analysis run_id.", 404)


@app.exception_handler(RunNotReady)
async def run_not_ready_handler(_: Request, exc: RunNotReady):
    return _safe_error("RUN_NOT_READY", str(exc), 409)


# ── Health & status ─────────────────────────────────────────


@app.get("/health", response_model=HealthResponse)
def health():
    s = get_settings()
    database = "ok"
    try:
        db.migrate()
    except Exception as exc:  # noqa: BLE001 -- health must not raise
        database = f"unavailable: {type(exc).__name__}"
    return HealthResponse(
        status="ok",
        service="cineguard-backend",
        version=s.app_version,
        api="ok",
        database=database,
        gemini="configured" if s.is_gemini_configured else "not-configured",
        parallel="configured" if s.is_parallel_configured else "not-configured",
    )


def _status_payload() -> dict:
    return {
        "service": "cineguard-backend",
        "version": settings.app_version,
        "workflow": describe_workflow(),
        "integrations": settings.public_status(),
    }


@app.get("/api/status")
def api_status():
    return _status_payload()


@app.get("/api/v1/status")
def api_v1_status():
    return _status_payload()


# ── Analyze (async: 202 + poll) ─────────────────────────────


class DemoScreenplay(BaseModel):
    title: str
    screenplay_text: str
    is_fictional: bool = True
    note: str = ""


@app.get("/api/demo/screenplay", response_model=DemoScreenplay)
def demo_screenplay():
    """Fictional demo screenplay, clearly labeled.

    The frontend loads this as *input* through the real analysis pipeline
    (never as pre-computed results). All names/entities are invented.
    """
    fixture = (
        Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_screenplay.txt"
    )
    try:
        text = fixture.read_text(encoding="utf-8").strip()
    except OSError:
        return JSONResponse(
            status_code=503,
            content=_err("DEMO_UNAVAILABLE", "Demo screenplay is unavailable in this deployment."),
        )
    return DemoScreenplay(
        title="Neon Harbor (Demo Production)",
        screenplay_text=text,
        is_fictional=True,
        note="Fictional demo input — all people, places and brands are invented. "
        "It runs through the real analysis pipeline; nothing is pre-computed.",
    )


@app.post("/api/analyze", response_model=RunAccepted, status_code=202)
def analyze(req: AnalyzeRequest):
    submitted = submit_analysis(req.screenplay_text, req.project_title, req.project_id)
    return RunAccepted(**submitted)


@app.post("/api/v1/analyze", response_model=RunAccepted, status_code=202)
def analyze_v1(req: AnalyzeRequest):
    return analyze(req)


# ── Runs ────────────────────────────────────────────────────


@app.get("/api/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: str):
    """Run status + events + results when complete. Poll this, not timers."""
    return get_run_status(run_id)


@app.post("/api/runs/{run_id}/retry", response_model=RetryAccepted, status_code=202)
def retry_run(run_id: str):
    """Safely restart a failed run (same id, no duplicated artifacts)."""
    reset = db.reset_run_for_retry(run_id)
    if reset is None:
        existing = db.get_run(run_id)
        if existing is None:
            raise RunNotFound(f"Unknown run_id: {run_id}")
        return JSONResponse(
            status_code=409,
            content=_err("RUN_NOT_RETRYABLE", "Only failed runs can be retried.",
                         {"status": existing["status"]}),
        )
    import threading

    thread = threading.Thread(target=execute_run, args=(run_id,), daemon=True)
    thread.start()
    return RetryAccepted(run_id=run_id, status="queued", attempt=reset["attempt"])


# ── Projects ────────────────────────────────────────────────


@app.get("/api/projects", response_model=list[ProjectSummary])
def list_projects():
    return [ProjectSummary(**p) for p in db.list_projects()]


@app.get("/api/projects/{project_id}/runs", response_model=list[RunSummary])
def list_project_runs(project_id: str):
    if not db.get_project(project_id):
        raise RunNotFound(f"Unknown project_id: {project_id}")
    out = []
    for r in db.list_runs(project_id):
        out.append(
            RunSummary(
                run_id=r["id"],
                project_id=r["project_id"],
                project_title=r["project_title"],
                status=r["status"],
                current_stage=r["current_stage"],
                progress=r["progress"],
                attempt=r["attempt"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                created_at=r["created_at"],
                error=None,
                has_results=bool(r.get("result_json")),
                event_count=r.get("event_count", 0),
            )
        )
    return out


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project; runs + events cascade so nothing orphans."""
    if not db.delete_project(project_id):
        raise RunNotFound(f"Unknown project_id: {project_id}")
    return {"deleted": project_id}


# ── Plan ────────────────────────────────────────────────────


def _plan(req: PlanRequest) -> PlanResponse:
    if req.run_id:
        # Run-based fix plan: deterministic mitigation over stored state.
        result = run_fix_plan(req.run_id, req.selected_recommendation_ids)
        title, analysis, risks, _recs = get_planning_inputs(req.run_id)
        legacy = run_planning(analysis, risks)
        return PlanResponse(
            project_title=result["project_title"],
            run_id=req.run_id,
            plan=legacy,
            fix_plan=result["fix_plan"],
            affected_risks=result["affected_risks"],
            projected_readiness=result["projected_readiness"],
            current_readiness=result["current_readiness"],
        )
    plan = run_planning(req.analysis, req.risks)
    title = req.project_title or (req.analysis.project_title if req.analysis else "Untitled")
    return PlanResponse(project_title=title, plan=plan)


@app.post("/api/plan", response_model=PlanResponse)
def plan(req: PlanRequest):
    return _plan(req)


@app.post("/api/v1/plan", response_model=PlanResponse)
def plan_v1(req: PlanRequest):
    return _plan(req)
