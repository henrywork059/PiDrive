from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.export.export_actions_panel import ExportActionsPanel
from ..panels.export.export_options_panel import ExportOptionsPanel
from ..panels.export.model_status_panel import ModelStatusPanel
from ..services.export.export_service import export_model_artifacts


class ExportPage(QWidget):
    def __init__(self, state: AppState, main_window) -> None:
        super().__init__()
        self.state = state
        self.main_window = main_window

        self.model_status_panel = ModelStatusPanel()
        self.options_panel = ExportOptionsPanel(self.state)
        self.actions_panel = ExportActionsPanel(self.export_model)
        self.log_panel = LogPanel("Export Log")

        left = QVBoxLayout()
        left.addWidget(self.model_status_panel)
        left.addWidget(self.options_panel)
        left.addWidget(self.actions_panel)
        left.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(self.log_panel, 1)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addLayout(right, 1)

    def refresh_from_state(self) -> None:
        model_ready = self.state.model is not None
        history_len = len(self.state.history.get("loss", [])) if self.state.history else 0
        self.model_status_panel.set_status(
            model_ready=model_ready,
            train_rows=len(self.state.train_df),
            val_rows=len(self.state.val_df),
            epochs_ran=history_len,
        )

    def export_model(self) -> None:
        self.options_panel.push_to_state()
        if self.state.model is None:
            self.log_panel.append_line("No trained model available. Train a model first.")
            return
        try:
            created = export_model_artifacts(
                model=self.state.model,
                export_config=self.state.export_config,
                train_df=self.state.train_df,
                train_config=self.state.train_config,
            )
        except Exception as exc:  # noqa: BLE001
            self.log_panel.append_line(f"ERROR: {exc}")
            self.main_window.set_status_message("Export failed.")
            return

        for item in created:
            self.log_panel.append_line(f"Created: {item}")
        self.main_window.set_status_message("Export finished.")
