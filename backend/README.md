# CineGuard backend

Python + FastAPI + Google ADK foundation. Offline-safe: works with no keys.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Test

```bash
pytest -q
```

## Structure

See root `README.md` + `docs/architecture.md`. Key seam:
`app/tools/research_tools.py::get_research_provider()` — swap the
placeholder for `ParallelResearchProvider` without touching agents/API.
