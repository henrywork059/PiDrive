from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState


class SessionSourceRowWidget(QFrame):
    def __init__(self, session: str, checked: bool) -> None:
        super().__init__()
        self.setObjectName('sessionRow')
        self.checkbox = QCheckBox()
        self.checkbox.setObjectName('sessionRowCheckbox')
        self.checkbox.setChecked(checked)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.name_label = QLabel(session)
        self.name_label.setObjectName('sessionRowLabel')
        self.name_label.setWordWrap(True)
        self.name_label.setTextInteractionFlags(Qt.NoTextInteraction)

        row_layout = QHBoxLayout(self)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(10)
        row_layout.addWidget(self.checkbox, 0, Qt.AlignTop)
        row_layout.addWidget(self.name_label, 1)

    def session_name(self) -> str:
        return self.name_label.text()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mouseReleaseEvent(event)


class SessionSourcePanel(QGroupBox):
    SETTINGS_KEY = 'data/last_records_root'

    def __init__(self, state: AppState, refresh_callback, load_callback) -> None:
        super().__init__('Session Source')
        self.setObjectName('sessionSourcePanel')
        self.state = state
        self.refresh_callback = refresh_callback
        self.load_callback = load_callback
        self._rows: list[SessionSourceRowWidget] = []

        help_label = QLabel(
            'Choose the records root, scan for sessions, then select one or more sessions to load.'
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.path_edit = QLineEdit(self._restore_last_root() or self.state.records_root)
        self.path_edit.setPlaceholderText('Folder containing session folders and records.jsonl files')
        self.path_edit.editingFinished.connect(self._apply_path_only)

        browse_btn = QPushButton('Browse')
        browse_btn.clicked.connect(self._browse)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._refresh)

        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse_btn)
        path_row.addWidget(refresh_btn)

        self.summary_label = QLabel('No sessions scanned yet.')
        self.summary_label.setWordWrap(True)
        self.summary_label.setProperty('role', 'muted')

        self.list_widget = QListWidget()
        self.list_widget.setObjectName('sessionListWidget')
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setSpacing(6)
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setUniformItemSizes(False)

        select_all_btn = QPushButton('Select All')
        select_all_btn.clicked.connect(self.select_all)
        clear_btn = QPushButton('Clear')
        clear_btn.clicked.connect(self.clear_all)
        load_btn = QPushButton('Load Selected')
        load_btn.clicked.connect(self.load_callback)

        buttons = QHBoxLayout()
        buttons.addWidget(select_all_btn)
        buttons.addWidget(clear_btn)
        buttons.addWidget(load_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(path_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(buttons)

        self._apply_path_only()
        self._update_summary()

    def _settings(self) -> QSettings:
        return QSettings('OpenAI', 'PiTrainer')

    def _restore_last_root(self) -> str:
        settings = self._settings()
        value = settings.value(self.SETTINGS_KEY, '')
        restored = str(value or '').strip()
        if restored:
            self.state.records_root = restored
        return restored

    def _save_last_root(self, path: str) -> None:
        self._settings().setValue(self.SETTINGS_KEY, path)

    def _apply_path_only(self) -> None:
        path = self.path_edit.text().strip()
        self.state.records_root = path
        if path:
            self._save_last_root(path)
        self._update_summary()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Choose records root', self.path_edit.text().strip())
        if folder:
            self.path_edit.setText(folder)
            self._apply_path_only()
            self.refresh_callback()

    def _refresh(self) -> None:
        self._apply_path_only()
        self.refresh_callback()

    def _build_row_widget(self, session: str, checked: bool) -> QWidget:
        row = SessionSourceRowWidget(session, checked)
        row.checkbox.toggled.connect(self._update_summary)
        return row

    def set_sessions(self, sessions: list[str]) -> None:
        selected = set(self.selected_sessions())
        self.list_widget.clear()
        self._rows.clear()
        for session in sessions:
            row_widget = self._build_row_widget(session, session in selected)
            item = QListWidgetItem(self.list_widget)
            item.setFlags(Qt.ItemIsEnabled)
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row_widget)
            self._rows.append(row_widget)
        self._update_summary()

    def selected_sessions(self) -> list[str]:
        selected: list[str] = []
        for row in self._rows:
            if row.checkbox.isChecked():
                selected.append(row.session_name())
        return selected

    def set_selected_sessions(self, sessions: list[str]) -> None:
        wanted = set(sessions)
        for row in self._rows:
            row.checkbox.setChecked(row.session_name() in wanted)
        self._update_summary()

    def select_all(self) -> None:
        for row in self._rows:
            row.checkbox.setChecked(True)
        self._update_summary()

    def clear_all(self) -> None:
        for row in self._rows:
            row.checkbox.setChecked(False)
        self._update_summary()

    def current_records_root(self) -> str:
        return self.path_edit.text().strip()

    def _update_summary(self) -> None:
        root = self.current_records_root()
        total = len(self._rows)
        selected = len(self.selected_sessions())
        if not root:
            self.summary_label.setText('Choose a records root folder to find sessions.')
            return
        if total == 0:
            self.summary_label.setText(f"Root: {root} | No sessions found yet.")
            return
        self.summary_label.setText(f"Root: {root} | Sessions found: {total} | Selected: {selected}")
