from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread
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
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import ensure_dataset_yaml
from custom_trainer.services.ultralytics_runner import build_export_command
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


class ExportPage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None

        self.weights_edit = QLineEdit(self)
        self.yaml_edit = QLineEdit(self)
        self.format_combo = QComboBox(self)
        self.format_combo.addItems(['tflite', 'onnx', 'openvino', 'torchscript'])
        self.imgsz_edit = QLineEdit('320', self)
        self.device_edit = QLineEdit('cpu', self)
        self.quant_combo = QComboBox(self)
        self.quant_combo.addItems(['int8', 'float16', 'float32'])
        self.nms_check = QCheckBox('Embed NMS when supported', self)
        self.nms_check.setChecked(True)
        self.status_note = QLabel('Idle', self)
        self.status_note.setProperty('role', 'muted')
        self.export_button = QPushButton('Export Model', self)
        self.export_button.clicked.connect(self.start_export)

        self._build()

    def _build(self) -> None:
        config_box = QGroupBox('Export Config', self)
        form = QFormLayout(config_box)
        form.addRow('Weights (.pt)', self._path_row(self.weights_edit, self.choose_weights))
        form.addRow('dataset.yaml (needed for INT8)', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Format', self.format_combo)
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Device', self.device_edit)
        form.addRow('Quantization', self.quant_combo)
        form.addRow('', self.nms_check)

        action_box = QGroupBox('Actions', self)
        action_layout = QHBoxLayout(action_box)
        use_current_button = QPushButton('Use Current Sessions Root', action_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        action_layout.addWidget(use_current_button)
        action_layout.addWidget(self.export_button)
        action_layout.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        info_box = QGroupBox('Pi Export Notes', self)
        info = QPlainTextEdit(self)
        info.setReadOnly(True)
        info.setPlainText(
            'Recommended Pi export path:\n\n'
            '- format: tflite\n'
            '- image size: 320 or 416\n'
            '- quantization: int8 first, then float16 if needed\n'
            '- device: cpu\n\n'
            'Use dataset.yaml when exporting INT8 so calibration data is available.'
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info)

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

    def choose_weights(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose weights', filter='PyTorch Weights (*.pt);;All Files (*)')
        if path:
            self.weights_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Choose dataset.yaml', filter='YAML (*.yaml *.yml)')
        if path:
            self.yaml_edit.setText(path)

    def use_current_root_defaults(self) -> None:
        dataset_yaml, created = ensure_dataset_yaml(self.state.sessions_root, self.state.class_names)
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
            if created:
                self.log(f'Created dataset YAML: {dataset_yaml}')
        self.set_status('Export defaults filled from the current sessions root.')

    def start_export(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'An export task is already running.')
            return
        try:
            imgsz = int(self.imgsz_edit.text())
        except ValueError:
            QMessageBox.critical(self, 'Invalid image size', 'Image size must be an integer.')
            return
        if not self.weights_edit.text().strip():
            QMessageBox.critical(self, 'Missing weights', 'Choose weights first.')
            return
        quant = self.quant_combo.currentText().strip()
        int8 = quant == 'int8'
        half = quant == 'float16'
        data = _prepare_dataset_yaml(self.state, self.yaml_edit.text(), self.state.class_names, self.log) if int8 else ''
        if int8:
            self.yaml_edit.setText(data)
        if int8 and (not data or not Path(data).exists()):
            QMessageBox.critical(self, 'dataset.yaml required', 'INT8 export needs a valid dataset.yaml for calibration.')
            return
        command = build_export_command(
            weights=self.weights_edit.text().strip(),
            export_format=self.format_combo.currentText().strip(),
            imgsz=imgsz,
            device=self.device_edit.text().strip(),
            int8=int8,
            half=half,
            nms=self.nms_check.isChecked(),
            data=data,
        )
        self.thread = QThread(self)
        self.worker = CommandWorker(command)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self.log)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.export_button.setEnabled(False)
        self.status_note.setText('Export started...')
        self.set_status('Export started...')
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.export_button.setEnabled(True)
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Export finished with exit code {exit_code}.')

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
