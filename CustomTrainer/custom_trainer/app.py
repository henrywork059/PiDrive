from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from custom_trainer.ui.main_window import CustomTrainerMainWindow
from custom_trainer.ui.styles import build_stylesheet


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('CustomTrainer')
    if 'Fusion' in QStyleFactory.keys():
        app.setStyle('Fusion')
    app.setStyleSheet(build_stylesheet())
    window = CustomTrainerMainWindow()
    window.show()
    return app.exec()
