# CineGuard frontend

Next.js + TypeScript filmmaker dashboard: UPLOAD → ANALYZE → UNDERSTAND RESULTS.

- Dark, professional production-tool aesthetic (`src/app/globals.css`).
- Upload PDF/TXT/MD: validated + text extracted in-browser (`src/lib/screenplay.ts`,
  pdfjs for PDFs), then `POST /api/analyze` with `{screenplay_text, project_title}`.
  No backend change was needed — text-only contract preserved.
- Staged progress (`src/lib/stages.ts` + `AnalysisProgress`) advances on real
  local-read → network-request lifecycle; success renders only on real response.
- Results render whatever the backend returns: readiness, risk counts/cards,
  dependency groups, research notes. Nothing hardcoded.
- Clean client in `src/lib/api.ts` (`ApiError` kinds: validation/backend/network);
  base URL from `NEXT_PUBLIC_API_URL`.

```bash
npm install
npm run dev      # http://localhost:3000
npm test         # vitest
npm run typecheck && npm run lint && npm run build
```

Env: `NEXT_PUBLIC_API_URL` (see `.env.example`, default `http://127.0.0.1:8000`).
