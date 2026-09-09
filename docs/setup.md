# Setup (local)

## Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000
pytest -q
```

Needs nothing else. Without keys it runs in local-heuristic mode.

## Frontend (shell only)

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000, points at NEXT_PUBLIC_API_URL
```

Dashboard UI is deferred; shell verifies backend reachability.
