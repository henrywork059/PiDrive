from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from custom_trainer.state import AppState
from custom_trainer.ui.pages.annotate_page import AnnotatePage
from custom_trainer.ui.pages.dataset_page import DatasetPage
from custom_trainer.ui.pages.export_page import ExportPage
from custom_trainer.ui.pages.pi_deploy_page import PiDeployPage
from custom_trainer.ui.pages.train_page import TrainPage
from custom_trainer.ui.pages.validate_page import ValidatePage
from custom_trainer.ui.widgets.log_panel import LogPanel


class CustomTrainerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('CustomTrainer — PySide6 Desktop App')
        self.resize(1480, 960)
        self.state = AppState()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabPosition(QTabWidget.North)

        self.dataset_page = DatasetPage(self.state, self.log, self.set_status_message, self)
        self.annotate_page = AnnotatePage(self.state, self.log, self.set_status_message, self)
        self.train_page = TrainPage(self.state, self.log, self.set_status_message, self)
        self.validate_page = ValidatePage(self.state, self.log, self.set_status_message, self)
        self.export_page = ExportPage(self.state, self.log, self.set_status_message, self)
        self.pi_deploy_page = PiDeployPage(self.state, self.log, self.set_status_message, self)

        self.tabs.addTab(self.dataset_page, 'Dataset')
        self.tabs.addTab(self.annotate_page, 'Annotate')
        self.tabs.addTab(self.train_page, 'Train')
        self.tabs.addTab(self.validate_page, 'Validate')
        self.tabs.addTab(self.export_page, 'Export')
        self.tabs.addTab(self.pi_deploy_page, 'Pi Deploy')
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
        for idx in range(6):
            QShortcut(QKeySequence(f'Ctrl+{idx + 1}'), self, activated=lambda i=idx: self.tabs.setCurrentIndex(i))
        QShortcut(QKeySequence('Ctrl+Tab'), self, activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Shift+Tab'), self, activated=self.previous_tab)
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
        lines = [
            'Ctrl+1..Ctrl+6 -> Switch pages',
            'Ctrl+Tab / Ctrl+Shift+Tab -> Next / Previous page',
            'F1 -> Show shortcuts',
            'Right-click annotation boxes -> Select box',
            'Drag on the annotation canvas -> Create box',
        ]
        QMessageBox.information(self, 'Shortcuts', '\n'.join(lines))
