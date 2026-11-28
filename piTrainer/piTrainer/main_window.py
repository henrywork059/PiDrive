from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QPushButton, QStatusBar, QStyle, QTabWidget, QHBoxLayout, QVBoxLayout, QWidget

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
from .ui.theme import current_theme, saved_theme, save_theme
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
        for config in (self.validation_page.config_panel, self.export_validation_page.config_panel):
            config.dataset_source_combo.currentTextChanged.connect(self.refresh_workflow_readiness)
        self.validation_page.config_panel.model_source_combo.currentTextChanged.connect(self.refresh_workflow_readiness)
        self.validation_page.config_panel.model_path_edit.textChanged.connect(self.refresh_workflow_readiness)
        self.export_validation_page.config_panel.tflite_path_edit.textChanged.connect(self.refresh_workflow_readiness)

        # Navigation only: never executes work or modifies selected inputs.
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        guidance = QHBoxLayout()
        guidance.setContentsMargins(8, 4, 8, 0)
        self.workflow_detail_label = QLabel()
        self.workflow_detail_label.setTextFormat(Qt.PlainText)
        self.workflow_detail_label.setWordWrap(True)
        self.workflow_detail_label.setObjectName('workflowReadinessLabel')
        guidance.addWidget(self.workflow_detail_label, 1)
        self.workflow_prerequisite_button = QPushButton()
        self.workflow_prerequisite_button.hide()
        self._workflow_prerequisite_index = None
        self.workflow_prerequisite_button.clicked.connect(self._open_workflow_prerequisite)
        guidance.addWidget(self.workflow_prerequisite_button)
        self.workflow_locate_button = QPushButton('Find action')
        self.workflow_locate_button.setObjectName('workflowLocateAction')
        self.workflow_locate_button.setProperty('role', 'secondary')
        self.workflow_locate_button.setMaximumWidth(140)
        self.workflow_locate_button.clicked.connect(self._locate_workflow_action)
        guidance.addWidget(self.workflow_locate_button)
        layout.addLayout(guidance)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(workspace)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(True)
        self.version_label = QLabel(STATUS_VERSION_TEXT)
        self.version_label.setObjectName('appVersionLabel')
        self.version_label.setProperty('role', 'muted')
        # The active stage's readiness remains readable without a tooltip or color cue.
        self.workflow_readiness_label = QLabel('Checking workflow')
        self.workflow_readiness_label.setObjectName('workflowReadinessLabel')
        self.workflow_readiness_label.setAccessibleName('Current workflow readiness')
        self.status.addPermanentWidget(self.workflow_readiness_label)
        self.status.addPermanentWidget(self._make_shortcuts_button())
        self.status.addPermanentWidget(self.version_label)
        self.setStatusBar(self.status)
        self._setup_appearance_menu()
        self._setup_workspace_menu()
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
        self.refresh_workflow_readiness()

    def _setup_workspace_menu(self) -> None:
        self.workspace_menu = self.menuBar().addMenu('Workspace')
        self.workspace_menu.aboutToShow.connect(self._refresh_workspace_menu)

    def _refresh_workspace_menu(self) -> None:
        menu = self.workspace_menu
        menu.clear()
        page = self.current_dock_page()
        titles = getattr(page, 'workspace_panel_titles', lambda: ())()
        self._workspace_panel_actions = []
        for index, title in enumerate(titles):
            action = menu.addAction('Focus ' + title)
            action.triggered.connect(lambda checked=False, i=index: self._focus_workspace_panel(i))
            self._workspace_panel_actions.append(action)
        if titles:
            menu.addSeparator()
        next_panel = menu.addAction('Next panel')
        next_panel.setEnabled(bool(titles))
        next_panel.triggered.connect(lambda checked=False: self._cycle_workspace_panel(1))
        previous_panel = menu.addAction('Previous panel')
        previous_panel.setEnabled(bool(titles))
        previous_panel.triggered.connect(lambda checked=False: self._cycle_workspace_panel(-1))

    def _focus_workspace_panel(self, index: int) -> None:
        page = self.current_dock_page()
        focus = getattr(page, 'focus_workspace_panel', None)
        if callable(focus):
            focus(index)

    def _cycle_workspace_panel(self, direction: int) -> None:
        page = self.current_dock_page()
        cycle = getattr(page, 'cycle_workspace_panel', None)
        if callable(cycle):
            cycle(direction)

    def _setup_appearance_menu(self) -> None:
        menu = self.menuBar().addMenu("Appearance")
        group = QActionGroup(self)
        group.setExclusive(True)
        self._appearance_actions = {}
        for value, label in (("dark", "Obsidian & Blue"), ("light", "Light")):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value == saved_theme())
            group.addAction(action)
            self._appearance_actions[value] = action
            action.triggered.connect(lambda checked, name=value: self._choose_appearance(name) if checked else None)
        self._appearance_group = group
        menu.addSeparator()
        note = menu.addAction("Applies on next launch")
        note.setEnabled(False)

    def _choose_appearance(self, name: str) -> None:
        if not save_theme(name):
            self._appearance_actions[saved_theme()].setChecked(True)
            QMessageBox.warning(self, "Appearance", "Could not save the theme preference.")
            return
        if name != current_theme():
            self.statusBar().showMessage("Theme saved. Restart piTrainer when convenient to apply it.", 12000)
        else:
            self.statusBar().showMessage("Theme preference saved.", 5000)

    def refresh_workflow_readiness(self, *_args) -> None:
        """Show confirmed local milestones separately from input readiness and historical results."""
        if not hasattr(self, 'tabs') or self.tabs.count() != 6:
            return
        state = self.state
        active = not state.filtered_df.empty
        model = state.model is not None
        def dataset_available(config):
            name = config.dataset_source()
            frame = (state.val_df if name == 'Validation split' else
                     state.train_df if name == 'Training split' else state.filtered_df)
            return not frame.empty
        def real_file(value, suffixes):
            if not value:
                return False
            try:
                path = Path(value).expanduser()
                return path.suffix.lower() in suffixes and path.is_file()
            except (OSError, ValueError):
                return False
        validation = self.validation_page.config_panel
        check = self.export_validation_page.config_panel
        validation_model = (model if validation.model_source() == 'Current trained model'
                            else real_file(validation.model_path(), {'.keras', '.h5'}))
        check_ready = real_file(check.tflite_path(), {'.tflite'}) and dataset_available(check)
        statuses = (
            (active, 'Active rows available' if active else 'Load usable recording rows'),
            (active, 'Active rows available for preprocessing' if active else 'Load usable recording rows'),
            (active, 'Active rows available; split/training still requires preflight' if active else 'Load usable recording rows'),
            (validation_model and dataset_available(validation), 'Model selection and dataset available; validation not implied' if validation_model and dataset_available(validation) else 'Choose a model source and populated dataset'),
            (model, 'In-memory model available' if model else 'Train a model first'),
            (check_ready, 'Existing TFLite file and dataset available; file validity not implied' if check_ready else 'Choose an existing TFLite file and populated dataset'),
        )
        # Results are historical evidence, not certification of current selections.
        history = {
            3: getattr(self.validation_page, 'last_result', None),
            5: getattr(self.export_validation_page, 'last_result', None),
        }
        preprocess = getattr(self, 'preprocess_page', None)
        export = getattr(self, 'export_page', None)
        completed = {
            0: 'Usable recording rows loaded' if active else '',
            1: 'Preprocessing applied to active rows' if active and getattr(preprocess, '_preprocess_applied', False) else '',
            2: 'A trained model is held in memory; no deployment implied' if model else '',
            4: 'Export files confirmed for this model; inference not implied'
               if model and export is not None and export.has_confirmed_export_for(state.model) else '',
        }
        for index, (ready, detail) in enumerate(statuses):
            if history.get(index):
                detail += '; previous result available (may refer to different inputs)'
            if completed.get(index):
                prefix, detail, symbol = 'Done — ', completed[index], QStyle.SP_DialogApplyButton
            elif ready:
                prefix, symbol = 'Inputs available — ', QStyle.SP_ArrowRight
            else:
                prefix, symbol = 'Needs input — ', QStyle.SP_MessageBoxInformation
            self.tabs.setTabIcon(index, self.style().standardIcon(symbol))
            message = prefix + detail
            if self.tabs.tabToolTip(index) != message:
                self.tabs.setTabToolTip(index, message)
            accessible_name = self.tabs.tabText(index) + ' — ' + message
            bar = self.tabs.tabBar()
            if bar.accessibleTabName(index) != accessible_name:
                bar.setAccessibleTabName(index, accessible_name)
            label = getattr(self, 'workflow_readiness_label', None)
            if label is not None and index == self.tabs.currentIndex():
                short_text = prefix.rstrip(' —')
                if label.text() != short_text:
                    label.setText(short_text)
                if label.toolTip() != message:
                    label.setToolTip(message)
                if label.accessibleName() != accessible_name:
                    label.setAccessibleName(accessible_name)

        # Route to a missing prerequisite without starting or changing work.
        index = self.tabs.currentIndex()
        target = None
        if index in (1, 2) and not active:
            target = 0
        elif index in (3, 5):
            config = validation if index == 3 else check
            if not dataset_available(config):
                target = 2 if active and config.dataset_source() in ('Validation split', 'Training split') else 0
            elif index == 3 and not validation_model and validation.model_source() == 'Current trained model':
                target = 2
            elif index == 5 and not check_ready and model:
                target = 4
        elif index == 4 and not model:
            target = 2
        if hasattr(self, 'workflow_detail_label'):
            message = self.tabs.tabToolTip(index)
            if self.workflow_detail_label.text() != message:
                self.workflow_detail_label.setText(message)
            self._workflow_prerequisite_index = target
            button = self.workflow_prerequisite_button
            if target is not None:
                caption = 'Open ' + self.tabs.tabText(target).split(' ', 1)[1]
                if button.text() != caption:
                    button.setText(caption)
            button.setVisible(target is not None)
        if hasattr(self, 'workflow_locate_button'):
            page = self.tabs.currentWidget()
            label = getattr(page, 'workspace_action_label', '')
            locate = self.workflow_locate_button
            locate.setVisible(bool(label))
            locate.setAccessibleName('Find ' + label)
            locate.setToolTip('Locate ' + label + ' without running it.')

    def _locate_workflow_action(self) -> None:
        page = self.tabs.currentWidget()
        locate = getattr(page, 'locate_primary_action', None)
        if callable(locate):
            locate()

    def _open_workflow_prerequisite(self) -> None:
        self.refresh_workflow_readiness()
        target = self._workflow_prerequisite_index
        if target is not None:
            self.tabs.setCurrentIndex(target)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._apply_responsive_density()

    def _apply_responsive_density(self) -> None:
        width = max(1, int(self.width()))
        density = density_for_width(width, height=self.height())
        if density == self._ui_density:
            apply_standard_widget_format(self, density=density)
            return
        self._ui_density = density
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(density))
        apply_standard_widget_format(self, density=density)
        # The global stylesheet was just replaced. Keep the explicit Session
        # Source geometry rather than inheriting the generic input minimum.
        if hasattr(self, 'data_page'):
            self.data_page.session_source_panel.refresh_session_list_geometry()

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
        self.refresh_workflow_readiness()
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

    def _make_shortcuts_button(self) -> QPushButton:
        button = QPushButton('Shortcuts (F1)')
        button.setProperty('role', 'secondary')
        button.setAccessibleName('Keyboard shortcuts for current page')
        button.setToolTip('Show keyboard shortcuts for the current workspace (F1).')
        button.clicked.connect(self.show_shortcuts)
        return button

    def show_shortcuts(self) -> None:
        context = (
            ['F5 → Refresh sessions', 'Ctrl+L → Load selected sessions',
             'Ctrl+A / Ctrl+Shift+A → Select / clear sessions',
             'Delete → Hide selected frames after Confirm Hide is ticked',
             'Up / Down in frame table or preview → Previous / next frame',
             'Playback → Play / Stop / Restart below the image',
             'Ctrl+Z, D (or Ctrl+Z, Ctrl+D) → Permanent purge of hidden frames; explicit confirmation required'],
            ['Use Auto Preprocess or Settings; no dedicated execution shortcut.'],
            ['Ctrl+P → Prepare split', 'Ctrl+R → Start training', 'Esc → Stop training'],
            ['Up / Down in frame table → Previous / next frame', 'Edit in Data → Open source frame'],
            ['Ctrl+E → Export model'],
            ['Ctrl+Shift+E → Run TFLite Check', 'Edit in Data → Open source frame'],
        )
        index = max(0, min(self.tabs.currentIndex(), len(context)-1))
        lines = [self.tabs.tabText(index), *context[index], '', 'Global navigation',
                 'Ctrl+1..Ctrl+6 → Switch pages', 'Ctrl+Tab / Ctrl+Shift+Tab → Next / previous page',
                 'Ctrl+Shift+R → Reset current page layout', 'F1 → Open this help']
        QMessageBox.information(self, 'Shortcuts', chr(10).join(lines))

    def set_status_message(self, message: str) -> None:
        self.status.showMessage(message, 5000)
        self.refresh_workflow_readiness()

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

    def can_start_task(self, requester) -> bool:
        for label, page in (
            ('Preprocess', self.preprocess_page), ('Train', self.train_page),
            ('Validate', self.validation_page), ('Export', self.export_page),
            ('TFLite Check', self.export_validation_page),
        ):
            if page is not requester and page.has_active_task():
                self.set_status_message(f'{label} is still running. Finish it before starting another background operation.')
                return False
        return True

    def closeEvent(self, event) -> None:
        active = [page for page in (
            self.preprocess_page, self.train_page, self.validation_page,
            self.export_page, self.export_validation_page,
        ) if page.has_active_task()]
        if active:
            if self.train_page in active:
                self.train_page.stop_training()
            self.set_status_message('An operation is still finishing; close after it completes to avoid incomplete output.')
            event.ignore()
            return
        # Closing the last window can stop a queued 450ms label-edit timer.
        # Commit before closing; on failure leave the editor and data intact.
        try:
            edits_saved = self.data_page.image_preview_panel._flush_pending_commit()
        except Exception as exc:
            self.set_status_message(f'Pending frame edits could not be saved: {exc}')
            event.ignore()
            return
        if not edits_saved:
            self.set_status_message('Pending frame edits were not saved. Resolve the error before closing.')
            event.ignore()
            return
        self.data_page.save_layout()
        self.preprocess_page.save_layout()
        self.train_page.save_layout()
        self.validation_page.save_layout()
        self.export_page.save_layout()
        self.export_validation_page.save_layout()
        self.train_page.shutdown_worker()
        super().closeEvent(event)
