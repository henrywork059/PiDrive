from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from custom_trainer.services.ultralytics_runner import build_export_command, run_command
from custom_trainer.state import AppState


class ExportPage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log
        self.is_running = False

        self.columnconfigure(1, weight=1)

        self.weights_var = tk.StringVar()
        self.yaml_var = tk.StringVar()
        self.format_var = tk.StringVar(value="tflite")
        self.imgsz_var = tk.StringVar(value="320")
        self.device_var = tk.StringVar(value="cpu")
        self.quant_var = tk.StringVar(value="int8")
        self.nms_var = tk.BooleanVar(value=True)

        self._build()

    def _build(self) -> None:
        row = 0
        ttk.Label(self, text="Weights (.pt)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.weights_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_weights).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="dataset.yaml (needed for INT8)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.yaml_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_yaml).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Format").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Combobox(
            self,
            textvariable=self.format_var,
            values=["tflite", "onnx", "openvino", "torchscript"],
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Image Size").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.imgsz_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Device").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.device_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Quantization").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Combobox(
            self,
            textvariable=self.quant_var,
            values=["int8", "float16", "float32"],
            state="readonly",
        ).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Checkbutton(self, text="Embed NMS when supported", variable=self.nms_var).grid(row=row, column=0, columnspan=2, sticky="w", padx=6, pady=6)

        row += 1
        ttk.Button(self, text="Export for Pi", command=self.start_export).grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=12)

        row += 1
        info = tk.Text(self, height=10, wrap="word")
        info.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self.rowconfigure(row, weight=1)
        info.insert(
            "1.0",
            "Recommended Pi export path:\n\n"
            "- format: tflite\n"
            "- image size: 320 or 416\n"
            "- quantization: int8 first, then float16 if int8 has export/runtime issues\n"
            "- device: cpu\n\n"
            "After export, use the Pi Deploy page to package the model with labels and a Pi runtime script."
        )
        info.config(state="disabled")

    def choose_weights(self) -> None:
        path = filedialog.askopenfilename(title="Choose weights", filetypes=[("PyTorch Weights", "*.pt"), ("All Files", "*")])
        if path:
            self.weights_var.set(path)

    def choose_yaml(self) -> None:
        path = filedialog.askopenfilename(title="Choose dataset.yaml", filetypes=[("YAML", "*.yaml *.yml")])
        if path:
            self.yaml_var.set(path)

    def start_export(self) -> None:
        if self.is_running:
            messagebox.showinfo("Busy", "An export task is already running.")
            return
        try:
            imgsz = int(self.imgsz_var.get())
        except ValueError:
            messagebox.showerror("Invalid image size", "Image size must be an integer.")
            return

        quant = self.quant_var.get().strip()
        int8 = quant == "int8"
        half = quant == "float16"
        data = self.yaml_var.get().strip() if int8 else ""
        if int8 and not data:
            messagebox.showerror("dataset.yaml required", "INT8 export needs dataset.yaml for calibration. Choose it first.")
            return

        command = build_export_command(
            weights=self.weights_var.get().strip(),
            export_format=self.format_var.get().strip(),
            imgsz=imgsz,
            device=self.device_var.get().strip(),
            int8=int8,
            half=half,
            nms=self.nms_var.get(),
            data=data,
        )
        self.is_running = True
        threading.Thread(target=self._run, args=(command,), daemon=True).start()

    def _run(self, command: list[str]) -> None:
        try:
            run_command(command, self.log)
        finally:
            self.is_running = False
