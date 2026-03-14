from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from custom_trainer.state import AppState
from custom_trainer.ui.pages.export_page import ExportPage
from custom_trainer.ui.pages.marking_page import MarkingPage
from custom_trainer.ui.pages.train_page import TrainPage
from custom_trainer.ui.pages.validate_page import ValidatePage
from custom_trainer.ui.widgets.log_panel import LogPanel


class CustomTrainerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('CustomTrainer 0_1_8')
        self.resize(1560, 980)
        self.state = AppState()

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabPosition(QTabWidget.North)

        self.marking_page = MarkingPage(self.state, self.log, self.set_status_message, self)
        self.train_page = TrainPage(self.state, self.log, self.set_status_message, self)
        self.validate_page = ValidatePage(self.state, self.log, self.set_status_message, self)
        self.export_page = ExportPage(self.state, self.log, self.set_status_message, self)

        self.tabs.addTab(self.marking_page, 'Marking')
        self.tabs.addTab(self.train_page, 'Training')
        self.tabs.addTab(self.validate_page, 'Validation')
        self.tabs.addTab(self.export_page, 'Export')
        self.setCentralWidget(self.tabs)

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
        for idx in range(self.tabs.count()):
            QShortcut(QKeySequence(f'Ctrl+{idx + 1}'), self, activated=lambda i=idx: self.tabs.setCurrentIndex(i))
        QShortcut(QKeySequence('Ctrl+Tab'), self, activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Shift+Tab'), self, activated=self.previous_tab)
        QShortcut(QKeySequence('Ctrl+S'), self, activated=self.marking_page.save_current_labels)
        QShortcut(QKeySequence('PageUp'), self, activated=self.marking_page.prev_image)
        QShortcut(QKeySequence('PageDown'), self, activated=self.marking_page.next_image)
        QShortcut(QKeySequence('F1'), self, activated=self.show_shortcuts)

    def next_tab(self) -> None:
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count())

    def previous_tab(self) -> None:
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count())

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
                    'Ctrl+1..Ctrl+4 -> Switch pages',
                    'Ctrl+Tab / Ctrl+Shift+Tab -> Next / previous page',
                    'Ctrl+S -> Save current labels on Marking page',
                    'PageUp / PageDown -> Previous / next image on Marking page',
                    'Right-click box -> Select box',
                    'Left-drag -> Create box',
                    'Delete / Arrow keys / Shift+Arrow keys -> Edit selected box',
                ]
            ),
        )
