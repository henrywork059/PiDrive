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


class SessionListResizeHandle(QFrame):
    def __init__(self, get_height, set_height, reset_height) -> None:
        super().__init__()
        self.setObjectName('sessionListResizeHandle')
        self.setCursor(Qt.SizeVerCursor)
        self.setFixedHeight(10)
        self.setToolTip(
            'Drag up or down to resize the session list. Double-click to reset.'
        )
        try:
            self.setFrameShape(QFrame.Shape.HLine)
        except AttributeError:
            self.setFrameShape(QFrame.HLine)
        self._get_height = get_height
        self._set_height = set_height
        self._reset_height = reset_height
        self._drag_start_y: int | None = None
        self._drag_start_height: int | None = None

    @staticmethod
    def _event_global_y(event) -> int:
        if hasattr(event, 'globalPosition'):
            return int(event.globalPosition().y())
        return int(event.globalPos().y())

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_start_y = self._event_global_y(event)
            self._drag_start_height = int(self._get_height())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_start_y is not None and self._drag_start_height is not None:
            delta_y = self._event_global_y(event) - self._drag_start_y
            self._set_height(self._drag_start_height + delta_y, persist=False)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        is_drag_release = (
            event.button() == Qt.LeftButton
            and self._drag_start_y is not None
            and self._drag_start_height is not None
        )
        if is_drag_release:
            delta_y = self._event_global_y(event) - self._drag_start_y
            self._set_height(self._drag_start_height + delta_y, persist=True)
            self._drag_start_y = None
            self._drag_start_height = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_start_y = None
            self._drag_start_height = None
            self._reset_height()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class SessionSourcePanel(QGroupBox):
    SETTINGS_KEY = 'data/last_records_root'
    LIST_HEIGHT_SETTINGS_KEY = 'data/session_source_list_height'

    def __init__(
        self,
        state: AppState,
        refresh_callback,
        load_callback,
        selection_changed_callback=None,
    ) -> None:
        super().__init__('Session Source')
        self.setObjectName('sessionSourcePanel')
        self.state = state
        self.refresh_callback = refresh_callback
        self.load_callback = load_callback
        self.selection_changed_callback = selection_changed_callback
        self._rows: list[SessionSourceRowWidget] = []
        self._suspend_selection_callback = False
        self._session_list_default_height = 260
        self._session_list_min_height = 180
        self._session_list_max_height = 900
        self._session_list_height = self._restore_session_list_height()

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
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._resize_session_list()
        self.resize_handle = SessionListResizeHandle(
            self._current_session_list_height,
            self._set_session_list_height,
            self._reset_session_list_height,
        )

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
        layout.addWidget(self.list_widget)
        layout.addWidget(self.resize_handle)
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

    def _restore_session_list_height(self) -> int:
        value = self._settings().value(
            self.LIST_HEIGHT_SETTINGS_KEY,
            self._session_list_default_height,
        )
        try:
            height = int(float(value))
        except (TypeError, ValueError):
            height = self._session_list_default_height
        return self._clamp_session_list_height(height)

    def _save_session_list_height(self, height: int) -> None:
        self._settings().setValue(self.LIST_HEIGHT_SETTINGS_KEY, int(height))

    def _clamp_session_list_height(self, height: int) -> int:
        return max(
            self._session_list_min_height,
            min(self._session_list_max_height, int(height)),
        )

    def _current_session_list_height(self) -> int:
        return self._clamp_session_list_height(
            self._session_list_height or self.list_widget.height()
        )

    def _set_session_list_height(self, height: int, persist: bool = True) -> None:
        height = self._clamp_session_list_height(height)
        self._session_list_height = height
        self.list_widget.setMinimumHeight(height)
        self.list_widget.setMaximumHeight(height)
        self.list_widget.updateGeometry()
        if persist:
            self._save_session_list_height(height)

    def _reset_session_list_height(self) -> None:
        self._set_session_list_height(self._session_list_default_height, persist=True)

    def _resize_session_list(self) -> None:
        """Apply the user-controlled session-list height after refreshes.

        The list no longer auto-grows with row count. Users can drag the thin
        handle under the list to make the Session Source area taller or shorter,
        and the chosen height is saved through QSettings.
        """
        self._set_session_list_height(self._session_list_height, persist=False)

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
