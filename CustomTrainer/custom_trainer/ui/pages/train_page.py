from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QThread
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

from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.ultralytics_runner import build_train_command
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
        self.start_button.clicked.connect(self.start_training)

        self._build()
        self.refresh_devices(log_runtime=False)

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
        refresh_devices_button = QPushButton('Refresh Devices', action_box)
        refresh_devices_button.clicked.connect(lambda: self.refresh_devices(log_runtime=True))
        action_layout.addWidget(use_current_button)
        action_layout.addWidget(refresh_devices_button)
        action_layout.addWidget(self.start_button)
        action_layout.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        info_box = QGroupBox('Workflow Notes', self)
        info_text = QPlainTextEdit(self)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            '1. Use Marking to load your sessions folder and label images.\n'
            '2. Point this page to the dataset.yaml for your YOLO dataset.\n'
            '3. Use Auto or CUDA:0 to train on GPU when your Python environment has CUDA-enabled PyTorch.\n'
            '4. Start with yolov8n.pt or another small model to verify the pipeline.\n'
            '5. Export after you have a good run.'
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info_text)

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(action_box)
        root.addWidget(status_box)
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
            self.log(f'[device] {probe.summary}')
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
        self.set_status('Training defaults filled from the current sessions root.')

    def start_training(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Training running', 'A training process is already running.')
            return
        if not self.yaml_edit.text().strip():
            QMessageBox.critical(self, 'Missing dataset.yaml', 'Choose dataset.yaml first.')
            return
        try:
            epochs = int(self.epochs_edit.text())
            imgsz = int(self.imgsz_edit.text())
            batch = int(self.batch_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid numbers', 'Epochs, image size, and batch must be integers.')
            return
        command = build_train_command(
            model=self.model_edit.text().strip(),
            data=self.yaml_edit.text().strip(),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=self.current_device_value(),
            project=self.project_edit.text().strip(),
            name=self.name_edit.text().strip(),
        )
        self._launch(command, 'Training started...')

    def _launch(self, command: list[str], status_message: str) -> None:
        self.thread = QThread(self)
        self.worker = CommandWorker(command)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self.log)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.start_button.setEnabled(False)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Training finished with exit code {exit_code}.')
        self.start_button.setEnabled(True)

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
