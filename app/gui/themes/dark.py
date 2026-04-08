"""
Dark theme stylesheet for the Bee Pagoda Benchmark desktop app.

Colors are inspired by professional system-monitor tools:
  Background:  #0f1117 (near-black)
  Surface:     #1a1e2e (card/panel)
  Border:      #2a2e42
  Accent:      #4f8ef7 (blue)
  Success:     #3cb371 (green)
  Warning:     #e6a817 (amber)
  Danger:      #e05252 (red)
  Muted:       #6b7394
  Text:        #e8eaf6
"""

DARK_STYLESHEET = """
/* ──────────────────────────────────────────────────────────────────── */
/*  Global                                                              */
/* ──────────────────────────────────────────────────────────────────── */
* {
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 13px;
    color: #e8eaf6;
}

QMainWindow, QWidget {
    background-color: #0f1117;
}

QDialog {
    background-color: #1a1e2e;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Sidebar                                                             */
/* ──────────────────────────────────────────────────────────────────── */
#Sidebar {
    background-color: #131722;
    border-right: 1px solid #2a2e42;
    min-width: 200px;
    max-width: 200px;
}

#AppTitle {
    font-size: 15px;
    font-weight: bold;
    color: #4f8ef7;
    padding: 20px 16px 8px 16px;
}

#AppVersion {
    font-size: 11px;
    color: #6b7394;
    padding: 0 16px 16px 16px;
}

#NavButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    color: #9099c0;
    font-size: 13px;
    margin: 2px 8px;
}

#NavButton:hover {
    background-color: #1e2438;
    color: #e8eaf6;
}

#NavButton[active="true"] {
    background-color: #1c2c52;
    color: #4f8ef7;
    font-weight: bold;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Cards / Panels                                                      */
/* ──────────────────────────────────────────────────────────────────── */
#Card {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    border-radius: 8px;
    padding: 16px;
}

#CardTitle {
    font-size: 13px;
    font-weight: bold;
    color: #9099c0;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

#CardValue {
    font-size: 22px;
    font-weight: bold;
    color: #e8eaf6;
}

#CardSub {
    font-size: 11px;
    color: #6b7394;
    margin-top: 4px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Buttons                                                             */
/* ──────────────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1e2438;
    border: 1px solid #2a2e42;
    border-radius: 6px;
    padding: 8px 18px;
    color: #e8eaf6;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #252d47;
    border-color: #4f8ef7;
}

QPushButton:pressed {
    background-color: #1a2040;
}

QPushButton:disabled {
    color: #4a4f68;
    border-color: #23273a;
    background-color: #161a28;
}

#PrimaryButton {
    background-color: #2a52c9;
    border: none;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 24px;
    border-radius: 6px;
}

#PrimaryButton:hover {
    background-color: #3461de;
}

#PrimaryButton:pressed {
    background-color: #213fa8;
}

#PrimaryButton:disabled {
    background-color: #1a2040;
    color: #4a4f68;
}

#DangerButton {
    background-color: #a01818;
    border: none;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 18px;
    border-radius: 6px;
}

#DangerButton:hover {
    background-color: #c01e1e;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Status Badges                                                       */
/* ──────────────────────────────────────────────────────────────────── */
#BadgeOk {
    background-color: #1a3a28;
    color: #3cb371;
    border: 1px solid #2a5a3a;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 11px;
}

#BadgeDegraded {
    background-color: #3a2e0a;
    color: #e6a817;
    border: 1px solid #5a4a10;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 11px;
}

#BadgeSkipped {
    background-color: #1e2438;
    color: #6b7394;
    border: 1px solid #2a2e42;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 11px;
}

#BadgeFailed {
    background-color: #3a1010;
    color: #e05252;
    border: 1px solid #5a1818;
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 11px;
}

#BadgeUnknown {
    background-color: #1a1e2e;
    color: #9099c0;
    border: 1px solid #2a2e42;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Log viewer                                                          */
/* ──────────────────────────────────────────────────────────────────── */
#LogViewer {
    background-color: #0a0d16;
    color: #a8b0d0;
    border: 1px solid #2a2e42;
    border-radius: 6px;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    font-size: 12px;
    padding: 8px;
    selection-background-color: #1c2c52;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Form controls                                                       */
/* ──────────────────────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f1117;
    border: 1px solid #2a2e42;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e8eaf6;
    selection-background-color: #1c2c52;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4f8ef7;
}

QComboBox {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e8eaf6;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #4f8ef7;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    selection-background-color: #1c2c52;
    color: #e8eaf6;
    padding: 4px;
}

QCheckBox {
    spacing: 8px;
    color: #e8eaf6;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid #4a4f68;
    background-color: #0f1117;
}

QCheckBox::indicator:checked {
    background-color: #2a52c9;
    border-color: #4f8ef7;
}

QLabel {
    color: #e8eaf6;
}

#MutedLabel {
    color: #6b7394;
    font-size: 12px;
}

#SectionHeader {
    font-size: 18px;
    font-weight: bold;
    color: #e8eaf6;
    margin-bottom: 4px;
}

#SubHeader {
    font-size: 13px;
    color: #9099c0;
    margin-bottom: 16px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Tables / Lists                                                      */
/* ──────────────────────────────────────────────────────────────────── */
QTableWidget, QListWidget, QTreeWidget {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    border-radius: 6px;
    gridline-color: #2a2e42;
    color: #e8eaf6;
    alternate-background-color: #1e2438;
}

QTableWidget::item:selected, QListWidget::item:selected {
    background-color: #1c2c52;
    color: #4f8ef7;
}

QHeaderView::section {
    background-color: #131722;
    color: #9099c0;
    border: none;
    border-bottom: 1px solid #2a2e42;
    padding: 8px 12px;
    font-weight: bold;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Scroll bars                                                         */
/* ──────────────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background-color: #0f1117;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2a2e42;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3a3e52;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #0f1117;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #2a2e42;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Progress bar                                                        */
/* ──────────────────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    border-radius: 4px;
    text-align: center;
    color: #9099c0;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #2a52c9;
    border-radius: 4px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Tab widget                                                          */
/* ──────────────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2a2e42;
    border-radius: 6px;
    background-color: #1a1e2e;
}

QTabBar::tab {
    background-color: #131722;
    border: 1px solid #2a2e42;
    border-bottom: none;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: #6b7394;
}

QTabBar::tab:selected {
    background-color: #1a1e2e;
    color: #e8eaf6;
}

QTabBar::tab:hover {
    color: #e8eaf6;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Splitter                                                            */
/* ──────────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #2a2e42;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Tooltips                                                            */
/* ──────────────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    color: #e8eaf6;
    padding: 6px 10px;
    border-radius: 4px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Menu bar / menus                                                    */
/* ──────────────────────────────────────────────────────────────────── */
QMenuBar {
    background-color: #131722;
    border-bottom: 1px solid #2a2e42;
    padding: 4px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
    color: #9099c0;
}

QMenuBar::item:selected {
    background-color: #1e2438;
    color: #e8eaf6;
}

QMenu {
    background-color: #1a1e2e;
    border: 1px solid #2a2e42;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 20px;
    border-radius: 4px;
    color: #e8eaf6;
}

QMenu::item:selected {
    background-color: #1c2c52;
    color: #4f8ef7;
}

QMenu::separator {
    height: 1px;
    background-color: #2a2e42;
    margin: 4px 8px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Status bar                                                          */
/* ──────────────────────────────────────────────────────────────────── */
QStatusBar {
    background-color: #131722;
    border-top: 1px solid #2a2e42;
    color: #6b7394;
    font-size: 11px;
    padding: 2px 8px;
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Group box                                                           */
/* ──────────────────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #2a2e42;
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px;
    color: #9099c0;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
}
"""


def apply_dark_theme(app) -> None:
    """Apply the dark stylesheet to a QApplication."""
    app.setStyleSheet(DARK_STYLESHEET)
    # Set application palette for native widgets that ignore stylesheets
    try:
        from PySide6.QtGui import QPalette, QColor
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0x0f, 0x11, 0x17))
        palette.setColor(QPalette.WindowText, QColor(0xe8, 0xea, 0xf6))
        palette.setColor(QPalette.Base, QColor(0x1a, 0x1e, 0x2e))
        palette.setColor(QPalette.AlternateBase, QColor(0x1e, 0x24, 0x38))
        palette.setColor(QPalette.Text, QColor(0xe8, 0xea, 0xf6))
        palette.setColor(QPalette.Button, QColor(0x1e, 0x24, 0x38))
        palette.setColor(QPalette.ButtonText, QColor(0xe8, 0xea, 0xf6))
        palette.setColor(QPalette.Highlight, QColor(0x2a, 0x52, 0xc9))
        palette.setColor(QPalette.HighlightedText, QColor(0xff, 0xff, 0xff))
        palette.setColor(QPalette.ToolTipBase, QColor(0x1a, 0x1e, 0x2e))
        palette.setColor(QPalette.ToolTipText, QColor(0xe8, 0xea, 0xf6))
        palette.setColor(QPalette.Link, QColor(0x4f, 0x8e, 0xf7))
        palette.setColor(QPalette.PlaceholderText, QColor(0x6b, 0x73, 0x94))
        app.setPalette(palette)
    except Exception:
        pass
