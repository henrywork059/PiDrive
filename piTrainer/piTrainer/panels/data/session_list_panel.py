from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState


class SessionRowWidget(QFrame):
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


class SessionListPanel(QGroupBox):
    def __init__(self, state: AppState, load_callback) -> None:
        super().__init__("Sessions")
        self.setObjectName('sessionListPanel')
        self.state = state
        self.load_callback = load_callback
        self._rows: list[SessionRowWidget] = []

        self.list_widget = QListWidget()
        self.list_widget.setObjectName('sessionListWidget')
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_widget.setSpacing(6)
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.setUniformItemSizes(False)

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_all)
        load_btn = QPushButton("Load Selected Sessions")
        load_btn.clicked.connect(self.load_callback)

        buttons = QHBoxLayout()
        buttons.addWidget(select_all_btn)
        buttons.addWidget(clear_btn)
        buttons.addWidget(load_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget, 1)
        layout.addLayout(buttons)

    def _build_row_widget(self, session: str, checked: bool) -> QWidget:
        row = SessionRowWidget(session, checked)
        self._rows.append(row)
        return row

    def set_sessions(self, sessions: list[str]) -> None:
        old_selected = set(self.state.selected_sessions)
        self._rows.clear()
        self.list_widget.clear()
        for session in sessions:
            item = QListWidgetItem()
            row_widget = self._build_row_widget(session, session in old_selected)
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row_widget)

    def selected_sessions(self) -> list[str]:
        return [row.session_name() for row in self._rows if row.checkbox.isChecked()]

    def select_all(self) -> None:
        for row in self._rows:
            row.checkbox.setChecked(True)

    def clear_all(self) -> None:
        for row in self._rows:
            row.checkbox.setChecked(False)

    def set_selected_sessions(self, sessions: list[str]) -> None:
        selected = set(sessions)
        for row in self._rows:
            row.checkbox.setChecked(row.session_name() in selected)
