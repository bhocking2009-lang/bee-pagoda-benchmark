"""Sidebar navigation widget."""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

_APP_NAME = "Bee Pagoda"
_APP_VERSION = "v1.0.0"

# (section_id, icon, label)
NAV_ITEMS: List[Tuple[str, str, str]] = [
    ("dashboard",    "⌂",  "Dashboard"),
    ("new_run",      "▶",  "New Benchmark"),
    ("monitor",      "◈",  "Live Monitor"),
    ("results",      "◉",  "Results"),
    ("history",      "⏱",  "Run History"),
    ("comparison",   "⇄",  "Compare Runs"),
    ("preflight",    "✔",  "Dependencies"),
]


class Sidebar(QWidget):
    """Vertical navigation sidebar."""

    # Emitted when a nav section is selected
    section_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._buttons: Dict[str, QPushButton] = {}
        self._active_id: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel(_APP_NAME)
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        version = QLabel(_APP_VERSION)
        version.setObjectName("AppVersion")
        layout.addWidget(version)

        for section_id, icon, label in NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("NavButton")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(False)
            btn.clicked.connect(lambda _, sid=section_id: self._on_clicked(sid))
            layout.addWidget(btn)
            self._buttons[section_id] = btn

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _on_clicked(self, section_id: str) -> None:
        self.set_active(section_id)
        self.section_changed.emit(section_id)

    def set_active(self, section_id: str) -> None:
        """Highlight the given section button."""
        for sid, btn in self._buttons.items():
            active = sid == section_id
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._active_id = section_id

    @property
    def active_section(self) -> str:
        return self._active_id
