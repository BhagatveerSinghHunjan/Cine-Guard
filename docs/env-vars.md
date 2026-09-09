# Environment variables

| Var | Status | Notes |
|---|---|---|
| `GEMINI_API_KEY` | optional now | Enables live Gemini reasoning via ADK later |
| `GOOGLE_CLOUD_PROJECT` | optional now | Needed for Agent Engine deploy |
| `GOOGLE_CLOUD_LOCATION` | default `us-central1` | Region |
| `GEMINI_MODEL` | default `gemini-2.0-flash` | Model id |
| `PARALLEL_API_KEY` | placeholder | Stored, never called yet |
| `DATABASE_URL` | unused v0.1 | Future Postgres persistence |
| `BACKEND_HOST/PORT` | defaults | Local bind |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL |

`GET /api/status` reports only booleans/mode — never secret values.
