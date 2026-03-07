from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStatusBar, QTabWidget

from .app_state import AppState
from .pages.data_page import DataPage
from .pages.export_page import ExportPage
from .pages.preprocess_page import PreprocessPage
from .pages.train_page import TrainPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('PiCar Trainer — PySide6 Desktop App')
        self.resize(1400, 900)
        self.state = AppState()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabPosition(QTabWidget.North)

        self.data_page = DataPage(self.state, self)
        self.preprocess_page = PreprocessPage(self.state, self)
        self.train_page = TrainPage(self.state, self)
        self.export_page = ExportPage(self.state, self)

        self.tabs.addTab(self.data_page, 'Data')
        self.tabs.addTab(self.preprocess_page, 'Preprocess')
        self.tabs.addTab(self.train_page, 'Train')
        self.tabs.addTab(self.export_page, 'Export')

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True)
        self.setStatusBar(self.status)
        self.set_status_message('Ready')

        self._setup_shortcuts()
        self.data_page.refresh_sessions()
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.export_page.refresh_from_state()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence('Ctrl+1'), self, activated=lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence('Ctrl+2'), self, activated=lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence('Ctrl+3'), self, activated=lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence('Ctrl+4'), self, activated=lambda: self.tabs.setCurrentIndex(3))
        QShortcut(QKeySequence('Ctrl+Tab'), self, activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Shift+Tab'), self, activated=self.previous_tab)
        QShortcut(QKeySequence('F5'), self, activated=self.data_page.refresh_sessions)
        QShortcut(QKeySequence('Ctrl+L'), self, activated=self.data_page.load_selected_sessions)
        QShortcut(QKeySequence('Ctrl+A'), self, activated=self.data_page.session_list_panel.select_all)
        QShortcut(QKeySequence('Ctrl+Shift+A'), self, activated=self.data_page.session_list_panel.clear_all)
        QShortcut(QKeySequence('Ctrl+P'), self, activated=self.train_page.prepare_split)
        QShortcut(QKeySequence('Ctrl+R'), self, activated=self.train_page.start_training)
        QShortcut(QKeySequence('Escape'), self, activated=self.train_page.stop_training)
        QShortcut(QKeySequence('Ctrl+E'), self, activated=self.export_page.export_model)
        QShortcut(QKeySequence('Ctrl+Shift+R'), self, activated=self.reset_current_page_layout)
        QShortcut(QKeySequence('F1'), self, activated=self.show_shortcuts)

    def next_tab(self) -> None:
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count())

    def previous_tab(self) -> None:
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count())

    def current_dock_page(self):
        return self.tabs.currentWidget()

    def reset_current_page_layout(self) -> None:
        page = self.current_dock_page()
        if hasattr(page, 'reset_layout'):
            page.reset_layout()
            self.set_status_message('Current page layout reset to default.')

    def show_shortcuts(self) -> None:
        lines = [
            'Ctrl+1 / Ctrl+2 / Ctrl+3 / Ctrl+4 -> Switch to Data / Preprocess / Train / Export',
            'Ctrl+Tab / Ctrl+Shift+Tab -> Next / Previous page',
            'F5 -> Refresh sessions',
            'Ctrl+L -> Load selected sessions',
            'Ctrl+A -> Select all sessions',
            'Ctrl+Shift+A -> Clear selected sessions',
            'Ctrl+P -> Prepare split',
            'Ctrl+R -> Start training',
            'Esc -> Stop training',
            'Ctrl+E -> Export model',
            'Ctrl+Shift+R -> Reset current page layout',
            'F1 -> Show this shortcut list',
        ]
        QMessageBox.information(self, 'Shortcuts', chr(10).join(lines))

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    def on_dataset_loaded(self) -> None:
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.preprocess_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.set_status_message(
            f'Loaded {len(self.state.filtered_df)} usable records from {len(self.state.selected_sessions)} session(s).'
        )

    def on_training_finished(self) -> None:
        self.export_page.refresh_from_state()
        self.set_status_message('Training finished.')

    def closeEvent(self, event) -> None:
        self.data_page.save_layout()
        self.preprocess_page.save_layout()
        self.train_page.save_layout()
        self.export_page.save_layout()
        self.train_page.shutdown_worker()
        super().closeEvent(event)
