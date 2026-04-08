"""
Live Run Monitor view.

Shows real-time log output, current phase, progress, and status badges
while a benchmark run is executing.
"""

from __future__ import annotations

import re
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.gui.widgets.log_viewer import LogViewer
from app.gui.widgets.status_badge import StatusBadge

_PHASE_PATTERNS = [
    (re.compile(r"\[INFO\]\s+Running\s+(cpu|gpu_compute|gpu_game|ai|memory|disk)", re.I),
     "category"),
    (re.compile(r"\[INFO\]\s+Running preflight", re.I), "preflight"),
    (re.compile(r"\[OK\]\s+Report:", re.I), "complete"),
    (re.compile(r"\[ERROR\]", re.I), "error"),
]

_CATEGORY_NAMES = {
    "cpu":         "CPU Benchmark",
    "gpu_compute": "GPU Compute",
    "gpu_game":    "GPU Graphics",
    "ai":          "AI Benchmark",
    "memory":      "Memory Benchmark",
    "disk":        "Storage Benchmark",
}


class MonitorView(QWidget):
    """Live progress view for an active benchmark run."""

    # User clicked cancel
    cancel_requested = Signal()
    # Run finished — emit to open results view
    run_finished = Signal(object)  # RunMetadata | None

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._selected_categories: list[str] = []
        self._completed_categories: list[str] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        title = QLabel("Live Monitor")
        title.setObjectName("SectionHeader")
        root.addWidget(title)

        # Status strip
        status_frame = QFrame()
        status_frame.setObjectName("Card")
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(16, 12, 16, 12)
        status_layout.setSpacing(20)

        self._phase_label = QLabel("Waiting…")
        self._phase_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self._phase_label)

        self._status_badge = StatusBadge("unknown")
        status_layout.addWidget(self._status_badge)

        status_layout.addStretch()

        self._cancel_btn = QPushButton("⛔  Cancel Run")
        self._cancel_btn.setObjectName("DangerButton")
        self._cancel_btn.clicked.connect(self.cancel_requested)
        status_layout.addWidget(self._cancel_btn)

        root.addWidget(status_frame)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Starting…")
        self._progress.setFixedHeight(10)
        root.addWidget(self._progress)

        # Category status row
        self._cat_row_container = QWidget()
        self._cat_row = QHBoxLayout(self._cat_row_container)
        self._cat_row.setContentsMargins(0, 0, 0, 0)
        self._cat_row.setSpacing(8)
        root.addWidget(self._cat_row_container)

        self._cat_badges: dict[str, StatusBadge] = {}

        # Log viewer
        self._log = LogViewer()
        self._log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._log)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_run(self, selected_categories: list[str]) -> None:
        """Prepare the view for a new run."""
        self._selected_categories = selected_categories
        self._completed_categories = []
        self._log.clear()
        self._phase_label.setText("Initialising…")
        self._status_badge.set_status("unknown")
        self._progress.setValue(0)
        self._progress.setFormat("Starting…")
        self._cancel_btn.setEnabled(True)

        # Build category badge row
        while self._cat_row.count():
            item = self._cat_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cat_badges.clear()

        for cat in selected_categories:
            col = QVBoxLayout()
            col.setSpacing(2)
            col.setAlignment(Qt.AlignCenter)
            name = QLabel(_CATEGORY_NAMES.get(cat, cat))
            name.setObjectName("MutedLabel")
            name.setAlignment(Qt.AlignCenter)
            badge = StatusBadge("unknown")
            badge.setAlignment(Qt.AlignCenter)
            col.addWidget(name)
            col.addWidget(badge)
            container = QWidget()
            container.setLayout(col)
            self._cat_row.addWidget(container)
            self._cat_badges[cat] = badge

        self._cat_row.addStretch()

    @Slot(str)
    def append_line(self, line: str) -> None:
        """Append a log line and update progress indicators."""
        self._log.append_line(line)
        self._parse_progress(line)

    def mark_done(self, exit_code: int) -> None:
        """Called when the run process terminates."""
        self._cancel_btn.setEnabled(False)
        if exit_code == 0:
            self._phase_label.setText("Run Complete")
            self._status_badge.set_status("ok")
            self._progress.setValue(100)
            self._progress.setFormat("Complete")
        else:
            self._phase_label.setText("Run finished with errors")
            self._status_badge.set_status("failed")

    # ------------------------------------------------------------------
    # Progress parsing
    # ------------------------------------------------------------------

    def _parse_progress(self, line: str) -> None:
        for pattern, kind in _PHASE_PATTERNS:
            m = pattern.search(line)
            if not m:
                continue

            if kind == "category":
                cat = m.group(1).lower()
                self._phase_label.setText(f"Running: {_CATEGORY_NAMES.get(cat, cat)}")
                if cat in self._cat_badges:
                    self._cat_badges[cat].set_status("degraded")  # in-progress
                self._update_progress()

            elif kind == "preflight":
                self._phase_label.setText("Running preflight checks…")
                self._status_badge.set_status("unknown")

            elif kind == "complete":
                # Mark all pending badges
                for cat, badge in self._cat_badges.items():
                    if cat not in self._completed_categories:
                        badge.set_status("ok")

            elif kind == "error":
                self._status_badge.set_status("failed")

            break

        # Detect category completion
        done_m = re.search(r"\[INFO\]\s+.*?(cpu|gpu_compute|gpu_game|ai|memory|disk)\s+step.*done", line, re.I)
        if done_m:
            cat = done_m.group(1).lower()
            if cat not in self._completed_categories:
                self._completed_categories.append(cat)
                if cat in self._cat_badges:
                    self._cat_badges[cat].set_status("ok")
                self._update_progress()

    def _update_progress(self) -> None:
        total = len(self._selected_categories)
        done  = len(self._completed_categories)
        if total > 0:
            pct = int(done / total * 100)
            self._progress.setValue(pct)
            self._progress.setFormat(f"{done}/{total} categories")
