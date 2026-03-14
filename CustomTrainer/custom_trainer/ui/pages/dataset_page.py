from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from custom_trainer.services.dataset_service import create_dataset_yaml, scan_dataset
from custom_trainer.state import AppState


class DatasetPage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log

        self.columnconfigure(1, weight=1)
        self.columnconfigure(3, weight=1)

        self.project_var = tk.StringVar()
        self.images_var = tk.StringVar()
        self.labels_var = tk.StringVar()
        self.yaml_var = tk.StringVar()
        self.classes_var = tk.StringVar(value=",".join(state.classes))

        self._build()

    def _build(self) -> None:
        row = 0
        ttk.Label(self, text="Project Root").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.project_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_project).grid(row=row, column=3, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Images Dir").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.images_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_images).grid(row=row, column=3, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Labels Dir").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.labels_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_labels).grid(row=row, column=3, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="dataset.yaml").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.yaml_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="Browse", command=self.choose_yaml).grid(row=row, column=3, sticky="ew", padx=6, pady=6)

        row += 1
        ttk.Label(self, text="Classes (comma-separated)").grid(row=row, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(self, textvariable=self.classes_var).grid(row=row, column=1, columnspan=3, sticky="ew", padx=6, pady=6)

        row += 1
        button_bar = ttk.Frame(self)
        button_bar.grid(row=row, column=0, columnspan=4, sticky="ew", padx=6, pady=10)
        for i in range(4):
            button_bar.columnconfigure(i, weight=1)
        ttk.Button(button_bar, text="Apply Paths", command=self.apply_paths).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(button_bar, text="Scan Dataset", command=self.on_scan).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(button_bar, text="Create dataset.yaml", command=self.on_create_yaml).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(button_bar, text="Load Defaults", command=self.load_defaults).grid(row=0, column=3, sticky="ew", padx=4)

        row += 1
        self.summary_text = tk.Text(self, height=18, wrap="word")
        self.summary_text.grid(row=row, column=0, columnspan=4, sticky="nsew", padx=6, pady=6)
        self.rowconfigure(row, weight=1)

    def choose_project(self) -> None:
        path = filedialog.askdirectory(title="Choose project root")
        if path:
            self.project_var.set(path)

    def choose_images(self) -> None:
        path = filedialog.askdirectory(title="Choose images directory")
        if path:
            self.images_var.set(path)

    def choose_labels(self) -> None:
        path = filedialog.askdirectory(title="Choose labels directory")
        if path:
            self.labels_var.set(path)

    def choose_yaml(self) -> None:
        path = filedialog.asksaveasfilename(title="Save dataset.yaml", defaultextension=".yaml", filetypes=[("YAML", "*.yaml")])
        if path:
            self.yaml_var.set(path)

    def load_defaults(self) -> None:
        root = self.project_var.get().strip()
        if not root:
            messagebox.showinfo("Project root needed", "Choose a project root first.")
            return
        project = Path(root)
        self.images_var.set(str(project / "images" / "train"))
        self.labels_var.set(str(project / "labels" / "train"))
        self.yaml_var.set(str(project / "dataset.yaml"))

    def apply_paths(self) -> None:
        self.state.project_root = Path(self.project_var.get()).expanduser() if self.project_var.get().strip() else None
        self.state.images_dir = Path(self.images_var.get()).expanduser() if self.images_var.get().strip() else None
        self.state.labels_dir = Path(self.labels_var.get()).expanduser() if self.labels_var.get().strip() else None
        self.state.dataset_yaml = Path(self.yaml_var.get()).expanduser() if self.yaml_var.get().strip() else None
        self.state.classes = [item.strip() for item in self.classes_var.get().split(",") if item.strip()]
        self.log("Applied dataset paths and classes.")

    def on_scan(self) -> None:
        self.apply_paths()
        if not self.state.images_dir or not self.state.labels_dir:
            messagebox.showerror("Missing paths", "Please set images and labels directories first.")
            return
        summary = scan_dataset(self.state.images_dir, self.state.labels_dir)
        self.state.last_summary = summary
        lines = [
            f"Images: {summary.image_count}",
            f"Labels: {summary.label_count}",
            f"Missing labels: {summary.missing_labels}",
            f"Extra labels: {summary.extra_labels}",
            "",
            "Class histogram:",
        ]
        if summary.class_histogram:
            for class_id, count in sorted(summary.class_histogram.items()):
                class_name = self.state.classes[class_id] if 0 <= class_id < len(self.state.classes) else f"class_{class_id}"
                lines.append(f"  {class_id} ({class_name}): {count}")
        else:
            lines.append("  No labels found.")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", "\n".join(lines))
        self.log("Dataset scan complete.")

    def on_create_yaml(self) -> None:
        self.apply_paths()
        if not self.state.dataset_yaml:
            messagebox.showerror("Missing dataset.yaml path", "Choose where to save dataset.yaml first.")
            return
        project_root = self.state.dataset_yaml.parent
        train_images = "images/train"
        val_images = "images/val"
        create_dataset_yaml(
            yaml_path=self.state.dataset_yaml,
            train_images=train_images,
            val_images=val_images,
            class_names=self.state.classes,
        )
        self.log(f"Created dataset yaml at: {self.state.dataset_yaml}")
        messagebox.showinfo("dataset.yaml created", f"Saved:\n{self.state.dataset_yaml}")
