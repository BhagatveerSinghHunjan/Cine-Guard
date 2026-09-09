# CineGuard

## AI Production-Risk Agent

"CineGuard turns a screenplay into a production risk map, researches real-world dependencies, and builds a mitigation plan before expensive production problems become reshoots."

## The Problem

Turning a screenplay into a shootable production plan means reasoning across
two worlds at once. Production teams must connect things scattered through
the script — locations, permits, schedules, cast, vehicles, weather, music,
brands, stunts, VFX, continuity — with facts that live *outside* the
screenplay: permit offices, trademark rules, location restrictions, stunt
regulations, weather patterns. Miss one dependency and a shoot day burns
tens of thousands of dollars. Today that reasoning is manual, slow, and
easy to get wrong.

## The Solution

CineGuard is an autonomous production-intelligence agent. Upload a
screenplay and it extracts every production dependency, researches the
risky ones against live external sources, reasons over evidence into
ranked risks, scores readiness deterministically, and builds a revised
plan from the mitigations you select. No chatbot, no canned answers —
every number is computed, every citation is real, every unknown is
labeled unknown.

## How It Works

```
Screenplay
→ Analyze      (Gemini structured extraction, or local heuristics)
→ Research     (planner turns dependencies into bounded queries)
→ Detect Risks (Parallel Search evidence + screenplay facts)
→ Reason       (Gemini evidence-aware risk reasoning, or heuristics)
→ Mitigate     (you select fixes → deterministic re-scoring)
→ Verify       (projected readiness, remaining blockers, revised plan)
```

## Agent Architecture

Five ADK agents (`backend/app/agents/*`) with one job each, orchestrated
by the root agent through a persisted run lifecycle
(`queued → analyzing_screenplay → researching → reasoning_risks →
building_plan → completed | failed`):

- **Screenplay Analysis Agent** — scenes, characters, locations,
  dependencies; every item marked explicit / inferred / unknown.
- **Research Agent** — deterministic query planner + Parallel Search
  provider with retries and provenance on every source.
- **Risk Analysis Agent** — answers "what could prevent or complicate
  production?" over screenplay facts + research evidence; merges
  duplicates and links cascading dependencies.
- **Production Planning Agent** — actionable recommendations tied to
  specific risks and scenes.
- **Readiness Engine** (deterministic, not an agent) — the final score.
  Gemini never invents it.

See `docs/architecture.md` (with diagram).

## Parallel Integration

Production risk often depends on facts outside the screenplay — a permit
office's lead time, a brand's trademark status, a location's filming
restrictions. CineGuard uses Parallel Search to investigate those
external dependencies at runtime: the planner emits bounded queries, the
provider calls `POST https://api.parallel.ai/v1/search`, and every source
keeps title, domain, URL, excerpt and retrieval timestamp. Transient
failures retry; empty results are recorded as unknown, never as facts;
without a key the API reports `not_run` with zero sources. Citations are
never fabricated — that guarantee is unit-tested.

## Gemini Integration

Gemini handles screenplay understanding and reasoning: structured
extraction (scenes, dependencies, unknowns) and evidence-aware risk
reasoning, both via schema-constrained JSON output validated with
Pydantic. Malformed output is retried once, calls enforce a wall-clock
timeout, and failures surface as typed errors — the pipeline degrades to
deterministic local heuristics (clearly labeled) instead of guessing.
Screenplay text and web excerpts are treated as untrusted data
(`<untrusted_*>` prompt framing; injection handling is tested).

## Readiness Engine

Asking a model for a percentage produces confident fiction. CineGuard
does the opposite: Gemini produces structured risk assessments, and the
backend calculates `score = clamp(100 − Σ(severity_weight ×
confidence_multiplier), 0, 100)` — critical 15 / high 5 / medium 2 /
low 0.5, confidence ×1.0 / ×0.7 / ×0.4, mitigated = 0. Thresholds
READY ≥ 80, AT RISK ≥ 60, HIGH RISK ≥ 40. Same risks + config always give
the same score; the projected score is this function re-run on mitigated
risks. All weights are env-configurable.

## Evidence Model

- `SCREENPLAY_FACT` — quoted from the upload.
- `RESEARCHED_FACT` — Parallel source with title/domain/URL/query/timestamp.
- `INFERENCE` — labeled production reasoning, never presented as confirmed.
- `UNKNOWN` — explicitly missing (permits, availability, weather) and
  surfaced as a trust feature, never guessed.

Risks link evidence; recommendations link risks; the UI traces
Risk → Evidence → Source → Recommendation.

## Demo

1. Start the app (below) → click **Load Demo Production** (a fictional
   screenplay — `backend/tests/fixtures/sample_screenplay.txt` — analyzed
   live through the real pipeline, nothing pre-computed).
2. **Analyze Production** → watch real stages via `GET /api/runs/{id}`.
3. Explore Overview / Scenes / Risks / Dependencies / Research / Plan.
4. Open a risk → trace evidence → open the dependency graph.
5. Select fixes → **Build Fix Plan** → compare current vs projected readiness.
6. Full presenter flow: `docs/demo-runbook.md` + `docs/demo-script.md`.

## Local Development

```bash
cp .env.example .env   # keys optional; app degrades honestly without them

# backend/ — FastAPI on :8000, SQLite auto-migrates on startup
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend/ — Next.js on :3000
npm install
npm run dev     # NEXT_PUBLIC_API_URL points at :8000
```

## Environment Variables

See `.env.example` (complete, marked required / optional / dev-only).
Secrets are never logged or returned — health/status expose only
`configured` / `not-configured` flags.

| Variable | Needed for |
|---|---|
| `GEMINI_API_KEY` (or Vertex `GOOGLE_CLOUD_PROJECT`) | AI extraction + risk reasoning |
| `PARALLEL_API_KEY` | Live research evidence |
| `DATABASE_URL` / `CINEGUARD_DB_PATH` | Persistence (SQLite default) |
| `NEXT_PUBLIC_API_URL` | Frontend → backend URL |

## Testing

```bash
python3 -m pytest -q               # backend — hermetic, per-test temp DBs
python3 -m ruff check app tests    # backend lint
npm test                           # frontend — vitest
npm run typecheck && npm run lint && npm run build
```

## Architecture

`docs/architecture.md` — diagram, request path, evidence discipline,
scoring methodology, persistence design.

## Security

Screenplay text and research excerpts are **untrusted data** (prompt
framing + tests). Filenames are never trusted (text-only API, 200-char
title cap, 200k input cap with clear 422, no filesystem paths). One
consistent error envelope, no stack traces, no secrets in logs or
responses.

## Hackathon Implementation

- **Google Gemini:** screenplay understanding (structured extraction),
  evidence-aware risk reasoning, and recommendations — via `google-genai`
  with schema-constrained JSON, Pydantic validation, retries, and
  timeouts (`backend/app/services/gemini_extraction.py`,
  `backend/app/services/gemini_risk.py`).
- **Google Cloud:** Vertex AI (`GOOGLE_CLOUD_PROJECT` /
  `GOOGLE_CLOUD_LOCATION`) as an alternative credential path for the same
  Gemini models; agents defined with Google ADK
  (`backend/app/agents/*`); the backend ships container-ready
  (`backend/Dockerfile`) for Google Cloud deployment.
- **Parallel:** live runtime research — the planner emits bounded queries
  per analysis and `ParallelResearchProvider` calls the Parallel Search
  API with retries, provenance, and honest empty/error states
  (`backend/app/tools/research_tools.py`). No key ⇒ `not_run`, zero
  sources, never fake citations.

## License

MIT — see [LICENSE](LICENSE).
