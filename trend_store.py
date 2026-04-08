"""trend_store.py — Lightweight historical trend storage for Bee Pagoda Benchmark.

Stores per-run normalized metrics in a SQLite database at
``reports/trend.db`` (next to the run directories).

Schema
------
runs table:
    id          INTEGER PRIMARY KEY
    run_dir     TEXT UNIQUE
    profile     TEXT
    captured_at TEXT   (ISO-8601 UTC)
    cpu_score   REAL
    mem_mib_per_sec REAL
    disk_seq_bw_kib REAL
    disk_rand_iops  REAL
    ai_composite    REAL
    kernel      TEXT
    cpu_model   TEXT

Usage
-----
    from trend_store import record_run, get_trend

    record_run(run_dir="/path/to/reports/run-xxx", summary=<summary_dict>)
    rows = get_trend(limit=20)
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


_DB_NAME = "trend.db"

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_dir         TEXT    UNIQUE NOT NULL,
    profile         TEXT,
    captured_at     TEXT    NOT NULL,
    cpu_score       REAL,
    mem_mib_per_sec REAL,
    disk_seq_bw_kib REAL,
    disk_rand_iops  REAL,
    ai_composite    REAL,
    kernel          TEXT,
    cpu_model       TEXT
);
"""

_INSERT_SQL = """
INSERT OR REPLACE INTO runs
    (run_dir, profile, captured_at, cpu_score, mem_mib_per_sec,
     disk_seq_bw_kib, disk_rand_iops, ai_composite, kernel, cpu_model)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def _db_path(run_dir: str) -> str:
    """Resolve the trend.db path relative to the reports root."""
    reports_root = os.path.dirname(run_dir)
    return os.path.join(reports_root, _DB_NAME)


def _safe_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def record_run(run_dir: str, summary: dict) -> None:
    """Insert or update a run record in the trend database.

    Parameters
    ----------
    run_dir:
        Absolute path to the run directory (e.g. ``reports/run-20260407-...``).
    summary:
        Parsed ``report/summary.json`` dict.
    """
    db_path = _db_path(run_dir)
    results = summary.get("results", {})
    normalized = summary.get("normalized", {}).get("metrics", {})
    fp = summary.get("env_fingerprint") or {}

    cpu_score = _safe_float(
        normalized.get("cpu", {}).get("baseline_score")
        or (results.get("cpu") or {}).get("score")
    )
    mem_score = _safe_float(
        normalized.get("memory", {}).get("read_write_mib_per_sec")
        or (results.get("memory") or {}).get("score")
    )
    disk_seq = _safe_float(
        normalized.get("disk", {}).get("seq_bw_kib_per_sec")
        or (results.get("disk") or {}).get("score")
    )
    disk_rand = _safe_float(
        normalized.get("disk", {}).get("rand_iops")
    )
    ai_comp = _safe_float(
        normalized.get("ai", {}).get("composite_normalized")
        or (results.get("ai") or {}).get("score")
    )

    captured_at = summary.get("generated_at") or datetime.now(timezone.utc).isoformat()
    profile = summary.get("profile", "")
    kernel = fp.get("kernel", "")
    cpu_model = fp.get("cpu_model", "")

    con = sqlite3.connect(db_path)
    try:
        con.execute(_CREATE_SQL)
        con.execute(_INSERT_SQL, (
            run_dir, profile, captured_at,
            cpu_score, mem_score, disk_seq, disk_rand, ai_comp,
            kernel, cpu_model,
        ))
        con.commit()
    finally:
        con.close()


def get_trend(run_dir: str, limit: int = 50) -> list[dict]:
    """Return up to *limit* recent run records ordered oldest-first.

    Parameters
    ----------
    run_dir:
        Any run directory — used only to locate the database.
    limit:
        Maximum number of rows to return.

    Returns
    -------
    list of dicts with keys matching the ``runs`` table columns.
    """
    db_path = _db_path(run_dir)
    if not os.path.exists(db_path):
        return []

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        con.execute(_CREATE_SQL)
        rows = con.execute(
            "SELECT * FROM runs ORDER BY captured_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        con.close()
