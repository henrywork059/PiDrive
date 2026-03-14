from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
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

from custom_trainer.services.dataset_service import create_dataset_yaml, scan_dataset
from custom_trainer.state import AppState


class DatasetPage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status

        self.project_edit = QLineEdit(self)
        self.images_edit = QLineEdit(self)
        self.labels_edit = QLineEdit(self)
        self.yaml_edit = QLineEdit(self)
        self.classes_edit = QLineEdit(','.join(state.classes), self)
        self.summary = QPlainTextEdit(self)
        self.summary.setReadOnly(True)
        self.summary.setPlaceholderText('Dataset scan results will appear here...')

        self._build()

    def _build(self) -> None:
        path_box = QGroupBox('Dataset Paths', self)
        grid = QGridLayout(path_box)
        self._add_path_row(grid, 0, 'Project Root', self.project_edit, self.choose_project)
        self._add_path_row(grid, 1, 'Images Dir', self.images_edit, self.choose_images)
        self._add_path_row(grid, 2, 'Labels Dir', self.labels_edit, self.choose_labels)
        self._add_path_row(grid, 3, 'dataset.yaml', self.yaml_edit, self.choose_yaml)
        grid.addWidget(QLabel('Classes (comma-separated)', self), 4, 0)
        grid.addWidget(self.classes_edit, 4, 1, 1, 2)

        actions_box = QGroupBox('Actions', self)
        actions = QHBoxLayout(actions_box)
        for text, handler in [
            ('Apply Paths', self.apply_paths),
            ('Scan Dataset', self.on_scan),
            ('Create dataset.yaml', self.on_create_yaml),
            ('Load Defaults', self.load_defaults),
        ]:
            button = QPushButton(text, self)
            button.clicked.connect(handler)
            actions.addWidget(button)

        summary_box = QGroupBox('Dataset Summary', self)
        summary_layout = QVBoxLayout(summary_box)
        summary_layout.addWidget(self.summary, 1)

        root = QVBoxLayout(self)
        root.addWidget(path_box)
        root.addWidget(actions_box)
        root.addWidget(summary_box, 1)

    def _add_path_row(self, grid: QGridLayout, row: int, label: str, line_edit: QLineEdit, handler: Callable[[], None]) -> None:
        grid.addWidget(QLabel(label, self), row, 0)
        grid.addWidget(line_edit, row, 1)
        button = QPushButton('Browse', self)
        button.clicked.connect(handler)
        grid.addWidget(button, row, 2)

    def choose_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose project root')
        if path:
            self.project_edit.setText(path)

    def choose_images(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose images directory')
        if path:
            self.images_edit.setText(path)

    def choose_labels(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose labels directory')
        if path:
            self.labels_edit.setText(path)

    def choose_yaml(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, 'Save dataset.yaml', filter='YAML (*.yaml *.yml)')
        if path:
            self.yaml_edit.setText(path)

    def load_defaults(self) -> None:
        root = self.project_edit.text().strip()
        if not root:
            QMessageBox.information(self, 'Project root needed', 'Choose a project root first.')
            return
        project = Path(root)
        self.images_edit.setText(str(project / 'images' / 'train'))
        self.labels_edit.setText(str(project / 'labels' / 'train'))
        self.yaml_edit.setText(str(project / 'dataset.yaml'))
        self.set_status('Loaded default dataset paths.')

    def apply_paths(self) -> None:
        self.state.project_root = Path(self.project_edit.text()).expanduser() if self.project_edit.text().strip() else None
        self.state.images_dir = Path(self.images_edit.text()).expanduser() if self.images_edit.text().strip() else None
        self.state.labels_dir = Path(self.labels_edit.text()).expanduser() if self.labels_edit.text().strip() else None
        self.state.dataset_yaml = Path(self.yaml_edit.text()).expanduser() if self.yaml_edit.text().strip() else None
        self.state.classes = [item.strip() for item in self.classes_edit.text().split(',') if item.strip()]
        self.log('Applied dataset paths and classes.')
        self.set_status('Dataset paths updated.')

    def on_scan(self) -> None:
        self.apply_paths()
        if not self.state.images_dir or not self.state.labels_dir:
            QMessageBox.critical(self, 'Missing paths', 'Please set images and labels directories first.')
            return
        summary = scan_dataset(self.state.images_dir, self.state.labels_dir)
        self.state.last_summary = summary
        lines = [
            f'Images: {summary.image_count}',
            f'Labels: {summary.label_count}',
            f'Missing labels: {summary.missing_labels}',
            f'Extra labels: {summary.extra_labels}',
            '',
            'Class histogram:',
        ]
        if summary.class_histogram:
            for class_id, count in sorted(summary.class_histogram.items()):
                class_name = self.state.classes[class_id] if 0 <= class_id < len(self.state.classes) else f'class_{class_id}'
                lines.append(f'  {class_id} ({class_name}): {count}')
        else:
            lines.append('  No labels found.')
        self.summary.setPlainText('\n'.join(lines))
        self.log('Dataset scan complete.')
        self.set_status('Dataset scan complete.')

    def on_create_yaml(self) -> None:
        self.apply_paths()
        if not self.state.dataset_yaml:
            QMessageBox.critical(self, 'Missing dataset.yaml path', 'Choose where to save dataset.yaml first.')
            return
        create_dataset_yaml(
            yaml_path=self.state.dataset_yaml,
            train_images='images/train',
            val_images='images/val',
            class_names=self.state.classes,
        )
        self.log(f'Created dataset yaml at: {self.state.dataset_yaml}')
        self.set_status('dataset.yaml created.')
        QMessageBox.information(self, 'dataset.yaml created', f'Saved:\n{self.state.dataset_yaml}')
