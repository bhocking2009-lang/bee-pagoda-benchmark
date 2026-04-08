"""Run History view — searchable list of all prior benchmark runs."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.history import HistoryEntry
from app.gui.widgets.status_badge import StatusBadge


class HistoryView(QWidget):
    """Browse and search previous benchmark runs."""

    open_run_requested = Signal(str)  # run_id
    compare_requested  = Signal(list)  # [run_id, run_id]
    refresh_requested  = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[HistoryEntry] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Run History")
        title.setObjectName("SectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()

        self._refresh_btn = QPushButton("🔄  Refresh")
        self._refresh_btn.clicked.connect(self.refresh_requested)
        hdr.addWidget(self._refresh_btn)

        self._rebuild_btn = QPushButton("⚙  Rebuild Index")
        self._rebuild_btn.clicked.connect(self.refresh_requested)
        hdr.addWidget(self._rebuild_btn)

        root.addLayout(hdr)

        # Search bar
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by profile, status, or category…")
        self._search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search)
        root.addLayout(search_row)

        # Table
        cols = ["Run ID", "Profile", "Categories", "Date", "Status", "OK", "Failed", ""]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.Interactive)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        root.addWidget(self._table)

        # Action buttons
        btn_row = QHBoxLayout()
        self._open_btn = QPushButton("Open Selected")
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._on_open)
        btn_row.addWidget(self._open_btn)

        self._compare_btn = QPushButton("Compare Selected (2)")
        self._compare_btn.setEnabled(False)
        self._compare_btn.clicked.connect(self._on_compare)
        btn_row.addWidget(self._compare_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_entries(self, entries: list[HistoryEntry]) -> None:
        self._entries = entries
        self._apply_filter(self._search.text())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        filtered = [
            e for e in self._entries
            if not q or q in e.profile or q in e.overall_status
               or any(q in cat for cat in e.selected_categories)
               or q in e.run_id
        ]
        self._populate_table(filtered)

    def _populate_table(self, entries: list[HistoryEntry]) -> None:
        self._table.setRowCount(0)
        for row_idx, entry in enumerate(entries):
            self._table.insertRow(row_idx)
            self._table.setItem(row_idx, 0, QTableWidgetItem(entry.run_id))
            self._table.setItem(row_idx, 1, QTableWidgetItem(entry.profile))
            self._table.setItem(row_idx, 2, QTableWidgetItem(", ".join(entry.selected_categories)))
            self._table.setItem(row_idx, 3, QTableWidgetItem(entry.generated_at[:19].replace("T", " ")))

            badge = StatusBadge(entry.overall_status)
            badge_container = QWidget()
            badge_layout = QHBoxLayout(badge_container)
            badge_layout.setContentsMargins(4, 2, 4, 2)
            badge_layout.addWidget(badge)
            self._table.setCellWidget(row_idx, 4, badge_container)

            self._table.setItem(row_idx, 5, _centered(str(entry.ok_count)))
            self._table.setItem(row_idx, 6, _centered(str(entry.failed_count)))

            open_btn = QPushButton("Open")
            open_btn.setFixedWidth(70)
            open_btn.clicked.connect(lambda _, rid=entry.run_id: self.open_run_requested.emit(rid))
            self._table.setCellWidget(row_idx, 7, open_btn)

            self._table.setRowHeight(row_idx, 36)

    def _on_selection_changed(self) -> None:
        selected_rows = self._table.selectionModel().selectedRows()
        count = len(selected_rows)
        self._open_btn.setEnabled(count == 1)
        self._compare_btn.setEnabled(count == 2)

    def _on_open(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if rows:
            run_id = self._table.item(rows[0].row(), 0).text()
            self.open_run_requested.emit(run_id)

    def _on_compare(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if len(rows) == 2:
            ids = [self._table.item(r.row(), 0).text() for r in rows]
            self.compare_requested.emit(ids)


def _centered(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    return item
