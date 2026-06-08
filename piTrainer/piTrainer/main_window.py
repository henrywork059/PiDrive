from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QStatusBar, QTabWidget

from .app_state import AppState
from .pages.data_page import DataPage
from .pages.export_page import ExportPage
from .pages.export_validation_page import ExportValidationPage
from .pages.preprocess_page import PreprocessPage
from .pages.train_page import TrainPage
from .pages.validation_page import ValidationPage
from .services.data.session_service import resolve_session_dir
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
        self.export_validation_page = ExportValidationPage(self.state, self)

        self.tabs.addTab(self.data_page, '1 Data')
        self.tabs.addTab(self.preprocess_page, '2 Preprocess')
        self.tabs.addTab(self.train_page, '3 Train')
        self.tabs.addTab(self.validation_page, '4 Validate')
        self.tabs.addTab(self.export_page, '5 Export')
        self.tabs.addTab(self.export_validation_page, '6 TFLite Check')
        self.tabs.setTabToolTip(0, 'Load sessions, review frames, and manage labels.')
        self.tabs.setTabToolTip(1, 'Filter, balance, resize, and preview data.')
        self.tabs.setTabToolTip(2, 'Split data, train, and review progress.')
        self.tabs.setTabToolTip(3, 'Validate a model and inspect errors.')
        self.tabs.setTabToolTip(4, 'Export model files for deployment.')
        self.tabs.setTabToolTip(5, 'Check the exported TFLite model.')
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True)
        self.version_label = QLabel(STATUS_VERSION_TEXT)
        self.version_label.setObjectName('appVersionLabel')
        self.version_label.setProperty('role', 'muted')
        self.status.addPermanentWidget(self.version_label)
        self.setStatusBar(self.status)
        self.set_status_message(
            f'Ready — {STATUS_VERSION_TEXT}. Follow the green buttons from 1 Data to 6 TFLite Check. Drag splitters to resize panels.'
        )
        self._apply_responsive_density()

        self._setup_shortcuts()
        self.data_page.refresh_sessions()
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.export_validation_page.refresh_from_state()


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
        QShortcut(QKeySequence('Ctrl+6'), self, activated=lambda: self.tabs.setCurrentIndex(5))
        QShortcut(QKeySequence('Ctrl+Tab'), self, activated=self.next_tab)
        QShortcut(QKeySequence('Ctrl+Shift+Tab'), self, activated=self.previous_tab)
        QShortcut(QKeySequence('F5'), self, activated=self.data_page.refresh_sessions)
        QShortcut(QKeySequence('Ctrl+L'), self, activated=self.data_page.load_selected_sessions)
        QShortcut(QKeySequence('Ctrl+A'), self, activated=self.data_page.session_list_panel.select_all)
        QShortcut(QKeySequence('Ctrl+Shift+A'), self, activated=self.data_page.session_list_panel.clear_all)
        QShortcut(QKeySequence('Delete'), self.data_page, activated=self.data_page.delete_selected_frame)
        QShortcut(QKeySequence('Ctrl+Z, D'), self.data_page, activated=self.data_page.purge_hidden_frames_shortcut)
        QShortcut(QKeySequence('Ctrl+Z, Ctrl+D'), self.data_page, activated=self.data_page.purge_hidden_frames_shortcut)
        QShortcut(QKeySequence('Ctrl+P'), self, activated=self.train_page.prepare_split)
        QShortcut(QKeySequence('Ctrl+R'), self, activated=self.train_page.start_training)
        QShortcut(QKeySequence('Escape'), self, activated=self.train_page.stop_training)
        QShortcut(QKeySequence('Ctrl+E'), self, activated=self.export_page.export_model)
        QShortcut(QKeySequence('Ctrl+Shift+E'), self, activated=self.export_validation_page.validate_export)
        QShortcut(QKeySequence('Ctrl+Shift+R'), self, activated=self.reset_current_page_layout)
        QShortcut(QKeySequence('F1'), self, activated=self.show_shortcuts)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        frame_review = getattr(widget, 'frame_review_panel', None)
        if frame_review is not None and hasattr(frame_review, 'restore_pending_selection'):
            frame_review.restore_pending_selection()

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
            'Ctrl+1..Ctrl+6 -> Switch pages',
            'Ctrl+Tab / Ctrl+Shift+Tab -> Next / previous page',
            'F5 -> Refresh sessions',
            'Ctrl+L -> Load selected sessions',
            'Ctrl+A -> Select all sessions',
            'Ctrl+Shift+A -> Clear selected sessions',
            'Delete -> Hide selected frames after Confirm Hide is ticked',
            'Ctrl+P -> Prepare split',
            'Ctrl+R -> Start training',
            'Esc -> Stop training',
            'Ctrl+E -> Export model',
            'Ctrl+Shift+E -> Run TFLite Check',
            'Ctrl+Shift+R -> Reset current page layout',
            'F1 -> Open this shortcut list',
        ]
        QMessageBox.information(self, 'Shortcuts', chr(10).join(lines))

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)

    def _records_root_is_session_dir(self) -> bool:
        root = self.state.records_root_path
        if not root.exists() or not root.is_dir():
            return False
        has_frames = (root / 'frames').is_dir()
        has_images = (root / 'images').is_dir()
        has_labels = (root / 'labels.jsonl').exists() and has_frames
        has_records = (root / 'records.jsonl').exists() and (has_frames or has_images)
        return bool(has_labels or has_records)

    def _loaded_session_working_dir(self) -> Path | None:
        """Return the save/output folder that should follow the selected data.

        For the normal single-session workflow, preprocessing outputs, saved
        trained models, and exported artifacts should all write back into the
        selected/loaded session folder. If the user intentionally selects
        multiple sessions, use the selected records root as a safe common folder.
        If the records root itself is a direct session folder, use that folder
        even before the synthetic `.` session row has been loaded.
        """

        selected = [str(session).strip() for session in self.state.selected_sessions if str(session).strip()]
        if len(selected) == 1:
            return resolve_session_dir(self.state.records_root_path, selected[0])
        if selected:
            return self.state.records_root_path
        if self._records_root_is_session_dir():
            return self.state.records_root_path
        return None

    def sync_working_folder_from_loaded_sessions(self, *, show_status: bool = True) -> None:
        working_dir = self._loaded_session_working_dir()
        if working_dir is None:
            return
        working_dir = working_dir.expanduser().resolve()
        working_dir_text = str(working_dir)

        # Keep every default output location tied to the selected/loaded session
        # folder. Preprocess save/settings use state.out_dir_path, export uses
        # export_config.out_dir, and Train's manual Save Model control has its
        # own remembered line edit that also needs to be updated.
        self.state.export_config.out_dir = working_dir_text
        self.state.trained_model_out_dir = working_dir_text

        preprocess_page = getattr(self, 'preprocess_page', None)
        if preprocess_page is not None and hasattr(preprocess_page, 'on_working_folder_changed'):
            preprocess_page.on_working_folder_changed(working_dir, show_log=show_status)

        train_page = getattr(self, 'train_page', None)
        if train_page is not None and hasattr(train_page, 'set_model_save_dir'):
            train_page.set_model_save_dir(working_dir_text)

        export_page = getattr(self, 'export_page', None)
        if export_page is not None and hasattr(export_page, 'set_output_dir'):
            export_page.set_output_dir(working_dir_text)

        validation_page = getattr(self, 'validation_page', None)
        if validation_page is not None and hasattr(validation_page, 'refresh_from_state'):
            validation_page.refresh_from_state()

        export_validation_page = getattr(self, 'export_validation_page', None)
        if export_validation_page is not None and hasattr(export_validation_page, 'refresh_from_state'):
            export_validation_page.refresh_from_state()

        if show_status:
            self.set_status_message(f'Working folder set to loaded session: {working_dir_text}')

    def on_dataset_loaded(self) -> None:
        self.preprocess_page.refresh_from_state()
        self.train_page.refresh_from_state()
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.export_validation_page.refresh_from_state()
        self.set_status_message(
            f'Loaded {len(self.state.filtered_df)} usable records from {len(self.state.selected_sessions)} session(s). Next: 2 Preprocess or 3 Train.'
        )

    def on_training_finished(self) -> None:
        self.validation_page.refresh_from_state()
        self.export_page.refresh_from_state()
        self.export_validation_page.refresh_from_state()
        self.set_status_message('Training finished.')

    def on_data_records_edited(self, records: list[dict] | dict | None) -> None:
        if not records:
            return
        for page in (getattr(self, 'validation_page', None), getattr(self, 'export_validation_page', None)):
            frame_review = getattr(page, 'frame_review_panel', None)
            if frame_review is not None and hasattr(frame_review, 'mark_edited_records'):
                frame_review.mark_edited_records(records)

    def open_validation_frame_in_data_editor(self, record: dict | None) -> None:
        if not record:
            self.set_status_message('No validation frame selected to open in Data.')
            return
        self.tabs.setCurrentIndex(0)
        ok = self.data_page.focus_record(record)
        if ok:
            if getattr(self.data_page, 'last_focus_redirected_to_source', False):
                source_id = getattr(self.data_page, 'last_focus_source_frame_id', '')
                suffix = f" source frame '{source_id}'" if source_id else ' original source frame'
                self.set_status_message(f'Opened the generated validation row in Data by redirecting to{suffix}.')
            else:
                self.set_status_message('Opened the validation frame in the Data editor.')
        else:
            self.set_status_message('Could not open that validation frame in the Data editor.')

    def closeEvent(self, event) -> None:
        self.data_page.save_layout()
        self.preprocess_page.save_layout()
        self.train_page.save_layout()
        self.validation_page.save_layout()
        self.export_page.save_layout()
        self.export_validation_page.save_layout()
        self.train_page.shutdown_worker()
        super().closeEvent(event)
