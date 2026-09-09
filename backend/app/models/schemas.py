"""Structured Pydantic schemas — the API contract.

All responses are structured JSON (never free prose as primary output).
Every optional screenplay field has a safe default so the API never
crashes on missing data.

Step 4 additions (backward compatible — all new fields optional):
- EvidenceLevel (explicit / inferred / unknown) on extracted items.
- ProjectInfo, CharacterDetail, LocationDetail, InitialConcern.
- Scene.interior_or_exterior + evidence_level.
- ScreenplayAnalysis: genre, estimated_complexity, special_equipment,
  permits_or_clearances, detailed lists, initial_concerns.
- AnalyzeResponse: analysis_source / extraction_model / extraction_warnings.
"""

from enum import Enum

from pydantic import BaseModel, Field

MAX_SCREENPLAY_CHARS = 200_000


# ── Evidence ────────────────────────────────────────────────

class EvidenceLevel(str, Enum):
    explicit = "explicit"
    inferred = "inferred"
    unknown = "unknown"


class InteriorExterior(str, Enum):
    interior = "interior"
    exterior = "exterior"
    int_ext = "int_ext"
    unknown = "unknown"


class ComplexityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"


# ── Screenplay ──────────────────────────────────────────────

class Scene(BaseModel):
    scene_number: int = Field(ge=1)
    heading: str = ""
    interior_or_exterior: InteriorExterior = InteriorExterior.unknown
    location: str = ""
    time_of_day: str = ""
    characters: list[str] = Field(default_factory=list)
    description: str = ""
    production_requirements: list[str] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.explicit


class CharacterDetail(BaseModel):
    name: str
    role: str | None = None
    scenes_present: list[int] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.explicit


class LocationDetail(BaseModel):
    name: str
    scenes: list[int] = Field(default_factory=list)
    location_type: str | None = None
    special_requirements: list[str] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.explicit


class ProjectInfo(BaseModel):
    title: str = "Untitled"
    genre: str | None = None
    estimated_complexity: ComplexityLevel = ComplexityLevel.unknown
    evidence_level: EvidenceLevel = EvidenceLevel.inferred


class InitialConcern(BaseModel):
    title: str
    description: str = ""
    category: str = "other"
    scene_numbers: list[int] = Field(default_factory=list)
    evidence_level: EvidenceLevel = EvidenceLevel.explicit
    recommendation: str = ""


class ScreenplayAnalysis(BaseModel):
    project_title: str = "Untitled"
    project: ProjectInfo | None = None
    genre: str | None = None
    estimated_complexity: ComplexityLevel = ComplexityLevel.unknown
    scenes: list[Scene] = Field(default_factory=list)
    characters: list[str] = Field(default_factory=list)
    characters_detailed: list[CharacterDetail] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    locations_detailed: list[LocationDetail] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    vehicles: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    music: list[str] = Field(default_factory=list)
    stunts: list[str] = Field(default_factory=list)
    vfx_requirements: list[str] = Field(default_factory=list)
    weather_dependencies: list[str] = Field(default_factory=list)
    time_dependencies: list[str] = Field(default_factory=list)
    special_equipment: list[str] = Field(default_factory=list)
    permits_or_clearances: list[str] = Field(default_factory=list)
    production_dependencies: list[str] = Field(default_factory=list)
    initial_concerns: list[InitialConcern] = Field(default_factory=list)
    # Explicit unknowns — facts the screenplay cannot establish. Agents must
    # surface these instead of guessing; they are a trust feature, not a gap.
    unknowns: list[str] = Field(default_factory=list)


# ── Risk ────────────────────────────────────────────────────

class RiskSeverity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RiskCategory(str, Enum):
    location = "location"
    cast = "cast"
    schedule = "schedule"
    permit = "permit"
    brand = "brand"
    music = "music"
    vehicle = "vehicle"
    stunt = "stunt"
    vfx = "vfx"
    weather = "weather"
    equipment = "equipment"
    continuity = "continuity"
    legal = "legal"
    other = "other"


class RiskConfidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RiskStatus(str, Enum):
    open = "open"
    mitigated = "mitigated"
    unknown = "unknown"


class EvidenceKind(str, Enum):
    """Provenance of a single evidence item — never upgraded silently."""

    screenplay = "screenplay"
    research = "research"
    inference = "inference"


class EvidenceItem(BaseModel):
    kind: EvidenceKind
    text: str
    source_title: str = ""
    source_domain: str = ""
    source_url: str = ""
    scene_numbers: list[int] = Field(default_factory=list)
    # Provenance for researched facts: originating query, provider, fetch time.
    query: str = ""
    provider: str = ""
    retrieved_at: str = ""


class Risk(BaseModel):
    id: str
    scene_number: int | None = None
    affected_scenes: list[int] = Field(default_factory=list)
    category: RiskCategory
    severity: RiskSeverity
    title: str
    description: str
    why_it_matters: str = ""
    evidence: str = ""
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    recommendation: str = ""
    affected_dependencies: list[str] = Field(default_factory=list)
    confidence: RiskConfidence = RiskConfidence.medium
    status: RiskStatus = RiskStatus.open


class DependencyRelationship(str, Enum):
    blocks = "blocks"
    causes = "causes"
    affects = "affects"
    depends_on = "depends_on"


class RiskDependency(BaseModel):
    id: str
    source_risk_id: str
    target_risk_id: str
    relationship: DependencyRelationship
    impact: str = ""


# ── Research evidence ───────────────────────────────────────

class ResearchSource(BaseModel):
    """One real citation. Empty when research did not run — never faked."""

    title: str = ""
    domain: str = ""
    url: str = ""
    excerpt: str = ""
    publish_date: str | None = None


class ResearchEvidence(BaseModel):
    topic: str
    provider: str = "parallel"
    status: str = "complete"  # complete | empty | not_run | error
    summary: str = ""
    sources: list[ResearchSource] = Field(default_factory=list)
    query: str = ""
    retrieved_at: str = ""


# ── Readiness (deterministic — never model-invented) ─────────

class ReadinessStatus(str, Enum):
    ready = "READY"
    at_risk = "AT RISK"
    high_risk = "HIGH RISK"
    not_ready = "NOT READY"


class PenaltyLine(BaseModel):
    severity: str
    count: int = 0
    weight: float = 0.0
    penalty: float = 0.0


class ProductionReadiness(BaseModel):
    score: float = Field(ge=0, le=100)
    status: ReadinessStatus = ReadinessStatus.ready
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_risks: int = 0
    blockers: list[str] = Field(default_factory=list)
    methodology: str = ""
    # Explainable breakdown: real per-severity penalty totals behind the score.
    penalty_breakdown: list[PenaltyLine] = Field(default_factory=list)


# ── Recommendations & fix plan ──────────────────────────────

class RecommendationAction(str, Enum):
    replace_location = "replace_location"
    change_schedule = "change_schedule"
    obtain_permit = "obtain_permit"
    confirm_cast = "confirm_cast"
    source_vehicle = "source_vehicle"
    replace_music = "replace_music"
    review_brand = "review_brand"
    plan_stunt = "plan_stunt"
    prepare_vfx = "prepare_vfx"
    other = "other"


class Recommendation(BaseModel):
    id: str
    priority: int = Field(ge=1, default=3)
    title: str
    description: str = ""
    addresses_risk_ids: list[str] = Field(default_factory=list)
    expected_impact: str = ""
    action_type: RecommendationAction = RecommendationAction.other


class PlanAction(BaseModel):
    id: str
    recommendation_id: str
    title: str
    description: str = ""
    affected_scenes: list[int] = Field(default_factory=list)
    affected_risk_ids: list[str] = Field(default_factory=list)
    expected_risk_reduction: float = 0.0
    schedule_impact: str = ""


class FixPlan(BaseModel):
    actions: list[PlanAction] = Field(default_factory=list)
    affected_risk_ids: list[str] = Field(default_factory=list)
    projected_readiness: ProductionReadiness = Field(
        default_factory=lambda: ProductionReadiness(
            score=100.0, status=ReadinessStatus.ready, methodology=""
        )
    )
    remaining_blockers: list[str] = Field(default_factory=list)
    schedule_impact: str = ""
    revised_plan: str = ""
    # Human-readable per-action improvement lines, e.g. "R-001 mitigated: −15.0 pts".
    improvements: list[str] = Field(default_factory=list)


# ── Production plan ─────────────────────────────────────────

class ProductionPlan(BaseModel):
    readiness_score: float = Field(ge=0, le=100)
    critical_blockers: int = 0
    high_risks: int = 0
    medium_risks: int = 0
    recommendations: list[str] = Field(default_factory=list)
    proposed_changes: list[str] = Field(default_factory=list)
    schedule_impact: str = ""
    revised_plan: str = ""


# ── API envelopes ───────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    screenplay_text: str = Field(min_length=1, max_length=MAX_SCREENPLAY_CHARS)
    project_title: str | None = Field(default=None, max_length=200)
    project_id: str | None = None


class AnalyzeResponse(BaseModel):
    project_title: str
    run_id: str = ""
    analysis: ScreenplayAnalysis
    risks: list[Risk] = Field(default_factory=list)
    dependencies: list[RiskDependency] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    research: list[ResearchEvidence] = Field(default_factory=list)
    readiness: ProductionReadiness | None = None
    # Legacy flat fields (kept for existing clients).
    research_notes: list[str] = Field(default_factory=list)
    readiness_score: float = 100.0
    risk_counts: dict[str, int] = Field(default_factory=dict)
    # Provenance — safe to expose (no secrets, just source + model name).
    analysis_source: str = "heuristic"
    extraction_model: str = ""
    extraction_warnings: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    run_id: str | None = None
    selected_recommendation_ids: list[str] = Field(default_factory=list)
    # Legacy inline path (kept for existing clients).
    project_title: str | None = None
    analysis: ScreenplayAnalysis | None = None
    risks: list[Risk] = Field(default_factory=list)


class PlanResponse(BaseModel):
    project_title: str
    run_id: str = ""
    plan: ProductionPlan
    fix_plan: FixPlan | None = None
    affected_risks: list[str] = Field(default_factory=list)
    projected_readiness: ProductionReadiness | None = None
    current_readiness: ProductionReadiness | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "cineguard-backend"
    version: str = "0.1.0"
    # Dependency checks — values only, never secrets. "ok" /
    # "configured" / "not-configured" / "unavailable: <reason>".
    api: str = "ok"
    database: str = "ok"
    gemini: str = "not-configured"
    parallel: str = "not-configured"


# ── Run lifecycle ───────────────────────────────────────────

TERMINAL_RUN_STATUSES = ("completed", "failed")


class RunEvent(BaseModel):
    seq: int = 0
    ts: str = ""
    type: str
    message: str
    metadata: dict = Field(default_factory=dict)


class RunError(BaseModel):
    code: str
    message: str
    stage: str = ""


class RunAccepted(BaseModel):
    run_id: str
    project_id: str
    status: str = "queued"


class RunStatusResponse(BaseModel):
    run_id: str
    project_id: str = ""
    project_title: str = "Untitled"
    status: str
    current_stage: str = ""
    progress: int = 0
    attempt: int = 1
    started_at: str = ""
    completed_at: str | None = None
    created_at: str = ""
    updated_at: str = ""
    error: RunError | None = None
    has_results: bool = False
    events: list[RunEvent] = Field(default_factory=list)
    result: AnalyzeResponse | None = None


class ProjectSummary(BaseModel):
    id: str
    name: str
    created_at: str = ""
    updated_at: str = ""
    latest_run_id: str | None = None
    latest_run_status: str | None = None


class RunSummary(BaseModel):
    run_id: str
    project_id: str = ""
    project_title: str = "Untitled"
    status: str
    current_stage: str = ""
    progress: int = 0
    attempt: int = 1
    started_at: str = ""
    completed_at: str | None = None
    created_at: str = ""
    error: RunError | None = None
    has_results: bool = False
    event_count: int = 0


class RetryAccepted(BaseModel):
    run_id: str
    status: str = "queued"
    attempt: int = 1
