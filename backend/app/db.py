"""SQLite persistence for projects, analysis runs, and run events.

Standard library only (no new dependencies). Thread-safe via a lock and
short per-operation connections (WAL mode). Production Postgres DDL that
mirrors this schema lives in backend/migrations/001_init.sql.

Design: lifecycle data (projects/runs/events) is relational with real
foreign keys + ON DELETE CASCADE. Variable analysis artifacts
(scenes/risks/evidence/...) are stored as one validated JSON payload on
the run row — see docs/architecture.md for the rationale.
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger("cineguard.db")

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analysis_runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    current_stage TEXT NOT NULL DEFAULT '',
    progress INTEGER NOT NULL DEFAULT 0,
    screenplay_text TEXT NOT NULL DEFAULT '',
    project_title TEXT NOT NULL DEFAULT 'Untitled',
    result_json TEXT,
    error_code TEXT,
    error_message TEXT,
    error_stage TEXT,
    attempt INTEGER NOT NULL DEFAULT 1,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON analysis_runs(project_id);
CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    ts TEXT NOT NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_run ON run_events(run_id, seq);
"""

_lock = threading.RLock()
_migrated_paths: set[str] = set()


def ensure_migrated() -> None:
    """Idempotent per-process migration (covers TestClient without lifespan)."""
    path = get_db_path()
    if path in _migrated_paths:
        return
    migrate()
    _migrated_paths.add(path)


def _default_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "data", "cineguard.db")


def _sqlite_path_from_url(url: str) -> str:
    if not url.startswith("sqlite:"):
        return ""
    path = url[len("sqlite:") :].lstrip("/")
    if url.startswith("sqlite:////"):
        path = "/" + path
    return path or ":memory:"


def get_db_path() -> str:
    """Resolve DB file. CINEGUARD_DB_PATH wins, then sqlite DATABASE_URL.

    Reads os.environ first (test-friendly), then .env-backed settings.
    A postgresql:// DATABASE_URL is NOT silently used — production Postgres
    uses migrations/001_init.sql; local dev stays on SQLite (see docs).
    """
    explicit = os.environ.get("CINEGUARD_DB_PATH", "").strip()
    if explicit:
        return explicit
    try:
        from app.config import get_settings

        settings = get_settings()
        if (settings.cineguard_db_path or "").strip():
            return settings.cineguard_db_path.strip()
        url = (settings.database_url or "").strip()
    except Exception:  # noqa: BLE001 -- settings backend may be unavailable
        url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("sqlite:"):
        return _sqlite_path_from_url(url)
    if url.startswith("postgresql"):
        log.warning("postgresql DATABASE_URL set — local dev uses SQLite file; see migrations/")
    return _default_path()


@contextmanager
def _connect():
    path = get_db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate() -> int:
    """Idempotent schema migration. Returns current schema version."""
    with _lock, _connect() as conn:
        conn.executescript(_SCHEMA)
        row = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
        if not row["v"]:
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utcnow()),
            )
    return SCHEMA_VERSION


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ── Projects ──────────────────────────────────────────────


def create_project(name: str) -> dict:
    ensure_migrated()
    now = _utcnow()
    pid = new_id("proj")
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (pid, name, now, now),
        )
    return get_project(pid)


def get_or_create_project(name: str, project_id: str | None = None) -> dict:
    ensure_migrated()
    name = (name or "").strip() or "Untitled"
    if project_id:
        existing = get_project(project_id)
        if existing:
            return existing
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE name = ? ORDER BY created_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        if row:
            return get_project(row["id"])
    return create_project(name)


def get_project(project_id: str) -> dict | None:
    ensure_migrated()
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None


def list_projects() -> list[dict]:
    ensure_migrated()
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            latest = conn.execute(
                "SELECT id, status FROM analysis_runs WHERE project_id = ? "
                "ORDER BY created_at DESC LIMIT 1",
                (d["id"],),
            ).fetchone()
            d["latest_run_id"] = latest["id"] if latest else None
            d["latest_run_status"] = latest["status"] if latest else None
            out.append(d)
        return out


def delete_project(project_id: str) -> bool:
    """Delete project; runs + events cascade (no orphans). Returns True if removed."""
    ensure_migrated()
    with _lock, _connect() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cur.rowcount > 0


# ── Runs ──────────────────────────────────────────────────

_RUN_COLUMNS = (
    "id, project_id, status, current_stage, progress, screenplay_text,"
    " project_title, result_json, error_code, error_message, error_stage,"
    " attempt, started_at, completed_at, created_at, updated_at"
)


def create_run(project_id: str, screenplay_text: str, project_title: str) -> dict:
    ensure_migrated()
    now = _utcnow()
    rid = new_id("run")
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT INTO analysis_runs (id, project_id, status, current_stage, progress,"
            " screenplay_text, project_title, started_at, created_at, updated_at)"
            " VALUES (?, ?, 'queued', 'queued', 0, ?, ?, ?, ?, ?)",
            (rid, project_id, screenplay_text, project_title, now, now, now),
        )
        conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
    return get_run(rid)


def get_run(run_id: str) -> dict | None:
    ensure_migrated()
    with _lock, _connect() as conn:
        row = conn.execute(
            f"SELECT {_RUN_COLUMNS} FROM analysis_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["events"] = _list_events_locked(conn, run_id)
        return d


def list_runs(project_id: str, limit: int = 20) -> list[dict]:
    ensure_migrated()
    with _lock, _connect() as conn:
        rows = conn.execute(
            f"SELECT {_RUN_COLUMNS} FROM analysis_runs WHERE project_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d.pop("screenplay_text", None)
            d.pop("result_json", None)
            d["event_count"] = conn.execute(
                "SELECT COUNT(*) AS c FROM run_events WHERE run_id = ?", (d["id"],)
            ).fetchone()["c"]
            out.append(d)
        return out


def update_run(run_id: str, **fields) -> None:
    ensure_migrated()
    allowed = {
        "status",
        "current_stage",
        "progress",
        "result_json",
        "error_code",
        "error_message",
        "error_stage",
        "attempt",
        "completed_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    updates["updated_at"] = _utcnow()
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    with _lock, _connect() as conn:
        conn.execute(f"UPDATE analysis_runs SET {cols} WHERE id = ?", (*updates.values(), run_id))


def fail_run(run_id: str, stage: str, code: str, message: str) -> None:
    update_run(
        run_id,
        status="failed",
        current_stage=stage,
        error_code=code,
        error_message=message,
        error_stage=stage,
        completed_at=_utcnow(),
    )


def complete_run(run_id: str, result: dict) -> None:
    update_run(
        run_id,
        status="completed",
        current_stage="completed",
        progress=100,
        result_json=json.dumps(result),
        error_code=None,
        error_message=None,
        error_stage=None,
        completed_at=_utcnow(),
    )


def reset_run_for_retry(run_id: str) -> dict | None:
    """Clear a failed run's result/events and re-queue it (same id, attempt+1).

    Runs inside one transaction: either fully reset or untouched.
    """
    ensure_migrated()
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT attempt FROM analysis_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        if _run_status_locked(conn, run_id) not in ("failed",):
            return None
        now = _utcnow()
        conn.execute("DELETE FROM run_events WHERE run_id = ?", (run_id,))
        conn.execute(
            "UPDATE analysis_runs SET status='queued', current_stage='queued', progress=0,"
            " result_json=NULL, error_code=NULL, error_message=NULL, error_stage=NULL,"
            " attempt=attempt+1, started_at=?, completed_at=NULL, updated_at=? WHERE id = ?",
            (now, now, run_id),
        )
    return get_run(run_id)


def _run_status_locked(conn, run_id: str) -> str | None:
    row = conn.execute("SELECT status FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
    return row["status"] if row else None


# ── Events ────────────────────────────────────────────────


def add_event(
    run_id: str, event_type: str, message: str, metadata: dict | None = None
) -> None:
    ensure_migrated()
    with _lock, _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) AS m FROM run_events WHERE run_id = ?", (run_id,)
        ).fetchone()
        conn.execute(
            "INSERT INTO run_events (run_id, seq, ts, type, message, metadata_json)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, (row["m"] or 0) + 1, _utcnow(), event_type, message,
             json.dumps(metadata or {})),
        )


def _list_events_locked(conn, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT seq, ts, type, message, metadata_json FROM run_events"
        " WHERE run_id = ? ORDER BY seq",
        (run_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        except (ValueError, TypeError):
            d["metadata"] = {}
        out.append(d)
    return out
