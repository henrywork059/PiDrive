from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QKeySequence, QShortcut
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

from custom_trainer.services.device_service import probe_runtime
from custom_trainer.services.ultralytics_runner import build_export_command, runner_working_directory
from custom_trainer.state import AppState
from custom_trainer.ui.qt_helpers import CommandWorker
from custom_trainer.ui.widgets.dock_workspace import DockWorkspacePage


class ExportPage(DockWorkspacePage):
    def __init__(self, state: AppState, log: Callable[[str], None], set_status: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__('export_dock_layout', parent)
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
        self.device_combo = QComboBox(self)
        self.device_combo.setEditable(True)
        self.device_summary = QLabel('Detecting runtime...', self)
        self.device_summary.setProperty('role', 'muted')
        self.device_summary.setWordWrap(True)
        self.quant_combo = QComboBox(self)
        self.quant_combo.addItems(['int8', 'float16', 'float32'])
        self.nms_check = QCheckBox('Embed NMS when supported', self)
        self.nms_check.setChecked(True)
        self.status_note = QLabel('Idle', self)
        self.status_note.setProperty('role', 'muted')
        self.export_button = QPushButton('Export Model', self)
        self.stop_button = QPushButton('Stop Export', self)
        self.stop_button.setEnabled(False)
        self.run_log_output = QPlainTextEdit(self)
        self.run_log_output.setReadOnly(True)
        self.run_log_output.setPlaceholderText('Export log will appear here...')
        self.export_button.clicked.connect(self.start_export)
        self.stop_button.clicked.connect(self.stop_export)

        self._build()
        self._setup_shortcuts()
        self.refresh_devices(log_runtime=False)

    def _build(self) -> None:
        config_box = QGroupBox('Export Config', self)
        form = QFormLayout(config_box)
        form.addRow('Weights (.pt)', self._path_row(self.weights_edit, self.choose_weights))
        form.addRow('dataset.yaml (needed for INT8)', self._path_row(self.yaml_edit, self.choose_yaml))
        form.addRow('Format', self.format_combo)
        form.addRow('Image Size', self.imgsz_edit)
        form.addRow('Device', self._device_row())
        form.addRow('', self.device_summary)
        form.addRow('Quantization', self.quant_combo)
        form.addRow('', self.nms_check)

        action_box = QGroupBox('Actions', self)
        action_layout = QHBoxLayout(action_box)
        use_current_button = QPushButton('Use Current Sessions Root', action_box)
        use_current_button.clicked.connect(self.use_current_root_defaults)
        latest_best_button = QPushButton('Use Latest best.pt', action_box)
        latest_best_button.clicked.connect(self.use_latest_best_weights)
        refresh_devices_button = QPushButton('Refresh Devices', action_box)
        refresh_devices_button.clicked.connect(lambda: self.refresh_devices(log_runtime=True))
        reset_layout_button = QPushButton('Reset Panels', action_box)
        reset_layout_button.clicked.connect(self.reset_panel_layout)
        action_layout.addWidget(use_current_button)
        action_layout.addWidget(latest_best_button)
        action_layout.addWidget(refresh_devices_button)
        action_layout.addWidget(reset_layout_button)
        action_layout.addWidget(self.export_button)
        action_layout.addWidget(self.stop_button)
        action_layout.addStretch(1)

        status_box = QGroupBox('Status', self)
        status_layout = QVBoxLayout(status_box)
        status_layout.addWidget(self.status_note)

        run_log_box = QGroupBox('Run Log', self)
        run_log_layout = QVBoxLayout(run_log_box)
        clear_log_layout = QHBoxLayout()
        clear_log_layout.addStretch(1)
        clear_log_button = QPushButton('Clear Log', run_log_box)
        clear_log_button.clicked.connect(self.run_log_output.clear)
        clear_log_layout.addWidget(clear_log_button)
        run_log_layout.addLayout(clear_log_layout)
        run_log_layout.addWidget(self.run_log_output, 1)

        info_box = QGroupBox('Pi Export Notes', self)
        info = QPlainTextEdit(self)
        info.setReadOnly(True)
        info.setPlainText(
            """Recommended Pi export path:

- format: tflite
- image size: 320 or 416
- quantization: int8 first, then float16 if needed
- device: Auto for desktop export, CPU for safest Pi-side compatibility

Useful additions in this build:
- Use Latest best.pt to grab your newest training result quickly
- Stop Export to terminate a long export task from the GUI
- Run Log captures the export command output directly on this page
- Drag panel title bars to snap or merge panels into tabs

Use dataset.yaml when exporting INT8 so calibration data is available."""
        )
        info_layout = QVBoxLayout(info_box)
        info_layout.addWidget(info)

        self.set_central_panel(run_log_box, title='Run Log')
        self.config_dock = self.create_dock('export_config_dock', 'Export Config', config_box, area=Qt.LeftDockWidgetArea)
        self.actions_dock = self.create_dock('export_actions_dock', 'Actions', action_box, area=Qt.LeftDockWidgetArea)
        self.status_dock = self.create_dock('export_status_dock', 'Status', status_box, area=Qt.LeftDockWidgetArea)
        self.notes_dock = self.create_dock('export_notes_dock', 'Pi Export Notes', info_box, area=Qt.RightDockWidgetArea)
        self.set_default_layout_builder(self._apply_default_layout)
        self._apply_default_layout()

    def _apply_default_layout(self) -> None:
        for dock in (self.config_dock, self.actions_dock, self.status_dock, self.notes_dock):
            dock.show()
            dock.setFloating(False)
        self.workspace.addDockWidget(Qt.LeftDockWidgetArea, self.config_dock)
        self.workspace.splitDockWidget(self.config_dock, self.actions_dock, Qt.Vertical)
        self.workspace.splitDockWidget(self.actions_dock, self.status_dock, Qt.Vertical)
        self.workspace.addDockWidget(Qt.RightDockWidgetArea, self.notes_dock)
        self.workspace.resizeDocks([self.config_dock, self.actions_dock, self.status_dock], [320, 170, 100], Qt.Vertical)

    def _setup_shortcuts(self) -> None:
        shortcuts: list[tuple[str, Callable[[], None]]] = [
            ('Ctrl+Return', self.start_export),
            ('Ctrl+U', self.use_current_root_defaults),
            ('Escape', self.stop_export),
            ('Ctrl+Shift+0', self.reset_panel_layout),
        ]
        for sequence, handler in shortcuts:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(handler)

    def shortcut_lines(self) -> list[str]:
        return [
            'Export: Ctrl+Enter start export',
            'Export: Esc stop export',
            'Export: Ctrl+U fill from current sessions root',
            'Export: Ctrl+Shift+0 reset dock layout',
        ]

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

    def _append_run_log(self, line: str) -> None:
        self.run_log_output.appendPlainText(line)

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
            self._append_run_log(f'[device] {probe.summary}')
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

    def use_current_root_defaults(self) -> None:
        dataset_yaml = self.state.preferred_dataset_yaml()
        if dataset_yaml is not None:
            self.yaml_edit.setText(str(dataset_yaml))
        self.refresh_devices(log_runtime=False)
        self.set_status('Export defaults filled from the current sessions root.')

    def use_latest_best_weights(self) -> None:
        best = self.state.latest_best_weights()
        if best is None:
            QMessageBox.information(self, 'No best.pt found', 'Train a model first, then try again.')
            return
        self.weights_edit.setText(str(best))
        self.set_status('Loaded latest best.pt into Export.')

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
        data = self.yaml_edit.text().strip() if int8 else ''
        if int8 and not data:
            QMessageBox.critical(self, 'dataset.yaml required', 'INT8 export needs dataset.yaml for calibration.')
            return
        command = build_export_command(
            weights=self.weights_edit.text().strip(),
            export_format=self.format_combo.currentText().strip(),
            imgsz=imgsz,
            device=self.current_device_value(),
            int8=int8,
            half=half,
            nms=self.nms_check.isChecked(),
            data=data,
        )
        self.run_log_output.clear()
        self._append_run_log(f'[cwd] {runner_working_directory()}')
        self.thread = QThread(self)
        self.worker = CommandWorker(command, cwd=runner_working_directory())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.line.connect(self._handle_worker_line)
        self.worker.finished.connect(self._on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)
        self.export_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_note.setText('Export started...')
        self.set_status('Export started...')
        self.thread.start()

    def stop_export(self) -> None:
        if self.worker is None:
            return
        self.worker.request_stop()
        self.stop_button.setEnabled(False)
        self.status_note.setText('Stopping export...')
        self.set_status('Stopping export...')

    def _handle_worker_line(self, line: str) -> None:
        self._append_run_log(line)
        self.log(line)

    def _on_finished(self, exit_code: int) -> None:
        self.export_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_note.setText(f'Finished with exit code {exit_code}.')
        self.set_status(f'Export finished with exit code {exit_code}.')

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None
