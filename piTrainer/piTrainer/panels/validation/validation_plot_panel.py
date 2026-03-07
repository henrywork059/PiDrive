from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from ...services.validation.validation_service import render_validation_plot


class ValidationPlotPanel(QGroupBox):
    PLOT_TYPES = [
        'Prediction vs Ground Truth',
        'Prediction Error Histogram',
        'Sample Prediction Trace',
    ]

    def __init__(self) -> None:
        super().__init__('Validation Plot')
        self.result: dict | None = None

        self.help_label = QLabel(
            'Review the trained model with scatter, error, and sample-trace plots for steering and speed.'
        )
        self.help_label.setWordWrap(True)

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(self.PLOT_TYPES)
        self.plot_type_combo.currentIndexChanged.connect(self.refresh_plot)

        self.summary_label = QLabel('No validation results yet.')
        self.summary_label.setWordWrap(True)

        self.figure = Figure(figsize=(6.2, 4.0), tight_layout=True)
        self.figure.patch.set_facecolor('#171c26')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(320)

        layout = QVBoxLayout(self)
        layout.addWidget(self.help_label)
        layout.addWidget(self.plot_type_combo)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.canvas, 1)

        self.refresh_plot()

    def set_result(self, result: dict | None) -> None:
        self.result = result
        self.refresh_plot()

    def refresh_plot(self) -> None:
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        plot_type = self.plot_type_combo.currentText() or self.PLOT_TYPES[0]
        if not self.result:
            self.summary_label.setText('No validation results yet. Run validation to populate this panel.')
            ax.set_axis_off()
            self.canvas.draw_idle()
            return

        render_validation_plot(ax, self.result, plot_type)
        self.summary_label.setText(
            f"Rows used: {self.result['rows_used']} | Steering MAE: {self.result['steering_mae']:.4f} | "
            f"Speed MAE: {self.result['throttle_mae']:.4f}"
        )
        self.canvas.draw_idle()
