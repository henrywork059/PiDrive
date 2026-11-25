from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QGroupBox, QLabel, QPushButton, QVBoxLayout

from ...services.validation.validation_service import render_validation_plot
from ...ui.theme import theme_color


class ValidationPlotPanel(QGroupBox):
    PLOT_TYPES = [
        'Prediction vs Ground Truth',
        'Prediction Error Histogram',
        'Sample Prediction Trace',
    ]

    def __init__(self) -> None:
        super().__init__('Plot')
        self.result: dict | None = None

        self.help_label = QLabel(
            'Review steering/speed scatter, error, and trace plots.'
        )
        self.help_label.setWordWrap(True)

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.setAccessibleName('Validation plot type')
        self.plot_type_combo.addItems(self.PLOT_TYPES)
        self.plot_type_combo.currentIndexChanged.connect(self.refresh_plot)

        self.summary_label = QLabel('No results yet.')
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.summary_label.setAccessibleName('Validation plot dataset and model context')

        self.figure = Figure(figsize=(6.2, 4.0), tight_layout=True)
        self.figure.patch.set_facecolor(theme_color('plot_bg'))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(180)

        self._artifact_paths = []
        self.copy_paths_btn = QPushButton('Copy artifact paths')
        self.copy_paths_btn.setEnabled(False)
        self.copy_paths_btn.clicked.connect(self.copy_artifact_paths)
        layout = QVBoxLayout(self)
        layout.addWidget(self.help_label)
        layout.addWidget(self.plot_type_combo)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.copy_paths_btn, 0, Qt.AlignRight)
        layout.addWidget(self.canvas, 1)

        self.refresh_plot()

    def set_result(self, result: dict | None) -> None:
        self.result = result
        self.refresh_plot()

    def copy_artifact_paths(self) -> None:
        if self._artifact_paths:
            QApplication.clipboard().setText('\n'.join(self._artifact_paths))

    def refresh_plot(self) -> None:
        self._artifact_paths = []
        self.copy_paths_btn.setEnabled(False)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        plot_type = self.plot_type_combo.currentText() or self.PLOT_TYPES[0]
        if not self.result:
            self.summary_label.setText('No results yet. Run validation to populate this panel.')
            self.summary_label.setToolTip('')
            ax.set_axis_off()
            self.canvas.draw_idle()
            return

        render_validation_plot(ax, self.result, plot_type)
        context = self.result.get('experiment_context') or {}
        run_id = context.get('run_id')
        run_label = f'{run_id[:12]}…' if run_id else 'Unknown'
        model_path = self.result.get('model_path') or ''
        model_kind = self.result.get('model_kind') or 'Unknown'
        receipt = self.result.get('validation_receipt') or {}
        self._artifact_paths = list(dict.fromkeys(str(path) for path in (model_path, receipt.get('path')) if path))
        self.copy_paths_btn.setEnabled(bool(self._artifact_paths))
        self.summary_label.setText(
            f"Dataset: {self.result.get('dataset_source') or 'Unknown'} | Run: {run_label}\n"
            f"Rows used: {self.result['rows_used']} | Steering MAE: {self.result['steering_mae']:.4f} | "
            f"Speed MAE: {self.result['throttle_mae']:.4f}\n"
            f"Model: {model_path or model_kind}"
            + (f"\nSummary: {receipt['path']}" if receipt.get('path') else "")
        )
        self.summary_label.setToolTip(f"Training run: {run_id or 'Unknown'}\n"
                                      f"Model: {model_path or model_kind}\n"
                                      f"SHA-256: {context.get('model_sha256') or 'Unknown'}\n"
                                      f"Validation ID: {receipt.get('id') or 'Unknown'}\n"
                                      f"Summary: {receipt.get('path') or 'Unknown'}")
        self.canvas.draw_idle()
