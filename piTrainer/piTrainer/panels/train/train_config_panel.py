from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QSpinBox, QVBoxLayout, QWidget

from ...app_state import AppState
from ...ui.layout_widgets import CollapsibleSection, standardize_form_layout


class TrainConfigPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__("Training Config")
        self.state = state
        cfg = self.state.train_config

        self.img_h = QSpinBox(); self.img_h.setRange(32, 1080); self.img_h.setValue(cfg.img_h)
        self.img_w = QSpinBox(); self.img_w.setRange(32, 1920); self.img_w.setValue(cfg.img_w)
        self.batch_size = QSpinBox(); self.batch_size.setRange(1, 1024); self.batch_size.setValue(cfg.batch_size)
        self.epochs = QSpinBox(); self.epochs.setRange(1, 10000); self.epochs.setValue(cfg.epochs)

        self.learning_rate = QDoubleSpinBox(); self.learning_rate.setRange(1e-6, 1.0); self.learning_rate.setDecimals(6); self.learning_rate.setSingleStep(0.0001); self.learning_rate.setValue(cfg.learning_rate)
        self.val_ratio = QDoubleSpinBox(); self.val_ratio.setRange(0.05, 0.95); self.val_ratio.setDecimals(2); self.val_ratio.setSingleStep(0.05); self.val_ratio.setValue(cfg.val_ratio)

        self.model_size = QComboBox(); self.model_size.addItems(['Small CNN', 'Medium CNN']); self.model_size.setCurrentText(getattr(cfg, 'model_size', 'Small CNN'))
        self.split_mode = QComboBox(); self.split_mode.addItems(['By session', 'Random rows', 'Sequential rows']); self.split_mode.setCurrentText(getattr(cfg, 'split_mode', 'By session'))
        self.seed = QSpinBox(); self.seed.setRange(0, 999999); self.seed.setValue(getattr(cfg, 'seed', 42))

        self.dropout_rate = QDoubleSpinBox(); self.dropout_rate.setRange(0.0, 0.8); self.dropout_rate.setDecimals(2); self.dropout_rate.setSingleStep(0.05); self.dropout_rate.setValue(float(getattr(cfg, 'dropout_rate', 0.2) or 0.2))
        self.steering_loss_weight = QDoubleSpinBox(); self.steering_loss_weight.setRange(0.1, 10.0); self.steering_loss_weight.setDecimals(2); self.steering_loss_weight.setSingleStep(0.1); self.steering_loss_weight.setValue(float(getattr(cfg, 'steering_loss_weight', 1.0) or 1.0))
        self.throttle_loss_weight = QDoubleSpinBox(); self.throttle_loss_weight.setRange(0.1, 10.0); self.throttle_loss_weight.setDecimals(2); self.throttle_loss_weight.setSingleStep(0.1); self.throttle_loss_weight.setValue(float(getattr(cfg, 'throttle_loss_weight', 1.0) or 1.0))
        self.clipnorm = QDoubleSpinBox(); self.clipnorm.setRange(0.0, 10.0); self.clipnorm.setDecimals(2); self.clipnorm.setSingleStep(0.1); self.clipnorm.setValue(float(getattr(cfg, 'clipnorm', 0.0) or 0.0))
        self.l2_reg = QDoubleSpinBox(); self.l2_reg.setRange(0.0, 0.1); self.l2_reg.setDecimals(5); self.l2_reg.setSingleStep(0.0005); self.l2_reg.setValue(float(getattr(cfg, 'l2_reg', 0.0) or 0.0))
        self.review_sample_count = QSpinBox(); self.review_sample_count.setRange(4, 256); self.review_sample_count.setSingleStep(4); self.review_sample_count.setValue(int(getattr(cfg, 'review_sample_count', 24) or 24))
        self.compute_device = QComboBox(); self.compute_device.addItems(['Auto (GPU if available)', 'CPU only', 'GPU only']); self.compute_device.setCurrentText(str(getattr(cfg, 'compute_device', 'Auto (GPU if available)') or 'Auto (GPU if available)'))
        self.compute_device.setToolTip('Auto uses TensorFlow GPU acceleration when the installed TensorFlow build can see a GPU. CPU only hides GPUs for safer compatibility. GPU only fails early if no GPU is available.')

        self.early_stopping = QCheckBox('Enable early stopping'); self.early_stopping.setChecked(getattr(cfg, 'early_stopping', True))
        self.early_stopping_patience = QSpinBox(); self.early_stopping_patience.setRange(1, 100); self.early_stopping_patience.setValue(getattr(cfg, 'early_stopping_patience', 4))
        self.reduce_lr = QCheckBox('Reduce learning rate on plateau'); self.reduce_lr.setChecked(getattr(cfg, 'reduce_lr_on_plateau', True))
        self.reduce_lr_patience = QSpinBox(); self.reduce_lr_patience.setRange(1, 100); self.reduce_lr_patience.setValue(getattr(cfg, 'reduce_lr_patience', 2))
        self.reduce_lr_factor = QDoubleSpinBox(); self.reduce_lr_factor.setRange(0.05, 0.95); self.reduce_lr_factor.setDecimals(2); self.reduce_lr_factor.setSingleStep(0.05); self.reduce_lr_factor.setValue(getattr(cfg, 'reduce_lr_factor', 0.5))

        self.only_manual = QCheckBox("Use only manual-mode rows when possible"); self.only_manual.setChecked(cfg.only_manual)
        self.augment = QCheckBox("Enable light image augmentation"); self.augment.setChecked(cfg.augment)
        self.shuffle = QCheckBox("Shuffle training rows"); self.shuffle.setChecked(cfg.shuffle)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(CollapsibleSection('Input Size + Split', self._input_split_section(), expanded=True))
        layout.addWidget(CollapsibleSection('Model + Loss', self._model_loss_section(), expanded=False))
        layout.addWidget(CollapsibleSection('Training Schedule', self._schedule_section(), expanded=True))
        layout.addWidget(CollapsibleSection('Device + Review Options', self._device_review_section(), expanded=True))
        layout.addWidget(CollapsibleSection('Advanced Dataset Options', self._review_options_section(), expanded=False))
        layout.addStretch(1)

        self.early_stopping.toggled.connect(self._update_enabled_state)
        self.reduce_lr.toggled.connect(self._update_enabled_state)
        self._update_enabled_state()

    def _section_form(self) -> tuple[QWidget, QFormLayout]:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(form)
        return widget, form

    def _input_split_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow("Image height", self.img_h)
        form.addRow("Image width", self.img_w)
        form.addRow("Validation ratio", self.val_ratio)
        form.addRow("Split mode", self.split_mode)
        form.addRow("Random seed", self.seed)
        return widget

    def _model_loss_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow("Model size", self.model_size)
        form.addRow("Dropout rate", self.dropout_rate)
        form.addRow("Steering loss weight", self.steering_loss_weight)
        form.addRow("Speed loss weight", self.throttle_loss_weight)
        form.addRow("Gradient clipnorm", self.clipnorm)
        form.addRow("L2 regularization", self.l2_reg)
        return widget

    def _schedule_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow("Batch size", self.batch_size)
        form.addRow("Epochs", self.epochs)
        form.addRow("Learning rate", self.learning_rate)
        form.addRow(self.early_stopping)
        form.addRow("Early-stop patience", self.early_stopping_patience)
        form.addRow(self.reduce_lr)
        form.addRow("LR patience", self.reduce_lr_patience)
        form.addRow("LR factor", self.reduce_lr_factor)
        return widget

    def _device_review_section(self) -> QWidget:
        widget, form = self._section_form()
        note = QLabel('Leave this on Auto. TensorFlow will use a GPU when a compatible GPU build/driver is available, otherwise it will continue on CPU.')
        note.setWordWrap(True)
        note.setProperty('role', 'muted')
        form.addRow(note)
        form.addRow('Training device', self.compute_device)
        form.addRow('Epoch review samples', self.review_sample_count)
        return widget

    def _review_options_section(self) -> QWidget:
        widget, form = self._section_form()
        form.addRow(self.only_manual)
        form.addRow(self.augment)
        form.addRow(self.shuffle)
        return widget

    def _update_enabled_state(self) -> None:
        self.early_stopping_patience.setEnabled(self.early_stopping.isChecked())
        reduce_enabled = self.reduce_lr.isChecked()
        self.reduce_lr_patience.setEnabled(reduce_enabled)
        self.reduce_lr_factor.setEnabled(reduce_enabled)

    def push_to_state(self) -> None:
        cfg = self.state.train_config
        cfg.img_h = self.img_h.value()
        cfg.img_w = self.img_w.value()
        cfg.batch_size = self.batch_size.value()
        cfg.epochs = self.epochs.value()
        cfg.learning_rate = self.learning_rate.value()
        cfg.val_ratio = self.val_ratio.value()
        cfg.model_size = self.model_size.currentText()
        cfg.seed = self.seed.value()
        cfg.early_stopping = self.early_stopping.isChecked()
        cfg.early_stopping_patience = self.early_stopping_patience.value()
        cfg.reduce_lr_on_plateau = self.reduce_lr.isChecked()
        cfg.reduce_lr_patience = self.reduce_lr_patience.value()
        cfg.reduce_lr_factor = self.reduce_lr_factor.value()
        cfg.only_manual = self.only_manual.isChecked()
        cfg.augment = self.augment.isChecked()
        cfg.shuffle = self.shuffle.isChecked()
        cfg.split_mode = self.split_mode.currentText()
        cfg.session_split = cfg.split_mode == 'By session'
        cfg.dropout_rate = self.dropout_rate.value()
        cfg.steering_loss_weight = self.steering_loss_weight.value()
        cfg.throttle_loss_weight = self.throttle_loss_weight.value()
        cfg.clipnorm = self.clipnorm.value()
        cfg.l2_reg = self.l2_reg.value()
        cfg.review_sample_count = self.review_sample_count.value()
        cfg.compute_device = self.compute_device.currentText()
