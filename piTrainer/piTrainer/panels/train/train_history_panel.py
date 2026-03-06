from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QGroupBox, QVBoxLayout

from ...services.train.history_service import build_plot_series


class TrainHistoryPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Training History")
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.history: dict[str, list[float]] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        self._draw_empty()

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

    def _draw_empty(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("No training history yet")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss / Metric")
        self.canvas.draw_idle()

    def _redraw(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        for label, xs, ys in build_plot_series(self.history):
            ax.plot(xs, ys, label=label)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss / Metric")
        ax.set_title("Training Curves")
        if ax.lines:
            ax.legend()
        self.canvas.draw_idle()
