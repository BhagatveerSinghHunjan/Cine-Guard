# CineGuard judge talking points

**What is novel?**
Screenplay analysis tools summarize scripts. CineGuard closes the loop:
extract dependencies → research them live → reason over evidence →
score deterministically → mitigate → re-verify. The product is the loop,
not the summary.

**Why is this agentic?**
Five single-responsibility ADK agents (screenplay, research, risk,
planning, root orchestrator) run a persisted, retryable workflow with
real stages and an event log — not one prompt call.

**Why Gemini?**
Schema-constrained structured extraction and evidence-aware risk
reasoning, validated with Pydantic, retried on malformed output, timed
out safely. The model understands and reasons; it never invents numbers.

**Why Google Cloud?**
Vertex AI is a first-class credential path for the same Gemini models;
agents are built on Google ADK; the backend ships container-ready for
Google Cloud deployment.

**Why Parallel?**
Risk lives outside the script — permit lead times, trademark rules,
location restrictions. Parallel Search investigates those facts at
runtime with provenance on every source. Without it, CineGuard would be
guessing about the outside world.

**Why not a chatbot?**
Production decisions need auditable artifacts — scores, evidence,
graphs, plans — not conversation. Every interaction is upload → analyze
→ investigate → decide → mitigate.

**How is readiness calculated?**
`100 − Σ(severity_weight × confidence_multiplier)`, mitigated = 0,
clamped 0–100. Configurable weights; same inputs always give the same
score. Shown live in the UI breakdown.

**How do you prevent hallucinations?**
Schema validation, single parse retry then typed failure, evidence-kind
labels, UNKNOWN as a first-class state, and a scoring engine the model
cannot touch.

**How is evidence sourced?**
Screenplay quotes from the upload; web facts only from live Parallel
results with title/domain/URL/timestamp; inferences explicitly labeled.

**What happens when information is unknown?**
It is recorded as UNKNOWN, shown in the UI, and weighted into risk —
never converted into a fact.

**How does the system scale?**
Stateless API + persisted runs + bounded research queries (max 6 by
default); polling stops at terminal states; SQLite locally, Postgres DDL
shipped for production.

**What is the production impact?**
One missed permit or weather dependency can burn a full shoot day.
CineGuard surfaces those weeks earlier, prices each mitigation in
readiness points, and leaves an auditable trail from risk to fix.
