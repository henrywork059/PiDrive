from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class FrameFilterPanel(QGroupBox):
    def __init__(self, apply_callback, clear_callback) -> None:
        super().__init__("Frame Filter")
        self.apply_callback = apply_callback
        self.clear_callback = clear_callback

        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Search session / frame_id / mode / ts")
        self.text_edit.returnPressed.connect(self.apply_callback)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["All Modes", "manual", "auto", "train", "user"])
        self.mode_combo.currentIndexChanged.connect(lambda *_: self.apply_callback())

        apply_btn = QPushButton("Apply Filter")
        apply_btn.clicked.connect(self.apply_callback)
        clear_btn = QPushButton("Clear Filter")
        clear_btn.clicked.connect(self.clear_callback)

        form = QVBoxLayout(self)
        form.addWidget(QLabel("Filter the loaded preview rows before selecting a frame."))

        row1 = QHBoxLayout()
        row1.addWidget(self.text_edit, 1)
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Mode"))
        row2.addWidget(self.mode_combo, 1)
        row2.addWidget(apply_btn)
        row2.addWidget(clear_btn)
        form.addLayout(row2)

    def filter_text(self) -> str:
        return self.text_edit.text().strip()

    def selected_mode(self) -> str:
        value = self.mode_combo.currentText().strip()
        return "" if value == "All Modes" else value

    def reset(self) -> None:
        self.text_edit.clear()
        self.mode_combo.setCurrentIndex(0)
