"""
Load and validate benchmark result JSON files from run directories.

A run directory is expected to have:
    <run_dir>/raw/<category>.json
    <run_dir>/report/summary.json   (produced by generate_report.py)

result_loader.py can load either the summary or individual raw files,
and will gracefully handle missing or partial data.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.schemas import CategoryResult, RunMetadata

log = logging.getLogger(__name__)

_KNOWN_CATEGORIES = ("cpu", "gpu_compute", "gpu_game", "ai", "memory", "disk")


def load_run(run_dir: str | Path) -> RunMetadata:
    """
    Load a complete run from *run_dir*.

    Prefers  <run_dir>/report/summary.json if present; otherwise
    reconstructs a RunMetadata from the individual raw JSON files.
    """
    run_dir = Path(run_dir)
    run_id = run_dir.name

    summary_path = run_dir / "report" / "summary.json"
    if summary_path.exists():
        try:
            data = _read_json(summary_path)
            return RunMetadata.from_dict(data, run_id=run_id, run_dir=str(run_dir))
        except Exception as exc:
            log.warning("Failed to load summary.json from %s: %s", run_dir, exc)

    # Fallback: reconstruct from raw files
    return _load_from_raw(run_dir, run_id)


def _load_from_raw(run_dir: Path, run_id: str) -> RunMetadata:
    """Reconstruct RunMetadata from individual raw category JSON files."""
    raw_dir = run_dir / "raw"
    results: Dict[str, CategoryResult] = {}

    for cat in _KNOWN_CATEGORIES:
        raw_file = raw_dir / f"{cat}.json"
        if raw_file.exists():
            try:
                d = _read_json(raw_file)
                results[cat] = CategoryResult.from_dict(d)
            except Exception as exc:
                log.warning("Failed to load raw %s.json: %s", cat, exc)
                results[cat] = CategoryResult(
                    category=cat,
                    status="failed",
                    notes=f"load error: {exc}",
                )

    meta = RunMetadata(
        run_id=run_id,
        run_dir=str(run_dir),
        profile=_infer_profile(run_dir.name),
        selected_categories=list(results.keys()),
        results=results,
    )
    return meta


def load_category_result(path: str | Path) -> CategoryResult:
    """Load a single raw category JSON file."""
    d = _read_json(path)
    return CategoryResult.from_dict(d)


def _read_json(path: str | Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _infer_profile(run_dir_name: str) -> str:
    """
    run directories are named  run-YYYYMMDD-HHMMSS-<profile>-<suffix>
    Try to extract the profile name.
    """
    parts = run_dir_name.split("-")
    if len(parts) >= 3:
        return parts[2]
    return "unknown"


def find_run_dirs(reports_root: str | Path) -> list[Path]:
    """
    Return all run directories inside *reports_root*, newest first.
    Run dirs are identified by starting with 'run-'.
    """
    root = Path(reports_root)
    if not root.is_dir():
        return []
    dirs = sorted(
        (d for d in root.iterdir() if d.is_dir() and d.name.startswith("run-")),
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs
