from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow
from .ui.styles import build_stylesheet



def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PiCar Trainer")
    app.setStyleSheet(build_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()
