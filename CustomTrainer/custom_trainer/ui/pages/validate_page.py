from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from custom_trainer.services.ultralytics_runner import build_predict_command, build_val_command, run_command
from custom_trainer.state import AppState


class ValidatePage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log
        self.is_running = False

        self.columnconfigure(1, weight=1)

        self.weights_var = tk.StringVar()
        self.yaml_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.imgsz_var = tk.StringVar(value="640")
        self.conf_var = tk.StringVar(value="0.25")
        self.device_var = tk.StringVar(value="cpu")

        self._build()

    def _build(self) -> None:
        row = 0
        ttk.Label(self, text="Weights (.pt)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.weights_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_weights).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="dataset.yaml").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.yaml_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_yaml).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Predict Source").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.source_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_source).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Image Size").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.imgsz_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Confidence").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.conf_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Device").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.device_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        buttons = ttk.Frame(self)
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=12)
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        ttk.Button(buttons, text="Run Validation", command=self.start_val).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(buttons, text="Run Prediction", command=self.start_predict).grid(row=0, column=1, sticky="ew", padx=4)

    def choose_weights(self) -> None:
        path = filedialog.askopenfilename(title="Choose weights", filetypes=[("PyTorch Weights", "*.pt"), ("All Files", "*")])
        if path:
            self.weights_var.set(path)

    def choose_yaml(self) -> None:
        path = filedialog.askopenfilename(title="Choose dataset.yaml", filetypes=[("YAML", "*.yaml *.yml")])
        if path:
            self.yaml_var.set(path)

    def choose_source(self) -> None:
        path = filedialog.askopenfilename(title="Choose source image/video", filetypes=[("Media", "*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.avi"), ("All Files", "*")])
        if path:
            self.source_var.set(path)

    def start_val(self) -> None:
        if self.is_running:
            messagebox.showinfo("Busy", "Another validation/prediction task is already running.")
            return
        try:
            imgsz = int(self.imgsz_var.get())
        except ValueError:
            messagebox.showerror("Invalid image size", "Image size must be an integer.")
            return
        command = build_val_command(
            weights=self.weights_var.get().strip(),
            data=self.yaml_var.get().strip(),
            imgsz=imgsz,
            device=self.device_var.get().strip(),
        )
        self._launch(command)

    def start_predict(self) -> None:
        if self.is_running:
            messagebox.showinfo("Busy", "Another validation/prediction task is already running.")
            return
        try:
            imgsz = int(self.imgsz_var.get())
            conf = float(self.conf_var.get())
        except ValueError:
            messagebox.showerror("Invalid values", "Image size must be integer and confidence must be numeric.")
            return
        command = build_predict_command(
            weights=self.weights_var.get().strip(),
            source=self.source_var.get().strip(),
            imgsz=imgsz,
            conf=conf,
            device=self.device_var.get().strip(),
        )
        self._launch(command)

    def _launch(self, command: list[str]) -> None:
        self.is_running = True
        threading.Thread(target=self._run, args=(command,), daemon=True).start()

    def _run(self, command: list[str]) -> None:
        try:
            run_command(command, self.log)
        finally:
            self.is_running = False
