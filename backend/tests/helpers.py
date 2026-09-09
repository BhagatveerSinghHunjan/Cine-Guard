"""Shared polling helper for async run tests."""

import time


def wait_for_run(client, run_id: str, timeout: float = 15.0) -> dict:
    """Poll GET /api/runs/{id} until terminal. Returns the status payload."""
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = client.get(f"/api/runs/{run_id}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] in ("completed", "failed"):
            return last
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s: {last}")
