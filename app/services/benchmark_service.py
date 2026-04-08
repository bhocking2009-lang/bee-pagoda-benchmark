"""
BenchmarkService: high-level orchestrator for the GUI.

The GUI creates one BenchmarkService and connects its signals/callbacks to
update the UI.  The service owns the Runner, tracks the active run directory,
and updates the history index when a run completes.

Because this layer is used from Qt worker threads, all Qt-specific signal
wiring is done in the GUI layer.  This service uses plain Python callbacks.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, Optional

from app.core.history import HistoryEntry, HistoryIndex
from app.core.result_loader import find_run_dirs, load_run
from app.core.runner import RunRequest, Runner
from app.core.schemas import RunMetadata

log = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent.parent
_REPORTS_ROOT = _ROOT / "reports"


class BenchmarkService:
    """
    Manages the lifecycle of a single benchmark run for the GUI.

    Callbacks (set before calling start_run):
        on_line(str)          – called for each line of output
        on_done(int, RunMetadata | None)  – called when run finishes
    """

    def __init__(self, reports_root: Optional[Path] = None) -> None:
        self.reports_root = reports_root or _REPORTS_ROOT
        self._runner = Runner()
        self._history = HistoryIndex(self.reports_root)
        self._history.load()
        self._active_run_dir: Optional[Path] = None

        # Callbacks to be wired by the GUI
        self.on_line: Optional[Callable[[str], None]] = None
        self.on_done: Optional[Callable[[int, Optional[RunMetadata]], None]] = None

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(self, request: RunRequest) -> None:
        """Start a benchmark run.  Raises if one is already in progress."""
        if self._runner.is_running:
            raise RuntimeError("A benchmark run is already in progress")

        log.info("Starting run: profile=%s categories=%s", request.profile, request.category_str())

        def _on_line(line: str) -> None:
            # Extract the run directory from run_suite.sh output lines
            if "[OK] Report:" in line or "[INFO] Run directory:" in line:
                self._try_capture_run_dir(line)
            if self.on_line:
                self.on_line(line)

        def _on_done(code: int) -> None:
            result: Optional[RunMetadata] = None
            if self._active_run_dir:
                try:
                    result = load_run(self._active_run_dir)
                    self._record_history(result)
                except Exception as exc:
                    log.warning("Failed to load run result: %s", exc)
            if self.on_done:
                self.on_done(code, result)

        self._runner.start(request, on_line=_on_line, on_done=_on_done)

    def cancel(self) -> None:
        """Gracefully cancel the active run."""
        if self._runner.is_running:
            log.info("Cancelling active run")
            self._runner.cancel()

    @property
    def is_running(self) -> bool:
        return self._runner.is_running

    @property
    def active_run_dir(self) -> Optional[Path]:
        return self._active_run_dir

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def load_history(self) -> list[HistoryEntry]:
        self._history.load()
        return self._history.all_entries()

    def load_run_by_id(self, run_id: str) -> Optional[RunMetadata]:
        entry = self._history.find(run_id)
        if entry and Path(entry.run_dir).exists():
            return load_run(entry.run_dir)
        return None

    def refresh_history_from_disk(self) -> int:
        return self._history.rebuild_from_disk()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_capture_run_dir(self, line: str) -> None:
        """
        run_suite.sh prints:
            [OK] Report: /path/to/run-dir/report/summary.md
        Extract the run directory from this.
        """
        import re
        m = re.search(r"\[OK\]\s+Report:\s+(.+)/report/summary\.md", line)
        if m:
            run_dir = Path(m.group(1).strip())
            if run_dir.exists():
                self._active_run_dir = run_dir
                log.info("Captured run dir: %s", run_dir)

    def _record_history(self, run: RunMetadata) -> None:
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
        self._history.add_or_update(entry)
        try:
            self._history.save()
        except Exception as exc:
            log.warning("Failed to save history index: %s", exc)
