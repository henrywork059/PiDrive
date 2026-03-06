from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget

from .app_state import AppState
from .pages.data_page import DataPage
from .pages.export_page import ExportPage
from .pages.train_page import TrainPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PiCar Trainer — PySide6 Desktop App")
        self.resize(1400, 900)
        self.state = AppState()

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabPosition(QTabWidget.North)

        self.data_page = DataPage(self.state, self)
        self.train_page = TrainPage(self.state, self)
        self.export_page = ExportPage(self.state, self)

        self.tabs.addTab(self.data_page, "Data")
        self.tabs.addTab(self.train_page, "Train")
        self.tabs.addTab(self.export_page, "Export")

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True)
        self.setStatusBar(self.status)
        self.set_status_message("Ready")

        self.data_page.refresh_sessions()
        self.train_page.refresh_from_state()
        self.export_page.refresh_from_state()

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    def on_dataset_loaded(self) -> None:
        self.train_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.set_status_message(
            f"Loaded {len(self.state.filtered_df)} usable records from {len(self.state.selected_sessions)} session(s)."
        )

    def on_training_finished(self) -> None:
        self.export_page.refresh_from_state()
        self.set_status_message("Training finished.")

    def closeEvent(self, event) -> None:  # noqa: N802
        self.train_page.shutdown_worker()
        super().closeEvent(event)
