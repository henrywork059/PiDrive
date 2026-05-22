from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from .main_window import MainWindow
from .ui.styles import build_stylesheet
from .version import APP_NAME, APP_VERSION



def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()
