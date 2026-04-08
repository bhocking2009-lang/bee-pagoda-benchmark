"""
Simple bar/metric chart widget using PySide6.QtCharts.

Falls back to a plain-text table if QtCharts is unavailable.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtCharts import (
        QBarCategoryAxis,
        QBarSeries,
        QBarSet,
        QChart,
        QChartView,
        QValueAxis,
    )
    _CHARTS_AVAILABLE = True
except ImportError:
    _CHARTS_AVAILABLE = False

try:
    from PySide6.QtGui import QColor, QPainter
    _GUI_AVAILABLE = True
except ImportError:
    _GUI_AVAILABLE = False


class BarChartWidget(QWidget):
    """
    Displays a simple bar chart.

    Parameters
    ----------
    title   : chart title
    data    : list of (label, value) pairs
    x_label : x-axis label
    y_label : y-axis (value) axis label
    """

    def __init__(
        self,
        title: str = "",
        data: Optional[List[Tuple[str, float]]] = None,
        x_label: str = "",
        y_label: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._data: List[Tuple[str, float]] = data or []
        self._x_label = x_label
        self._y_label = y_label
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _CHARTS_AVAILABLE and _GUI_AVAILABLE and self._data:
            self._build_qtchart(layout)
        else:
            self._build_fallback(layout)

    def _build_qtchart(self, layout: QVBoxLayout) -> None:
        bar_set = QBarSet(self._y_label or "Value")
        categories = []
        max_val = 0.0

        for label, value in self._data:
            bar_set.append(value)
            categories.append(label)
            max_val = max(max_val, value)

        bar_set.setColor(QColor("#2a52c9"))

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(self._title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.setTitleFont(self.font())

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setRange(0, max_val * 1.15 if max_val else 1)
        if self._y_label:
            axis_y.setTitleText(self._y_label)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)

        # Style the chart
        chart.setBackgroundBrush(QColor("#1a1e2e"))
        chart.setTitleBrush(QColor("#e8eaf6"))
        for axis in (axis_x, axis_y):
            axis.setLabelsColor(QColor("#9099c0"))
            axis.setLinePenColor(QColor("#2a2e42"))
            axis.setGridLineColor(QColor("#2a2e42"))

        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        view.setMinimumHeight(220)
        layout.addWidget(view)

    def _build_fallback(self, layout: QVBoxLayout) -> None:
        """Plain-text table fallback when QtCharts is unavailable."""
        if self._title:
            title_label = QLabel(f"<b>{self._title}</b>")
            layout.addWidget(title_label)

        if not self._data:
            layout.addWidget(QLabel("No data"))
            return

        max_val = max(v for _, v in self._data) if self._data else 1.0
        for label, value in self._data:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(140)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(lbl)

            # ASCII bar
            bar_width = int((value / max_val) * 30) if max_val > 0 else 0
            bar_str = "█" * bar_width
            bar_lbl = QLabel(f"  {bar_str}  {value:.2f}")
            bar_lbl.setObjectName("MutedLabel")
            row.addWidget(bar_lbl)
            layout.addLayout(row)

    def update_data(self, data: List[Tuple[str, float]]) -> None:
        """Replace data and rebuild the chart."""
        self._data = data
        # Rebuild by clearing and re-populating
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        if _CHARTS_AVAILABLE and _GUI_AVAILABLE and self._data:
            self._build_qtchart(self.layout())
        else:
            self._build_fallback(self.layout())


class MetricCard(QFrame):
    """A simple metric display card (title + value + subtitle)."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        self._title_lbl = QLabel(title.upper())
        self._title_lbl.setObjectName("CardTitle")
        layout.addWidget(self._title_lbl)

        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("CardValue")
        layout.addWidget(self._value_lbl)

        if subtitle:
            self._sub_lbl = QLabel(subtitle)
            self._sub_lbl.setObjectName("CardSub")
            layout.addWidget(self._sub_lbl)
        else:
            self._sub_lbl = None

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def set_value(self, value: str) -> None:
        self._value_lbl.setText(value)

    def set_subtitle(self, subtitle: str) -> None:
        if self._sub_lbl:
            self._sub_lbl.setText(subtitle)
