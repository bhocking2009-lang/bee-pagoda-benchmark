"""
Bee Pagoda Benchmark — desktop application entry point.

Usage:
    python -m app.gui.main          # run GUI
    bee-pagoda                      # run GUI (installed)
    bee-pagoda-cli                  # CLI runner (see app.core.runner)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def main() -> None:
    """Launch the PySide6 desktop application."""
    _configure_logging()

    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
    except ImportError:
        print(
            "ERROR: PySide6 is not installed.\n"
            "Install it with:  pip install PySide6",
            file=sys.stderr,
        )
        sys.exit(1)

    from app.gui.themes.dark import apply_dark_theme
    from app.gui.windows.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Bee Pagoda Benchmark")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Bee Pagoda")

    # Enable high-DPI scaling
    try:
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        pass  # Qt6 handles this automatically

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _configure_logging() -> None:
    import platform
    level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )
    # Log to a platform-appropriate directory
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local" / "BeePagodaBenchmark" / "logs"
    else:
        base = Path.home() / ".local" / "share" / "bee-pagoda-benchmark" / "logs"
    try:
        base.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(base / "app.log", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
        ))
        logging.getLogger().addHandler(fh)
    except Exception:
        pass


if __name__ == "__main__":
    main()
