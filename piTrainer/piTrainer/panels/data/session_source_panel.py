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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState
from ...ui.layout_widgets import style_next_step_button


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

    def __init__(self, state: AppState, refresh_callback, load_callback, selection_changed_callback=None) -> None:
        super().__init__('Session Source')
        self.setObjectName('sessionSourcePanel')
        self.state = state
        self.refresh_callback = refresh_callback
        self.load_callback = load_callback
        self.selection_changed_callback = selection_changed_callback
        self._rows: list[SessionSourceRowWidget] = []
        self._suspend_selection_callback = False
        self._min_visible_session_rows = 5
        self._max_visible_session_rows = 16

        help_label = QLabel(
            'Choose a records root, refresh sessions, select sessions, then load.'
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.path_edit = QLineEdit(self._restore_last_root() or self.state.records_root)
        self.path_edit.setPlaceholderText('Records root folder')
        self.path_edit.editingFinished.connect(self._apply_path_only)

        browse_btn = QPushButton('Browse')
        browse_btn.setProperty('role', 'amber')
        browse_btn.clicked.connect(self._browse)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.setProperty('role', 'amber')
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
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self._resize_session_list()

        select_all_btn = QPushButton('Select All')
        select_all_btn.setProperty('role', 'secondary')
        select_all_btn.clicked.connect(self.select_all)
        clear_btn = QPushButton('Clear')
        clear_btn.setProperty('role', 'secondary')
        clear_btn.clicked.connect(self.clear_all)
        self.load_btn = QPushButton('Load Selected')
        style_next_step_button(self.load_btn, 'Load Selected')
        self.load_btn.clicked.connect(self.load_callback)

        select_row = QHBoxLayout()
        select_row.addWidget(select_all_btn)
        select_row.addWidget(clear_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addLayout(path_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(select_row)
        layout.addWidget(self.load_btn)

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
        row.checkbox.toggled.connect(self._on_selection_changed)
        return row

    def set_sessions(self, sessions: list[str]) -> None:
        selected = set(self.selected_sessions())
        self._suspend_selection_callback = True
        try:
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
        finally:
            self._suspend_selection_callback = False
        self._resize_session_list()
        self._update_summary()

    def _resize_session_list(self) -> None:
        """Grow the session list with the scanned rows so more sessions are visible.

        The workflow sidebar itself remains scrollable, so increasing this
        minimum height is safer than forcing an inner list scrollbar after only
        a few sessions. A cap keeps the list from swallowing the whole Data
        workflow panel when a records root contains many sessions.
        """
        row_count = len(self._rows)
        visible_rows = min(
            max(row_count, self._min_visible_session_rows),
            self._max_visible_session_rows,
        )
        sample_height = 42
        if self._rows:
            sample_height = max(sample_height, max(row.sizeHint().height() for row in self._rows))
        spacing = max(0, int(self.list_widget.spacing()))
        frame_padding = 18
        target_height = int((sample_height + spacing) * visible_rows + frame_padding)
        self.list_widget.setMinimumHeight(max(180, target_height))
        self.list_widget.updateGeometry()

    def selected_sessions(self) -> list[str]:
        selected: list[str] = []
        for row in self._rows:
            if row.checkbox.isChecked():
                selected.append(row.session_name())
        return selected

    def set_selected_sessions(self, sessions: list[str]) -> None:
        wanted = set(sessions)
        self._suspend_selection_callback = True
        try:
            for row in self._rows:
                row.checkbox.setChecked(row.session_name() in wanted)
        finally:
            self._suspend_selection_callback = False
        self._on_selection_changed()

    def select_all(self) -> None:
        self._suspend_selection_callback = True
        try:
            for row in self._rows:
                row.checkbox.setChecked(True)
        finally:
            self._suspend_selection_callback = False
        self._on_selection_changed()

    def clear_all(self) -> None:
        self._suspend_selection_callback = True
        try:
            for row in self._rows:
                row.checkbox.setChecked(False)
        finally:
            self._suspend_selection_callback = False
        self._on_selection_changed()

    def current_records_root(self) -> str:
        return self.path_edit.text().strip()

    def _on_selection_changed(self) -> None:
        self._update_summary()
        if self._suspend_selection_callback:
            return
        if callable(self.selection_changed_callback):
            self.selection_changed_callback(self.selected_sessions())

    def _update_summary(self) -> None:
        root = self.current_records_root()
        total = len(self._rows)
        selected = len(self.selected_sessions())
        if not root:
            self.summary_label.setText('Choose a records root to find sessions.')
            return
        if total == 0:
            self.summary_label.setText(f"Root: {root} | No sessions found.")
            return
        self.summary_label.setText(f"Root: {root} | Found: {total} | Selected: {selected}")
