from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from ...services.data.plot_service import (
    build_plot_summary,
    filter_plot_dataframe,
    plot_sessions_for_combo,
    render_plot,
)


class DataPlotPanel(QGroupBox):
    PLOT_TYPES = [
        'Steering + Speed Timeline',
        'Steering Histogram',
        'Speed Histogram',
        'Steering vs Speed Scatter',
        'Mode Distribution',
        'Session Frame Count',
    ]

    def __init__(self) -> None:
        super().__init__('Data Plot')
        self.df = pd.DataFrame()
        self._current_sessions: list[str] = []

        help_label = QLabel(
            'Explore the filtered data with multiple plot types: timeline, histograms, scatter, and distribution charts.'
        )
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self.refresh_plot)

        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(self.PLOT_TYPES)
        self.plot_type_combo.currentIndexChanged.connect(self.refresh_plot)

        self.summary_label = QLabel('Load sessions to see session plots and statistics.')
        self.summary_label.setWordWrap(True)

        self.figure = Figure(figsize=(6.0, 3.8), tight_layout=True)
        self.figure.patch.set_facecolor('#171c26')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(280)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.session_combo)
        layout.addWidget(self.plot_type_combo)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.canvas, 1)

        self._set_combo_items([])
        self.refresh_plot()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.df = df.reset_index(drop=True).copy() if not df.empty else pd.DataFrame()
        sessions = plot_sessions_for_combo(self.df)
        current_text = self.session_combo.currentText()
        self._set_combo_items(sessions)
        if current_text and current_text in sessions:
            self.session_combo.setCurrentText(current_text)
        self.refresh_plot()

    def _set_combo_items(self, sessions: list[str]) -> None:
        self._current_sessions = sessions
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        self.session_combo.addItem('All loaded sessions')
        for session in sessions:
            self.session_combo.addItem(session)
        self.session_combo.blockSignals(False)

    def refresh_plot(self) -> None:
        session_name = self.session_combo.currentText() or 'All loaded sessions'
        plot_type = self.plot_type_combo.currentText() or self.PLOT_TYPES[0]
        plot_df = filter_plot_dataframe(self.df, session_name)
        summary = build_plot_summary(plot_df)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        render_plot(ax, plot_df, plot_type, session_name)

        if plot_df.empty:
            self.summary_label.setText('No plotted frames. Load sessions or relax the current filter.')
            self.canvas.draw_idle()
            return

        self.summary_label.setText(
            'Plot: {plot} | Frames: {rows} | Sessions: {sessions} | Steering min/max/mean: {steering_min:.3f} / '
            '{steering_max:.3f} / {steering_mean:.3f} | Speed min/max/mean: {throttle_min:.3f} / '
            '{throttle_max:.3f} / {throttle_mean:.3f}'.format(plot=plot_type, **summary)
        )
        self.canvas.draw_idle()
