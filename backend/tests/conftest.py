"""Isolated SQLite DB per test — no shared state, no dev-data pollution."""


import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CINEGUARD_DB_PATH", str(tmp_path / "test.db"))
    yield
