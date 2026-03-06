from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QGroupBox, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout

from ...app_state import AppState


class SessionListPanel(QGroupBox):
    def __init__(self, state: AppState, load_callback) -> None:
        super().__init__("Sessions")
        self.setObjectName('sessionListPanel')
        self.state = state
        self.load_callback = load_callback
        self.list_widget = QListWidget()
        self.list_widget.setObjectName('sessionListWidget')
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)

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

    def set_sessions(self, sessions: list[str]) -> None:
        old_selected = set(self.state.selected_sessions)
        self.list_widget.clear()
        for session in sessions:
            item = QListWidgetItem(session)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if session in old_selected else Qt.Unchecked)
            self.list_widget.addItem(item)

    def selected_sessions(self) -> list[str]:
        sessions: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                sessions.append(item.text())
        return sessions

    def select_all(self) -> None:
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.Checked)

    def clear_all(self) -> None:
        for index in range(self.list_widget.count()):
            self.list_widget.item(index).setCheckState(Qt.Unchecked)
