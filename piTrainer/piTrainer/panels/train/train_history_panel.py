from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from ...services.train.history_service import build_plot_series
from ...ui.theme import theme_color


class TrainHistoryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Training History")
        self.figure = Figure(figsize=(6, 4), facecolor=theme_color("plot_bg"))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.history: dict[str, list[float]] = {}

        self.context_label = QLabel("Training run: Unknown")
        self.context_label.setTextFormat(Qt.PlainText)
        self.context_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.context_label.setWordWrap(True)
        self.context_label.setAccessibleName("Training plot run and artifact context")
        layout = QVBoxLayout(self)
        layout.addWidget(self.context_label)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def set_run_context(self, record: dict | None) -> None:
        record = record or {}
        run_id = record.get("run_id")
        groups = record.get("source_groups")
        group_count = len(groups) if isinstance(groups, list) else "Unknown"
        train_rows = record.get("train_rows", "Unknown")
        val_rows = record.get("validation_rows", "Unknown")
        paths = [str(item["model_path"]) for item in (record.get("artifacts") or [])
                 if isinstance(item, dict) and item.get("model_path")]
        if run_id:
            label = f"Run: {run_id[:12]}… | {record.get('status', 'Unknown')} | Train: {train_rows} | Val: {val_rows} | Sessions: {group_count}"
            label += "\nArtifact: " + (paths[-1] if paths else "Not recorded")
            tooltip = f"Run: {run_id}\n" + "\n".join(paths)
        else:
            label = "Training run: Unknown | Artifact: Unknown"
            tooltip = ""
        self.context_label.setText(label)
        self.context_label.setToolTip(tooltip)

    def clear_history(self) -> None:
        self.history = {}
        self._draw_empty()

    def append_epoch_metrics(self, metrics: dict) -> None:
        epoch = int(metrics.get("epoch", 0))
        for key, value in metrics.items():
            if key == "epoch":
                continue
            self.history.setdefault(key, [])
            while len(self.history[key]) < epoch - 1:
                self.history[key].append(None)
            self.history[key].append(float(value))
        self._redraw()

    def set_history(self, history: dict[str, list[float]]) -> None:
        self.history = {k: list(v) for k, v in (history or {}).items()}
        if self.history:
            self._redraw()
        else:
            self._draw_empty()

    def _style_axes(self, ax) -> None:
        self.figure.patch.set_facecolor(theme_color("plot_bg"))
        ax.set_facecolor(theme_color("plot_axis"))
        ax.tick_params(colors=theme_color("text_secondary"))
        ax.xaxis.label.set_color(theme_color("text_secondary"))
        ax.yaxis.label.set_color(theme_color("text_secondary"))
        ax.title.set_color(theme_color("text_primary"))
        for spine in ax.spines.values():
            spine.set_color(theme_color("border"))
        ax.grid(color=theme_color("plot_grid"), alpha=0.55)

    def _draw_empty(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._style_axes(ax)
        ax.set_title("No training history yet")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss / Metric")
        self.canvas.draw_idle()

    def _redraw(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self._style_axes(ax)
        palette = [theme_color("plot_steering"), theme_color("plot_speed"), theme_color("success"), theme_color("plot_reference"), theme_color("plot_error")]
        ax.set_prop_cycle(color=palette)
        for label, xs, ys in build_plot_series(self.history):
            ax.plot(xs, ys, label=label, linewidth=2)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss / Metric")
        ax.set_title("Training Curves")
        if ax.lines:
            legend = ax.legend(facecolor=theme_color("plot_bg"), edgecolor=theme_color("border"))
            for text in legend.get_texts():
                text.set_color(theme_color("text_secondary"))
        self.canvas.draw_idle()
