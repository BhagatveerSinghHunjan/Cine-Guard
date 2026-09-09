# Agent workflow (current + planned)

## Current (v0.1, local, no network)

```
Root (SequentialAgent or local fallback)
├── screenplay_agent → parse_screenplay_text → ScreenplayAnalysis
├── research_agent   → run_research_placeholder → honest not-implemented notes
├── risk_agent       → assess_risks → Risk[]
└── planning_agent   → build_plan → ProductionPlan + readiness
```

Deterministic and testable offline.

## Next (Parallel integration)

1. Add `ParallelResearchProvider.search(queries)` using `PARALLEL_API_KEY`.
2. Research agent calls it; results feed `evidence`/`sources` in risks.
3. Risk agent re-ranks with real citations; planning recomputes readiness.
4. Persist projects/runs to Postgres; deploy to Agent Engine.

No endpoint or schema changes required — only the provider body.
