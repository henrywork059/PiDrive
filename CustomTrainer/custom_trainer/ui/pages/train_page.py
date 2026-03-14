from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from custom_trainer.services.ultralytics_runner import build_train_command, run_command
from custom_trainer.state import AppState


class TrainPage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log
        self.is_running = False

        self.columnconfigure(1, weight=1)

        self.model_var = tk.StringVar(value=state.model_path)
        self.yaml_var = tk.StringVar()
        self.epochs_var = tk.StringVar(value="100")
        self.imgsz_var = tk.StringVar(value="640")
        self.batch_var = tk.StringVar(value="16")
        self.device_var = tk.StringVar(value="cpu")
        self.project_var = tk.StringVar(value="runs")
        self.name_var = tk.StringVar(value="customtrainer_train")

        self._build()

    def _build(self) -> None:
        row = 0
        ttk.Label(self, text="Model (.pt / preset)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.model_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_model).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="dataset.yaml").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.yaml_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_yaml).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Epochs").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.epochs_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Image Size").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.imgsz_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Batch").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.batch_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Device").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.device_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Runs Project Dir").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.project_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Run Name").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.name_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Button(self, text="Start Training", command=self.start_training).grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=12)

    def choose_model(self) -> None:
        path = filedialog.askopenfilename(title="Choose model weights", filetypes=[("PyTorch Weights", "*.pt"), ("All Files", "*")])
        if path:
            self.model_var.set(path)

    def choose_yaml(self) -> None:
        path = filedialog.askopenfilename(title="Choose dataset.yaml", filetypes=[("YAML", "*.yaml *.yml")])
        if path:
            self.yaml_var.set(path)

    def start_training(self) -> None:
        if self.is_running:
            messagebox.showinfo("Training running", "A training process is already running.")
            return
        data = self.yaml_var.get().strip()
        if not data:
            messagebox.showerror("Missing dataset.yaml", "Choose dataset.yaml first.")
            return
        try:
            epochs = int(self.epochs_var.get())
            imgsz = int(self.imgsz_var.get())
            batch = int(self.batch_var.get())
        except ValueError:
            messagebox.showerror("Invalid numbers", "Epochs, image size, and batch must be integers.")
            return
        command = build_train_command(
            model=self.model_var.get().strip(),
            data=data,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=self.device_var.get().strip(),
            project=self.project_var.get().strip(),
            name=self.name_var.get().strip(),
        )
        self.is_running = True
        threading.Thread(target=self._run, args=(command,), daemon=True).start()

    def _run(self, command: list[str]) -> None:
        try:
            run_command(command, self.log)
        finally:
            self.is_running = False
