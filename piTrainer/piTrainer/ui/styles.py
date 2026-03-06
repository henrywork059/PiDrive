from __future__ import annotations


def build_stylesheet() -> str:
    return """
    QWidget {
        font-size: 12px;
        color: #e6e8ee;
        background: #12161f;
    }
    QMainWindow {
        background: #12161f;
    }
    QToolBar {
        background: #171c26;
        border-bottom: 1px solid #2a3140;
        spacing: 6px;
        padding: 4px;
    }
    QMainWindow::separator {
        background: #56a7ff;
        width: 4px;
        height: 4px;
    }
    QStatusBar {
        background: #12161f;
        color: #c6cad4;
        border-top: 1px solid #2a3140;
    }
    QDockWidget {
        color: #f7fbff;
        font-weight: 700;
    }
    QDockWidget::title {
        background: #244c7a;
        color: #ffffff;
        padding: 8px 12px;
        border: 1px solid #56a7ff;
        border-bottom: none;
    }
    #dockPageFiller {
        background: #0f141c;
        border: none;
    }
    QGroupBox {
        border: 1px solid #2f3747;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
        background: #171c26;
        font-weight: 600;
        color: #f4f7ff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px 0 4px;
    }
    QPushButton {
        min-height: 30px;
        padding: 4px 10px;
        background: #263245;
        color: #eef2fb;
        border: 1px solid #3b4d67;
        border-radius: 6px;
    }
    QPushButton:hover {
        background: #30415a;
    }
    QPushButton:pressed {
        background: #213044;
    }
    QPushButton:disabled {
        background: #1a1f28;
        color: #6f7788;
        border-color: #2a3140;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTextEdit, QPlainTextEdit, QTableWidget {
        background: #0f141c;
        color: #e6e8ee;
        border: 1px solid #2f3747;
        border-radius: 6px;
        selection-background-color: #335b9a;
        selection-color: #ffffff;
    }
    #sessionListWidget {
        padding: 6px;
    }
    #sessionRow {
        background: #121a24;
        border: 1px solid #2a3444;
        border-radius: 8px;
    }
    #sessionRow:hover {
        background: #172232;
        border: 1px solid #3e5d86;
    }
    #sessionRowCheckbox {
        spacing: 12px;
        color: #f5f8ff;
        background: transparent;
        font-weight: 600;
    }
    #sessionRowCheckbox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #7fd3ff;
        background: #102033;
        margin-right: 4px;
    }
    #sessionRowCheckbox::indicator:hover {
        border-color: #b4ecff;
        background: #15304b;
    }
    #sessionRowCheckbox::indicator:checked {
        background: #18b2ff;
        border: 2px solid #eef9ff;
    }
    QHeaderView::section {
        background: #1c2430;
        color: #e6e8ee;
        border: 1px solid #2f3747;
        padding: 4px;
    }
    QTabWidget::pane {
        border: 1px solid #2f3747;
        background: #12161f;
    }
    QTabBar::tab {
        min-width: 100px;
        padding: 8px 14px;
        background: #171c26;
        color: #cfd5df;
        border: 1px solid #2f3747;
        border-bottom: none;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    QTabBar::tab:selected {
        background: #263245;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background: #1f2937;
    }
    QProgressBar {
        border: 1px solid #2f3747;
        border-radius: 6px;
        text-align: center;
        background: #0f141c;
        color: #e6e8ee;
    }
    QProgressBar::chunk {
        background: #4d85d1;
        border-radius: 5px;
    }
    QCheckBox {
        color: #f3f7ff;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid #7fbaff;
        background: #101722;
    }
    QCheckBox::indicator:hover {
        border-color: #a9d2ff;
        background: #162132;
    }
    QCheckBox::indicator:checked {
        background: #56a7ff;
        border: 2px solid #cfe7ff;
        image: none;
    }
    QLabel[role='muted'] {
        color: #8b94a7;
    }
    """
