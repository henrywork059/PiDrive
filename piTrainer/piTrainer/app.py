from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QStyleFactory

from .ui.theme import apply_application_palette, saved_theme, set_theme
from .ui.styles import build_stylesheet
from .ui.typography import apply_local_typography
from .security.version_gate import check_version_gate
from .version import APP_NAME, APP_VERSION



def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    set_theme(saved_theme())
    apply_application_palette(app)
    apply_local_typography(app)
    app.setStyleSheet(build_stylesheet())

    gate_result = check_version_gate(APP_VERSION)
    if not gate_result.allowed:
        detail = f"\n\nDetail: {gate_result.detail}" if gate_result.detail else ""
        QMessageBox.critical(None, gate_result.title, f"{gate_result.message}{detail}")
        return 2

    from .main_window import MainWindow
    window = MainWindow()
    window.show()
    return app.exec()
