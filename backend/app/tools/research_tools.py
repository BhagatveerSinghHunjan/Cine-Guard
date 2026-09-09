"""External research: deterministic planner + live Parallel Search provider.

- Planner turns production dependencies into bounded research queries.
- ParallelResearchProvider calls POST https://api.parallel.ai/v1/search
  with x-api-key when PARALLEL_API_KEY is set, with bounded retries on
  transient failures (rate limits, 5xx, timeouts).
- Status vocabulary: "complete" (sources found), "empty" (no usable
  results — distinct from failure), "not_run" (no key / nothing to ask),
  "error" (provider failed after retries).
- Without a key (or on provider error) research degrades honestly:
  zero sources — never fake citations. Every researched item carries
  query, provider, and retrieval timestamp provenance.
"""

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.schemas import ResearchEvidence, ResearchSource

log = logging.getLogger("cineguard.research")

PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"


class ResearchQuery(BaseModel):
    topic: str
    objective: str = ""
    search_queries: list[str] = Field(default_factory=list)
    scene_numbers: list[int] = Field(default_factory=list)


class ResearchError(Exception):
    """Provider failure — never carries the API key."""


class ResearchTransientError(ResearchError):
    """Retryable: timeouts, rate limits, 5xx, connection resets."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def plan_research_queries(analysis) -> list[ResearchQuery]:
    """Deterministic query planner over extracted dependencies (max N)."""
    settings = get_settings()
    queries: list[ResearchQuery] = []

    def add(topic: str, objective: str, terms: list[str], scenes: list[int]):
        if terms and len(queries) < settings.research_max_queries:
            queries.append(
                ResearchQuery(
                    topic=topic,
                    objective=objective,
                    search_queries=terms[:3],
                    scene_numbers=scenes[:8],
                )
            )

    scenes = analysis.scenes if analysis else []
    scene_of = lambda dep: [
        s.scene_number for s in scenes if dep.lower() in {r.lower() for r in s.production_requirements}
    ]

    locs = (analysis.locations if analysis else [])[:3]
    if locs:
        add(
            "location filming permits",
            f"Filming permit requirements and restrictions for: {', '.join(locs)}.",
            [f"filming permit {loc}" for loc in locs],
            [s.scene_number for s in scenes if s.location in locs],
        )
    if analysis and analysis.brands:
        brand_scenes = sorted({s for b in analysis.brands[:2] for s in scene_of(b)})
        add(
            "brand clearance",
            f"Trademark clearance risk for visible brands: {', '.join(analysis.brands[:4])}.",
            [f"trademark clearance {b} film" for b in analysis.brands[:3]],
            brand_scenes,
        )
    if analysis and analysis.music:
        add(
            "music licensing",
            "Sync licensing requirements for commercial music cues in film.",
            ["film sync licensing commercial song cost", "music clearance independent film"],
            [],
        )
    stunts = (analysis.stunts if analysis else [])[:3]
    if stunts:
        add(
            "stunt safety requirements",
            f"Safety personnel and permit requirements for film stunts: {', '.join(stunts)}.",
            [f"film stunt coordinator requirements {s}" for s in stunts[:2]],
            [s for dep in stunts for s in scene_of(dep)][:8],
        )
    vehicles = [v for v in (analysis.vehicles if analysis else []) if v not in ("car", "chase")][:2]
    if vehicles:
        add(
            "special vehicle sourcing",
            f"Sourcing and regulations for picture vehicles: {', '.join(vehicles)}.",
            [f"picture vehicle rental {v} film production" for v in vehicles],
            [s for dep in vehicles for s in scene_of(dep)][:8],
        )
    weather = (analysis.weather_dependencies if analysis else [])[:2]
    if weather and len(queries) < settings.research_max_queries:
        add(
            "weather contingency",
            f"Filming contingency planning for: {', '.join(weather)}.",
            [f"film production weather contingency {w}" for w in weather],
            [s for dep in weather for s in scene_of(dep)][:8],
        )
    return queries


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001 -- unparsable URL has no domain
        return ""


class ParallelResearchProvider:
    """Live Parallel Search API client (stdlib only, no new deps)."""

    name = "parallel"

    def __init__(self, api_key: str, timeout_seconds: int = 20, max_results: int = 5,
                 max_retries: int = 2, retry_base_seconds: float = 0.5):
        if not api_key:
            raise ResearchError("Parallel API key missing")
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._max_results = max_results
        self._max_retries = max(0, max_retries)
        self._retry_base = retry_base_seconds

    def search(self, queries: list[ResearchQuery]) -> list[ResearchEvidence]:
        out: list[ResearchEvidence] = []
        for q in queries:
            try:
                out.append(self._search_with_retries(q))
            except ResearchError as exc:
                log.warning("parallel search failed for topic %r", q.topic)
                out.append(
                    ResearchEvidence(
                        topic=q.topic, provider="parallel", status="error", summary=str(exc),
                        query=", ".join(q.search_queries or [q.topic]),
                        retrieved_at=_utcnow(),
                    )
                )
        return out

    def _search_with_retries(self, query: ResearchQuery) -> ResearchEvidence:
        attempt = 0
        while True:
            try:
                return self._search_one(query)
            except ResearchTransientError:
                if attempt >= self._max_retries:
                    raise
                attempt += 1
                time.sleep(self._retry_base * (2 ** (attempt - 1)))

    def _search_one(self, query: ResearchQuery) -> ResearchEvidence:
        payload = {
            "objective": query.objective or query.topic,
            "search_queries": query.search_queries or [query.topic],
            "mode": "basic",
            "advanced_settings": {"max_results": self._max_results},
        }
        req = urllib.request.Request(
            PARALLEL_SEARCH_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-api-key": self._api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status_code = getattr(resp, "status", 200)
                body = json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or 500 <= exc.code < 600:
                raise ResearchTransientError(
                    "Parallel rate-limited or unavailable — retry shortly"
                ) from exc
            raise ResearchError(f"Parallel rejected the request (HTTP {exc.code})") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ResearchTransientError("Parallel request failed — retry shortly") from exc
        except Exception as exc:
            raise ResearchError("Parallel request failed — retry shortly") from exc
        if status_code == 429 or status_code >= 500:
            raise ResearchTransientError("Parallel unavailable — retry shortly")
        query_label = ", ".join(query.search_queries or [query.topic])
        retrieved_at = _utcnow()
        sources: list[ResearchSource] = []
        for item in (body.get("results") or [])[: self._max_results]:
            url = item.get("url", "")
            excerpts = item.get("excerpts") or []
            sources.append(
                ResearchSource(
                    title=item.get("title") or "",
                    domain=_domain_of(url),
                    url=url,
                    excerpt=" ".join(excerpts)[:1200],
                    publish_date=item.get("publish_date"),
                )
            )
        if not sources:
            # "No evidence found" is information, not a failure.
            return ResearchEvidence(
                topic=query.topic,
                provider="parallel",
                status="empty",
                summary=f"No usable results for '{query.topic}'.",
                sources=[],
                query=query_label,
                retrieved_at=retrieved_at,
            )
        summary_bits = [f"{len(sources)} source(s) for '{query.topic}'."]
        if query.scene_numbers:
            summary_bits.append(f"Relevant scenes: {sorted(set(query.scene_numbers))}.")
        return ResearchEvidence(
            topic=query.topic,
            provider="parallel",
            status="complete",
            summary=" ".join(summary_bits),
            sources=sources,
            query=query_label,
            retrieved_at=retrieved_at,
        )


def run_research(analysis, on_event=None) -> tuple[list[ResearchEvidence], list[str]]:
    """Run planned research; honest degradation without key or on error.

    on_event(type, message, metadata) receives real lifecycle callbacks:
    research_query_created / parallel_search_started / parallel_search_completed.
    """
    settings = get_settings()
    queries = plan_research_queries(analysis)
    if not queries:
        return [], ["No research-worthy dependencies found — research skipped."]
    for q in queries:
        if on_event:
            on_event("research_query_created",
                     f"Research query planned: {q.topic}",
                     {"topic": q.topic, "scenes": q.scene_numbers})
    if not settings.is_parallel_configured:
        n = len(analysis.scenes) if analysis else 0
        return [], [
            f"External research: not run ({len(queries)} querie(s) planned, {n} scene(s)).",
            "Set PARALLEL_API_KEY to enable live Parallel Search evidence.",
        ]
    if on_event:
        on_event("parallel_search_started",
                 f"Parallel Search started for {len(queries)} querie(s)",
                 {"provider": "parallel", "queries": len(queries)})
    provider = ParallelResearchProvider(
        settings.parallel_api_key,
        timeout_seconds=settings.parallel_timeout_seconds,
        max_results=settings.parallel_max_results,
        max_retries=settings.parallel_max_retries,
        retry_base_seconds=settings.parallel_retry_base_seconds,
    )
    evidence = provider.search(queries)
    complete = sum(1 for e in evidence if e.status == "complete")
    if on_event:
        on_event("parallel_search_completed",
                 f"Parallel Search finished: {complete}/{len(evidence)} querie(s) with sources",
                 {"complete": complete, "total": len(evidence)})
        on_event("evidence_added",
                 f"{sum(len(e.sources) for e in evidence)} evidence item(s) collected",
                 {"items": sum(len(e.sources) for e in evidence)})
    notes = [f"Parallel evidence: {complete}/{len(evidence)} querie(s) returned sources."]
    return evidence, notes


# ── Research notes ────────────────────────────

def build_research_notes(analysis) -> list[str]:
    """Honest notes for API responses — never fake external evidence."""
    n = len(analysis.scenes) if analysis else 0
    settings = get_settings()
    if not settings.is_parallel_configured:
        return [
            f"External research: not run (live provider not configured, {n} scene(s) queued).",
            "Set PARALLEL_API_KEY to enable live Parallel Search evidence.",
        ]
    return [f"External research: live Parallel provider enabled ({n} scene(s))."]
