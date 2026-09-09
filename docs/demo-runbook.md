# CineGuard demo runbook

## Demo objective

Show that CineGuard can discover hidden production risks in a screenplay
and produce a better production plan — with live agent activity, real
Parallel research, evidence-backed risks, and a dynamically calculated
before/after readiness.

## Pre-demo setup (5 minutes before)

1. Start the backend: `python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
   from `backend/` (SQLite auto-migrates; delete `backend/data/cineguard.db`
   first for a pristine demo).
2. Start the frontend: `npm run dev` from `frontend/`, open http://localhost:3000.
3. Optional: set `GEMINI_API_KEY` / `PARALLEL_API_KEY` for the full live
   path. Without keys the app runs labeled heuristics + honest not-run
   research — never fake output. Decide which story you are telling and say
   it out loud in step 2 of the script.

## Demo sequence

| # | Action | Say |
|---|--------|-----|
| 1 | Open CineGuard. | Point at the header: production intelligence, not a chatbot. |
| 2 | Click **Load Demo Production**. | "A fictional screenplay — Neon Harbor. All names invented. It goes through the real pipeline; nothing is pre-computed." |
| 3 | Click **Analyze Production**. | "One request creates a persisted run. Watch real stages, not a spinner." |
| 4 | Show agent activity. | Read 2–3 events with timestamps: parsed, dependencies identified, research executed. |
| 5 | Show Parallel research. | Open Research tab: "Each risky dependency became a bounded Parallel query. Sources keep title, domain, URL, timestamp." |
| 6 | Show readiness. | Overview: score, status, blockers. Read the one-line explanation. |
| 7 | Open highest-severity risk. | "Why this matters, what we know, what we don't know." |
| 8 | Show evidence. | Point at SCREENPLAY FACT vs RESEARCHED FACT vs INFERENCE badges; open a source link. |
| 9 | Open dependency graph. | Click a node: "One permit problem cascades into these scenes and risks." |
| 10 | Select mitigations. | Check 2 recommendations on the Plan tab. |
| 11 | Click **Build Fix Plan**. | "Projected score is recomputed by the backend, not guessed." |
| 12 | Show projected readiness. | Before/after numbers + mitigated risks. |
| 13 | Show remaining blockers. | "Honest about what's left — that's the shooting plan for week one." |

## If something goes wrong

- **Analysis fails:** the run card names the exact failed stage — click Retry (same run id, nothing duplicated).
- **No research sources:** say so plainly — "no key configured" or "no usable sources," both are first-class states.
- **Slow network:** heuristic analysis completes locally in seconds; narrate the persisted stages while polling.
