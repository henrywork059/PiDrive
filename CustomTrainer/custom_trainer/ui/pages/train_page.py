from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Qt
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import ensure_dataset_yaml
from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.ultralytics_runner import build_train_command, runner_working_directory
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker


class TrainPage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None

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
        self.preview_label.setMinimumSize(360, 240)
        self.preview_label.setStyleSheet('background: #0d1118; border: 1px solid #263244;')
        self.preview_info = QLabel('Open Marking and select a frame to mirror a quick preview here.', self)
        self.preview_info.setWordWrap(True)
        self.preview_info.setProperty('role', 'muted')
        self.run_log_output = QPlainTextEdit(self)
        self.run_log_output.setReadOnly(True)
        self.run_log_output.setPlaceholderText('Training command and runtime log will appear here...')

        self.start_button.clicked.connect(self.start_training)
        self.stop_button.clicked.connect(self.stop_training)

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

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        preview_box = QGroupBox('Training Preview', self)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview_label, 1)
        preview_layout.addWidget(self.preview_info)

        run_log_box = QGroupBox('Run Log', self)
        run_log_layout = QVBoxLayout(run_log_box)
        run_log_actions = QHBoxLayout()
        clear_log_button = QPushButton('Clear Log', run_log_box)
        clear_log_button.clicked.connect(self.run_log_output.clear)
        run_log_actions.addStretch(1)
        run_log_actions.addWidget(clear_log_button)
        run_log_layout.addLayout(run_log_actions)
        run_log_layout.addWidget(self.run_log_output, 1)

        monitor_tabs = QTabWidget(self)
        monitor_tabs.setDocumentMode(True)
        monitor_tabs.addTab(preview_box, 'Preview')
        monitor_tabs.addTab(run_log_box, 'Run Log')

        info_box = QGroupBox('Workflow Notes', self)
        info_text = QPlainTextEdit(self)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            '1. Use Marking to load your sessions folder and label images.\n'
            '2. Point this page to the dataset.yaml for your YOLO dataset.\n'
            '3. Use Auto or CUDA:0 to train on GPU when your Python environment has CUDA-enabled PyTorch.\n'
            '4. Use Stop Training to terminate a run cleanly from the GUI.\n'
            '5. The Run Log tab shows the exact training command, working folder, and runtime output.\n'
            '6. If dataset.yaml is missing but a sessions root is loaded, the app will try to create one automatically.\n'
            '7. After training, Validation and Export can auto-pick the latest best.pt.'
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info_text)

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(action_box)
        root.addWidget(status_box)
        root.addWidget(monitor_tabs, 1)
        root.addWidget(info_box, 1)

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
        self._launch(command, 'Training started...', cwd=runner_working_directory())

    def stop_training(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
        self.status_note.setText('Stopping training...')
        self.set_status('Stopping training...')

    def _launch(self, command: list[str], status_message: str, *, cwd: Path) -> None:
        self.run_log_output.clear()
        self._append_run_log(f'[cwd] {cwd}')
        self.thread = QThread(self)
        self.worker = CommandWorker(command, cwd=cwd)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self._append_run_log)
        self.worker.line.connect(self.log)
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
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Training finished with exit code {exit_code}.')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_preview()

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
