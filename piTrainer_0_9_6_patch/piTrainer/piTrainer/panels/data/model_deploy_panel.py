from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState
from ...services.data.model_deploy_service import MODEL_SOURCE_CURRENT, MODEL_SOURCE_SAVED, MODEL_SOURCE_TFLITE, latest_model_path
from ...ui.layout_widgets import CollapsibleSection, standardize_form_layout


class ModelDeployPanel(QGroupBox):
    """Run a model over visible Data rows and optionally apply predictions."""

    def __init__(
        self,
        state: AppState,
        deploy_callback: Callable[[], None],
        apply_selected_callback: Callable[[], None],
        sort_steering_diff_callback: Callable[[], None],
        sort_speed_diff_callback: Callable[[], None],
    ) -> None:
        super().__init__('Model Deploy')
        self.state = state
        self.deploy_callback = deploy_callback
        self.apply_selected_callback = apply_selected_callback
        self.sort_steering_diff_callback = sort_steering_diff_callback
        self.sort_speed_diff_callback = sort_speed_diff_callback
        self._selected_count = 0
        self._prediction_count = 0

        help_label = QLabel('Run a model on visible frames, compare AI output with labels, then apply AI output to selected rows.')
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.model_source_combo = QComboBox()
        self.model_source_combo.addItems([MODEL_SOURCE_CURRENT, MODEL_SOURCE_SAVED, MODEL_SOURCE_TFLITE])
        self.model_source_combo.currentTextChanged.connect(self._update_button_state)

        self.model_path_edit = QLineEdit()
        self.model_path_edit.setPlaceholderText('Model file path')
        self.model_path_edit.textChanged.connect(self._update_button_state)

        browse_btn = QPushButton('Browse')
        browse_btn.setProperty('role', 'secondary')
        browse_btn.clicked.connect(self._browse_model)

        latest_keras_btn = QPushButton('Use Latest Keras')
        latest_keras_btn.setProperty('role', 'secondary')
        latest_keras_btn.clicked.connect(self._use_latest_keras)

        latest_tflite_btn = QPushButton('Use Latest TFLite')
        latest_tflite_btn.setProperty('role', 'secondary')
        latest_tflite_btn.clicked.connect(self._use_latest_tflite)

        path_buttons = QWidget()
        path_row = QHBoxLayout(path_buttons)
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(browse_btn)
        path_row.addWidget(latest_keras_btn)
        path_row.addWidget(latest_tflite_btn)
        path_row.addStretch(1)

        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 512)
        self.batch_spin.setValue(max(1, int(getattr(self.state.train_config, 'batch_size', 32))))

        self.max_rows_spin = QSpinBox()
        self.max_rows_spin.setRange(0, 1000000)
        self.max_rows_spin.setSpecialValueText('All visible')
        self.max_rows_spin.setValue(0)

        model_widget, model_form = self._section_form()
        model_form.addRow('Source', self.model_source_combo)
        model_form.addRow('Model file', self.model_path_edit)
        model_form.addRow(path_buttons)
        model_form.addRow('Batch', self.batch_spin)
        model_form.addRow('Max rows', self.max_rows_spin)

        self.summary_label = QLabel('No deployed output yet.')
        self.summary_label.setProperty('role', 'summaryLine')
        self.summary_label.setWordWrap(True)

        self.deploy_btn = QPushButton('Deploy Visible')
        self.deploy_btn.setProperty('role', 'primary')
        self.deploy_btn.setToolTip('Run the selected model on the currently visible Records rows.')
        self.deploy_btn.clicked.connect(self.deploy_callback)

        self.sort_steer_btn = QPushButton('Sort Steer Diff')
        self.sort_steer_btn.setProperty('role', 'secondary')
        self.sort_steer_btn.clicked.connect(self.sort_steering_diff_callback)

        self.sort_speed_btn = QPushButton('Sort Speed Diff')
        self.sort_speed_btn.setProperty('role', 'secondary')
        self.sort_speed_btn.clicked.connect(self.sort_speed_diff_callback)

        self.confirm_apply_check = QCheckBox('Confirm Apply')
        self.confirm_apply_check.setToolTip('Required before overwriting selected labels with deployed AI output.')
        self.confirm_apply_check.toggled.connect(self._update_button_state)

        self.apply_selected_btn = QPushButton('Apply AI to Selected')
        self.apply_selected_btn.setProperty('role', 'amber')
        self.apply_selected_btn.clicked.connect(self.apply_selected_callback)

        sort_row = QHBoxLayout()
        sort_row.addWidget(self.sort_steer_btn)
        sort_row.addWidget(self.sort_speed_btn)
        sort_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(CollapsibleSection('Model', model_widget, expanded=True))
        layout.addWidget(self.deploy_btn)
        layout.addWidget(self.summary_label)
        layout.addLayout(sort_row)
        layout.addWidget(self.confirm_apply_check)
        layout.addWidget(self.apply_selected_btn)
        layout.addStretch(1)
        self._update_button_state()

    def _section_form(self) -> tuple[QWidget, QFormLayout]:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(form)
        return widget, form

    def model_source(self) -> str:
        return self.model_source_combo.currentText()

    def model_path(self) -> str:
        return self.model_path_edit.text().strip()

    def batch_size(self) -> int:
        return int(self.batch_spin.value())

    def max_rows(self) -> int:
        return int(self.max_rows_spin.value())

    def apply_confirmed(self) -> bool:
        return bool(self.confirm_apply_check.isChecked())

    def set_selected_count(self, count: int) -> None:
        self._selected_count = max(0, int(count))
        self._update_button_state()

    def set_prediction_count(self, count: int) -> None:
        self._prediction_count = max(0, int(count))
        if self._prediction_count:
            self.summary_label.setText(f'Deployed output: {self._prediction_count} frame(s). Sort by diff or apply selected rows.')
        else:
            self.summary_label.setText('No deployed output yet.')
        self._update_button_state()

    def _model_path_needed(self) -> bool:
        return self.model_source() in {MODEL_SOURCE_SAVED, MODEL_SOURCE_TFLITE}

    def _can_deploy(self) -> bool:
        if not self._model_path_needed():
            return True
        return bool(self.model_path())

    def _can_apply(self) -> bool:
        return self._prediction_count > 0 and self._selected_count > 0 and self.apply_confirmed()

    def _update_button_state(self) -> None:
        self.model_path_edit.setEnabled(self._model_path_needed())
        if not hasattr(self, 'deploy_btn'):
            return
        self.deploy_btn.setEnabled(self._can_deploy())
        self.sort_steer_btn.setEnabled(self._prediction_count > 0)
        self.sort_speed_btn.setEnabled(self._prediction_count > 0)
        self.apply_selected_btn.setEnabled(self._can_apply())

    def _browse_model(self) -> None:
        source = self.model_source()
        if source == MODEL_SOURCE_TFLITE:
            file_filter = 'TFLite Models (*.tflite);;All Files (*)'
            title = 'Choose TFLite model'
        else:
            file_filter = 'Keras Models (*.keras *.h5);;TFLite Models (*.tflite);;All Files (*)'
            title = 'Choose model file'
        path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(Path(self.state.export_config.out_dir).expanduser()),
            file_filter,
        )
        if not path:
            return
        self.model_path_edit.setText(path)
        if path.lower().endswith('.tflite'):
            self.model_source_combo.setCurrentText(MODEL_SOURCE_TFLITE)
        else:
            self.model_source_combo.setCurrentText(MODEL_SOURCE_SAVED)

    def _use_latest_keras(self) -> None:
        last_model = str(getattr(self.state, 'last_saved_model_path', '') or '').strip()
        path = last_model if last_model and Path(last_model).expanduser().exists() else ''
        if not path:
            trained_dir = str(getattr(self.state, 'trained_model_out_dir', '') or '').strip()
            if trained_dir:
                path = latest_model_path(trained_dir, include_tflite=False)
        if not path:
            path = latest_model_path(self.state.export_config.out_dir, include_tflite=False)
        if path:
            self.model_path_edit.setText(path)
            self.model_source_combo.setCurrentText(MODEL_SOURCE_SAVED)

    def _use_latest_tflite(self) -> None:
        last_tflite = str(getattr(self.state, 'last_exported_tflite_path', '') or '').strip()
        path = last_tflite if last_tflite and Path(last_tflite).expanduser().exists() else ''
        if not path:
            path = latest_model_path(self.state.export_config.out_dir, include_tflite=True)
        if path:
            self.model_path_edit.setText(path)
            self.model_source_combo.setCurrentText(MODEL_SOURCE_TFLITE)
