from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from .app_state import AppState
from .pages.data_page import DataPage
from .pages.export_page import ExportPage
from .pages.preprocess_page import PreprocessPage
from .pages.train_page import TrainPage
from .pages.validation_page import ValidationPage
from .ui.formatting import apply_standard_widget_format, density_for_width
from .ui.styles import build_stylesheet
from .version import APP_WORKFLOW_TITLE, STATUS_VERSION_TEXT


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_WORKFLOW_TITLE)
        self.resize(1440, 880)
        self.setMinimumSize(960, 620)
        self._ui_density = ''
        self.state = AppState()

        self.tabs = QTabWidget()
        self.tabs.setObjectName('mainWorkflowTabs')
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.setTabPosition(QTabWidget.North)

        self.data_page = DataPage(self.state, self)
        self.preprocess_page = PreprocessPage(self.state, self)
        self.train_page = TrainPage(self.state, self)
        self.validation_page = ValidationPage(self.state, self)
        self.export_page = ExportPage(self.state, self)

        self.tabs.addTab(self.data_page, '1 Data')
        self.tabs.addTab(self.preprocess_page, '2 Preprocess')
        self.tabs.addTab(self.train_page, '3 Train')
        self.tabs.addTab(self.validation_page, '4 Validate')
        self.tabs.addTab(self.export_page, '5 Export')
        self.tabs.setTabToolTip(0, 'Load PiSD/piTrainer sessions and review frames with overlays.')
        self.tabs.setTabToolTip(1, 'Filter, balance, resize, and preview the active dataset.')
        self.tabs.setTabToolTip(2, 'Prepare the split, configure training, and review training progress.')
        self.tabs.setTabToolTip(3, 'Validate a trained or saved model and inspect best/worst frames.')
        self.tabs.setTabToolTip(4, 'Export the trained model and deployment artifacts.')

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True)
        self.version_label = QLabel(STATUS_VERSION_TEXT)
        self.version_label.setObjectName('appVersionLabel')
        self.version_label.setProperty('role', 'muted')
        self.status.addPermanentWidget(self.version_label)
        self.setStatusBar(self.status)
        self.set_status_message(
            f'Ready — {STATUS_VERSION_TEXT}. Follow the green action buttons from 1 Data through 5 Export. Drag splitter handles to adjust panel proportions.'
        )
        self._apply_responsive_density()

        self._setup_shortcuts()
        self.data_page.refresh_sessions()
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()


    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._apply_responsive_density()

    def _apply_responsive_density(self) -> None:
        width = max(1, int(self.width()))
        density = density_for_width(width)
        if density == self._ui_density:
            apply_standard_widget_format(self, density=density)
            return
        self._ui_density = density
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(density))
        apply_standard_widget_format(self, density=density)

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence('Ctrl+1'), self, activated=lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence('Ctrl+2'), self, activated=lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence('Ctrl+3'), self, activated=lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence('Ctrl+4'), self, activated=lambda: self.tabs.setCurrentIndex(3))
        QShortcut(QKeySequence('Ctrl+5'), self, activated=lambda: self.tabs.setCurrentIndex(4))
        QShortcut(QKeySequence('Ctrl+Tab'), self, activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Shift+Tab'), self, activated=self.previous_tab)
        QShortcut(QKeySequence('F5'), self, activated=self.data_page.refresh_sessions)
        QShortcut(QKeySequence('Ctrl+L'), self, activated=self.data_page.load_selected_sessions)
        QShortcut(QKeySequence('Ctrl+A'), self, activated=self.data_page.session_list_panel.select_all)
        QShortcut(QKeySequence('Ctrl+Shift+A'), self, activated=self.data_page.session_list_panel.clear_all)
        QShortcut(QKeySequence('Delete'), self.data_page, activated=self.data_page.delete_selected_frame)
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
            'Ctrl+1 / Ctrl+2 / Ctrl+3 / Ctrl+4 / Ctrl+5 -> Switch to 1 Data / 2 Preprocess / 3 Train / 4 Validate / 5 Export',
            'Ctrl+Tab / Ctrl+Shift+Tab -> Next / Previous page',
            'F5 -> Refresh sessions',
            'Ctrl+L -> Load selected sessions',
            'Ctrl+A -> Select all sessions',
            'Ctrl+Shift+A -> Clear selected sessions',
            'Delete -> Hide selected frame row(s) from training after the Data Control checkbox is ticked',
            'Ctrl+P -> Prepare split',
            'Ctrl+R -> Start training',
            'Esc -> Stop training',
            'Ctrl+E -> Export model',
            'Ctrl+Shift+R -> Reset current page layout',
            'F1 -> Open this shortcut list',
        ]
        QMessageBox.information(self, 'Shortcuts', chr(10).join(lines))

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    def on_dataset_loaded(self) -> None:
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.set_status_message(
            f'Loaded {len(self.state.filtered_df)} usable records from {len(self.state.selected_sessions)} session(s). Next: open 2 Preprocess or 3 Train.'
        )

    def on_training_finished(self) -> None:
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.set_status_message('Training finished.')

    def open_validation_frame_in_data_editor(self, record: dict | None) -> None:
        if not record:
            self.set_status_message('No validation frame selected to open in Data.')
            return
        self.tabs.setCurrentIndex(0)
        ok = self.data_page.focus_record(record)
        if ok:
            self.set_status_message('Opened the validation frame in the Data editor.')
        else:
            self.set_status_message('Could not open that validation frame in the Data editor.')

    def closeEvent(self, event) -> None:
        self.data_page.save_layout()
        self.preprocess_page.save_layout()
        self.train_page.save_layout()
        self.validation_page.save_layout()
        self.export_page.save_layout()
        self.train_page.shutdown_worker()
        super().closeEvent(event)
