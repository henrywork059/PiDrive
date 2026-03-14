from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox, QStatusBar

from custom_trainer.state import AppState
from custom_trainer.ui.pages.marking_page import MarkingPage
from custom_trainer.ui.widgets.log_panel import LogPanel


class CustomTrainerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('CustomTrainer 0_1_2')
        self.resize(1560, 980)
        self.state = AppState()

        self.marking_page = MarkingPage(self.state, self.log, self.set_status_message, self)
        self.setCentralWidget(self.marking_page)

        self.log_panel = LogPanel(self)
        self.log_dock = QDockWidget('Log Console', self)
        self.log_dock.setWidget(self.log_panel)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

        self.status = QStatusBar(self)
        self.status.setSizeGripEnabled(True)
        self.setStatusBar(self.status)
        self.set_status_message('Ready')
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence('Ctrl+S'), self, activated=self.marking_page.save_current_labels)
        QShortcut(QKeySequence('PageUp'), self, activated=self.marking_page.prev_image)
        QShortcut(QKeySequence('PageDown'), self, activated=self.marking_page.next_image)
        QShortcut(QKeySequence('F1'), self, activated=self.show_shortcuts)

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    def log(self, message: str) -> None:
        self.log_panel.log(message)

    def show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            'Shortcuts',
            '\n'.join(
                [
                    'Ctrl+S -> Save current labels',
                    'PageUp / PageDown -> Previous / next image',
                    'Right-click a box -> Select box',
                    'Left-drag -> Create box',
                    'Arrow keys -> Move selected box',
                    'Shift + Arrow keys -> Move selected box faster',
                    'Delete -> Delete selected box',
                ]
            ),
        )
