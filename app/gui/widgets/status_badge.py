"""Status badge widget — displays ok/degraded/skipped/failed/unknown."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel


_STATUS_OBJECT_NAMES = {
    "ok":       "BadgeOk",
    "degraded": "BadgeDegraded",
    "skipped":  "BadgeSkipped",
    "failed":   "BadgeFailed",
    "missing":  "BadgeFailed",
    "unknown":  "BadgeUnknown",
}

_STATUS_TEXT = {
    "ok":       "✓ OK",
    "degraded": "⚠ DEGRADED",
    "skipped":  "– SKIPPED",
    "failed":   "✗ FAILED",
    "missing":  "✗ MISSING",
    "unknown":  "? UNKNOWN",
}


class StatusBadge(QLabel):
    """A coloured label that shows a benchmark status."""

    def __init__(self, status: str = "unknown", parent=None) -> None:
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        s = status.lower()
        self.setText(_STATUS_TEXT.get(s, status.upper()))
        self.setObjectName(_STATUS_OBJECT_NAMES.get(s, "BadgeUnknown"))
        # Force Qt to re-apply the stylesheet for the new object name
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
