"""
Main application window.

Hosts the sidebar and a QStackedWidget that holds all the views.
Wires the BenchmarkService to Qt signals so the GUI stays responsive.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.runner import RunRequest
from app.core.schemas import RunMetadata
from app.gui.widgets.sidebar import Sidebar
from app.gui.windows.comparison_view import ComparisonView
from app.gui.windows.dashboard_view import DashboardView
from app.gui.windows.history_view import HistoryView
from app.gui.windows.monitor_view import MonitorView
from app.gui.windows.preflight_view import PreflightView
from app.gui.windows.results_view import ResultsView
from app.gui.windows.run_view import RunView
from app.services.benchmark_service import BenchmarkService
from app.services.preflight_service import PreflightService

log = logging.getLogger(__name__)

_APP_VERSION = "1.0.0"


# ------------------------------------------------------------------
# Thread-safe bridge for BenchmarkService → Qt signals
# ------------------------------------------------------------------

class _BenchmarkBridge(QObject):
    """Emit Qt signals from the ProcessManager reader thread."""
    line_received = Signal(str)
    run_finished  = Signal(int, object)   # exit_code, RunMetadata|None


class _PrefightWorker(QObject):
    """Run preflight check in a background thread."""
    finished = Signal(object)  # PreflightResult

    def __init__(self, python_bin: Optional[str] = None) -> None:
        super().__init__()
        self._python_bin = python_bin

    def run(self) -> None:
        svc = PreflightService()
        result = svc.run(self._python_bin)
        self.finished.emit(result)


# ------------------------------------------------------------------
# Main window
# ------------------------------------------------------------------

_VIEW_INDICES = {
    "dashboard":  0,
    "new_run":    1,
    "monitor":    2,
    "results":    3,
    "history":    4,
    "comparison": 5,
    "preflight":  6,
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Bee Pagoda Benchmark  v{_APP_VERSION}")
        self.setMinimumSize(1100, 700)

        self._service = BenchmarkService()
        self._bridge  = _BenchmarkBridge()
        self._current_run: Optional[RunMetadata] = None

        self._setup_ui()
        self._wire_signals()
        self._load_history()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        h_layout.addWidget(self._sidebar)

        # Stacked views
        self._stack = QStackedWidget()
        h_layout.addWidget(self._stack, stretch=1)

        self._dashboard_view  = DashboardView()
        self._run_view        = RunView()
        self._monitor_view    = MonitorView()
        self._results_view    = ResultsView()
        self._history_view    = HistoryView()
        self._comparison_view = ComparisonView()
        self._preflight_view  = PreflightView()

        for view in (
            self._dashboard_view,
            self._run_view,
            self._monitor_view,
            self._results_view,
            self._history_view,
            self._comparison_view,
            self._preflight_view,
        ):
            self._stack.addWidget(view)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready")

        # Menu bar
        self._setup_menus()

        # Start on dashboard
        self._sidebar.set_active("dashboard")
        self._stack.setCurrentIndex(0)

    def _setup_menus(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction("Open Report Folder…", self._open_report_folder)
        file_menu.addSeparator()
        file_menu.addAction("&Quit", self.close)

        run_menu = menubar.addMenu("&Run")
        run_menu.addAction("New Benchmark…", lambda: self._navigate("new_run"))
        run_menu.addAction("Stop / Cancel", self._cancel_run)

        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("Check Dependencies", lambda: self._navigate("preflight"))
        tools_menu.addAction("Rebuild History Index", self._rebuild_history)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("About…", self._show_about)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _wire_signals(self) -> None:
        self._sidebar.section_changed.connect(self._navigate)

        self._dashboard_view.launch_requested.connect(self._on_quick_launch)

        self._run_view.run_requested.connect(self._on_run_requested)

        self._monitor_view.cancel_requested.connect(self._cancel_run)
        self._monitor_view.run_finished.connect(self._on_run_finished_from_monitor)

        self._history_view.open_run_requested.connect(self._on_open_run)
        self._history_view.compare_requested.connect(self._on_compare_runs)
        self._history_view.refresh_requested.connect(self._load_history)

        self._preflight_view.refresh_requested.connect(self._run_preflight)

        # Bridge signals (thread-safe)
        self._bridge.line_received.connect(self._monitor_view.append_line)
        self._bridge.run_finished.connect(self._on_run_finished)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @Slot(str)
    def _navigate(self, section_id: str) -> None:
        idx = _VIEW_INDICES.get(section_id, 0)
        self._stack.setCurrentIndex(idx)
        self._sidebar.set_active(section_id)

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    @Slot(str, list)
    def _on_quick_launch(self, profile: str, categories: list) -> None:
        self._navigate("new_run")
        self._run_view.preset_profile(profile)

    @Slot(object)
    def _on_run_requested(self, request: RunRequest) -> None:
        if self._service.is_running:
            QMessageBox.warning(self, "Run in progress",
                                "A benchmark run is already in progress.")
            return

        log.info("Starting run: %s", request.to_cmd())

        def _on_line(line: str) -> None:
            self._bridge.line_received.emit(line)

        def _on_done(code: int, run: Optional[RunMetadata]) -> None:
            self._bridge.run_finished.emit(code, run)

        self._service.on_line = _on_line
        self._service.on_done = _on_done

        try:
            self._service.start_run(request)
        except Exception as exc:
            QMessageBox.critical(self, "Failed to start run", str(exc))
            return

        self._run_view.set_enabled(False)
        categories = request.categories or ["cpu", "gpu_compute", "gpu_game", "ai", "memory", "disk"]
        self._monitor_view.start_run(categories)
        self._navigate("monitor")
        self._status_bar.showMessage(f"Running: {request.profile} profile…")

    @Slot()
    def _cancel_run(self) -> None:
        if self._service.is_running:
            self._service.cancel()
            self._status_bar.showMessage("Cancellation requested…")

    @Slot(int, object)
    def _on_run_finished(self, exit_code: int, run: Optional[RunMetadata]) -> None:
        self._run_view.set_enabled(True)
        self._monitor_view.mark_done(exit_code)
        self._current_run = run

        if run:
            self._results_view.load_run(run)
            self._load_history()
            self._status_bar.showMessage(
                f"Run complete — exit code {exit_code}  |  {run.run_id}"
            )
            self._navigate("results")
        else:
            self._status_bar.showMessage(
                f"Run finished with exit code {exit_code} (no results loaded)"
            )

    @Slot()
    def _on_run_finished_from_monitor(self, run) -> None:
        pass  # handled by _on_run_finished

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _load_history(self) -> None:
        entries = self._service.load_history()
        self._history_view.load_entries(entries)
        self._dashboard_view.update_recent_runs(entries)

    def _rebuild_history(self) -> None:
        count = self._service.refresh_history_from_disk()
        self._load_history()
        self._status_bar.showMessage(f"Rebuilt history index: {count} runs indexed")

    @Slot(str)
    def _on_open_run(self, run_id: str) -> None:
        run = self._service.load_run_by_id(run_id)
        if run:
            self._results_view.load_run(run)
            self._navigate("results")
        else:
            QMessageBox.warning(self, "Not found",
                                f"Could not load run: {run_id}")

    @Slot(list)
    def _on_compare_runs(self, run_ids: list) -> None:
        if len(run_ids) < 2:
            return
        run_a = self._service.load_run_by_id(run_ids[0])
        run_b = self._service.load_run_by_id(run_ids[1])
        if run_a and run_b:
            self._comparison_view.compare(run_a, run_b)
            self._navigate("comparison")
        else:
            QMessageBox.warning(self, "Not found",
                                "Could not load one or both runs for comparison.")

    # ------------------------------------------------------------------
    # Preflight
    # ------------------------------------------------------------------

    def _run_preflight(self) -> None:
        self._status_bar.showMessage("Running dependency checks…")
        self._preflight_thread = QThread()
        self._preflight_worker = _PrefightWorker()
        self._preflight_worker.moveToThread(self._preflight_thread)
        self._preflight_thread.started.connect(self._preflight_worker.run)
        self._preflight_worker.finished.connect(self._on_preflight_done)
        self._preflight_worker.finished.connect(self._preflight_thread.quit)
        self._preflight_thread.start()

    @Slot(object)
    def _on_preflight_done(self, result) -> None:
        self._preflight_view.load_preflight(result)
        self._status_bar.showMessage("Dependency check complete")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_report_folder(self) -> None:
        import os, subprocess, shutil
        reports_dir = Path(__file__).parent.parent.parent.parent / "reports"
        folder = QFileDialog.getExistingDirectory(
            self, "Open Report Folder", str(reports_dir))
        if folder:
            from app.core.result_loader import load_run
            try:
                run = load_run(folder)
                self._results_view.load_run(run)
                self._navigate("results")
            except Exception as exc:
                QMessageBox.warning(self, "Load failed", str(exc))

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Bee Pagoda Benchmark",
            f"<h2>Bee Pagoda Benchmark</h2>"
            f"<p>Version {_APP_VERSION}</p>"
            f"<p>A professional Linux benchmark suite with a native PySide6 desktop GUI.</p>"
            f"<p>Benchmark scripts: bash<br>"
            f"GUI framework: PySide6 / Qt6<br>"
            f"Python: 3.12+</p>",
        )
