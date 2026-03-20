from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.session_service import resolve_prediction_source
from custom_trainer.services.ultralytics_runner import build_predict_command, build_val_command, runner_working_directory
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker
from custom_trainer.ui.widgets.dock_workspace import DockWorkspacePage


_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


class ValidatePage(DockWorkspacePage):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__('validate_dock_layout', parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None
        self.current_task_kind = ''
        self.last_metrics_text = ''
        self.last_prediction_summary: list[str] = []
        self.last_preview_source = ''
        self.last_save_dir = ''
        self.current_preview_index = -1
        self.predicted_frame_paths: list[Path] = []

        self.weights_edit = QLineEdit(self)
        self.yaml_edit = QLineEdit(self)
        self.source_edit = QLineEdit(self)
        self.imgsz_edit = QLineEdit('640', self)
        self.conf_edit = QLineEdit('0.25', self)
        self.line_width_edit = QLineEdit('', self)
        self.font_size_edit = QLineEdit('', self)
        self.show_labels_check = QCheckBox('Show labels', self)
        self.show_labels_check.setChecked(True)
        self.show_conf_check = QCheckBox('Show confidence', self)
        self.show_conf_check.setChecked(True)
        self.show_boxes_check = QCheckBox('Show boxes', self)
        self.show_boxes_check.setChecked(True)
        self.device_combo = QComboBox(self)
        self.device_combo.setEditable(True)
        self.device_summary = QLabel('Detecting runtime...', self)
        self.device_summary.setProperty('role', 'muted')
        self.device_summary.setWordWrap(True)
        self.status_note = QLabel('Idle', self)
        self.status_note.setProperty('role', 'muted')
        self.val_button = QPushButton('Run Validation', self)
        self.predict_button = QPushButton('Run Prediction', self)
        self.stop_button = QPushButton('Stop Task', self)
        self.stop_button.setEnabled(False)
        self.preview_label = QLabel('No preview source selected.', self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(420, 260)
        self.preview_label.setStyleSheet('background: #0d1118; border: 1px solid #263244;')
        self.preview_info = QLabel('Prediction source preview will appear here.', self)
        self.preview_info.setWordWrap(True)
        self.preview_info.setProperty('role', 'muted')
        self.frame_selector = QComboBox(self)
        self.frame_selector.currentIndexChanged.connect(self._on_frame_selected)
        self.frame_status = QLabel('No predicted frames yet.', self)
        self.frame_status.setProperty('role', 'muted')
        self.run_log_output = QPlainTextEdit(self)
        self.run_log_output.setReadOnly(True)
        self.run_log_output.setPlaceholderText('Validation / prediction runtime log will appear here...')
        self.autoplay_button = QPushButton('Autoplay', self)
        self.autoplay_button.setCheckable(True)
        self.autoplay_button.toggled.connect(self._set_autoplay_running)
        self.autoplay_speed_spin = QSpinBox(self)
        self.autoplay_speed_spin.setRange(100, 5000)
        self.autoplay_speed_spin.setSingleStep(100)
        self.autoplay_speed_spin.setSuffix(' ms')
        self.autoplay_speed_spin.setValue(450)
        self.autoplay_speed_spin.valueChanged.connect(self._sync_autoplay_interval)
        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(self.autoplay_speed_spin.value())
        self.autoplay_timer.timeout.connect(self.next_frame)

        self.val_button.clicked.connect(self.start_val)
        self.predict_button.clicked.connect(self.start_predict)
        self.stop_button.clicked.connect(self.stop_task)
        self.source_edit.textChanged.connect(self._reset_prediction_preview)

        self._build()
        self._setup_shortcuts()
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()

    def _build(self) -> None:
        config_box = QGroupBox('Validation / Prediction Config', self)
        form = QFormLayout(config_box)
        form.addRow('Weights (.pt)', self._path_row(self.weights_edit, self.choose_weights))
        form.addRow('dataset.yaml', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Predict Source', self._source_row())
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Confidence', self.conf_edit)
        form.addRow('Device', self._device_row())
        form.addRow('', self.device_summary)

        overlay_box = QGroupBox('Prediction Overlay Settings', self)
        overlay_form = QFormLayout(overlay_box)
        overlay_form.addRow('Box line width', self.line_width_edit)
        overlay_form.addRow('Label text size', self.font_size_edit)
        toggles = QWidget(overlay_box)
        toggles_layout = QHBoxLayout(toggles)
        toggles_layout.setContentsMargins(0, 0, 0, 0)
        toggles_layout.addWidget(self.show_labels_check)
        toggles_layout.addWidget(self.show_conf_check)
        toggles_layout.addWidget(self.show_boxes_check)
        toggles_layout.addStretch(1)
        overlay_form.addRow('Output switches', toggles)

        actions_box = QGroupBox('Actions', self)
        actions = QHBoxLayout(actions_box)
        use_current_button = QPushButton('Use Current Session Frames', actions_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        latest_best_button = QPushButton('Use Latest best.pt', actions_box)
        latest_best_button.clicked.connect(self.use_latest_best_weights)
        refresh_preview_button = QPushButton('Refresh Preview', actions_box)
        refresh_preview_button.clicked.connect(self.refresh_preview)
        refresh_devices_button = QPushButton('Refresh Devices', actions_box)
        refresh_devices_button.clicked.connect(lambda: self.refresh_devices(log_runtime=True))
        reset_layout_button = QPushButton('Reset Panels', actions_box)
        reset_layout_button.clicked.connect(self.reset_panel_layout)
        actions.addWidget(use_current_button)
        actions.addWidget(latest_best_button)
        actions.addWidget(refresh_preview_button)
        actions.addWidget(refresh_devices_button)
        actions.addWidget(reset_layout_button)
        actions.addWidget(self.val_button)
        actions.addWidget(self.predict_button)
        actions.addWidget(self.stop_button)
        actions.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        preview_box = QGroupBox('Validation Frame Preview', self)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.preview_info)

        browser_box = QGroupBox('Predicted Frame Browser', self)
        browser_layout = QVBoxLayout(browser_box)
        browser_actions = QHBoxLayout()
        prev_frame_button = QPushButton('Prev Frame', browser_box)
        prev_frame_button.clicked.connect(self.prev_frame)
        next_frame_button = QPushButton('Next Frame', browser_box)
        next_frame_button.clicked.connect(self.next_frame)
        browser_actions.addWidget(prev_frame_button)
        browser_actions.addWidget(next_frame_button)
        browser_actions.addWidget(self.frame_selector, 1)
        browser_actions.addWidget(self.autoplay_button)
        browser_actions.addWidget(self.autoplay_speed_spin)
        browser_layout.addLayout(browser_actions)
        browser_layout.addWidget(self.frame_status)
        browser_hint = QLabel('Use Alt+Left / Alt+Right to cycle frames. Ctrl+Space toggles autoplay.', browser_box)
        browser_hint.setProperty('role', 'muted')
        browser_hint.setWordWrap(True)
        browser_layout.addWidget(browser_hint)

        run_log_box = QGroupBox('Run Log', self)
        run_log_layout = QVBoxLayout(run_log_box)
        run_log_actions = QHBoxLayout()
        clear_log_button = QPushButton('Clear Log', run_log_box)
        clear_log_button.clicked.connect(self.run_log_output.clear)
        run_log_actions.addStretch(1)
        run_log_actions.addWidget(clear_log_button)
        run_log_layout.addLayout(run_log_actions)
        run_log_layout.addWidget(self.run_log_output, 1)

        notes_box = QGroupBox('Validation Notes', self)
        notes_text = QPlainTextEdit(self)
        notes_text.setReadOnly(True)
        notes_text.setPlainText(
            """1. Use Current Session Frames to point prediction at the whole current images folder.
2. Run Prediction to save model-rendered outputs for every frame the source contains.
3. Use Prev/Next Frame, autoplay, or the drop-down to inspect model performance visually.
4. Overlay settings let you adjust box line width, label text size, and what annotations are shown.
5. Drag panel title bars to snap them to a side or merge them into tabs."""
        )
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.addWidget(notes_text)

        self.set_central_panel(preview_box, title='Validation Frame Preview')
        self.config_dock = self.create_dock('validate_config_dock', 'Validation / Prediction Config', config_box, area=Qt.LeftDockWidgetArea)
        self.overlay_dock = self.create_dock('validate_overlay_dock', 'Prediction Overlay Settings', overlay_box, area=Qt.LeftDockWidgetArea)
        self.actions_dock = self.create_dock('validate_actions_dock', 'Actions', actions_box, area=Qt.LeftDockWidgetArea)
        self.status_dock = self.create_dock('validate_status_dock', 'Status', status_box, area=Qt.LeftDockWidgetArea)
        self.browser_dock = self.create_dock('validate_browser_dock', 'Predicted Frame Browser', browser_box, area=Qt.BottomDockWidgetArea)
        self.log_dock = self.create_dock('validate_log_dock', 'Run Log', run_log_box, area=Qt.RightDockWidgetArea)
        self.notes_dock = self.create_dock('validate_notes_dock', 'Validation Notes', notes_box, area=Qt.RightDockWidgetArea)
        self.set_default_layout_builder(self._apply_default_layout)
        self._apply_default_layout()

    def _apply_default_layout(self) -> None:
        for dock in (
            self.config_dock,
            self.overlay_dock,
            self.actions_dock,
            self.status_dock,
            self.browser_dock,
            self.log_dock,
            self.notes_dock,
        ):
            dock.show()
            dock.setFloating(False)
        self.workspace.addDockWidget(Qt.LeftDockWidgetArea, self.config_dock)
        self.workspace.splitDockWidget(self.config_dock, self.overlay_dock, Qt.Vertical)
        self.workspace.splitDockWidget(self.overlay_dock, self.actions_dock, Qt.Vertical)
        self.workspace.splitDockWidget(self.actions_dock, self.status_dock, Qt.Vertical)
        self.workspace.addDockWidget(Qt.BottomDockWidgetArea, self.browser_dock)
        self.workspace.addDockWidget(Qt.RightDockWidgetArea, self.log_dock)
        self.workspace.splitDockWidget(self.log_dock, self.notes_dock, Qt.Vertical)
        self.workspace.resizeDocks([self.config_dock, self.overlay_dock, self.actions_dock, self.status_dock], [260, 220, 170, 100], Qt.Vertical)
        self.workspace.resizeDocks([self.log_dock, self.notes_dock], [360, 220], Qt.Vertical)

    def _setup_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ('Ctrl+Return', self.start_predict),
            ('Ctrl+Shift+Return', self.start_val),
            ('Alt+Left', self.prev_frame),
            ('Alt+Right', self.next_frame),
            ('Ctrl+Space', self.toggle_autoplay),
            ('Escape', self.stop_task),
            ('Ctrl+Shift+0', self.reset_panel_layout),
            ('F5', self.refresh_preview),
        ]
        for sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)

    def shortcut_lines(self) -> list[str]:
        return [
            'Validation: Ctrl+Enter run prediction',
            'Validation: Ctrl+Shift+Enter run validation',
            'Validation: Alt+Left / Alt+Right previous / next predicted frame',
            'Validation: Ctrl+Space toggle autoplay',
            'Validation: Esc stop active task',
            'Validation: Ctrl+Shift+0 reset dock layout',
        ]

    def _sync_autoplay_interval(self) -> None:
        self.autoplay_timer.setInterval(int(self.autoplay_speed_spin.value()))

    def _set_autoplay_running(self, enabled: bool) -> None:
        self._sync_autoplay_interval()
        has_frames = bool(self.predicted_frame_paths)
        if enabled and has_frames:
            self.autoplay_timer.start()
            self.autoplay_button.setText('Pause')
            self.set_status('Validation autoplay started.')
        else:
            self.autoplay_timer.stop()
            self.autoplay_button.blockSignals(True)
            self.autoplay_button.setChecked(False)
            self.autoplay_button.blockSignals(False)
            self.autoplay_button.setText('Autoplay')
            if enabled and not has_frames:
                self.set_status('No predicted frames available for autoplay.')

    def toggle_autoplay(self) -> None:
        self.autoplay_button.setChecked(not self.autoplay_button.isChecked())

    def _path_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton('Browse', container)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def _source_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.source_edit, 1)
        file_button = QPushButton('File', container)
        file_button.clicked.connect(self.choose_source_file)
        folder_button = QPushButton('Folder', container)
        folder_button.clicked.connect(self.choose_source_folder)
        layout.addWidget(file_button)
        layout.addWidget(folder_button)
        return container

    def _device_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.device_combo, 1)
        return container

    def _append_run_log(self, line: str) -> None:
        self.run_log_output.appendPlainText(line)

    def refresh_devices(self, *, log_runtime: bool) -> None:
        probe = probe_runtime()
        current = self.device_combo.currentText().strip()
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for label, value in probe.options:
            self.device_combo.addItem(label, value)
        target_value = current or probe.default_value
        index = next((i for i in range(self.device_combo.count()) if self.device_combo.itemData(i) == target_value), -1)
        if index >= 0:
            self.device_combo.setCurrentIndex(index)
        else:
            self.device_combo.setEditText(target_value)
        self.device_combo.blockSignals(False)
        self.device_summary.setText(probe.summary)
        if log_runtime:
            self._append_run_log(f'[device] {probe.summary}')
            self.log(f'[device] {probe.summary}')
            self.set_status('Device list refreshed.')

    def current_device_value(self) -> str:
        current_index = self.device_combo.currentIndex()
        if current_index >= 0:
            data = self.device_combo.itemData(current_index)
            if isinstance(data, str) and data.strip():
                return data.strip()
        return self.device_combo.currentText().strip() or 'auto'

    def choose_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose weights', filter='PyTorch Weights (*.pt);;All Files (*)')
        if path:
            self.weights_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose dataset.yaml', filter='YAML (*.yaml *.yml)')
        if path:
            self.yaml_edit.setText(path)

    def choose_source_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose source image/video',
            filter='Media (*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi);;All Files (*)',
        )
        if path:
            self.source_edit.setText(path)
            self.refresh_preview()

    def choose_source_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose source folder')
        if path:
            self.source_edit.setText(path)
            self.refresh_preview()

    def use_current_root_defaults(self) -> None:
        dataset_yaml = self.state.preferred_dataset_yaml()
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
        if self.state.current_session is not None:
            self.source_edit.setText(str(self.state.current_session.image_root))
        elif self.state.sessions_root is not None:
            self.source_edit.setText(str(self.state.sessions_root))
        elif self.state.current_image_path is not None:
            self.source_edit.setText(str(self.state.current_image_path))
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()
        self.set_status('Validation defaults filled from the current session frames.')

    def use_latest_best_weights(self) -> None:
        best = self.state.latest_best_weights()
        if best is None:
            QMessageBox.information(self, 'No best.pt found', 'Train a model first, then try again.')
            return
        self.weights_edit.setText(str(best))
        self.set_status('Loaded latest best.pt into Validation.')
        self.refresh_preview()

    def _current_source_text(self) -> str:
        source_text = self.source_edit.text().strip()
        if source_text:
            return source_text
        if self.state.current_session is not None:
            return str(self.state.current_session.image_root)
        current = self.state.current_image_path
        if current is not None:
            return str(current)
        return ''

    def _render_pixmap(self, image_path: Path, empty_text: str) -> bool:
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(empty_text)
            return False
        scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        self.preview_label.setText('')
        return True

    def _reset_prediction_preview(self) -> None:
        current_source = self.source_edit.text().strip()
        if current_source != self.last_preview_source:
            self.predicted_frame_paths = []
            self.current_preview_index = -1
            self.last_prediction_summary = []
            self.last_save_dir = ''
            self._set_autoplay_running(False)
            self._refresh_frame_selector()

    def _refresh_frame_selector(self) -> None:
        self.frame_selector.blockSignals(True)
        self.frame_selector.clear()
        for path in self.predicted_frame_paths:
            self.frame_selector.addItem(path.name)
        if 0 <= self.current_preview_index < len(self.predicted_frame_paths):
            self.frame_selector.setCurrentIndex(self.current_preview_index)
            self.frame_status.setText(f'Predicted frames: {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}')
        elif self.predicted_frame_paths:
            self.current_preview_index = 0
            self.frame_selector.setCurrentIndex(0)
            self.frame_status.setText(f'Predicted frames: 1/{len(self.predicted_frame_paths)}')
        else:
            self.current_preview_index = -1
            self.frame_status.setText('No predicted frames yet.')
            self._set_autoplay_running(False)
        self.frame_selector.blockSignals(False)
        self.autoplay_button.setEnabled(bool(self.predicted_frame_paths))

    def _current_predicted_frame(self) -> Path | None:
        if 0 <= self.current_preview_index < len(self.predicted_frame_paths):
            path = self.predicted_frame_paths[self.current_preview_index]
            if path.exists():
                return path
        return None

    def _find_first_image_in_dir(self, directory: Path) -> Path | None:
        current = self.state.current_image_path
        if current is not None:
            try:
                current.relative_to(directory)
                if current.exists():
                    return current
            except ValueError:
                pass
        for path in sorted(directory.rglob('*')):
            if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES:
                return path
        return None

    def refresh_preview(self) -> None:
        source_text = self._current_source_text()
        if not source_text:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('No preview source selected.')
            self.preview_info.setText('Pick an image or folder source, or use the current frame/session from Marking.')
            return
        source_path = Path(source_text)
        if not source_path.exists():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview source not found.')
            self.preview_info.setText(f'Source path does not exist:\n{source_text}')
            return

        resolved_source_path, source_note = resolve_prediction_source(source_path)

        prediction_frame = self._current_predicted_frame()
        if prediction_frame is not None:
            self._render_pixmap(prediction_frame, 'Predicted frame preview unavailable.')
            info_lines = [
                f'Source: {source_path}',
                f'Showing predicted frame {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}',
                f'Weights: {self.weights_edit.text().strip() or "not set"}',
                f'Dataset YAML: {self.yaml_edit.text().strip() or "not set"}',
            ]
            if source_note:
                info_lines.append(f'Resolved predict source: {resolved_source_path}')
            if self.last_metrics_text:
                info_lines.append(f'Latest validation: {self.last_metrics_text}')
            if self.last_prediction_summary:
                info_lines.extend(self.last_prediction_summary[:6])
            if self.last_save_dir:
                info_lines.append(f'Saved to: {self.last_save_dir}')
            self.preview_info.setText('\n'.join(info_lines))
            self.frame_status.setText(f'Predicted frames: {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}')
            return

        raw_image_path: Path | None = None
        preview_source_path = resolved_source_path if resolved_source_path.exists() else source_path
        if preview_source_path.is_dir():
            raw_image_path = self._find_first_image_in_dir(preview_source_path)
        elif preview_source_path.suffix.lower() in _IMAGE_SUFFIXES:
            raw_image_path = preview_source_path
        if raw_image_path is not None:
            self._render_pixmap(raw_image_path, 'Preview unavailable for this file.')
        else:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview unavailable for non-image sources.')

        info_lines = [
            f'Source: {source_path}',
            f'Weights: {self.weights_edit.text().strip() or "not set"}',
            f'Dataset YAML: {self.yaml_edit.text().strip() or "not set"}',
            'Raw source preview. Run Prediction to render boxed detections for all frames.',
        ]
        if source_note:
            info_lines.append(f'Resolved predict source: {resolved_source_path}')
        if preview_source_path.is_dir():
            info_lines.append('Directory source detected — prediction will iterate through the resolved folder contents.')
        self.preview_info.setText('\n'.join(info_lines))

    def _prediction_output_args(self, prefix: str) -> tuple[str, str]:
        project_dir = self.state.preferred_runs_dir() / 'detect'
        run_name = f'{prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        return str(project_dir), run_name

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_preview()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible():
            self.refresh_preview()

    def _parse_optional_int(self, value: str, label: str) -> int | None:
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            raise ValueError(f'{label} must be an integer when provided.')

    def start_val(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'Another validation or prediction task is already running.')
            return
        try:
            imgsz = int(self.imgsz_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid image size', 'Image size must be an integer.')
            return
        if not self.weights_edit.text().strip() or not self.yaml_edit.text().strip():
            QMessageBox.critical(self, 'Missing inputs', 'Choose weights and dataset.yaml first.')
            return
        project_dir, run_name = self._prediction_output_args('val')
        command = build_val_command(
            weights=self.weights_edit.text().strip(),
            data=self.yaml_edit.text().strip(),
            imgsz=imgsz,
            device=self.current_device_value(),
            project=project_dir,
            name=run_name,
        )
        self.current_task_kind = 'val'
        self.last_metrics_text = ''
        self._launch(command, 'Validation started...')

    def start_predict(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'Another validation or prediction task is already running.')
            return
        try:
            imgsz = int(self.imgsz_edit.text())
            conf = float(self.conf_edit.text())
            line_width = self._parse_optional_int(self.line_width_edit.text(), 'Box line width')
            font_size = self._parse_optional_int(self.font_size_edit.text(), 'Label text size')
        except ValueError as exc:
            QMessageBox.critical(self, 'Invalid values', str(exc))
            return
        source_text = self._current_source_text()
        if not self.weights_edit.text().strip() or not source_text:
            QMessageBox.critical(self, 'Missing inputs', 'Choose weights and a prediction source first.')
            return
        source_path = Path(source_text)
        if not source_path.exists():
            QMessageBox.critical(self, 'Missing source', f'The selected source does not exist:\n{source_path}')
            return
        resolved_source_path, source_note = resolve_prediction_source(source_path)
        project_dir, run_name = self._prediction_output_args('predict')
        self.last_preview_source = source_text
        self.predicted_frame_paths = []
        self.current_preview_index = -1
        self.last_prediction_summary = []
        self.last_save_dir = ''
        self._set_autoplay_running(False)
        self._refresh_frame_selector()
        if source_note:
            self.last_prediction_summary.append(source_note)
        command = build_predict_command(
            weights=self.weights_edit.text().strip(),
            source=str(resolved_source_path),
            imgsz=imgsz,
            conf=conf,
            device=self.current_device_value(),
            project=project_dir,
            name=run_name,
            line_width=line_width,
            font_size=font_size,
            show_labels=self.show_labels_check.isChecked(),
            show_conf=self.show_conf_check.isChecked(),
            show_boxes=self.show_boxes_check.isChecked(),
        )
        self.current_task_kind = 'predict'
        self._launch(command, 'Prediction started...')

    def stop_task(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
        self.status_note.setText('Stopping task...')
        self.set_status('Stopping validation/prediction task...')

    def _add_predicted_frame(self, path: Path) -> None:
        normalized = path.resolve() if path.exists() else path
        for index, existing in enumerate(self.predicted_frame_paths):
            existing_norm = existing.resolve() if existing.exists() else existing
            if existing_norm == normalized:
                self.current_preview_index = index
                self._refresh_frame_selector()
                return
        self.predicted_frame_paths.append(path)
        self.predicted_frame_paths.sort(key=lambda item: item.name.lower())
        target_name = path.name
        self.current_preview_index = next((i for i, item in enumerate(self.predicted_frame_paths) if item.name == target_name), 0)
        self._refresh_frame_selector()

    def _load_saved_prediction_frames(self) -> None:
        if not self.last_save_dir:
            return
        save_dir = Path(self.last_save_dir)
        if not save_dir.exists() or not save_dir.is_dir():
            return
        files = [path for path in sorted(save_dir.iterdir()) if path.is_file() and path.suffix.lower() in _IMAGE_SUFFIXES]
        if not files:
            return
        self.predicted_frame_paths = files
        if self.current_preview_index < 0:
            self.current_preview_index = 0
        elif self.current_preview_index >= len(files):
            self.current_preview_index = len(files) - 1
        self._refresh_frame_selector()

    def _handle_worker_line(self, line: str) -> None:
        self._append_run_log(line)
        self.log(line)
        if line.startswith('[preview-image] '):
            preview_path = Path(line.removeprefix('[preview-image] ').strip())
            self._add_predicted_frame(preview_path)
            self.refresh_preview()
            return
        if line.startswith('[predict] '):
            self.last_prediction_summary = [line.removeprefix('[predict] ').strip()]
            self.refresh_preview()
            return
        if line.startswith('[predict-box] '):
            self.last_prediction_summary.append(line.removeprefix('[predict-box] ').strip())
            self.refresh_preview()
            return
        if line.startswith('[metrics] '):
            self.last_metrics_text = line.removeprefix('[metrics] ').strip()
            self.refresh_preview()
            return
        if line.startswith('[save-dir] '):
            self.last_save_dir = line.removeprefix('[save-dir] ').strip()
            self.refresh_preview()

    def _launch(self, command: list[str], status_message: str) -> None:
        self.run_log_output.clear()
        self._append_run_log(f'[cwd] {runner_working_directory()}')
        self.thread = QThread(self)
        self.worker = CommandWorker(command, cwd=runner_working_directory())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self._handle_worker_line)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.val_button.setEnabled(False)
        self.predict_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.val_button.setEnabled(True)
        self.predict_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        if self.current_task_kind == 'predict' and exit_code == 0:
            self._load_saved_prediction_frames()
            message = f'Prediction finished. {len(self.predicted_frame_paths)} frame(s) available for review.'
        elif self.current_task_kind == 'val' and exit_code == 0 and self.last_metrics_text:
            message = f'Validation finished. {self.last_metrics_text}'
        else:
            message = f'Validation or prediction finished with exit code {exit_code}.'
        self.status_note.setText(message)
        self.set_status(message)
        if not self.predicted_frame_paths:
            self._set_autoplay_running(False)
        self.refresh_preview()

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
        self.current_task_kind = ''

    def _on_frame_selected(self, index: int) -> None:
        if 0 <= index < len(self.predicted_frame_paths):
            self.current_preview_index = index
            self.refresh_preview()

    def prev_frame(self) -> None:
        if not self.predicted_frame_paths:
            return
        self.current_preview_index = (self.current_preview_index - 1) % len(self.predicted_frame_paths)
        self._refresh_frame_selector()
        self.refresh_preview()

    def next_frame(self) -> None:
        if not self.predicted_frame_paths:
            return
        self.current_preview_index = (self.current_preview_index + 1) % len(self.predicted_frame_paths)
        self._refresh_frame_selector()
        self.refresh_preview()
