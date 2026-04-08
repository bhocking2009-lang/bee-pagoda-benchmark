"""Comparison view — compare two benchmark runs side-by-side."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
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

from app.core.schemas import BenchmarkStatus, CategoryResult, RunMetadata
from app.gui.widgets.status_badge import StatusBadge


class ComparisonView(QWidget):
    """Side-by-side comparison of two RunMetadata objects."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._run_a: Optional[RunMetadata] = None
        self._run_b: Optional[RunMetadata] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Compare Runs")
        title.setObjectName("SectionHeader")
        root.addWidget(title)
        sub = QLabel("Select two runs from the history view to compare.")
        sub.setObjectName("SubHeader")
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 16, 0)
        self._content_layout.setSpacing(8)
        scroll.setWidget(self._content)
        root.addWidget(scroll)

        self._placeholder = QLabel("No runs selected for comparison.")
        self._placeholder.setObjectName("MutedLabel")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._content_layout.addWidget(self._placeholder)
        self._content_layout.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(self, run_a: RunMetadata, run_b: RunMetadata) -> None:
        self._run_a = run_a
        self._run_b = run_b
        self._rebuild()

    def _rebuild(self) -> None:
        if not self._run_a or not self._run_b:
            return

        # Clear layout
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        run_a = self._run_a
        run_b = self._run_b

        # Column headers
        grid = QGridLayout()
        grid.setSpacing(10)

        def header(text: str, col: int) -> None:
            lbl = QLabel(f"<b>{text}</b>")
            lbl.setObjectName("CardTitle")
            grid.addWidget(lbl, 0, col)

        header("Category", 0)
        header(run_a.run_id[:30], 1)
        header(run_b.run_id[:30], 2)
        header("Δ Change", 3)

        all_cats = sorted(set(list(run_a.results.keys()) + list(run_b.results.keys())))

        for row, cat in enumerate(all_cats, start=1):
            res_a = run_a.results.get(cat)
            res_b = run_b.results.get(cat)

            cat_lbl = QLabel(cat)
            grid.addWidget(cat_lbl, row, 0)

            grid.addWidget(self._result_cell(res_a), row, 1)
            grid.addWidget(self._result_cell(res_b), row, 2)
            grid.addWidget(self._delta_cell(res_a, res_b, cat), row, 3)

        frame = QFrame()
        frame.setObjectName("Card")
        frame.setLayout(grid)
        self._content_layout.addWidget(frame)
        self._content_layout.addStretch()

    @staticmethod
    def _result_cell(result: Optional[CategoryResult]) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        if result is None:
            h.addWidget(QLabel("—"))
        else:
            h.addWidget(StatusBadge(result.status))
            metric = result.score or result.fps or result.prompt_tps or result.eval_tps
            if metric is not None:
                h.addWidget(QLabel(f"{metric:.4g}"))
        return w

    @staticmethod
    def _delta_cell(res_a: Optional[CategoryResult], res_b: Optional[CategoryResult], cat: str) -> QLabel:
        def _metric(r: Optional[CategoryResult]) -> Optional[float]:
            if r is None:
                return None
            return r.score or r.fps or r.prompt_tps or r.eval_tps

        a = _metric(res_a)
        b = _metric(res_b)

        if a is None or b is None or a == 0:
            lbl = QLabel("N/A")
            lbl.setObjectName("MutedLabel")
            return lbl

        delta_pct = (b - a) / abs(a) * 100
        sign = "+" if delta_pct >= 0 else ""
        color = "#3cb371" if delta_pct >= 0 else "#e05252"
        lbl = QLabel(f"<span style='color:{color};font-weight:bold;'>{sign}{delta_pct:.1f}%</span>")
        return lbl
