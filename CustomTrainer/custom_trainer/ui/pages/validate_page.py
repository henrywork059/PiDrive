from __future__ import annotations

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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.ultralytics_runner import build_predict_command, build_val_command
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker

_IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}


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
        self.preview_label.setMinimumSize(420, 280)
        self.preview_label.setStyleSheet('background: #0d1118; border: 1px solid #263244;')
        self.preview_info = QLabel('Prediction source preview will appear here.', self)
        self.preview_info.setWordWrap(True)
        self.preview_info.setProperty('role', 'muted')

        self.val_button.clicked.connect(self.start_val)
        self.predict_button.clicked.connect(self.start_predict)
        self.stop_button.clicked.connect(self.stop_task)

        self._build()
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()

    def _build(self) -> None:
        config_box = QGroupBox('Validation / Prediction Config', self)
        form = QFormLayout(config_box)
        form.addRow('Weights (.pt)', self._path_row(self.weights_edit, self.choose_weights))
        form.addRow('dataset.yaml', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Predict Source', self._path_row(self.source_edit, self.choose_source))
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Confidence', self.conf_edit)
        form.addRow('Device', self._device_row())
        form.addRow('', self.device_summary)

        actions_box = QGroupBox('Actions', self)
        actions = QHBoxLayout(actions_box)
        use_current_button = QPushButton('Use Current Sessions Root', actions_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        latest_best_button = QPushButton('Use Latest best.pt', actions_box)
        latest_best_button.clicked.connect(self.use_latest_best_weights)
        refresh_preview_button = QPushButton('Refresh Preview', actions_box)
        refresh_preview_button.clicked.connect(self.refresh_preview)
        refresh_devices_button = QPushButton('Refresh Devices', actions_box)
        refresh_devices_button.clicked.connect(lambda: self.refresh_devices(log_runtime=True))
        actions.addWidget(use_current_button)
        actions.addWidget(latest_best_button)
        actions.addWidget(refresh_preview_button)
        actions.addWidget(refresh_devices_button)
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

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(actions_box)
        root.addWidget(status_box)
        root.addWidget(preview_box, 1)
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
            self.refresh_preview()

    def use_current_root_defaults(self) -> None:
        dataset_yaml = self.state.preferred_dataset_yaml()
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
        current_image = self.state.current_image_path
        if current_image is not None:
            self.source_edit.setText(str(current_image))
        self.refresh_devices(log_runtime=False)
        self.refresh_preview()
        self.set_status('Validation defaults filled from the current sessions root.')

    def use_latest_best_weights(self) -> None:
        best = self.state.latest_best_weights()
        if best is None:
            QMessageBox.information(self, 'No best.pt found', 'Train a model first, then try again.')
            return
        self.weights_edit.setText(str(best))
        self.set_status('Loaded latest best.pt into Validation.')

    def refresh_preview(self) -> None:
        source_text = self.source_edit.text().strip()
        if not source_text:
            current = self.state.current_image_path
            if current is not None:
                source_text = str(current)
        if not source_text:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('No preview source selected.')
            self.preview_info.setText('Pick an image source, or use the current frame from Marking.')
            return
        from pathlib import Path
        source_path = Path(source_text)
        if not source_path.exists():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview source not found.')
            self.preview_info.setText(f'Source path does not exist:\n{source_text}')
            return
        if source_path.suffix.lower() not in _IMAGE_SUFFIXES:
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview unavailable for non-image sources.')
            self.preview_info.setText(f'Source: {source_path.name}\nPreview is shown for image files only.')
            return
        pixmap = QPixmap(str(source_path))
        if pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText('Preview unavailable for this file.')
        else:
            scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText('')
        self.preview_info.setText(
            f'Source: {source_path.name}\n'
            f'Weights: {self.weights_edit.text().strip() or "not set"}\n'
            f'Dataset YAML: {self.yaml_edit.text().strip() or "not set"}'
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_preview()

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
        command = build_val_command(
            weights=self.weights_edit.text().strip(),
            data=self.yaml_edit.text().strip(),
            imgsz=imgsz,
            device=self.current_device_value(),
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
            device=self.current_device_value(),
        )
        self._launch(command, 'Prediction started...')

    def stop_task(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
        self.status_note.setText('Stopping task...')
        self.set_status('Stopping validation/prediction task...')

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
        self.stop_button.setEnabled(True)
        self.status_note.setText(status_message)
        self.set_status(status_message)
        self.thread.start()

    def _on_finished(self, exit_code: int) -> None:
        self.val_button.setEnabled(True)
        self.predict_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Validation or prediction finished with exit code {exit_code}.')

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
