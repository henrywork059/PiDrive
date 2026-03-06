from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...app_state import AppState


class SessionListPanel(QGroupBox):
    def __init__(self, state: AppState, load_callback) -> None:
        super().__init__("Sessions")
        self.setObjectName('sessionListPanel')
        self.state = state
        self.load_callback = load_callback
        self._checkboxes: list[QCheckBox] = []

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
        row = QFrame()
        row.setObjectName('sessionRow')
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 6, 10, 6)
        row_layout.setSpacing(10)

        checkbox = QCheckBox(session)
        checkbox.setObjectName('sessionRowCheckbox')
        checkbox.setChecked(checked)
        checkbox.setCursor(Qt.PointingHandCursor)
        row_layout.addWidget(checkbox, 1)
        self._checkboxes.append(checkbox)
        return row

    def set_sessions(self, sessions: list[str]) -> None:
        old_selected = set(self.state.selected_sessions)
        self._checkboxes.clear()
        self.list_widget.clear()
        for session in sessions:
            item = QListWidgetItem()
            row_widget = self._build_row_widget(session, session in old_selected)
            item.setSizeHint(row_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, row_widget)

    def selected_sessions(self) -> list[str]:
        return [checkbox.text() for checkbox in self._checkboxes if checkbox.isChecked()]

    def select_all(self) -> None:
        for checkbox in self._checkboxes:
            checkbox.setChecked(True)

    def clear_all(self) -> None:
        for checkbox in self._checkboxes:
            checkbox.setChecked(False)
