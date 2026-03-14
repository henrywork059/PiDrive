from __future__ import annotations

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
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.ultralytics_runner import build_train_command
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker


class TrainPage(QWidget):
    def __init__(
        self,
        state: AppState,
        log: Callable[[str], None],
        set_status: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.thread: QThread | None = None
        self.worker: CommandWorker | None = None

        self.model_edit = QLineEdit(state.model_path, self)
        self.yaml_edit = QLineEdit(self)
        self.epochs_edit = QLineEdit("100", self)
        self.imgsz_edit = QLineEdit("640", self)
        self.batch_edit = QLineEdit("16", self)
        self.device_edit = QLineEdit("cpu", self)
        self.project_edit = QLineEdit("runs", self)
        self.name_edit = QLineEdit("customtrainer_train", self)
        self.status_note = QLabel("Idle", self)
        self.status_note.setProperty("role", "muted")

        self.start_button = QPushButton("Start Training", self)
        self.start_button.clicked.connect(self.start_training)

        self._build()

    def _build(self) -> None:
        config_box = QGroupBox("Training Config", self)
        form = QFormLayout(config_box)
        form.addRow("Model (.pt / preset)", self._path_row(self.model_edit, self.choose_model))
        form.addRow("dataset.yaml", self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow("Epochs", self.epochs_edit)
        form.addRow("Image Size", self.imgsz_edit)
        form.addRow("Batch", self.batch_edit)
        form.addRow("Device", self.device_edit)
        form.addRow("Runs Project Dir", self.project_edit)
        form.addRow("Run Name", self.name_edit)

        action_box = QGroupBox("Actions", self)
        action_layout = QVBoxLayout(action_box)
        action_layout.addWidget(self.start_button)
        action_layout.addWidget(self.status_note)

        info_box = QGroupBox("Recommended Workflow", self)
        info_text = QPlainTextEdit(self)
        info_text.setReadOnly(True)
        info_text.setPlainText(
            "Start with a small model such as yolov8n.\n"
            "Use moderate image sizes first to validate the pipeline.\n"
            "Use the Export page after you have a stable training run."
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info_text)

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(action_box)
        root.addWidget(info_box, 1)

    def _path_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton("Browse", container)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def choose_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose model weights",
            filter="PyTorch Weights (*.pt);;All Files (*)",
        )
        if path:
            self.model_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose dataset.yaml", filter="YAML (*.yaml *.yml)")
        if path:
            self.yaml_edit.setText(path)

    def start_training(self) -> None:
        if self.thread is not None:
            QMessageBox.information(self, "Training running", "A training process is already running.")
            return
        if not self.yaml_edit.text().strip():
            QMessageBox.critical(self, "Missing dataset.yaml", "Choose dataset.yaml first.")
            return
        try:
            epochs = int(self.epochs_edit.text())
            imgsz = int(self.imgsz_edit.text())
            batch = int(self.batch_edit.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid numbers", "Epochs, image size, and batch must be integers.")
            return
        command = build_train_command(
            model=self.model_edit.text().strip(),
            data=self.yaml_edit.text().strip(),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=self.device_edit.text().strip(),
            project=self.project_edit.text().strip(),
            name=self.name_edit.text().strip(),
        )
        self._launch(command, "Training started...")

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
        self.status_note.setText(f"Finished with exit code {exit_code}.")
        self.set_status(f"Training finished with exit code {exit_code}.")
        self.start_button.setEnabled(True)

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
