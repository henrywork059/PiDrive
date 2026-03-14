from __future__ import annotations


def build_stylesheet() -> str:
    return """
    QWidget {
        background: #12161f;
        color: #e8ecf4;
        font-size: 12px;
    }
    QMainWindow {
        background: #12161f;
    }
    QMenuBar, QMenu {
        background: #171c26;
        color: #e8ecf4;
    }
    QStatusBar {
        background: #10141c;
        color: #d0d8e6;
        border-top: 1px solid #2b3443;
    }
    QDockWidget {
        color: #ffffff;
        font-weight: 700;
    }
    QDockWidget::title {
        background: #214874;
        color: #ffffff;
        padding: 6px 10px;
        border: 1px solid #4f9cf8;
        border-bottom: none;
    }
    QTabWidget::pane {
        border: 1px solid #2b3443;
        border-radius: 8px;
        background: #12161f;
    }
    QTabBar::tab {
        min-width: 120px;
        padding: 8px 14px;
        background: #171c26;
        color: #ccd6e6;
        border: 1px solid #2b3443;
        border-bottom: none;
        margin-right: 2px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
    }
    QTabBar::tab:selected {
        background: #243146;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background: #1d2634;
    }
    QGroupBox {
        background: #171c26;
        border: 1px solid #2f394a;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 12px;
        font-weight: 700;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #f5f8ff;
    }
    QLineEdit, QComboBox, QListWidget, QTextEdit, QPlainTextEdit, QSpinBox, QFrame {
        background: #0f141c;
        color: #e8ecf4;
        border: 1px solid #2f394a;
        border-radius: 6px;
        selection-background-color: #3463a8;
        selection-color: #ffffff;
    }
    QListWidget {
        padding: 4px;
    }
    QPushButton {
        min-height: 28px;
        padding: 4px 10px;
        background: #263245;
        color: #eef4ff;
        border: 1px solid #415470;
        border-radius: 6px;
    }
    QPushButton:hover {
        background: #30405b;
    }
    QPushButton:pressed {
        background: #1e2a3b;
    }
    QPushButton:disabled {
        background: #1a202a;
        color: #758198;
        border-color: #2a3240;
    }
    QLabel[role='muted'] {
        color: #92a0b7;
    }
    QLabel[role='value'] {
        color: #ffffff;
        font-weight: 700;
    }
    QSplitter::handle {
        background: #1e2633;
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: #10141c;
        border: 1px solid #222b38;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
        background: #385173;
        border-radius: 5px;
        min-height: 24px;
        min-width: 24px;
    }
    """
