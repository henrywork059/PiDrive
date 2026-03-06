from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox, QSpinBox

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
        layout.addRow(self.only_manual)
        layout.addRow(self.augment)
        layout.addRow(self.session_split)
        layout.addRow(self.shuffle)

    def push_to_state(self) -> None:
        cfg = self.state.train_config
        cfg.img_h = self.img_h.value()
        cfg.img_w = self.img_w.value()
        cfg.batch_size = self.batch_size.value()
        cfg.epochs = self.epochs.value()
        cfg.learning_rate = self.learning_rate.value()
        cfg.val_ratio = self.val_ratio.value()
        cfg.only_manual = self.only_manual.isChecked()
        cfg.augment = self.augment.isChecked()
        cfg.session_split = self.session_split.isChecked()
        cfg.shuffle = self.shuffle.isChecked()
