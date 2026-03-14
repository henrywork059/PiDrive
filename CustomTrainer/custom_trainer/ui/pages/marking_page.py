from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from custom_trainer.services.dataset_service import ensure_dataset_yaml
from custom_trainer.services.session_service import SessionInfo, discover_sessions, load_class_names, save_class_names, sync_legacy_labels
from custom_trainer.services.yolo_io import pixel_to_yolo, read_yolo_label_file, write_yolo_label_file, yolo_to_pixel
from custom_trainer.state import AppState
from custom_trainer.ui.widgets.annotation_canvas import AnnotationCanvas


class MarkingPage(QWidget):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.log = log
        self.set_status = set_status
        self.current_image_path: Path | None = None
        self.current_label_path: Path | None = None
        self.current_image_size: tuple[int, int] = (0, 0)
        self.is_dirty = False

        self.root_edit = QLineEdit(self)
        self.session_list = QListWidget(self)
        self.image_list = QListWidget(self)
        self.class_combo = QComboBox(self)
        self.class_editor = QPlainTextEdit(self)
        self.summary_value = QLabel('No sessions loaded.', self)
        self.summary_value.setProperty('role', 'value')
        self.image_info = QLabel('No image selected.', self)
        self.image_info.setWordWrap(True)
        self.image_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.selection_info = QLabel('Right-click a box to select it.', self)
        self.selection_info.setWordWrap(True)
        self.selection_info.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.canvas = AnnotationCanvas(self.current_class_id, self)

        self._build()
        self._connect()
        self.refresh_class_widgets()

    def _build(self) -> None:
        source_box = QGroupBox('Session Source', self)
        source_form = QFormLayout(source_box)
        source_form.addRow('Sessions Root', self._path_row())
        source_buttons = QWidget(source_box)
        source_buttons_layout = QHBoxLayout(source_buttons)
        source_buttons_layout.setContentsMargins(0, 0, 0, 0)
        scan_button = QPushButton('Scan Sessions', source_buttons)
        scan_button.clicked.connect(self.scan_sessions)
        source_buttons_layout.addWidget(scan_button)
        source_buttons_layout.addStretch(1)
        source_form.addRow('', source_buttons)

        sessions_box = QGroupBox('Sessions', self)
        sessions_layout = QVBoxLayout(sessions_box)
        sessions_layout.addWidget(self.session_list)

        images_box = QGroupBox('Images', self)
        images_layout = QVBoxLayout(images_box)
        images_layout.addWidget(self.image_list)

        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(source_box)
        left_layout.addWidget(sessions_box, 1)
        left_layout.addWidget(images_box, 2)

        preview_box = QGroupBox('Image Preview', self)
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.canvas, 1)

        classes_box = QGroupBox('Classes', self)
        classes_layout = QVBoxLayout(classes_box)
        classes_layout.addWidget(QLabel('Current class for new boxes / apply to selected box', classes_box))
        classes_layout.addWidget(self.class_combo)
        apply_class_button = QPushButton('Apply Class To Selected Box', classes_box)
        apply_class_button.clicked.connect(self.apply_class_to_selected)
        classes_layout.addWidget(apply_class_button)
        classes_layout.addWidget(QLabel('One class name per line', classes_box))
        classes_layout.addWidget(self.class_editor, 1)
        save_classes_button = QPushButton('Save classes.txt', classes_box)
        save_classes_button.clicked.connect(self.save_classes)
        classes_layout.addWidget(save_classes_button)

        tools_box = QGroupBox('Annotation Tools', self)
        tools_layout = QGridLayout(tools_box)
        prev_button = QPushButton('Prev Image', tools_box)
        next_button = QPushButton('Next Image', tools_box)
        save_button = QPushButton('Save Labels', tools_box)
        delete_button = QPushButton('Delete Selected Box', tools_box)
        prev_button.clicked.connect(self.prev_image)
        next_button.clicked.connect(self.next_image)
        save_button.clicked.connect(self.save_current_labels)
        delete_button.clicked.connect(self.delete_selected_box)
        tools_layout.addWidget(prev_button, 0, 0)
        tools_layout.addWidget(next_button, 0, 1)
        tools_layout.addWidget(save_button, 1, 0)
        tools_layout.addWidget(delete_button, 1, 1)
        help_label = QLabel(
            'Draw: left-drag\n'
            'Select: right-click\n'
            'Move selected box: arrow keys\n'
            'Fast move: Shift + arrow keys\n'
            'Delete: Delete key',
            tools_box,
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)
        tools_layout.addWidget(help_label, 2, 0, 1, 2)

        info_box = QGroupBox('Current Item', self)
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(self.summary_value)
        info_layout.addWidget(self.image_info)
        info_layout.addWidget(self.selection_info)
        info_layout.addStretch(1)

        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(classes_box, 2)
        right_layout.addWidget(tools_box)
        right_layout.addWidget(info_box)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(left_panel)
        splitter.addWidget(preview_box)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([320, 900, 320])

        root = QVBoxLayout(self)
        root.addWidget(splitter, 1)

    def _connect(self) -> None:
        self.session_list.currentRowChanged.connect(self.on_session_changed)
        self.image_list.currentRowChanged.connect(self.on_image_changed)
        self.class_combo.currentIndexChanged.connect(self.on_class_combo_changed)
        self.canvas.selection_changed.connect(self.on_selection_changed)
        self.canvas.boxes_changed.connect(self.on_boxes_changed)

    def _path_row(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.root_edit, 1)
        browse = QPushButton('Browse', row)
        browse.clicked.connect(self.choose_root_folder)
        layout.addWidget(browse)
        return row

    def choose_root_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, 'Choose sessions root folder')
        if path:
            self.root_edit.setText(path)
            self.scan_sessions()

    def current_class_id(self) -> int:
        return int(self.class_combo.currentData() or 0)

    def refresh_class_widgets(self) -> None:
        class_names = [name.strip() for name in self.state.class_names if name.strip()] or ['object']
        self.state.class_names = class_names
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        for idx, name in enumerate(class_names):
            self.class_combo.addItem(f'{idx}: {name}', idx)
        self.class_combo.blockSignals(False)
        self.class_editor.setPlainText('\n'.join(class_names))

    def scan_sessions(self) -> None:
        root_text = self.root_edit.text().strip()
        if not root_text:
            QMessageBox.information(self, 'Sessions root missing', 'Choose the folder that contains your sessions.')
            return
        root = Path(root_text).expanduser()
        if not root.exists() or not root.is_dir():
            QMessageBox.critical(self, 'Invalid folder', 'The selected sessions root does not exist.')
            return
        sessions = discover_sessions(root)
        self.state.sessions_root = root
        self.state.sessions = sessions
        self.state.current_session_index = -1
        self.state.current_image_index = -1
        self.session_list.clear()
        self.image_list.clear()
        self.canvas.clear_scene()
        if not sessions:
            self.summary_value.setText('No sessions found in the selected folder.')
            self.image_info.setText('No image selected.')
            self.current_image_path = None
            self.current_label_path = None
            self.current_image_size = (0, 0)
            self.log(f'No sessions found under: {root}')
            self.set_status('No sessions found.')
            return
        for session in sessions:
            item = QListWidgetItem(f'{session.name}  ({len(session.image_paths)} images)')
            item.setToolTip(str(session.session_dir))
            self.session_list.addItem(item)
        self.state.class_names = load_class_names(root, sessions[0])
        self.refresh_class_widgets()
        total_images = sum(len(session.image_paths) for session in sessions)
        self.summary_value.setText(f'{len(sessions)} sessions loaded • {total_images} images total')
        migrated = sync_legacy_labels(sessions)
        dataset_yaml, created = ensure_dataset_yaml(root, self.state.class_names)
        self.log(f'Scanned {len(sessions)} sessions from {root}')
        if migrated:
            self.log(f'Repaired {migrated} legacy label file(s) into canonical YOLO paths.')
        if dataset_yaml is not None and created:
            self.log(f'Created dataset YAML: {dataset_yaml}')
        self.set_status(f'Loaded {len(sessions)} sessions.')
        self.session_list.setCurrentRow(0)

    def on_session_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.state.sessions):
            return
        if not self.maybe_save_before_switch():
            self.session_list.blockSignals(True)
            self.session_list.setCurrentRow(self.state.current_session_index)
            self.session_list.blockSignals(False)
            return
        self.state.current_session_index = index
        self.state.current_image_index = -1
        session = self.state.sessions[index]
        self.state.class_names = load_class_names(self.state.sessions_root, session)
        self.refresh_class_widgets()
        self.populate_image_list(session)
        self.log(f'Opened session: {session.name}')
        self.set_status(f'Session loaded: {session.name}')

    def populate_image_list(self, session: SessionInfo) -> None:
        self.image_list.clear()
        self.current_image_path = None
        self.current_label_path = None
        self.current_image_size = (0, 0)
        self.canvas.clear_scene()
        for image_path in session.image_paths:
            label_path = session.find_existing_label_path(image_path)
            has_content = False
            if label_path is not None:
                try:
                    has_content = bool(label_path.read_text(encoding='utf-8').strip())
                except Exception:
                    has_content = False
            marker = '●' if has_content else '○'
            item = QListWidgetItem(f'{marker} {image_path.name}')
            item.setToolTip(str(image_path))
            self.image_list.addItem(item)
        labeled = session.labeled_count
        self.summary_value.setText(f'Session: {session.name} • {len(session.image_paths)} images • {labeled} labeled')
        if session.image_paths:
            self.image_list.setCurrentRow(0)

    def on_image_changed(self, index: int) -> None:
        session = self.state.current_session
        if session is None or index < 0 or index >= len(session.image_paths):
            return
        if not self.maybe_save_before_switch():
            self.image_list.blockSignals(True)
            self.image_list.setCurrentRow(self.state.current_image_index)
            self.image_list.blockSignals(False)
            return
        self.state.current_image_index = index
        image_path = session.image_paths[index]
        label_path, migrated = session.ensure_canonical_label_path(image_path)
        boxes = read_yolo_label_file(label_path)
        self.current_image_path = image_path
        self.current_label_path = label_path
        if migrated:
            self.log(f'Repaired legacy label path for {image_path.name} -> {label_path}')
        probe = QPixmap(str(image_path))
        self.current_image_size = (probe.width(), probe.height())
        pixel_boxes = [yolo_to_pixel(box, probe.width(), probe.height()) for box in boxes]
        self.canvas.set_scene(image_path, pixel_boxes)
        self.is_dirty = False
        self.image_info.setText(
            f'Image {index + 1}/{len(session.image_paths)}\n'
            f'{image_path.name}\n'
            f'Label file: {label_path.name}'
        )
        self.selection_info.setText('Right-click a box to select it.')
        self.log(f'Loaded image: {image_path.name}')
        self.set_status(f'Image loaded: {image_path.name}')

    def maybe_save_before_switch(self) -> bool:
        if not self.is_dirty or self.current_image_path is None:
            return True
        result = QMessageBox.question(
            self,
            'Unsaved labels',
            'Save label changes before switching?',
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes,
        )
        if result == QMessageBox.Cancel:
            return False
        if result == QMessageBox.Yes:
            return self.save_current_labels()
        self.is_dirty = False
        return True

    def save_current_labels(self) -> bool:
        if self.current_image_path is None or self.current_label_path is None:
            return False
        width, height = self.current_image_size
        if width <= 0 or height <= 0:
            return False
        session = self.state.current_session
        if session is not None:
            self.current_label_path = session.label_path_for_image(self.current_image_path)
        yolo_boxes = [pixel_to_yolo(box, width, height) for box in self.canvas.boxes]
        write_yolo_label_file(self.current_label_path, yolo_boxes)
        self.is_dirty = False
        self.refresh_current_image_item_marker()
        self.log(f'Saved labels: {self.current_label_path}')
        self.set_status('Labels saved.')
        return True

    def refresh_current_image_item_marker(self) -> None:
        row = self.state.current_image_index
        session = self.state.current_session
        if session is None or row < 0 or row >= self.image_list.count() or self.current_label_path is None or self.current_image_path is None:
            return
        has_labels = self.current_label_path.exists() and self.current_label_path.read_text(encoding='utf-8').strip()
        marker = '●' if has_labels else '○'
        self.image_list.item(row).setText(f'{marker} {self.current_image_path.name}')
        self.summary_value.setText(f'Session: {session.name} • {len(session.image_paths)} images • {session.labeled_count} labeled')

    def prev_image(self) -> None:
        if self.image_list.count() == 0:
            return
        row = self.image_list.currentRow()
        self.image_list.setCurrentRow((row - 1) % self.image_list.count())

    def next_image(self) -> None:
        if self.image_list.count() == 0:
            return
        row = self.image_list.currentRow()
        self.image_list.setCurrentRow((row + 1) % self.image_list.count())

    def delete_selected_box(self) -> None:
        if self.canvas.delete_selected():
            self.is_dirty = True
            self.selection_info.setText('Selected box deleted.')
            self.set_status('Selected box deleted.')

    def apply_class_to_selected(self) -> None:
        if self.canvas.set_selected_class_id(self.current_class_id()):
            self.is_dirty = True
            self.selection_info.setText(f'Updated selected box to class {self.current_class_id()}.')
            self.set_status('Selected box class updated.')

    def save_classes(self) -> None:
        target_root = self.state.current_session.session_dir if self.state.current_session is not None else self.state.sessions_root
        if target_root is None:
            QMessageBox.information(self, 'No target folder', 'Load sessions before saving classes.')
            return
        class_names = [line.strip() for line in self.class_editor.toPlainText().splitlines() if line.strip()]
        if not class_names:
            QMessageBox.information(self, 'No classes', 'Enter at least one class name.')
            return
        self.state.class_names = class_names
        self.refresh_class_widgets()
        path = save_class_names(target_root, class_names)
        dataset_root = self.state.sessions_root or target_root
        dataset_yaml, _ = ensure_dataset_yaml(dataset_root, class_names, overwrite=True)
        self.log(f'Saved class list: {path}')
        if dataset_yaml is not None:
            self.log(f'Updated dataset YAML: {dataset_yaml}')
        self.set_status('classes.txt saved.')

    def on_class_combo_changed(self, index: int) -> None:
        if index >= 0:
            self.set_status(f'Active class: {self.current_class_id()}')

    def on_selection_changed(self, index: int) -> None:
        if index < 0:
            self.selection_info.setText('No box selected. Right-click a box to select it.')
            return
        if index >= len(self.canvas.boxes):
            return
        box = self.canvas.boxes[index]
        class_name = self.state.class_names[box.class_id] if 0 <= box.class_id < len(self.state.class_names) else 'unknown'
        combo_index = self.class_combo.findData(box.class_id)
        if combo_index >= 0:
            self.class_combo.blockSignals(True)
            self.class_combo.setCurrentIndex(combo_index)
            self.class_combo.blockSignals(False)
        self.selection_info.setText(f'Selected box #{index + 1} • class {box.class_id}: {class_name}')
        self.set_status(f'Box #{index + 1} selected.')

    def on_boxes_changed(self) -> None:
        self.is_dirty = True
        box_count = len(self.canvas.boxes)
        self.set_status(f'{box_count} boxes on current image.')
