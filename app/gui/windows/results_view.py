"""
Results Viewer — shows summary cards, category breakdown, charts,
and export actions for a completed benchmark run.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.schemas import BenchmarkStatus, CategoryResult, RunMetadata
from app.gui.widgets.chart_widget import BarChartWidget, MetricCard
from app.gui.widgets.status_badge import StatusBadge
from app.services.export_service import ExportService

_METRIC_LABELS = {
    "cpu":         ("Score", "score"),
    "gpu_compute": ("GFLOPS", "score"),
    "gpu_game":    ("FPS", "fps"),
    "ai":          ("Eval TPS", "eval_tps"),
    "memory":      ("Score", "score"),
    "disk":        ("Score", "score"),
}


class ResultsView(QWidget):
    """Displays the full results of a completed benchmark run."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._run: Optional[RunMetadata] = None
        self._export: Optional[ExportService] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header row
        hdr = QHBoxLayout()
        title = QLabel("Results")
        title.setObjectName("SectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()

        # Export buttons
        self._btn_open_folder = QPushButton("📁  Open Folder")
        self._btn_copy_md     = QPushButton("📋  Copy Markdown")
        self._btn_export_json = QPushButton("⬇  Export JSON")
        self._btn_export_csv  = QPushButton("⬇  Export CSV")

        for btn in (self._btn_open_folder, self._btn_copy_md,
                    self._btn_export_json, self._btn_export_csv):
            btn.setEnabled(False)
            hdr.addWidget(btn)

        self._btn_open_folder.clicked.connect(self._on_open_folder)
        self._btn_copy_md.clicked.connect(self._on_copy_md)
        self._btn_export_json.clicked.connect(self._on_export_json)
        self._btn_export_csv.clicked.connect(self._on_export_csv)
        root.addLayout(hdr)

        # Run metadata strip
        self._meta_frame = QFrame()
        self._meta_frame.setObjectName("Card")
        self._meta_layout = QHBoxLayout(self._meta_frame)
        self._meta_layout.setContentsMargins(16, 12, 16, 12)
        self._meta_layout.setSpacing(20)
        self._meta_label = QLabel("Load a run to view results.")
        self._meta_label.setObjectName("MutedLabel")
        self._meta_layout.addWidget(self._meta_label)
        self._meta_layout.addStretch()
        root.addWidget(self._meta_frame)

        # Summary cards
        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(16)
        self._ok_card      = MetricCard("OK", "—")
        self._deg_card     = MetricCard("DEGRADED", "—")
        self._skip_card    = MetricCard("SKIPPED", "—")
        self._fail_card    = MetricCard("FAILED", "—")
        for card in (self._ok_card, self._deg_card, self._skip_card, self._fail_card):
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._cards_row.addWidget(card)
        root.addLayout(self._cards_row)

        # Tab widget: breakdown + chart
        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

        # Tab 1: Category breakdown
        self._breakdown_widget = QWidget()
        self._breakdown_layout = QVBoxLayout(self._breakdown_widget)
        self._breakdown_layout.setSpacing(8)
        self._breakdown_layout.setContentsMargins(8, 8, 8, 8)
        empty_lbl = QLabel("No run loaded.")
        empty_lbl.setObjectName("MutedLabel")
        self._breakdown_layout.addWidget(empty_lbl)
        self._breakdown_layout.addStretch()
        self._tabs.addTab(self._breakdown_widget, "Category Breakdown")

        # Tab 2: Charts
        self._chart_widget = QScrollArea()
        self._chart_widget.setWidgetResizable(True)
        self._chart_widget.setFrameShape(QFrame.NoFrame)
        self._chart_inner = QWidget()
        self._chart_layout = QVBoxLayout(self._chart_inner)
        self._chart_layout.setContentsMargins(8, 8, 8, 8)
        self._chart_layout.setSpacing(16)
        self._chart_widget.setWidget(self._chart_inner)
        self._tabs.addTab(self._chart_widget, "Charts")

        # Tab 3: AI details
        self._ai_widget = QWidget()
        self._ai_layout = QVBoxLayout(self._ai_widget)
        self._ai_layout.setContentsMargins(8, 8, 8, 8)
        self._tabs.addTab(self._ai_widget, "AI Details")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_run(self, run: RunMetadata) -> None:
        """Populate the view with a completed RunMetadata."""
        self._run = run
        self._export = ExportService(run)
        self._populate(run)
        for btn in (self._btn_open_folder, self._btn_copy_md,
                    self._btn_export_json, self._btn_export_csv):
            btn.setEnabled(True)

    def _populate(self, run: RunMetadata) -> None:
        # Meta strip
        meta_text = (
            f"<b>{run.run_id}</b>  •  Profile: <b>{run.profile}</b>  •  "
            f"{run.generated_at[:19].replace('T', '  ')}  •  "
            f"Interpreter: {run.suite_interpreter}"
        )
        self._meta_label.setText(meta_text)

        # Summary counts
        self._ok_card.set_value(str(run.ok_count))
        self._deg_card.set_value(str(
            sum(1 for r in run.results.values() if r.status == BenchmarkStatus.DEGRADED.value)
        ))
        self._skip_card.set_value(str(
            sum(1 for r in run.results.values() if r.status == BenchmarkStatus.SKIPPED.value)
        ))
        self._fail_card.set_value(str(run.failed_count))

        self._build_breakdown(run)
        self._build_charts(run)
        self._build_ai_tab(run)

    def _build_breakdown(self, run: RunMetadata) -> None:
        # Clear
        while self._breakdown_layout.count():
            item = self._breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for cat, result in run.results.items():
            row_frame = QFrame()
            row_frame.setObjectName("Card")
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.setSpacing(16)

            name_lbl = QLabel(f"<b>{cat}</b>")
            name_lbl.setFixedWidth(120)
            row_layout.addWidget(name_lbl)

            badge = StatusBadge(result.status)
            row_layout.addWidget(badge)

            bench_lbl = QLabel(result.benchmark or "—")
            bench_lbl.setObjectName("MutedLabel")
            bench_lbl.setFixedWidth(160)
            row_layout.addWidget(bench_lbl)

            # Key metric
            metric_str = self._format_metric(cat, result)
            metric_lbl = QLabel(metric_str)
            row_layout.addWidget(metric_lbl)

            # Notes
            if result.notes:
                notes_lbl = QLabel(result.notes[:80] + ("…" if len(result.notes) > 80 else ""))
                notes_lbl.setObjectName("MutedLabel")
                row_layout.addWidget(notes_lbl)

            row_layout.addStretch()
            self._breakdown_layout.addWidget(row_frame)

        self._breakdown_layout.addStretch()

    def _build_charts(self, run: RunMetadata) -> None:
        # Clear existing charts
        while self._chart_layout.count():
            item = self._chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        chart_data = []
        for cat, result in run.results.items():
            label, field = _METRIC_LABELS.get(cat, ("Score", "score"))
            val = getattr(result, field, None)
            if val is not None:
                chart_data.append((cat, float(val)))

        if chart_data:
            chart = BarChartWidget(
                title="Benchmark Scores by Category",
                data=chart_data,
                y_label="Score",
            )
            chart.setMinimumHeight(260)
            self._chart_layout.addWidget(chart)
        else:
            self._chart_layout.addWidget(QLabel("No numeric metrics available for charting."))

        self._chart_layout.addStretch()

    def _build_ai_tab(self, run: RunMetadata) -> None:
        # Clear
        while self._ai_layout.count():
            item = self._ai_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        ai_result = run.results.get("ai")
        if not ai_result or not ai_result.backend_results:
            lbl = QLabel("No AI results in this run.")
            lbl.setObjectName("MutedLabel")
            self._ai_layout.addWidget(lbl)
            self._ai_layout.addStretch()
            return

        # Credible AI mode banner
        if ai_result.credible_ai_mode is True:
            banner = QLabel("✓  Credible AI Mode: real model results")
            banner.setStyleSheet("color: #3cb371; font-weight: bold; padding: 4px;")
        elif ai_result.credible_ai_mode is False:
            banner = QLabel("⚠  Credible AI Mode: synthetic proxy results only")
            banner.setStyleSheet("color: #e6a817; font-weight: bold; padding: 4px;")
        else:
            banner = QLabel("? Credible AI mode unknown")
            banner.setObjectName("MutedLabel")
        self._ai_layout.addWidget(banner)

        for br in ai_result.backend_results:
            frame = QFrame()
            frame.setObjectName("Card")
            fl = QVBoxLayout(frame)
            fl.setContentsMargins(12, 10, 12, 10)
            fl.setSpacing(4)

            hdr_row = QHBoxLayout()
            hdr_row.addWidget(QLabel(f"<b>{br.backend}</b>"))
            hdr_row.addWidget(StatusBadge(br.status))
            ds_lbl = QLabel(br.data_source or "")
            ds_lbl.setObjectName("MutedLabel")
            hdr_row.addWidget(ds_lbl)
            hdr_row.addStretch()
            fl.addLayout(hdr_row)

            metrics = []
            if br.prompt_tps is not None:
                metrics.append(f"Prompt TPS: {br.prompt_tps:.2f}")
            if br.eval_tps is not None:
                metrics.append(f"Eval TPS: {br.eval_tps:.2f}")
            if br.score is not None:
                metrics.append(f"Score: {br.score:.4g}")
            if br.model:
                metrics.append(f"Model: {br.model}")

            if metrics:
                fl.addWidget(QLabel("  ·  ".join(metrics)))

            if br.notes:
                notes = QLabel(br.notes[:120])
                notes.setObjectName("MutedLabel")
                fl.addWidget(notes)

            self._ai_layout.addWidget(frame)

        self._ai_layout.addStretch()

    # ------------------------------------------------------------------
    # Metric formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_metric(cat: str, result: CategoryResult) -> str:
        if cat == "gpu_game" and result.fps is not None:
            return f"{result.fps:.1f} FPS"
        if cat == "ai":
            if result.eval_tps is not None:
                return f"{result.eval_tps:.2f} TPS (eval)"
            if result.prompt_tps is not None:
                return f"{result.prompt_tps:.2f} TPS (prompt)"
        if result.score is not None:
            return f"{result.score:.4g}"
        return "—"

    # ------------------------------------------------------------------
    # Export actions
    # ------------------------------------------------------------------

    def _on_open_folder(self) -> None:
        if self._export:
            self._export.open_report_folder()

    def _on_copy_md(self) -> None:
        if self._export:
            ok = self._export.copy_markdown_to_clipboard()
            if not ok:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Copy Markdown",
                                        "Clipboard not available. Try installing xclip.")

    def _on_export_json(self) -> None:
        if not self._export:
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON", "summary.json", "JSON files (*.json)")
        if path:
            self._export.export_json(path)

    def _on_export_csv(self) -> None:
        if not self._export:
            return
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "summary.csv", "CSV files (*.csv)")
        if path:
            self._export.export_csv(path)
