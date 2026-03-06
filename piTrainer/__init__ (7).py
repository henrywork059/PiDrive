from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel


class DatasetStatsPanel(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Dataset Stats")
        self.labels = {
            "rows": QLabel("0"),
            "sessions": QLabel("0"),
            "steer_mean": QLabel("0.0000"),
            "steer_std": QLabel("0.0000"),
            "thr_mean": QLabel("0.0000"),
            "thr_std": QLabel("0.0000"),
        }
        layout = QFormLayout(self)
        layout.addRow("Usable rows", self.labels["rows"])
        layout.addRow("Sessions", self.labels["sessions"])
        layout.addRow("Steering mean", self.labels["steer_mean"])
        layout.addRow("Steering std", self.labels["steer_std"])
        layout.addRow("Throttle mean", self.labels["thr_mean"])
        layout.addRow("Throttle std", self.labels["thr_std"])

    def set_stats(self, stats: dict) -> None:
        self.labels["rows"].setText(str(stats.get("rows", 0)))
        self.labels["sessions"].setText(str(stats.get("sessions", 0)))
        self.labels["steer_mean"].setText(f"{stats.get('steering_mean', 0.0):.4f}")
        self.labels["steer_std"].setText(f"{stats.get('steering_std', 0.0):.4f}")
        self.labels["thr_mean"].setText(f"{stats.get('throttle_mean', 0.0):.4f}")
        self.labels["thr_std"].setText(f"{stats.get('throttle_std', 0.0):.4f}")
