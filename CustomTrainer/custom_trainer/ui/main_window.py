from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QDockWidget, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from custom_trainer.state import AppState
from custom_trainer.ui.pages.export_page import ExportPage
from custom_trainer.ui.pages.export_validate_page import ExportValidatePage
from custom_trainer.ui.pages.marking_page import MarkingPage
from custom_trainer.ui.pages.train_page import TrainPage
from custom_trainer.ui.pages.validate_page import ValidatePage
from custom_trainer.ui.widgets.log_panel import LogPanel


class CustomTrainerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('CustomTrainer 0_2_9')
        self.resize(1500, 920)
        self.setMinimumSize(960, 680)
        self._startup_geometry_applied = False
        self.state = AppState()

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabPosition(QTabWidget.North)

        self.marking_page = MarkingPage(self.state, self.log, self.set_status_message, self)
        self.train_page = TrainPage(self.state, self.log, self.set_status_message, self._open_validation_from_training, self)
        self.validate_page = ValidatePage(self.state, self.log, self.set_status_message, self)
        self.export_validate_page = ExportValidatePage(self.state, self.log, self.set_status_message, self)
        self.export_page = ExportPage(self.state, self.log, self.set_status_message, self)

        self.tabs.addTab(self.marking_page, 'Marking')
        self.tabs.addTab(self.train_page, 'Training')
        self.tabs.addTab(self.validate_page, 'Validation')
        self.tabs.addTab(self.export_validate_page, 'Export Validate')
        self.tabs.addTab(self.export_page, 'Export')
        self.setCentralWidget(self.tabs)

        self.log_panel = LogPanel(self)
        self.log_dock = QDockWidget('Log Console', self)
        self.log_dock.setWidget(self.log_panel)
        self.log_dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.log_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.log_dock.setMinimumHeight(96)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

        self.status = QStatusBar(self)
        self.status.setSizeGripEnabled(True)
        self.setStatusBar(self.status)
        self.set_status_message('Ready')
        self._setup_shortcuts()
        self._schedule_startup_geometry_fix()
        QTimer.singleShot(0, self._restore_startup_state)

    def _schedule_startup_geometry_fix(self) -> None:
        QTimer.singleShot(0, self._apply_startup_geometry)

    def _apply_startup_geometry(self) -> None:
        if self._startup_geometry_applied:
            return
        self._startup_geometry_applied = True
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin_w = 80
        margin_h = 80
        target_width = max(960, min(1500, available.width() - margin_w))
        target_height = max(680, min(920, available.height() - margin_h))
        self.resize(target_width, target_height)
        self.move(
            available.x() + max(0, (available.width() - target_width) // 2),
            available.y() + max(0, (available.height() - target_height) // 2),
        )
        log_height = max(96, min(180, available.height() // 5))
        self.resizeDocks([self.log_dock], [log_height], Qt.Vertical)

    def _restore_startup_state(self) -> None:
        self.marking_page.restore_last_sessions_root(auto_scan=True)
        self.marking_page.restore_splitters()
        self.train_page.restore_splitters()
        self.validate_page.restore_splitters()
        self.export_validate_page.restore_splitters()
        self.export_page.restore_splitters()
        self.train_page.refresh_preview()
        self.validate_page.refresh_preview()
        self.export_validate_page.refresh_preview()

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

    def _open_validation_from_training(
        self,
        weights_path,
        source_path,
        dataset_yaml,
        auto_predict: bool,
    ) -> None:
        self.validate_page.prepare_prediction_from_training(
            weights_path=weights_path,
            source_path=source_path,
            dataset_yaml=dataset_yaml,
            auto_start=False,
        )
        self.tabs.setCurrentWidget(self.validate_page)
        if auto_predict:
            QTimer.singleShot(
                0,
                lambda: self.validate_page.prepare_prediction_from_training(
                    weights_path=weights_path,
                    source_path=source_path,
                    dataset_yaml=dataset_yaml,
                    auto_start=True,
                ),
            )

    def show_shortcuts(self) -> None:
        QMessageBox.information(
            self,
            'Shortcuts',
            '\n'.join(
                [
                    'Ctrl+1..Ctrl+5 -> Switch pages',
                    'Ctrl+Tab / Ctrl+Shift+Tab -> Next / previous page',
                    'Ctrl+S -> Save current labels on Marking page',
                    'PageUp / PageDown -> Previous / next image (extra shortcut)',
                    'Right-click box -> Select or drag box',
                    'Left-drag -> Create box',
                    'Arrow keys -> Move selected box',
                    'Shift + Arrow keys -> Move selected box faster',
                    'A / D -> Previous / next frame with auto-save',
                    'W / S -> Cycle class up / down (selected box or active class)',
                    'X -> Delete selected frame(s)',
                    'Delete -> Delete selected box',
                    'Ctrl + Click in frame list -> Multi-select frames',
                    'Validation prediction browser now lets you step through saved frames.',
                    'Export Validate adds a similar review flow for exported .tflite / .onnx models.',
                    'Marking page Quick Deploy is now a single button that runs on the current frame and loads predicted boxes into the main canvas.',
                ]
            ),
        )

    def closeEvent(self, event) -> None:
        self.marking_page.save_splitters()
        self.train_page.save_splitters()
        self.validate_page.save_splitters()
        self.export_validate_page.save_splitters()
        self.export_page.save_splitters()
        super().closeEvent(event)
