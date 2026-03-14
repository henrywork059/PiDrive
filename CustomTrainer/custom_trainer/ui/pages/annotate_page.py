from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.state import AppState
from custom_trainer.ui.widgets.annotation_canvas import AnnotationCanvas
from custom_trainer.utils.file_utils import list_images
from custom_trainer.utils.yolo_io import pixel_to_yolo, read_yolo_label_file, write_yolo_label_file, yolo_to_pixel


class AnnotatePage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.image_paths: list[Path] = []
        self.current_index = 0
        self.current_image_size: tuple[int, int] = (0, 0)

        self.images_edit = QLineEdit(self)
        self.labels_edit = QLineEdit(self)
        self.class_spin = QSpinBox(self)
        self.class_spin.setRange(0, 999)
        self.status_label = QLabel('No image loaded.', self)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.canvas = AnnotationCanvas(self.current_class_id, self)
        self.canvas.selection_changed.connect(self.on_selection_changed)

        self._build()

    def _build(self) -> None:
        paths_box = QGroupBox('Annotation Sources', self)
        form = QFormLayout(paths_box)
        form.addRow('Images Dir', self._dir_row(self.images_edit, self.choose_images))
        form.addRow('Labels Dir', self._dir_row(self.labels_edit, self.choose_labels))
        load_button = QPushButton('Load Images', self)
        load_button.clicked.connect(self.load_image_list)
        form.addRow('', load_button)

        tools_box = QGroupBox('Annotation Tools', self)
        tools_layout = QVBoxLayout(tools_box)
        tools_layout.addWidget(QLabel('Class ID', self))
        tools_layout.addWidget(self.class_spin)
        prev_button = QPushButton('Prev', self)
        prev_button.clicked.connect(self.prev_image)
        next_button = QPushButton('Next', self)
        next_button.clicked.connect(self.next_image)
        delete_button = QPushButton('Delete Box', self)
        delete_button.clicked.connect(self.delete_selected_box)
        save_button = QPushButton('Save Labels', self)
        save_button.clicked.connect(self.save_labels)
        tools_layout.addWidget(prev_button)
        tools_layout.addWidget(next_button)
        tools_layout.addWidget(delete_button)
        tools_layout.addWidget(save_button)
        tools_layout.addStretch(1)
        tools_layout.addWidget(self.status_label)

        root = QVBoxLayout(self)
        root.addWidget(paths_box)
        body = QHBoxLayout()
        body.addWidget(self.canvas, 1)
        body.addWidget(tools_box)
        root.addLayout(body, 1)

    def _dir_row(self, line_edit: QLineEdit, handler: Callable[[], None]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit, 1)
        button = QPushButton('Browse', container)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return container

    def current_class_id(self) -> int:
        return int(self.class_spin.value())

    def choose_images(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose images directory')
        if path:
            self.images_edit.setText(path)

    def choose_labels(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose labels directory')
        if path:
            self.labels_edit.setText(path)

    def load_image_list(self) -> None:
        images_dir = Path(self.images_edit.text()).expanduser()
        labels_dir = Path(self.labels_edit.text()).expanduser()
        if not images_dir.exists():
            QMessageBox.critical(self, 'Images folder missing', 'Choose a valid images folder.')
            return
        labels_dir.mkdir(parents=True, exist_ok=True)
        self.state.images_dir = images_dir
        self.state.labels_dir = labels_dir
        self.image_paths = list_images(images_dir)
        self.current_index = 0
        if not self.image_paths:
            QMessageBox.information(self, 'No images', 'No supported images found in that folder.')
            return
        self.log(f'Loaded {len(self.image_paths)} images for annotation.')
        self.set_status(f'Loaded {len(self.image_paths)} images for annotation.')
        self.load_current_image()

    def label_path_for_image(self, image_path: Path) -> Path:
        assert self.state.labels_dir is not None
        return self.state.labels_dir / f'{image_path.stem}.txt'

    def load_current_image(self) -> None:
        if not self.image_paths:
            return
        image_path = self.image_paths[self.current_index]
        with Image.open(image_path) as img:
            width, height = img.size
        self.current_image_size = (width, height)
        label_path = self.label_path_for_image(image_path)
        boxes = [yolo_to_pixel(box, width, height) for box in read_yolo_label_file(label_path)]
        self.canvas.set_scene(image_path, boxes)
        self.status_label.setText(
            f'Image {self.current_index + 1}/{len(self.image_paths)}\n'
            f'{image_path.name}\n'
            f'Labels: {label_path.name}'
        )
        self.set_status(f'Loaded annotation image: {image_path.name}')

    def save_labels(self) -> None:
        if not self.image_paths:
            return
        image_path = self.image_paths[self.current_index]
        label_path = self.label_path_for_image(image_path)
        width, height = self.current_image_size
        yolo_boxes = [pixel_to_yolo(box, width, height) for box in self.canvas.boxes]
        write_yolo_label_file(label_path, yolo_boxes)
        self.log(f'Saved labels: {label_path}')
        self.set_status('Annotation labels saved.')
        self.status_label.setText(self.status_label.text() + '\nSaved.')

    def delete_selected_box(self) -> None:
        if self.canvas.delete_selected():
            self.set_status('Deleted selected annotation box.')

    def prev_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self.load_current_image()

    def next_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.load_current_image()

    def on_selection_changed(self, index: int) -> None:
        if index >= 0:
            self.set_status(f'Selected box #{index + 1}.')
