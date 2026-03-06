from __future__ import annotations


def build_stylesheet() -> str:
    return """
    QWidget {
        font-size: 12px;
    }
    QMainWindow {
        background: #f6f7fb;
    }
    QGroupBox {
        border: 1px solid #d9dbe7;
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 10px;
        background: white;
        font-weight: 600;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 4px 0 4px;
    }
    QPushButton {
        min-height: 30px;
        padding: 4px 10px;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget, QTextEdit, QPlainTextEdit, QTableWidget {
        background: white;
    }
    QTabWidget::pane {
        border: 1px solid #d9dbe7;
        background: #f6f7fb;
    }
    QTabBar::tab {
        min-width: 100px;
        padding: 8px 14px;
    }
    QLabel[role='muted'] {
        color: #667085;
    }
    """
