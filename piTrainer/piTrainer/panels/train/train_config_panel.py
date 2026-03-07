from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QSpinBox

from ...app_state import AppState


class TrainConfigPanel(QGroupBox):
    def __init__(self, state: AppState) -> None:
        super().__init__("Training Config")
        self.state = state
        cfg = self.state.train_config

        self.img_h = QSpinBox()
        self.img_h.setRange(32, 1080)
        self.img_h.setValue(cfg.img_h)

        self.img_w = QSpinBox()
        self.img_w.setRange(32, 1920)
        self.img_w.setValue(cfg.img_w)

        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 1024)
        self.batch_size.setValue(cfg.batch_size)

        self.epochs = QSpinBox()
        self.epochs.setRange(1, 10000)
        self.epochs.setValue(cfg.epochs)

        self.learning_rate = QDoubleSpinBox()
        self.learning_rate.setRange(1e-6, 1.0)
        self.learning_rate.setDecimals(6)
        self.learning_rate.setSingleStep(0.0001)
        self.learning_rate.setValue(cfg.learning_rate)

        self.val_ratio = QDoubleSpinBox()
        self.val_ratio.setRange(0.05, 0.95)
        self.val_ratio.setDecimals(2)
        self.val_ratio.setSingleStep(0.05)
        self.val_ratio.setValue(cfg.val_ratio)

        self.model_size = QComboBox()
        self.model_size.addItems(['Small CNN', 'Medium CNN'])
        self.model_size.setCurrentText(getattr(cfg, 'model_size', 'Small CNN'))

        self.seed = QSpinBox()
        self.seed.setRange(0, 999999)
        self.seed.setValue(getattr(cfg, 'seed', 42))

        self.early_stopping = QCheckBox('Enable early stopping')
        self.early_stopping.setChecked(getattr(cfg, 'early_stopping', True))
        self.early_stopping_patience = QSpinBox()
        self.early_stopping_patience.setRange(1, 100)
        self.early_stopping_patience.setValue(getattr(cfg, 'early_stopping_patience', 4))

        self.reduce_lr = QCheckBox('Reduce learning rate on plateau')
        self.reduce_lr.setChecked(getattr(cfg, 'reduce_lr_on_plateau', True))
        self.reduce_lr_patience = QSpinBox()
        self.reduce_lr_patience.setRange(1, 100)
        self.reduce_lr_patience.setValue(getattr(cfg, 'reduce_lr_patience', 2))
        self.reduce_lr_factor = QDoubleSpinBox()
        self.reduce_lr_factor.setRange(0.05, 0.95)
        self.reduce_lr_factor.setDecimals(2)
        self.reduce_lr_factor.setSingleStep(0.05)
        self.reduce_lr_factor.setValue(getattr(cfg, 'reduce_lr_factor', 0.5))

        self.only_manual = QCheckBox("Use only manual-mode rows when possible")
        self.only_manual.setChecked(cfg.only_manual)
        self.augment = QCheckBox("Enable light image augmentation")
        self.augment.setChecked(cfg.augment)
        self.session_split = QCheckBox("Split by session")
        self.session_split.setChecked(cfg.session_split)
        self.shuffle = QCheckBox("Shuffle training rows")
        self.shuffle.setChecked(cfg.shuffle)

        layout = QFormLayout(self)
        layout.addRow("Image height", self.img_h)
        layout.addRow("Image width", self.img_w)
        layout.addRow("Batch size", self.batch_size)
        layout.addRow("Epochs", self.epochs)
        layout.addRow("Learning rate", self.learning_rate)
        layout.addRow("Validation ratio", self.val_ratio)
        layout.addRow("Model size", self.model_size)
        layout.addRow("Random seed", self.seed)
        layout.addRow(self.early_stopping)
        layout.addRow("Early-stop patience", self.early_stopping_patience)
        layout.addRow(self.reduce_lr)
        layout.addRow("LR patience", self.reduce_lr_patience)
        layout.addRow("LR factor", self.reduce_lr_factor)
        layout.addRow(self.only_manual)
        layout.addRow(self.augment)
        layout.addRow(self.session_split)
        layout.addRow(self.shuffle)

        self.early_stopping.toggled.connect(self._update_enabled_state)
        self.reduce_lr.toggled.connect(self._update_enabled_state)
        self._update_enabled_state()

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
        cfg.session_split = self.session_split.isChecked()
        cfg.shuffle = self.shuffle.isChecked()
