from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
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
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import ensure_dataset_yaml
from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.ultralytics_runner import build_train_command, runner_working_directory
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker
from custom_trainer.ui.widgets.dock_workspace import DockWorkspacePage
from custom_trainer.ui.widgets.line_plot_widget import LinePlotWidget


class TrainPage(DockWorkspacePage):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__('train_dock_layout', parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None
        self.current_run_dir: Path | None = None
        self.current_results_csv: Path | None = None
        self._last_plot_signature: tuple[str, int, int] | None = None
        self._metric_columns: list[str] = []

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
        self.stop_button = QPushButton('Stop Training', self)
        self.stop_button.setEnabled(False)
        self.preview_label = QLabel('No frame preview yet.', self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(320, 220)
        self.preview_label.setStyleSheet('background: #0d1118; border: 1px solid #263244;')
        self.preview_info = QLabel('Open Marking and select a frame to mirror a quick preview here.', self)
        self.preview_info.setWordWrap(True)
        self.preview_info.setProperty('role', 'muted')
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

        self._build()
        self._setup_shortcuts()
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
        reset_layout_button = QPushButton('Reset Panels', action_box)
        reset_layout_button.clicked.connect(self.reset_panel_layout)
        action_layout.addWidget(use_current_button)
        action_layout.addWidget(refresh_preview_button)
        action_layout.addWidget(refresh_devices_button)
        action_layout.addWidget(reset_layout_button)
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.stop_button)
        action_layout.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        preview_box = QGroupBox('Training Preview', self)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.preview_info)

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
            """1. Use Marking to load your sessions folder and label images.
2. Point this page to the dataset.yaml for your YOLO dataset.
3. Use Auto or CUDA:0 to train on GPU when your Python environment has CUDA-enabled PyTorch.
4. Use Stop Training to terminate a run cleanly from the GUI.
5. The Run Log shows the exact training command, working folder, and runtime output.
6. The Training Progress Plot reads results.csv live while training when Ultralytics writes it.
7. Drag panel title bars to snap them to an edge or merge them into tabs.
8. Validation and Export can auto-pick the latest best.pt after training."""
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info_text)

        self.set_central_panel(plot_box, title='Training Progress Plot')
        self.config_dock = self.create_dock('train_config_dock', 'Training Config', config_box, area=Qt.LeftDockWidgetArea)
        self.actions_dock = self.create_dock('train_actions_dock', 'Actions', action_box, area=Qt.LeftDockWidgetArea)
        self.status_dock = self.create_dock('train_status_dock', 'Status', status_box, area=Qt.LeftDockWidgetArea)
        self.preview_dock = self.create_dock('train_preview_dock', 'Training Preview', preview_box, area=Qt.RightDockWidgetArea)
        self.notes_dock = self.create_dock('train_notes_dock', 'Workflow Notes', info_box, area=Qt.RightDockWidgetArea)
        self.log_dock = self.create_dock('train_log_dock', 'Run Log', run_log_box, area=Qt.BottomDockWidgetArea)
        self.set_default_layout_builder(self._apply_default_layout)
        self._apply_default_layout()

    def _apply_default_layout(self) -> None:
        for dock in (self.config_dock, self.actions_dock, self.status_dock, self.preview_dock, self.notes_dock, self.log_dock):
            dock.show()
            dock.setFloating(False)
        self.workspace.addDockWidget(Qt.LeftDockWidgetArea, self.config_dock)
        self.workspace.splitDockWidget(self.config_dock, self.actions_dock, Qt.Vertical)
        self.workspace.splitDockWidget(self.actions_dock, self.status_dock, Qt.Vertical)
        self.workspace.addDockWidget(Qt.RightDockWidgetArea, self.preview_dock)
        self.workspace.splitDockWidget(self.preview_dock, self.notes_dock, Qt.Vertical)
        self.workspace.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.workspace.resizeDocks([self.config_dock, self.actions_dock, self.status_dock], [360, 180, 120], Qt.Vertical)
        self.workspace.resizeDocks([self.preview_dock, self.notes_dock], [360, 240], Qt.Vertical)

    def _setup_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ('Ctrl+Return', self.start_training),
            ('Ctrl+U', self.use_current_root_defaults),
            ('F5', self.refresh_preview),
            ('Escape', self.stop_training),
            ('Ctrl+Shift+0', self.reset_panel_layout),
        ]
        for sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)

    def shortcut_lines(self) -> list[str]:
        return [
            'Training: Ctrl+Enter start training',
            'Training: Esc stop training',
            'Training: Ctrl+U fill from current sessions root',
            'Training: F5 refresh preview',
            'Training: Ctrl+Shift+0 reset dock layout',
        ]

    def _path_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton('Browse', container)
        button.clicked.connect(handler)
        layout.addWidget(button)
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

    def refresh_preview(self) -> None:
        image_path = self.state.current_preview_image()
        session = self.state.current_session
        dataset_yaml = self.state.preferred_dataset_yaml()
        if image_path is None or not image_path.exists():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('No frame preview yet.')
            self.preview_info.setText(
                'Open Marking and select a frame to mirror a quick preview here.\n'
                f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}'
            )
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview unavailable for this file.')
        else:
            scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText('')
        session_name = session.name if session is not None else 'none'
        self.preview_info.setText(
            f'Session: {session_name}\n'
            f'Current frame: {image_path.name}\n'
            f'Dataset YAML: {dataset_yaml if dataset_yaml else "not set"}'
        )

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
        yaml_path = self._ensure_training_yaml()
        if yaml_path is None:
            QMessageBox.critical(
                self,
                'Missing dataset.yaml',
                'Choose dataset.yaml first, or load a valid sessions root so the app can generate one automatically.',
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
        self._launch(command, 'Training started...', cwd=runner_working_directory())
        self.plot_timer.start()

    def stop_training(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
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

    def _handle_worker_line(self, line: str) -> None:
        self._append_run_log(line)
        self.log(line)
        if line.startswith('[save-dir] '):
            save_dir = Path(line.removeprefix('[save-dir] ').strip())
            self.current_run_dir = save_dir
            self.current_results_csv = save_dir / 'results.csv'
            self.plot_status.setText(f'Using training output folder: {save_dir}')
        self._poll_training_progress()

    def _launch(self, command: list[str], status_message: str, *, cwd: Path) -> None:
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
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.plot_timer.stop()
        self._poll_training_progress()
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Training finished with exit code {exit_code}.')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_preview()

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
