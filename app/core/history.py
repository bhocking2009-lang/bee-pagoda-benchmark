"""
Run history index.

Maintains a lightweight JSON index at <reports_root>/history.json that
tracks every known run without requiring a full directory scan.

The index is append-safe: it is only ever written by appending a new
entry or removing an entry by run_id.  Concurrent GUI + CLI usage is
safe as long as both refresh from disk before writing.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

log = logging.getLogger(__name__)

_INDEX_FILENAME = "history.json"
_INDEX_VERSION = 1


@dataclass
class HistoryEntry:
    run_id: str
    run_dir: str
    profile: str
    selected_categories: List[str]
    generated_at: str
    overall_status: str
    category_count: int = 0
    ok_count: int = 0
    failed_count: int = 0
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryEntry":
        return cls(
            run_id=str(d.get("run_id", "")),
            run_dir=str(d.get("run_dir", "")),
            profile=str(d.get("profile", "")),
            selected_categories=list(d.get("selected_categories", [])),
            generated_at=str(d.get("generated_at", "")),
            overall_status=str(d.get("overall_status", "unknown")),
            category_count=int(d.get("category_count", 0)),
            ok_count=int(d.get("ok_count", 0)),
            failed_count=int(d.get("failed_count", 0)),
            schema_version=str(d.get("schema_version", "1.0")),
        )


class HistoryIndex:
    """JSON-backed index of benchmark run history."""

    def __init__(self, reports_root: str | Path) -> None:
        self.reports_root = Path(reports_root)
        self._index_path = self.reports_root / _INDEX_FILENAME
        self._entries: List[HistoryEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Reload the index from disk."""
        if not self._index_path.exists():
            self._entries = []
            return
        try:
            with open(self._index_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self._entries = [HistoryEntry.from_dict(e) for e in raw.get("entries", [])]
        except Exception as exc:
            log.warning("Failed to load history index: %s", exc)
            self._entries = []

    def save(self) -> None:
        """Write the current in-memory index to disk atomically."""
        self.reports_root.mkdir(parents=True, exist_ok=True)
        tmp = self._index_path.with_suffix(".tmp")
        payload = {
            "version": _INDEX_VERSION,
            "entries": [e.to_dict() for e in self._entries],
        }
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self._index_path)

    def all_entries(self) -> List[HistoryEntry]:
        """Return all history entries, newest first."""
        return sorted(self._entries, key=lambda e: e.generated_at, reverse=True)

    def add_or_update(self, entry: HistoryEntry) -> None:
        """Insert or replace an entry with the same run_id."""
        self._entries = [e for e in self._entries if e.run_id != entry.run_id]
        self._entries.append(entry)

    def remove(self, run_id: str) -> bool:
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.run_id != run_id]
        return len(self._entries) < before

    def find(self, run_id: str) -> Optional[HistoryEntry]:
        for e in self._entries:
            if e.run_id == run_id:
                return e
        return None

    # ------------------------------------------------------------------
    # Convenience: rebuild from directory scan
    # ------------------------------------------------------------------

    def rebuild_from_disk(self) -> int:
        """
        Scan reports_root for run directories and rebuild the index.
        Returns the number of entries added.
        """
        from app.core.result_loader import find_run_dirs, load_run  # local import

        self._entries = []
        count = 0
        for run_dir in find_run_dirs(self.reports_root):
            try:
                run = load_run(run_dir)
                entry = HistoryEntry(
                    run_id=run.run_id,
                    run_dir=run.run_dir,
                    profile=run.profile,
                    selected_categories=run.selected_categories,
                    generated_at=run.generated_at,
                    overall_status=run.overall_status,
                    category_count=run.category_count,
                    ok_count=run.ok_count,
                    failed_count=run.failed_count,
                    schema_version=run.schema_version,
                )
                self._entries.append(entry)
                count += 1
            except Exception as exc:
                log.warning("Failed to index run %s: %s", run_dir.name, exc)
        self.save()
        return count
