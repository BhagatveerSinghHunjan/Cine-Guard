-- CineGuard 001_init.sql — Postgres mirror of the SQLite schema in app/db.py.
-- Local dev uses SQLite (zero-dependency); apply this file to Postgres for
-- production. Variable analysis artifacts stay JSONB on the run row by design.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL DEFAULT '',
    progress INTEGER NOT NULL DEFAULT 0,
    screenplay_text TEXT NOT NULL DEFAULT '',
    project_title TEXT NOT NULL DEFAULT 'Untitled',
    result_json JSONB,
    error_code TEXT,
    error_message TEXT,
    error_stage TEXT,
    attempt INTEGER NOT NULL DEFAULT 1,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON analysis_runs(project_id);

CREATE TABLE IF NOT EXISTS run_events (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id, seq);

INSERT INTO schema_migrations (version, applied_at)
VALUES (1, now())
ON CONFLICT (version) DO NOTHING;
