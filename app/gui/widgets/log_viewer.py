"""Streaming log viewer widget."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_MAX_BLOCK_COUNT = 10_000  # limit memory usage for very long runs


class LogViewer(QWidget):
    """
    Scrollable, monospace log panel that can receive lines from any thread.

    Connect ``append_line`` slot to a Qt signal emitting strings.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._text = QPlainTextEdit()
        self._text.setObjectName("LogViewer")
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(_MAX_BLOCK_COUNT)
        self._text.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self._text)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_clear = QPushButton("Clear")
        self._btn_clear.setFixedWidth(72)
        self._btn_clear.clicked.connect(self.clear)
        btn_row.addWidget(self._btn_clear)

        self._btn_scroll_end = QPushButton("↓ Follow")
        self._btn_scroll_end.setFixedWidth(80)
        self._btn_scroll_end.setCheckable(True)
        self._btn_scroll_end.setChecked(True)
        btn_row.addWidget(self._btn_scroll_end)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    @Slot(str)
    def append_line(self, line: str) -> None:
        """Append a single line.  Safe to call from any thread via signal."""
        self._text.appendPlainText(line)
        if self._btn_scroll_end.isChecked():
            self._text.moveCursor(QTextCursor.End)

    @Slot()
    def clear(self) -> None:
        self._text.clear()

    def set_follow(self, enabled: bool) -> None:
        self._btn_scroll_end.setChecked(enabled)

    def text(self) -> str:
        return self._text.toPlainText()
