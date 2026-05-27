from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from .main_window import MainWindow
from .ui.styles import build_stylesheet
from .security.version_gate import check_version_gate
from .version import APP_NAME, APP_VERSION



def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())

    gate_result = check_version_gate(APP_VERSION)
    if not gate_result.allowed:
        detail = f"\n\nDetail: {gate_result.detail}" if gate_result.detail else ""
        QMessageBox.critical(None, gate_result.title, f"{gate_result.message}{detail}")
        return 2

    window = MainWindow()
    window.show()
    return app.exec()
