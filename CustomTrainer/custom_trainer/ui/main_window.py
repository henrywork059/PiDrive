from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from custom_trainer.state import AppState
from custom_trainer.ui.pages.annotate_page import AnnotatePage
from custom_trainer.ui.pages.dataset_page import DatasetPage
from custom_trainer.ui.pages.export_page import ExportPage
from custom_trainer.ui.pages.pi_deploy_page import PiDeployPage
from custom_trainer.ui.pages.train_page import TrainPage
from custom_trainer.ui.pages.validate_page import ValidatePage
from custom_trainer.ui.widgets.log_panel import LogPanel


class CustomTrainerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CustomTrainer - Object Detection Trainer")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 760)

        self.state = AppState()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.log_panel = LogPanel(self.root)
        self.log_panel.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self.dataset_page = DatasetPage(self.notebook, self.state, self.log_panel.log)
        self.annotate_page = AnnotatePage(self.notebook, self.state, self.log_panel.log)
        self.train_page = TrainPage(self.notebook, self.state, self.log_panel.log)
        self.validate_page = ValidatePage(self.notebook, self.state, self.log_panel.log)
        self.export_page = ExportPage(self.notebook, self.state, self.log_panel.log)
        self.pi_deploy_page = PiDeployPage(self.notebook, self.state, self.log_panel.log)

        self.notebook.add(self.dataset_page, text="Dataset")
        self.notebook.add(self.annotate_page, text="Annotate")
        self.notebook.add(self.train_page, text="Train")
        self.notebook.add(self.validate_page, text="Validate")
        self.notebook.add(self.export_page, text="Export")
        self.notebook.add(self.pi_deploy_page, text="Pi Deploy")

    def run(self) -> None:
        self.root.mainloop()
