from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..app_state import AppState
from ..panels.common.log_panel import LogPanel
from ..panels.train.split_summary_panel import SplitSummaryPanel
from ..panels.train.train_config_panel import TrainConfigPanel
from ..panels.train.train_control_panel import TrainControlPanel
from ..panels.train.train_history_panel import TrainHistoryPanel
from ..services.train.split_service import split_dataframe
from ..services.train.worker import TrainingWorker


class TrainPage(QWidget):
    def __init__(self, state: AppState, main_window) -> None:
        super().__init__()
        self.state = state
        self.main_window = main_window
        self.worker: TrainingWorker | None = None

        self.split_summary_panel = SplitSummaryPanel()
        self.config_panel = TrainConfigPanel(self.state)
        self.control_panel = TrainControlPanel(
            prepare_callback=self.prepare_split,
            start_callback=self.start_training,
            stop_callback=self.stop_training,
        )
        self.history_panel = TrainHistoryPanel()
        self.log_panel = LogPanel("Training Log")

        left = QVBoxLayout()
        left.addWidget(self.split_summary_panel)
        left.addWidget(self.config_panel)
        left.addWidget(self.control_panel)
        left.addWidget(self.log_panel, 1)

        right = QVBoxLayout()
        right.addWidget(self.history_panel, 1)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)

    def refresh_from_state(self) -> None:
        self.split_summary_panel.set_counts(
            total_rows=len(self.state.filtered_df),
            train_rows=len(self.state.train_df),
            val_rows=len(self.state.val_df),
            sessions=len(set(self.state.filtered_df.get("session", []))) if not self.state.filtered_df.empty else 0,
            model_ready=self.state.model is not None,
        )
        self.history_panel.set_history(self.state.history)

    def prepare_split(self) -> None:
        self.config_panel.push_to_state()
        train_df, val_df = split_dataframe(self.state.filtered_df, self.state.train_config)
        self.state.train_df = train_df
        self.state.val_df = val_df
        self.refresh_from_state()
        self.log_panel.append_line(
            f"Prepared split: train={len(train_df)} rows, val={len(val_df)} rows."
        )
        self.main_window.set_status_message("Prepared training split.")

    def start_training(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.log_panel.append_line("Training is already running.")
            return
        self.config_panel.push_to_state()
        if self.state.filtered_df.empty:
            self.log_panel.append_line("No data loaded. Load sessions on the Data page first.")
            return
        if self.state.train_df.empty and self.state.val_df.empty:
            self.prepare_split()
        self.history_panel.clear_history()
        self.log_panel.append_line("Starting training worker...")
        self.control_panel.set_running(True)

        self.worker = TrainingWorker(self.state.train_df, self.state.val_df, self.state.train_config)
        self.worker.log_message.connect(self.log_panel.append_line)
        self.worker.progress_changed.connect(self.control_panel.set_progress)
        self.worker.epoch_metrics.connect(self.history_panel.append_epoch_metrics)
        self.worker.error_message.connect(self._on_training_error)
        self.worker.training_finished.connect(self._on_training_finished)
        self.worker.start()

    def stop_training(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.log_panel.append_line("Stop requested. Training will stop after the current epoch.")

    def _on_training_error(self, message: str) -> None:
        self.state.last_error = message
        self.control_panel.set_running(False)
        self.log_panel.append_line(f"ERROR: {message}")
        self.main_window.set_status_message("Training failed.")

    def _on_training_finished(self, model, history: dict) -> None:
        self.state.model = model
        self.state.history = history
        self.control_panel.set_running(False)
        self.control_panel.set_progress(100)
        self.history_panel.set_history(history)
        self.log_panel.append_line("Training finished successfully.")
        self.refresh_from_state()
        self.main_window.on_training_finished()

    def shutdown_worker(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(1500)
