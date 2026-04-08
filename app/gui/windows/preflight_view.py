"""Dependency / preflight status view."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.schemas import PreflightCheck, PreflightResult
from app.gui.widgets.status_badge import StatusBadge


class PreflightView(QWidget):
    """Shows dependency status and version info from preflight checks."""

    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Dependencies")
        title.setObjectName("SectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()

        self._refresh_btn = QPushButton("🔄  Re-check")
        self._refresh_btn.clicked.connect(self.refresh_requested)
        hdr.addWidget(self._refresh_btn)
        root.addLayout(hdr)

        sub = QLabel(
            "Benchmark capabilities depend on the tools listed below.  "
            "Missing optional tools will degrade (but not block) the suite."
        )
        sub.setObjectName("MutedLabel")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # Status summary frame
        self._summary_frame = QFrame()
        self._summary_frame.setObjectName("Card")
        self._summary_layout = QHBoxLayout(self._summary_frame)
        self._summary_layout.setContentsMargins(16, 12, 16, 12)
        self._summary_layout.setSpacing(16)
        self._summary_label = QLabel("Run a preflight check to see dependency status.")
        self._summary_label.setObjectName("MutedLabel")
        self._summary_layout.addWidget(self._summary_label)
        self._summary_layout.addStretch()
        root.addWidget(self._summary_frame)

        # Table
        cols = ["Dependency", "Type", "Required", "Status", "Version", "Path", "Notes"]
        self._table = QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        hdr_view = self._table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr_view.setSectionResizeMode(5, QHeaderView.Stretch)
        hdr_view.setSectionResizeMode(6, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        root.addWidget(self._table)

        # Copy install guidance button
        self._copy_btn = QPushButton("📋  Copy Install Guidance")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_guidance)
        root.addWidget(self._copy_btn)

        self._preflight: PreflightResult | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_preflight(self, result: PreflightResult) -> None:
        self._preflight = result

        # Summary
        counts = result.status_counts
        present   = counts.get("present", 0)
        missing   = counts.get("missing", 0)
        mismatch  = counts.get("version-mismatch", 0)
        opt_miss  = counts.get("optional-missing", 0)
        self._summary_label.setText(
            f"Overall: <b>{result.status}</b>  |  "
            f"Present: {present}  •  Missing: {missing}  •  "
            f"Version mismatch: {mismatch}  •  Optional missing: {opt_miss}"
        )

        self._populate_table(result.checks)
        self._copy_btn.setEnabled(bool(result.checks))

    def _populate_table(self, checks: list[PreflightCheck]) -> None:
        self._table.setRowCount(0)
        for row_idx, check in enumerate(checks):
            self._table.insertRow(row_idx)
            self._table.setItem(row_idx, 0, QTableWidgetItem(check.name))
            self._table.setItem(row_idx, 1, QTableWidgetItem(check.type))
            req_lbl = "Yes" if check.required else "No"
            self._table.setItem(row_idx, 2, _centered(req_lbl))

            badge = StatusBadge(check.status)
            badge_container = QWidget()
            bl = QHBoxLayout(badge_container)
            bl.setContentsMargins(4, 2, 4, 2)
            bl.addWidget(badge)
            self._table.setCellWidget(row_idx, 3, badge_container)

            self._table.setItem(row_idx, 4, QTableWidgetItem(check.version or "—"))
            self._table.setItem(row_idx, 5, QTableWidgetItem(check.path or "—"))
            self._table.setItem(row_idx, 6, QTableWidgetItem(check.notes or ""))
            self._table.setRowHeight(row_idx, 32)

    def _copy_guidance(self) -> None:
        if not self._preflight:
            return
        missing = [
            c.name for c in self._preflight.checks
            if c.status in ("missing", "optional-missing")
        ]
        if not missing:
            text = "All required dependencies are present."
        else:
            text = "Missing dependencies:\n\n"
            text += "  # Ubuntu / Debian:\n"
            text += f"  sudo apt install {' '.join(missing)}\n\n"
            text += "  # Fedora:\n"
            text += f"  sudo dnf install {' '.join(missing)}\n"

        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.clipboard().setText(text)
        except Exception:
            pass


def _centered(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    return item
