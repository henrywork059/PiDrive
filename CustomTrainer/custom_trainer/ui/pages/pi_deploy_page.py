from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from custom_trainer.services.pi_deploy_service import build_pi_bundle
from custom_trainer.state import AppState


class PiDeployPage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log

        self.columnconfigure(1, weight=1)

        self.model_var = tk.StringVar()
        self.labels_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.imgsz_var = tk.StringVar(value="320")
        self.conf_var = tk.StringVar(value="0.25")
        self.iou_var = tk.StringVar(value="0.45")

        self._build()

    def _build(self) -> None:
        row = 0
        ttk.Label(self, text="Exported Model (.tflite)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.model_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_model).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="labels.txt / classes.txt").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.labels_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_labels).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Bundle Output Dir").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.output_dir_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_output_dir).grid(row=row, column=2, padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Input Size").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.imgsz_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Confidence Threshold").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.conf_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="IoU Threshold").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.iou_var).grid(row=row, column=1, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Button(self, text="Build Pi Bundle", command=self.build_bundle).grid(row=row, column=0, columnspan=3, sticky="ew", padx=6, pady=12)

        row += 1
        note = tk.Text(self, height=12, wrap="word")
        note.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=6, pady=6)
        self.rowconfigure(row, weight=1)
        note.insert(
            "1.0",
            "Pi deployment path:\n\n"
            "1. Train on PC with a small YOLO model.\n"
            "2. Export to TFLite, ideally at 320 or 416 input size.\n"
            "3. Build a Pi bundle from the exported .tflite.\n"
            "4. Copy the bundle to Raspberry Pi and run run_tflite_detect.py.\n\n"
            "This page prepares a ready-to-copy deployment folder with the model, labels, config, a Pi runtime script, a benchmark script, and Pi requirements."
        )
        note.config(state="disabled")

    def choose_model(self) -> None:
        path = filedialog.askopenfilename(title="Choose exported model", filetypes=[("TFLite Model", "*.tflite"), ("All Files", "*")])
        if path:
            self.model_var.set(path)

    def choose_labels(self) -> None:
        path = filedialog.askopenfilename(title="Choose labels file", filetypes=[("Text", "*.txt"), ("All Files", "*")])
        if path:
            self.labels_var.set(path)

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose output directory")
        if path:
            self.output_dir_var.set(path)

    def build_bundle(self) -> None:
        model = Path(self.model_var.get().strip()).expanduser()
        labels_text = self.labels_var.get().strip()
        labels = Path(labels_text).expanduser() if labels_text else None
        output_dir = Path(self.output_dir_var.get().strip()).expanduser()
        try:
            imgsz = int(self.imgsz_var.get().strip())
            conf = float(self.conf_var.get().strip())
            iou = float(self.iou_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid values", "Input size must be an integer. Thresholds must be numeric.")
            return

        if not model.exists():
            messagebox.showerror("Missing model", "Choose an exported .tflite model first.")
            return
        if not output_dir:
            messagebox.showerror("Missing output folder", "Choose a bundle output directory.")
            return

        bundle_dir = build_pi_bundle(
            model_path=model,
            labels_path=labels,
            output_dir=output_dir,
            image_size=imgsz,
            conf_threshold=conf,
            iou_threshold=iou,
        )
        self.log(f"Built Pi bundle: {bundle_dir}")
        messagebox.showinfo("Pi bundle ready", f"Saved:\n{bundle_dir}")
