from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.pi_deploy_service import build_pi_bundle
from custom_trainer.state import AppState


class PiDeployPage(QWidget):
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

        self.model_edit = QLineEdit(self)
        self.labels_edit = QLineEdit(self)
        self.output_edit = QLineEdit(self)
        self.imgsz_edit = QLineEdit("320", self)
        self.conf_edit = QLineEdit("0.25", self)
        self.iou_edit = QLineEdit("0.45", self)

        self._build()

    def _build(self) -> None:
        config_box = QGroupBox("Pi Bundle Config", self)
        form = QFormLayout(config_box)
        form.addRow("Exported Model (.tflite)", self._path_row(self.model_edit, self.choose_model))
        form.addRow("labels.txt / classes.txt", self._path_row(self.labels_edit, self.choose_labels))
        form.addRow("Bundle Output Dir", self._path_row(self.output_edit, self.choose_output_dir))
        form.addRow("Input Size", self.imgsz_edit)
        form.addRow("Confidence Threshold", self.conf_edit)
        form.addRow("IoU Threshold", self.iou_edit)

        action_box = QGroupBox("Actions", self)
        action_layout = QVBoxLayout(action_box)
        build_button = QPushButton("Build Pi Bundle", self)
        build_button.clicked.connect(self.build_bundle)
        action_layout.addWidget(build_button)

        notes_box = QGroupBox("Deployment Notes", self)
        notes = QPlainTextEdit(self)
        notes.setReadOnly(True)
        notes.setPlainText(
            "1. Train on PC with a small YOLO model.\n"
            "2. Export to TFLite, ideally at 320 or 416 input size.\n"
            "3. Build a Pi bundle from the exported .tflite.\n"
            "4. Copy the bundle to Raspberry Pi and run run_tflite_detect.py.\n\n"
            "This page prepares a ready-to-copy deployment folder with the model, labels, config, a Pi runtime script, a benchmark script, and Pi requirements."
        )
        notes_layout = QVBoxLayout(notes_box)
        notes_layout.addWidget(notes)

        root = QVBoxLayout(self)
        root.addWidget(config_box)
        root.addWidget(action_box)
        root.addWidget(notes_box, 1)

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
        path, _ = QFileDialog.getOpenFileName(self, "Choose exported model", filter="TFLite Model (*.tflite);;All Files (*)")
        if path:
            self.model_edit.setText(path)

    def choose_labels(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose labels file", filter="Text Files (*.txt);;All Files (*)")
        if path:
            self.labels_edit.setText(path)

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose output directory")
        if path:
            self.output_edit.setText(path)

    def build_bundle(self) -> None:
        model = Path(self.model_edit.text().strip()).expanduser()
        labels_text = self.labels_edit.text().strip()
        labels = Path(labels_text).expanduser() if labels_text else None
        output_text = self.output_edit.text().strip()
        if not output_text:
            QMessageBox.critical(self, "Missing output folder", "Choose a bundle output directory.")
            return
        output_dir = Path(output_text).expanduser()
        try:
            imgsz = int(self.imgsz_edit.text().strip())
            conf = float(self.conf_edit.text().strip())
            iou = float(self.iou_edit.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Invalid values", "Input size must be an integer. Thresholds must be numeric.")
            return
        if not model.exists():
            QMessageBox.critical(self, "Missing model", "Choose an exported .tflite model first.")
            return
        bundle_dir = build_pi_bundle(
            model_path=model,
            labels_path=labels,
            output_dir=output_dir,
            image_size=imgsz,
            conf_threshold=conf,
            iou_threshold=iou,
        )
        self.log(f"Built Pi bundle: {bundle_dir}")
        self.set_status("Pi bundle ready.")
        QMessageBox.information(self, "Pi bundle ready", f"Saved:\n{bundle_dir}")
