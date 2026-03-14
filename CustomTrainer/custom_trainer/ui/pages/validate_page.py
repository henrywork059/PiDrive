from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import ensure_dataset_yaml
from custom_trainer.services.ultralytics_runner import build_predict_command, build_val_command
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker


def _prepare_dataset_yaml(state: AppState, yaml_text: str, class_names: list[str], log: Callable[[str], None]) -> str:
    yaml_path = Path(yaml_text).expanduser() if yaml_text.strip() else None
    if yaml_path is not None and yaml_path.exists():
        return str(yaml_path)
    if state.sessions_root is None:
        return yaml_text.strip()
    preferred = state.preferred_dataset_yaml()
    matches_default = yaml_path is None or preferred is None or yaml_path == preferred
    if matches_default:
        created_path, created = ensure_dataset_yaml(state.sessions_root, class_names)
        if created_path is not None:
            if created:
                log(f'Created dataset YAML: {created_path}')
            return str(created_path)
    return yaml_text.strip()


class ValidatePage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None

        self.weights_edit = QLineEdit(self)
        self.yaml_edit = QLineEdit(self)
        self.source_edit = QLineEdit(self)
        self.imgsz_edit = QLineEdit('640', self)
        self.conf_edit = QLineEdit('0.25', self)
        self.device_edit = QLineEdit('cpu', self)
        self.status_note = QLabel('Idle', self)
        self.status_note.setProperty('role', 'muted')
        self.val_button = QPushButton('Run Validation', self)
        self.predict_button = QPushButton('Run Prediction', self)
        self.val_button.clicked.connect(self.start_val)
        self.predict_button.clicked.connect(self.start_predict)

        self._build()

    def _build(self) -> None:
        config_box = QGroupBox('Validation / Prediction Config', self)
        form = QFormLayout(config_box)
        form.addRow('Weights (.pt)', self._path_row(self.weights_edit, self.choose_weights))
        form.addRow('dataset.yaml', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Predict Source', self._path_row(self.source_edit, self.choose_source))
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Confidence', self.conf_edit)
        form.addRow('Device', self.device_edit)

        actions_box = QGroupBox('Actions', self)
        actions = QHBoxLayout(actions_box)
        use_current_button = QPushButton('Use Current Sessions Root', actions_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        actions.addWidget(use_current_button)
        actions.addWidget(self.val_button)
        actions.addWidget(self.predict_button)
        actions.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(actions_box)
        root.addWidget(status_box)
        root.addStretch(1)

    def _path_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton('Browse', container)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def choose_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose weights', filter='PyTorch Weights (*.pt);;All Files (*)')
        if path:
            self.weights_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose dataset.yaml', filter='YAML (*.yaml *.yml)')
        if path:
            self.yaml_edit.setText(path)

    def choose_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose source image/video', filter='Media (*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi);;All Files (*)')
        if path:
            self.source_edit.setText(path)

    def use_current_root_defaults(self) -> None:
        dataset_yaml, created = ensure_dataset_yaml(self.state.sessions_root, self.state.class_names)
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
            if created:
                self.log(f'Created dataset YAML: {dataset_yaml}')
        current_image = self.state.current_image_path
        if current_image is not None:
            self.source_edit.setText(str(current_image))
        self.set_status('Validation defaults filled from the current sessions root.')

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
        yaml_path = _prepare_dataset_yaml(self.state, self.yaml_edit.text(), self.state.class_names, self.log)
        self.yaml_edit.setText(yaml_path)
        if not yaml_path or not Path(yaml_path).exists():
            QMessageBox.critical(self, 'Missing dataset.yaml', 'dataset.yaml does not exist. Load sessions on Marking first or choose a valid dataset.yaml.')
            return
        command = build_val_command(
            weights=self.weights_edit.text().strip(),
            data=yaml_path,
            imgsz=imgsz,
            device=self.device_edit.text().strip(),
        )
        self._launch(command, 'Validation started...')

    def start_predict(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'Another validation or prediction task is already running.')
            return
        try:
            imgsz = int(self.imgsz_edit.text())
            conf = float(self.conf_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid values', 'Image size must be integer and confidence must be numeric.')
            return
        if not self.weights_edit.text().strip() or not self.source_edit.text().strip():
            QMessageBox.critical(self, 'Missing inputs', 'Choose weights and a prediction source first.')
            return
        command = build_predict_command(
            weights=self.weights_edit.text().strip(),
            source=self.source_edit.text().strip(),
            imgsz=imgsz,
            conf=conf,
            device=self.device_edit.text().strip(),
        )
        self._launch(command, 'Prediction started...')

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
        self.val_button.setEnabled(False)
        self.predict_button.setEnabled(False)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.val_button.setEnabled(True)
        self.predict_button.setEnabled(True)
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Validation or prediction finished with exit code {exit_code}.')

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
