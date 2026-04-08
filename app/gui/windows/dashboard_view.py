"""
Dashboard view — machine summary, recent runs, quick launch.
"""

from __future__ import annotations

import threading
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.diagnostics import SystemInfo, detect_system_info
from app.core.history import HistoryEntry
from app.core.schemas import BenchmarkStatus
from app.gui.widgets.chart_widget import MetricCard
from app.gui.widgets.status_badge import StatusBadge


class _SysInfoWorker(QObject):
    finished = Signal(object)  # SystemInfo

    def run(self) -> None:
        try:
            info = detect_system_info()
        except Exception:
            info = SystemInfo()
        self.finished.emit(info)


class DashboardView(QWidget):
    """Main dashboard with machine summary cards and recent run history."""

    # Emitted when user clicks Quick Launch
    launch_requested = Signal(str, list)  # profile, categories

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._load_system_info()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)

        # Header
        hdr = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("SectionHeader")
        hdr.addWidget(title)
        sub = QLabel("System overview and benchmark readiness")
        sub.setObjectName("SubHeader")
        hdr.addWidget(sub)
        root.addLayout(hdr)

        # Machine summary cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        self._cpu_card = MetricCard("CPU", "—", "Detecting…")
        self._gpu_card = MetricCard("GPU", "—", "Detecting…")
        self._ram_card = MetricCard("Memory", "—", "")
        self._os_card  = MetricCard("OS", "—", "")

        for card in (self._cpu_card, self._gpu_card, self._ram_card, self._os_card):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            cards_row.addWidget(card)

        root.addLayout(cards_row)

        # Quick launch buttons
        launch_frame = QFrame()
        launch_frame.setObjectName("Card")
        launch_layout = QVBoxLayout(launch_frame)
        launch_layout.setContentsMargins(16, 14, 16, 14)

        launch_title = QLabel("QUICK LAUNCH")
        launch_title.setObjectName("CardTitle")
        launch_layout.addWidget(launch_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        for profile, desc in (
            ("quick",    "Quick  (~2 min)"),
            ("balanced", "Balanced  (~8 min)"),
            ("deep",     "Deep  (~25 min)"),
        ):
            btn = QPushButton(desc)
            btn.setObjectName("PrimaryButton" if profile == "balanced" else "")
            btn.clicked.connect(lambda _, p=profile: self.launch_requested.emit(p, []))
            btn_row.addWidget(btn)

        btn_row.addStretch()
        launch_layout.addLayout(btn_row)
        root.addWidget(launch_frame)

        # Recent runs
        recent_frame = QFrame()
        recent_frame.setObjectName("Card")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(16, 14, 16, 14)

        recent_title = QLabel("RECENT RUNS")
        recent_title.setObjectName("CardTitle")
        recent_layout.addWidget(recent_title)

        self._recent_container = QVBoxLayout()
        self._recent_container.setSpacing(6)
        recent_layout.addLayout(self._recent_container)

        self._empty_label = QLabel("No recent runs found.  Click a Quick Launch button to start.")
        self._empty_label.setObjectName("MutedLabel")
        self._recent_container.addWidget(self._empty_label)

        root.addWidget(recent_frame)
        root.addStretch()

    # ------------------------------------------------------------------
    # Public slots
    # ------------------------------------------------------------------

    def update_recent_runs(self, entries: list[HistoryEntry]) -> None:
        """Populate the recent-runs panel with up to 5 entries."""
        # Clear old items
        while self._recent_container.count():
            item = self._recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not entries:
            lbl = QLabel("No recent runs.")
            lbl.setObjectName("MutedLabel")
            self._recent_container.addWidget(lbl)
            return

        for entry in entries[:5]:
            row = QHBoxLayout()
            row.setSpacing(12)

            ts = QLabel(entry.generated_at[:19].replace("T", "  "))
            ts.setObjectName("MutedLabel")
            ts.setFixedWidth(150)
            row.addWidget(ts)

            profile = QLabel(entry.profile.capitalize())
            profile.setFixedWidth(80)
            row.addWidget(profile)

            cats = QLabel(", ".join(entry.selected_categories) or "all")
            cats.setObjectName("MutedLabel")
            row.addWidget(cats)

            badge = StatusBadge(entry.overall_status)
            row.addWidget(badge)
            row.addStretch()

            container = QWidget()
            container.setLayout(row)
            self._recent_container.addWidget(container)

    # ------------------------------------------------------------------
    # System info loading
    # ------------------------------------------------------------------

    def _load_system_info(self) -> None:
        self._worker_thread = QThread()
        self._worker = _SysInfoWorker()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_system_info)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker_thread.start()

    @Slot(object)
    def _on_system_info(self, info: SystemInfo) -> None:
        # CPU
        cpu_model = info.cpu.model or info.cpu.architecture or "Unknown CPU"
        self._cpu_card.set_value(cpu_model[:28] + "…" if len(cpu_model) > 30 else cpu_model)
        cores = info.cpu.cores_logical
        self._cpu_card.set_subtitle(f"{cores} logical cores")

        # GPU
        if info.gpus:
            g = info.gpus[0]
            gpu_name = g.model or g.vendor or "Unknown GPU"
            self._gpu_card.set_value(gpu_name[:28] + "…" if len(gpu_name) > 30 else gpu_name)
            vram = f"{g.vram_mb / 1024:.1f} GB VRAM" if g.vram_mb else g.driver_version or ""
            self._gpu_card.set_subtitle(vram)
        else:
            self._gpu_card.set_value("Not detected")
            self._gpu_card.set_subtitle("")

        # RAM
        total_gb = info.memory.total_mb / 1024 if info.memory.total_mb else 0
        avail_gb = info.memory.available_mb / 1024 if info.memory.available_mb else 0
        self._ram_card.set_value(f"{total_gb:.1f} GB")
        self._ram_card.set_subtitle(f"{avail_gb:.1f} GB available")

        # OS
        os_name = info.os_name or "Linux"
        self._os_card.set_value(os_name[:24] + "…" if len(os_name) > 26 else os_name)
        self._os_card.set_subtitle(info.kernel or "")
