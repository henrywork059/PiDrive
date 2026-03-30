from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
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
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import DatasetSummary, ensure_dataset_yaml, ensure_dataset_yaml_with_summary
from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.session_service import IMAGE_SUFFIXES, list_images, resolve_prediction_source
from custom_trainer.services.ui_state_service import get_splitter_state, set_splitter_state
from custom_trainer.services.ultralytics_runner import build_predict_command, build_train_command, runner_working_directory
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker
from custom_trainer.ui.widgets.line_plot_widget import LinePlotWidget


class TrainPage(QWidget):
    def __init__(
        self,
        state: AppState,
        log: Callable[[str], None],
        set_status: Callable[[str], None],
        open_validation_for_prediction: Callable[[Path | None, Path | None, Path | None, bool], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.open_validation_for_prediction = open_validation_for_prediction
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None
        self.current_task_kind = ''
        self.current_run_dir: Path | None = None
        self.current_results_csv: Path | None = None
        self._last_plot_signature: tuple[str, int, int] | None = None
        self._metric_columns: list[str] = []
        self.last_preview_source = ''
        self.last_prediction_summary: list[str] = []
        self.last_save_dir = ''
        self.predicted_frame_paths: list[Path] = []
        self.current_preview_index = -1

        self.model_edit = QLineEdit('yolov8n.pt', self)
        self.yaml_edit = QLineEdit(self)
        self.epochs_edit = QLineEdit('100', self)
        self.imgsz_edit = QLineEdit('640', self)
        self.batch_edit = QLineEdit('16', self)
        self.device_combo = QComboBox(self)
        self.device_combo.setEditable(True)
        self.device_summary = QLabel('Detecting runtime...', self)
        self.device_summary.setProperty('role', 'muted')
        self.device_summary.setWordWrap(True)
        self.project_edit = QLineEdit('runs', self)
        self.name_edit = QLineEdit('customtrainer_train', self)
        self.status_note = QLabel('Idle', self)
        self.status_note.setProperty('role', 'muted')
        self.start_button = QPushButton('Start Training', self)
        self.stop_button = QPushButton('Stop Task', self)
        self.stop_button.setEnabled(False)
        self.deploy_weights_edit = QLineEdit(self)
        self.deploy_source_edit = QLineEdit(self)
        self.deploy_status = QLabel('No deploy model or frame source selected yet.', self)
        self.deploy_status.setProperty('role', 'muted')
        self.deploy_status.setWordWrap(True)
        self.preview_label = QLabel('No frame preview yet.', self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(360, 220)
        self.preview_label.setStyleSheet('background: #0d1118; border: 1px solid #263244;')
        self.preview_info = QLabel('Open Marking and select a frame to mirror a quick preview here.', self)
        self.preview_info.setWordWrap(True)
        self.preview_info.setProperty('role', 'muted')
        self.frame_selector = QComboBox(self)
        self.frame_selector.currentIndexChanged.connect(self._on_frame_selected)
        self.frame_status = QLabel('No deploy preview frames yet.', self)
        self.frame_status.setProperty('role', 'muted')
        self.run_log_output = QPlainTextEdit(self)
        self.run_log_output.setReadOnly(True)
        self.run_log_output.setPlaceholderText('Training command and runtime log will appear here...')
        self.metric_combo = QComboBox(self)
        self.metric_combo.currentIndexChanged.connect(self._refresh_plot_from_current_csv)
        self.plot_status = QLabel('No training results.csv loaded yet.', self)
        self.plot_status.setProperty('role', 'muted')
        self.plot_status.setWordWrap(True)
        self.plot_widget = LinePlotWidget(self)
        self.plot_widget.clear()
        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(1500)
        self.plot_timer.timeout.connect(self._poll_training_progress)

        self.start_button.clicked.connect(self.start_training)
        self.stop_button.clicked.connect(self.stop_training)
        self.deploy_source_edit.textChanged.connect(self._reset_prediction_preview)

        self._build()
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()

    def _build(self) -> None:
        config_box = QGroupBox('Training Config', self)
        form = QFormLayout(config_box)
        form.addRow('Model (.pt / preset)', self._path_row(self.model_edit, self.choose_model))
        form.addRow('dataset.yaml', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Epochs', self.epochs_edit)
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Batch', self.batch_edit)
        form.addRow('Device', self._device_row())
        form.addRow('', self.device_summary)
        form.addRow('Runs Project Dir', self.project_edit)
        form.addRow('Run Name', self.name_edit)

        action_box = QGroupBox('Actions', self)
        action_layout = QHBoxLayout(action_box)
        use_current_button = QPushButton('Use Current Sessions Root', action_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        refresh_preview_button = QPushButton('Refresh Preview', action_box)
        refresh_preview_button.clicked.connect(self.refresh_preview)
        refresh_devices_button = QPushButton('Refresh Devices', action_box)
        refresh_devices_button.clicked.connect(lambda: self.refresh_devices(log_runtime=True))
        action_layout.addWidget(use_current_button)
        action_layout.addWidget(refresh_preview_button)
        action_layout.addWidget(refresh_devices_button)
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.stop_button)
        action_layout.addStretch(1)

        deploy_box = QGroupBox('Quick Deploy To Frames', self)
        deploy_form = QFormLayout(deploy_box)
        deploy_form.addRow('Trained Weights (.pt)', self._path_row(self.deploy_weights_edit, self.choose_deploy_weights))
        deploy_form.addRow('Frame Source', self._deploy_source_row())
        deploy_actions = QWidget(deploy_box)
        deploy_actions_layout = QHBoxLayout(deploy_actions)
        deploy_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.latest_deploy_button = QPushButton('Use Latest best.pt', deploy_actions)
        self.latest_deploy_button.clicked.connect(self.use_latest_best_weights_for_deploy)
        self.current_frames_button = QPushButton('Use Current Session Frames', deploy_actions)
        self.current_frames_button.clicked.connect(self.use_current_frames_for_deploy)
        self.deploy_predict_button = QPushButton('Quick Predict Here', deploy_actions)
        self.deploy_predict_button.clicked.connect(self.predict_model_on_frames)
        deploy_actions_layout.addWidget(self.latest_deploy_button)
        deploy_actions_layout.addWidget(self.current_frames_button)
        deploy_actions_layout.addWidget(self.deploy_predict_button)
        deploy_form.addRow('', deploy_actions)
        deploy_form.addRow('', self.deploy_status)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        preview_box = QGroupBox('Training Preview', self)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.preview_info)
        preview_browser = QWidget(preview_box)
        preview_browser_layout = QHBoxLayout(preview_browser)
        preview_browser_layout.setContentsMargins(0, 0, 0, 0)
        prev_frame_button = QPushButton('Prev Result', preview_browser)
        prev_frame_button.clicked.connect(self.prev_frame)
        next_frame_button = QPushButton('Next Result', preview_browser)
        next_frame_button.clicked.connect(self.next_frame)
        preview_browser_layout.addWidget(prev_frame_button)
        preview_browser_layout.addWidget(next_frame_button)
        preview_browser_layout.addWidget(self.frame_selector, 1)
        preview_layout.addWidget(preview_browser)
        preview_layout.addWidget(self.frame_status)

        plot_box = QGroupBox('Training Progress Plot', self)
        plot_layout = QVBoxLayout(plot_box)
        plot_controls = QHBoxLayout()
        plot_controls.addWidget(QLabel('Metric', plot_box))
        plot_controls.addWidget(self.metric_combo, 1)
        refresh_plot_button = QPushButton('Refresh Plot', plot_box)
        refresh_plot_button.clicked.connect(self._poll_training_progress)
        clear_plot_button = QPushButton('Clear Plot', plot_box)
        clear_plot_button.clicked.connect(lambda: self._reset_training_plot('Training plot cleared.'))
        plot_controls.addWidget(refresh_plot_button)
        plot_controls.addWidget(clear_plot_button)
        plot_layout.addLayout(plot_controls)
        plot_layout.addWidget(self.plot_widget, 1)
        plot_layout.addWidget(self.plot_status)

        run_log_box = QGroupBox('Run Log', self)
        run_log_layout = QVBoxLayout(run_log_box)
        run_log_actions = QHBoxLayout()
        clear_log_button = QPushButton('Clear Log', run_log_box)
        clear_log_button.clicked.connect(self.run_log_output.clear)
        run_log_actions.addStretch(1)
        run_log_actions.addWidget(clear_log_button)
        run_log_layout.addLayout(run_log_actions)
        run_log_layout.addWidget(self.run_log_output, 1)

        info_box = QGroupBox('Workflow Notes', self)
        info_text = QPlainTextEdit(self)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            '1. Use Marking to load your sessions folder and label images.\n'
            '2. Point this page to the dataset.yaml for your YOLO dataset.\n'
            '3. Use Auto or CUDA:0 to train on GPU when your Python environment has CUDA-enabled PyTorch.\n'
            '4. Use Stop Training to terminate a run cleanly from the GUI.\n'
            '5. The Run Log shows the exact training command, working folder, and runtime output.\n'
            '6. The Training Progress Plot reads results.csv live while training when Ultralytics writes it.\n'
            '7. Quick deploy has moved to the Marking tab for fast frame checks with the current session.\n'
            '8. Validation and Export can still auto-pick the latest best.pt after training.'
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info_text)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(config_box)
        left_layout.addWidget(action_box)
        left_layout.addWidget(status_box)
        left_layout.addStretch(1)

        self.monitor_splitter = QSplitter(Qt.Vertical, self)
        self.monitor_splitter.addWidget(plot_box)
        self.monitor_splitter.addWidget(run_log_box)
        self.monitor_splitter.setStretchFactor(0, 3)
        self.monitor_splitter.setStretchFactor(1, 2)
        self.monitor_splitter.setSizes([420, 280])

        self.side_splitter = QSplitter(Qt.Vertical, self)
        self.side_splitter.addWidget(preview_box)
        self.side_splitter.addWidget(info_box)
        self.side_splitter.setStretchFactor(0, 2)
        self.side_splitter.setStretchFactor(1, 1)
        self.side_splitter.setSizes([360, 220])

        self.main_splitter = QSplitter(Qt.Horizontal, self)
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(self.monitor_splitter)
        self.main_splitter.addWidget(self.side_splitter)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 4)
        self.main_splitter.setStretchFactor(2, 2)
        self.main_splitter.setSizes([360, 760, 360])

        root = QVBoxLayout(self)
        root.addWidget(self.main_splitter, 1)

    def restore_splitters(self) -> None:
        for name, splitter in (
            ('train_main_splitter', self.main_splitter),
            ('train_monitor_splitter', self.monitor_splitter),
            ('train_side_splitter', self.side_splitter),
        ):
            sizes = get_splitter_state(name)
            if sizes:
                splitter.setSizes(sizes)

    def save_splitters(self) -> None:
        for name, splitter in (
            ('train_main_splitter', self.main_splitter),
            ('train_monitor_splitter', self.monitor_splitter),
            ('train_side_splitter', self.side_splitter),
        ):
            set_splitter_state(name, splitter.sizes())

    def _path_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton('Browse', container)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def _deploy_source_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.deploy_source_edit, 1)
        file_button = QPushButton('File', container)
        file_button.clicked.connect(self.choose_deploy_source_file)
        folder_button = QPushButton('Folder', container)
        folder_button.clicked.connect(self.choose_deploy_source_folder)
        layout.addWidget(file_button)
        layout.addWidget(folder_button)
        return container

    def _device_row(self) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.device_combo, 1)
        return container

    def _append_run_log(self, message: str) -> None:
        self.run_log_output.appendPlainText(message)

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
            message = f'[device] {probe.summary}'
            self._append_run_log(message)
            self.log(message)
            self.set_status('Device list refreshed.')

    def current_device_value(self) -> str:
        current_index = self.device_combo.currentIndex()
        if current_index >= 0:
            data = self.device_combo.itemData(current_index)
            if isinstance(data, str) and data.strip():
                return data.strip()
        return self.device_combo.currentText().strip() or 'auto'

    def choose_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose model weights', filter='PyTorch Weights (*.pt);;All Files (*)')
        if path:
            self.model_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose dataset.yaml', filter='YAML (*.yaml *.yml)')
        if path:
            self.yaml_edit.setText(path)

    def choose_deploy_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose trained weights', filter='PyTorch Weights (*.pt);;All Files (*)')
        if path:
            self.deploy_weights_edit.setText(path)
            self._update_deploy_status('Loaded deploy weights.')

    def choose_deploy_source_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Choose deploy source image/video',
            filter='Media (*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi);;All Files (*)',
        )
        if path:
            self.deploy_source_edit.setText(path)
            self._update_deploy_status('Loaded deploy source file.')

    def choose_deploy_source_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose deploy source folder')
        if path:
            self.deploy_source_edit.setText(path)
            self._update_deploy_status('Loaded deploy source folder.')

    def _default_deploy_source(self) -> Path | None:
        if self.state.current_session is not None:
            return self.state.current_session.image_root
        if self.state.current_image_path is not None:
            return self.state.current_image_path
        if self.state.sessions_root is not None:
            return self.state.sessions_root
        return None

    def _update_deploy_status(self, message: str | None = None) -> None:
        weights_text = self.deploy_weights_edit.text().strip() or 'not set'
        source_text = self.deploy_source_edit.text().strip() or 'not set'
        prefix = f'{message} ' if message else ''
        self.deploy_status.setText(f'{prefix}Weights: {weights_text}\nSource: {source_text}')

    def use_latest_best_weights_for_deploy(self) -> None:
        best = self.state.latest_best_weights()
        if best is None:
            QMessageBox.information(self, 'No best.pt found', 'Train a model first, then try again.')
            return
        self.deploy_weights_edit.setText(str(best))
        self._update_deploy_status('Loaded latest best.pt for deploy.')

    def use_current_frames_for_deploy(self) -> None:
        source = self._default_deploy_source()
        if source is None:
            QMessageBox.information(self, 'No current frames', 'Open a session or select a frame in Marking first.')
            return
        self.deploy_source_edit.setText(str(source))
        self._update_deploy_status('Loaded current frame source for deploy.')

    def _deploy_weights_path(self) -> Path | None:
        raw = self.deploy_weights_edit.text().strip()
        if raw:
            path = Path(raw).expanduser()
            return path if path.exists() else None
        best = self.state.latest_best_weights()
        if best is not None:
            self.deploy_weights_edit.setText(str(best))
            return best
        return None

    def _deploy_source_path(self) -> Path | None:
        raw = self.deploy_source_edit.text().strip()
        if raw:
            path = Path(raw).expanduser()
            return path if path.exists() else None
        source = self._default_deploy_source()
        if source is not None:
            self.deploy_source_edit.setText(str(source))
            return source
        return None

    def predict_model_on_frames(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'A training or quick deploy task is already running.')
            return
        weights_path = self._deploy_weights_path()
        if weights_path is None:
            QMessageBox.critical(self, 'Missing trained weights', 'Choose a trained .pt file first, or train a model and use the latest best.pt.')
            return
        source_path = self._deploy_source_path()
        if source_path is None:
            QMessageBox.critical(self, 'Missing frame source', 'Choose a frame or folder source first.')
            return
        try:
            imgsz = int(self.imgsz_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid image size', 'Image size must be an integer.')
            return
        if not source_path.exists():
            QMessageBox.critical(self, 'Missing frame source', f'The selected frame source does not exist:\n{source_path}')
            return
        resolved_source_path, source_note = resolve_prediction_source(source_path)
        project_dir, run_name = self._deploy_output_args('predict')
        self.last_preview_source = str(source_path)
        self.predicted_frame_paths = []
        self.current_preview_index = -1
        self.last_prediction_summary = []
        self.last_save_dir = ''
        self._refresh_frame_selector()
        if source_note:
            self.last_prediction_summary.append(source_note)
        command = build_predict_command(
            weights=str(weights_path),
            source=str(resolved_source_path),
            imgsz=imgsz,
            conf=0.25,
            device=self.current_device_value(),
            project=project_dir,
            name=run_name,
            show_labels=True,
            show_conf=True,
            show_boxes=True,
        )
        self._launch(command, 'Quick deploy prediction started...', cwd=runner_working_directory(), task_kind='deploy_predict')
        self.refresh_preview()

    def use_current_root_defaults(self) -> None:
        dataset_yaml = self.state.preferred_dataset_yaml()
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
        if self.state.sessions_root is not None:
            self.project_edit.setText(str(self.state.sessions_root / 'runs'))
        self.name_edit.setText(f'train_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()
        self.set_status('Training defaults filled from the current sessions root.')

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
        current_source = self.deploy_source_edit.text().strip()
        if current_source != self.last_preview_source:
            self.predicted_frame_paths = []
            self.current_preview_index = -1
            self.last_prediction_summary = []
            self.last_save_dir = ''
            self._refresh_frame_selector()
            self.refresh_preview()

    def _refresh_frame_selector(self) -> None:
        self.frame_selector.blockSignals(True)
        self.frame_selector.clear()
        for path in self.predicted_frame_paths:
            self.frame_selector.addItem(path.name)
        if 0 <= self.current_preview_index < len(self.predicted_frame_paths):
            self.frame_selector.setCurrentIndex(self.current_preview_index)
            self.frame_status.setText(f'Quick deploy results: {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}')
        elif self.predicted_frame_paths:
            self.current_preview_index = 0
            self.frame_selector.setCurrentIndex(0)
            self.frame_status.setText(f'Quick deploy results: 1/{len(self.predicted_frame_paths)}')
        else:
            self.current_preview_index = -1
            self.frame_status.setText('No deploy preview frames yet.')
        self.frame_selector.blockSignals(False)

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
                if current.exists() and current.parent == directory:
                    return current
            except ValueError:
                pass
        files = list_images(directory)
        return files[0] if files else None

    def refresh_preview(self) -> None:
        dataset_yaml = self.state.preferred_dataset_yaml()
        deploy_source_text = self.deploy_source_edit.text().strip()
        deploy_weights_text = self.deploy_weights_edit.text().strip() or 'not set'
        prediction_frame = self._current_predicted_frame()
        if deploy_source_text:
            source_path = Path(deploy_source_text)
            if not source_path.exists():
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText('Deploy source not found.')
                self.preview_info.setText(
                    f'Deploy source path does not exist:\n{deploy_source_text}\n'
                    f'Weights: {deploy_weights_text}'
                )
                self.frame_status.setText('No deploy preview frames yet.')
                return
            resolved_source_path, source_note = resolve_prediction_source(source_path)
            if prediction_frame is not None:
                self._render_pixmap(prediction_frame, 'Predicted frame preview unavailable.')
                info_lines = [
                    f'Quick deploy source: {source_path}',
                    f'Showing result {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}',
                    f'Weights: {deploy_weights_text}',
                    f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}',
                ]
                if source_note:
                    info_lines.append(f'Resolved source: {resolved_source_path}')
                if self.last_prediction_summary:
                    info_lines.extend(self.last_prediction_summary[:6])
                if self.last_save_dir:
                    info_lines.append(f'Saved to: {self.last_save_dir}')
                self.preview_info.setText('\n'.join(info_lines))
                self.frame_status.setText(f'Quick deploy results: {self.current_preview_index + 1}/{len(self.predicted_frame_paths)}')
                return
            preview_source = resolved_source_path if resolved_source_path.exists() else source_path
            raw_image_path: Path | None = None
            if preview_source.is_dir():
                raw_image_path = self._find_first_image_in_dir(preview_source)
            elif preview_source.suffix.lower() in IMAGE_SUFFIXES:
                raw_image_path = preview_source
            if raw_image_path is not None:
                self._render_pixmap(raw_image_path, 'Preview unavailable for this file.')
            else:
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText('Preview unavailable for non-image sources.')
            info_lines = [
                f'Quick deploy source: {source_path}',
                f'Weights: {deploy_weights_text}',
                f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}',
                'Run Quick Predict Here to render detections without leaving the Training tab.',
            ]
            if source_note:
                info_lines.append(f'Resolved source: {resolved_source_path}')
            self.preview_info.setText('\n'.join(info_lines))
            self.frame_status.setText('No deploy preview frames yet.')
            return

        image_path = self.state.current_preview_image()
        session = self.state.current_session
        if image_path is None or not image_path.exists():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('No frame preview yet.')
            self.preview_info.setText(
                'Open Marking and select a frame to mirror a quick preview here.\n'
                f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}'
            )
            self.frame_status.setText('No deploy preview frames yet.')
            return
        self._render_pixmap(image_path, 'Preview unavailable for this file.')
        session_name = session.name if session is not None else 'none'
        self.preview_info.setText(
            f'Session: {session_name}\n'
            f'Current frame: {image_path.name}\n'
            f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}'
        )
        self.frame_status.setText('No deploy preview frames yet.')

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_preview()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible():
            self.refresh_preview()

    def _ensure_training_yaml(self) -> Path | None:
        yaml_text = self.yaml_edit.text().strip()
        yaml_path = Path(yaml_text).expanduser() if yaml_text else None
        if yaml_path is not None and yaml_path.exists() and yaml_path.is_file():
            return yaml_path
        ensured_path, _created = ensure_dataset_yaml(self.state.sessions_root, self.state.class_names)
        if ensured_path is not None and ensured_path.exists() and ensured_path.is_file():
            self.yaml_edit.setText(str(ensured_path))
            return ensured_path
        return None

    def _prepare_training_dataset(self) -> tuple[Path | None, DatasetSummary | None]:
        if self.state.sessions_root is not None:
            ensured_path, _created, summary = ensure_dataset_yaml_with_summary(
                self.state.sessions_root,
                self.state.class_names,
                overwrite=True,
            )
            if ensured_path is not None and ensured_path.exists() and ensured_path.is_file():
                self.yaml_edit.setText(str(ensured_path))
                return ensured_path, summary
        yaml_path = self._ensure_training_yaml()
        return yaml_path, None

    def _reset_training_plot(self, message: str) -> None:
        self.current_run_dir = None
        self.current_results_csv = None
        self._last_plot_signature = None
        self._metric_columns = []
        self.metric_combo.blockSignals(True)
        self.metric_combo.clear()
        self.metric_combo.blockSignals(False)
        self.plot_widget.clear(message)
        self.plot_status.setText(message)

    def start_training(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Training running', 'A training process is already running.')
            return
        yaml_path, dataset_summary = self._prepare_training_dataset()
        if yaml_path is None:
            QMessageBox.critical(
                self,
                'Missing dataset.yaml',
                'Choose dataset.yaml first, or load a valid sessions root so the app can generate one automatically.',
            )
            return
        if dataset_summary is not None:
            self.log(f'[dataset] {dataset_summary.describe()}')
            if dataset_summary.migrated_labels:
                self.log(f'[dataset] Migrated {dataset_summary.migrated_labels} legacy label file(s) into canonical YOLO paths.')
            if dataset_summary.total_images <= 0:
                QMessageBox.critical(self, 'No images found', 'No images were found under the current sessions root.')
                return
            if not dataset_summary.has_usable_labels:
                QMessageBox.critical(
                    self,
                    'No usable labels found',
                    'The current sessions root does not contain any usable YOLO boxes for training.\n\n'
                    f'{dataset_summary.describe()}\n\n'
                    'Save at least one valid bounding box and try again.',
                )
                return
        try:
            epochs = int(self.epochs_edit.text())
            imgsz = int(self.imgsz_edit.text())
            batch = int(self.batch_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid numbers', 'Epochs, image size, and batch must be integers.')
            return
        model_text = self.model_edit.text().strip() or 'yolov8n.pt'
        if any(sep in model_text for sep in ('/', '\\')) and not Path(model_text).expanduser().exists():
            QMessageBox.critical(self, 'Model not found', f'The selected model path does not exist:\n{model_text}')
            return
        project_dir = self.project_edit.text().strip() or str(self.state.preferred_runs_dir())
        self.project_edit.setText(project_dir)
        run_name = self.name_edit.text().strip() or f'train_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.name_edit.setText(run_name)
        command = build_train_command(
            model=model_text,
            data=str(yaml_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=self.current_device_value(),
            project=project_dir,
            name=run_name,
        )
        expected_run_dir = Path(project_dir).expanduser() / run_name
        expected_results_csv = expected_run_dir / 'results.csv'
        self._reset_training_plot(f'Waiting for training metrics in {expected_results_csv}')
        self.current_run_dir = expected_run_dir
        self.current_results_csv = expected_results_csv
        self.plot_status.setText(f'Waiting for training metrics in {expected_run_dir}')
        self._launch(command, 'Training started...', cwd=runner_working_directory(), task_kind='train')
        self.plot_timer.start()

    def stop_training(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
        if self.current_task_kind == 'deploy_predict':
            self.status_note.setText('Stopping quick deploy prediction...')
            self.set_status('Stopping quick deploy prediction...')
        else:
            self.status_note.setText('Stopping training...')
            self.set_status('Stopping training...')

    def _find_results_csv(self) -> Path | None:
        candidates: list[Path] = []
        if self.current_results_csv is not None:
            candidates.append(self.current_results_csv)
        if self.current_run_dir is not None:
            candidates.append(self.current_run_dir / 'results.csv')
        project_text = self.project_edit.text().strip()
        run_name = self.name_edit.text().strip()
        if project_text:
            project_dir = Path(project_text).expanduser()
            if run_name:
                candidates.extend(sorted(project_dir.glob(f'{run_name}*/results.csv')))
            candidates.extend(sorted(project_dir.rglob('results.csv'))[-4:])
        seen: set[str] = set()
        for candidate in candidates:
            key = candidate.as_posix().lower()
            if key in seen:
                continue
            seen.add(key)
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _parse_results_csv(self, path: Path) -> tuple[list[float], dict[str, list[float]]]:
        rows = list(csv.DictReader(path.open('r', encoding='utf-8-sig', newline='')))
        if not rows:
            return [], {}
        x_values: list[float] = []
        series: dict[str, list[float]] = {}
        numeric_columns: list[str] = []
        for column in rows[0].keys():
            if column is None:
                continue
            name = column.strip()
            if not name or name == 'epoch':
                continue
            numeric_columns.append(name)
            series[name] = []
        for index, row in enumerate(rows):
            epoch_text = str(row.get('epoch', '')).strip()
            try:
                x_values.append(float(epoch_text) + 1.0)
            except Exception:
                x_values.append(float(index + 1))
            for column in list(series.keys()):
                raw = str(row.get(column, '')).strip()
                try:
                    series[column].append(float(raw))
                except Exception:
                    series[column].append(float('nan'))
        valid_series = {name: values for name, values in series.items() if any(value == value for value in values)}
        return x_values, valid_series

    def _preferred_metric_columns(self, series: dict[str, list[float]]) -> list[str]:
        preferred = [
            'metrics/mAP50(B)',
            'metrics/mAP50-95(B)',
            'metrics/precision(B)',
            'metrics/recall(B)',
            'train/box_loss',
            'train/cls_loss',
            'train/dfl_loss',
            'val/box_loss',
            'val/cls_loss',
            'val/dfl_loss',
            'lr/pg0',
        ]
        ordered = [name for name in preferred if name in series]
        for name in sorted(series):
            if name not in ordered:
                ordered.append(name)
        return ordered

    def _refresh_plot_from_current_csv(self) -> None:
        path = self._find_results_csv()
        if path is None:
            return
        self._load_plot_from_csv(path)

    def _load_plot_from_csv(self, path: Path) -> None:
        try:
            stat = path.stat()
            signature = (str(path), int(stat.st_mtime_ns), int(stat.st_size))
            x_values, series = self._parse_results_csv(path)
        except Exception as exc:
            self.plot_status.setText(f'Could not read training metrics: {exc}')
            return
        if not series or not x_values:
            self.plot_status.setText(f'Waiting for numeric metrics in {path}')
            return
        metric_columns = self._preferred_metric_columns(series)
        if metric_columns != self._metric_columns:
            current = self.metric_combo.currentText().strip()
            self.metric_combo.blockSignals(True)
            self.metric_combo.clear()
            self.metric_combo.addItems(metric_columns)
            default_metric = current if current in metric_columns else metric_columns[0]
            self.metric_combo.setCurrentText(default_metric)
            self.metric_combo.blockSignals(False)
            self._metric_columns = metric_columns
        metric_name = self.metric_combo.currentText().strip() or metric_columns[0]
        values = series.get(metric_name, [])
        if not values:
            return
        latest_value = next((value for value in reversed(values) if value == value), None)
        summary = f'File: {path.name} | Points: {len(values)}'
        if latest_value is not None:
            summary += f' | Latest {metric_name}={latest_value:.4f}'
        self.plot_widget.set_series(
            title='Training Progress',
            metric_name=metric_name,
            x_values=x_values,
            y_values=values,
            summary=summary,
        )
        self.plot_status.setText(f'Live metrics loaded from {path}')
        self._last_plot_signature = signature
        self.current_results_csv = path
        self.current_run_dir = path.parent

    def _poll_training_progress(self) -> None:
        path = self._find_results_csv()
        if path is None:
            if self.current_run_dir is not None:
                self.plot_status.setText(f'Waiting for results.csv in {self.current_run_dir}')
            return
        try:
            stat = path.stat()
            signature = (str(path), int(stat.st_mtime_ns), int(stat.st_size))
        except Exception:
            return
        if signature == self._last_plot_signature:
            return
        self._load_plot_from_csv(path)

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
        files = [path for path in sorted(save_dir.iterdir()) if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES]
        if not files:
            return
        self.predicted_frame_paths = files
        if self.current_preview_index < 0:
            self.current_preview_index = 0
        elif self.current_preview_index >= len(files):
            self.current_preview_index = len(files) - 1
        self._refresh_frame_selector()

    def _deploy_output_args(self, prefix: str) -> tuple[str, str]:
        project_dir = self.state.preferred_runs_dir() / 'quick_predict'
        run_name = f'{prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        return str(project_dir), run_name

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
        if line.startswith('[save-dir] '):
            save_dir = Path(line.removeprefix('[save-dir] ').strip())
            self.last_save_dir = str(save_dir)
            if self.current_task_kind == 'train':
                self.current_run_dir = save_dir
                self.current_results_csv = save_dir / 'results.csv'
                self.plot_status.setText(f'Using training output folder: {save_dir}')
            self.refresh_preview()
        if self.current_task_kind == 'train':
            self._poll_training_progress()

    def _set_busy_state(self, busy: bool) -> None:
        self.start_button.setEnabled(not busy)
        self.deploy_predict_button.setEnabled(not busy)
        self.latest_deploy_button.setEnabled(not busy)
        self.current_frames_button.setEnabled(not busy)
        self.stop_button.setEnabled(busy)

    def _launch(self, command: list[str], status_message: str, *, cwd: Path, task_kind: str) -> None:
        self.run_log_output.clear()
        self._append_run_log(f'[cwd] {cwd}')
        self.thread = QThread(self)
        self.worker = CommandWorker(command, cwd=cwd)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self._handle_worker_line)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.current_task_kind = task_kind
        self._set_busy_state(True)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        if self.current_task_kind == 'train':
            self.plot_timer.stop()
            self._poll_training_progress()
            message = f'Training finished with exit code {exit_code}.'
        elif self.current_task_kind == 'deploy_predict':
            self._load_saved_prediction_frames()
            if exit_code == 0:
                message = f'Quick deploy finished. {len(self.predicted_frame_paths)} result frame(s) available in Training.'
                self._update_deploy_status('Quick deploy results are ready in the Training preview.')
            else:
                message = f'Quick deploy finished with exit code {exit_code}.'
        else:
            message = f'Finished with exit code {exit_code}.'
        self.status_note.setText(message)
        self.set_status(message)
        self._set_busy_state(False)
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
