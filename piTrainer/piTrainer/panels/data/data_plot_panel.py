from __future__ import annotations

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QVBoxLayout

from ...services.data.plot_service import build_plot_summary, filter_plot_dataframe, plot_sessions_for_combo


class DataPlotPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__('Data Plot')
        self.df = pd.DataFrame()
        self._current_sessions: list[str] = []

        help_label = QLabel('Plot steering and speed across the currently loaded or filtered frames.')
        help_label.setProperty('role', 'muted')
        help_label.setWordWrap(True)

        self.session_combo = QComboBox()
        self.session_combo.currentIndexChanged.connect(self.refresh_plot)

        self.summary_label = QLabel('Load sessions to see session plots and statistics.')
        self.summary_label.setWordWrap(True)

        self.figure = Figure(figsize=(6.0, 3.4), tight_layout=True)
        self.figure.patch.set_facecolor('#171c26')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(260)

        layout = QVBoxLayout(self)
        layout.addWidget(help_label)
        layout.addWidget(self.session_combo)
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
        plot_df = filter_plot_dataframe(self.df, session_name)
        summary = build_plot_summary(plot_df)

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f141c')
        ax.tick_params(colors='#d8deea')
        for spine in ax.spines.values():
            spine.set_color('#3b4d67')
        ax.grid(True, alpha=0.25)

        if plot_df.empty:
            ax.text(0.5, 0.5, 'No session data to plot', ha='center', va='center', color='#d8deea', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            self.summary_label.setText('No plotted frames. Load sessions or relax the current filter.')
            self.canvas.draw_idle()
            return

        x = range(len(plot_df))
        steering = pd.to_numeric(plot_df.get('steering', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
        throttle = pd.to_numeric(plot_df.get('throttle', pd.Series(dtype=float)), errors='coerce').fillna(0.0)

        ax.plot(x, steering, label='Steering', linewidth=1.6)
        ax.plot(x, throttle, label='Speed', linewidth=1.4)
        ax.set_xlabel('Frame index', color='#d8deea')
        ax.set_ylabel('Value', color='#d8deea')
        ax.set_title(session_name, color='#f4f7ff')
        legend = ax.legend(loc='upper right')
        if legend is not None:
            frame = legend.get_frame()
            frame.set_facecolor('#171c26')
            frame.set_edgecolor('#3b4d67')
            for text in legend.get_texts():
                text.set_color('#f4f7ff')

        self.summary_label.setText(
            'Frames: {rows} | Sessions: {sessions} | Steering min/max/mean: {steering_min:.3f} / {steering_max:.3f} / {steering_mean:.3f} | '
            'Speed min/max/mean: {throttle_min:.3f} / {throttle_max:.3f} / {throttle_mean:.3f}'.format(**summary)
        )
        self.canvas.draw_idle()
