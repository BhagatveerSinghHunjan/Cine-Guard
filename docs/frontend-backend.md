# Frontend ↔ backend

- Backend owns schemas, scoring, and workflow (`backend/app/**`).
- Frontend owns presentation only; typed client in `frontend/src/lib/api.ts`
  mirrors `AnalyzeResponse` / `PlanResponse`.
- Contract: `GET /health`, `GET /api/status`, `POST /api/analyze` (202 +
  poll `GET /api/runs/{id}`), `POST /api/runs/{id}/retry`, `POST /api/plan`,
  `GET /api/projects…` (plus `/api/v1/*` aliases for analyze/plan).
  Structured JSON; one error envelope; `422` on validation.
- Swapping Gemini/Parallel changes backend behavior, never the contract,
  so the future dashboard needs no rewrite.
