from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...ui.layout_widgets import standardize_form_layout, style_next_step_button


class TrainControlPanel(QGroupBox):
    SETTINGS_KEY = 'train/last_model_save_dir'

    def __init__(self, prepare_callback, start_callback, stop_callback, save_model_callback, default_save_dir: str = '') -> None:
        super().__init__("Controls")
        self.prepare_btn = QPushButton("Prepare Split")
        self.prepare_btn.setProperty('role', 'amber')
        self.prepare_btn.clicked.connect(prepare_callback)
        self.start_btn = QPushButton("Start Training")
        style_next_step_button(self.start_btn, "Start Training")
        self.start_btn.clicked.connect(start_callback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setProperty('role', 'danger')
        self.stop_btn.clicked.connect(stop_callback)
        self.stop_btn.setEnabled(False)
        self.save_model_btn = QPushButton('Save Model')
        self.save_model_btn.setProperty('role', 'secondary')
        self.save_model_btn.clicked.connect(save_model_callback)

        self.save_dir_edit = QLineEdit(self._restore_last_model_save_dir() or str(default_save_dir or ''))
        self.save_dir_edit.setPlaceholderText('Folder for saved .keras model')
        self.browse_save_dir_btn = QPushButton('Browse')
        self.browse_save_dir_btn.setProperty('role', 'amber')
        self.browse_save_dir_btn.clicked.connect(self._browse_model_save_dir)

        save_dir_widget = QWidget()
        save_dir_layout = QHBoxLayout(save_dir_widget)
        save_dir_layout.setContentsMargins(0, 0, 0, 0)
        save_dir_layout.addWidget(self.save_dir_edit, 1)
        save_dir_layout.addWidget(self.browse_save_dir_btn)

        save_form_widget = QWidget()
        save_form = QFormLayout(save_form_widget)
        save_form.setContentsMargins(0, 0, 0, 0)
        standardize_form_layout(save_form)
        save_form.addRow('Model save folder', save_dir_widget)

        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)

        row1 = QHBoxLayout(); row1.addWidget(self.prepare_btn); row1.addWidget(self.stop_btn)
        row2 = QHBoxLayout(); row2.addWidget(self.save_model_btn); row2.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(row1)
        layout.addWidget(self.start_btn)
        layout.addWidget(save_form_widget)
        layout.addLayout(row2)
        layout.addWidget(self.progress)

    def _settings(self) -> QSettings:
        return QSettings('OpenAI', 'PiTrainer')

    def _restore_last_model_save_dir(self) -> str:
        return str(self._settings().value(self.SETTINGS_KEY, '') or '').strip()

    def _dialog_start_dir(self) -> str:
        current = self.model_save_dir()
        if current:
            path = Path(current).expanduser()
            if path.exists():
                return str(path)
            if path.parent.exists():
                return str(path.parent)
        return str(Path.home())

    def _browse_model_save_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Choose model save folder', self._dialog_start_dir())
        if folder:
            self.set_model_save_dir(folder)

    def set_model_save_dir(self, folder: str) -> None:
        cleaned = str(folder or '').strip()
        self.save_dir_edit.setText(cleaned)
        if cleaned:
            self._settings().setValue(self.SETTINGS_KEY, cleaned)

    def model_save_dir(self, fallback: str = '') -> str:
        cleaned = self.save_dir_edit.text().strip()
        return cleaned or str(fallback or '').strip()

    def set_running(self, running: bool) -> None:
        self.prepare_btn.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.save_model_btn.setEnabled(not running)
        self.browse_save_dir_btn.setEnabled(not running)
        self.save_dir_edit.setEnabled(not running)
        if not running:
            self.progress.setValue(0)

    def set_progress(self, value: int) -> None:
        self.progress.setValue(max(0, min(100, int(value))))
