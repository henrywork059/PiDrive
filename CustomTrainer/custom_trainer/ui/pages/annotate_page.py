from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, List, Optional

from PIL import Image, ImageTk

from custom_trainer.state import AppState
from custom_trainer.utils.file_utils import list_images
from custom_trainer.utils.yolo_io import PixelBox, pixel_to_yolo, read_yolo_label_file, write_yolo_label_file, yolo_to_pixel


class AnnotatePage(ttk.Frame):
    def __init__(self, master: tk.Misc, state: AppState, log: Callable[[str], None]) -> None:
        super().__init__(master)
        self.state = state
        self.log = log

        self.image_paths: List[Path] = []
        self.current_index = 0
        self.original_image: Optional[Image.Image] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.display_scale = 1.0
        self.display_w = 1
        self.display_h = 1
        self.boxes: List[PixelBox] = []
        self.selected_box_index: Optional[int] = None
        self.drag_start: Optional[tuple[float, float]] = None
        self.temp_rect: Optional[int] = None

        self.class_var = tk.StringVar(value="0")
        self.images_dir_var = tk.StringVar()
        self.labels_dir_var = tk.StringVar()
        self.status_var = tk.StringVar(value="No image loaded.")

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        for i in range(8):
            top.columnconfigure(i, weight=1 if i in (1, 3) else 0)

        ttk.Label(top, text="Images").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(top, textvariable=self.images_dir_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="Browse", command=self.choose_images).grid(row=0, column=2, padx=4)
        ttk.Label(top, text="Labels").grid(row=0, column=3, sticky="w", padx=4)
        ttk.Entry(top, textvariable=self.labels_dir_var).grid(row=0, column=4, sticky="ew", padx=4)
        ttk.Button(top, text="Browse", command=self.choose_labels).grid(row=0, column=5, padx=4)
        ttk.Button(top, text="Load Images", command=self.load_image_list).grid(row=0, column=6, padx=4)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=6)
        ttk.Label(toolbar, text="Class ID").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Entry(toolbar, textvariable=self.class_var, width=8).grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="Prev", command=self.prev_image).grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Button(toolbar, text="Next", command=self.next_image).grid(row=3, column=0, sticky="ew", pady=2)
        ttk.Button(toolbar, text="Delete Box", command=self.delete_selected_box).grid(row=4, column=0, sticky="ew", pady=8)
        ttk.Button(toolbar, text="Save Labels", command=self.save_labels).grid(row=5, column=0, sticky="ew", pady=2)
        ttk.Label(toolbar, textvariable=self.status_var, wraplength=220, justify="left").grid(row=6, column=0, sticky="ew", pady=(10, 0))

        self.canvas = tk.Canvas(self, bg="#222222")
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Configure>", lambda _event: self.render_current_image())

    def choose_images(self) -> None:
        path = filedialog.askdirectory(title="Choose images directory")
        if path:
            self.images_dir_var.set(path)

    def choose_labels(self) -> None:
        path = filedialog.askdirectory(title="Choose labels directory")
        if path:
            self.labels_dir_var.set(path)

    def load_image_list(self) -> None:
        images_dir = Path(self.images_dir_var.get()).expanduser()
        labels_dir = Path(self.labels_dir_var.get()).expanduser()
        if not images_dir.exists():
            messagebox.showerror("Images folder missing", "Choose a valid images folder.")
            return
        labels_dir.mkdir(parents=True, exist_ok=True)
        self.state.images_dir = images_dir
        self.state.labels_dir = labels_dir
        self.image_paths = list_images(images_dir)
        self.current_index = 0
        if not self.image_paths:
            messagebox.showinfo("No images", "No supported images found in that folder.")
            return
        self.log(f"Loaded {len(self.image_paths)} images for annotation.")
        self.load_current_image()

    def label_path_for_image(self, image_path: Path) -> Path:
        assert self.state.labels_dir is not None
        return self.state.labels_dir / f"{image_path.stem}.txt"

    def load_current_image(self) -> None:
        if not self.image_paths:
            return
        image_path = self.image_paths[self.current_index]
        self.original_image = Image.open(image_path).convert("RGB")
        label_path = self.label_path_for_image(image_path)
        self.boxes = [yolo_to_pixel(box, self.original_image.width, self.original_image.height) for box in read_yolo_label_file(label_path)]
        self.selected_box_index = None
        self.status_var.set(f"Image {self.current_index + 1}/{len(self.image_paths)}\n{image_path.name}\nLabels: {label_path.name}")
        self.render_current_image()

    def render_current_image(self) -> None:
        self.canvas.delete("all")
        if self.original_image is None:
            return
        canvas_w = max(self.canvas.winfo_width(), 200)
        canvas_h = max(self.canvas.winfo_height(), 200)
        scale = min(canvas_w / self.original_image.width, canvas_h / self.original_image.height)
        scale = max(scale, 0.05)
        self.display_scale = scale
        self.display_w = max(1, int(self.original_image.width * scale))
        self.display_h = max(1, int(self.original_image.height * scale))
        resized = self.original_image.resize((self.display_w, self.display_h))
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        for idx, box in enumerate(self.boxes):
            x1 = box.x1 * scale
            y1 = box.y1 * scale
            x2 = box.x2 * scale
            y2 = box.y2 * scale
            color = "yellow" if idx == self.selected_box_index else "lime"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2)
            self.canvas.create_text(x1 + 4, max(10, y1 + 10), anchor="w", fill=color, text=str(box.class_id))

    def canvas_to_image(self, x: float, y: float) -> tuple[float, float]:
        return x / max(self.display_scale, 1e-6), y / max(self.display_scale, 1e-6)

    def on_canvas_press(self, event: tk.Event) -> None:
        if self.original_image is None:
            return
        self.drag_start = (event.x, event.y)
        self.temp_rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="cyan", width=2)

    def on_canvas_drag(self, event: tk.Event) -> None:
        if self.drag_start is None or self.temp_rect is None:
            return
        self.canvas.coords(self.temp_rect, self.drag_start[0], self.drag_start[1], event.x, event.y)

    def on_canvas_release(self, event: tk.Event) -> None:
        if self.original_image is None or self.drag_start is None:
            return
        start_x, start_y = self.drag_start
        end_x, end_y = event.x, event.y
        self.drag_start = None
        if self.temp_rect is not None:
            self.canvas.delete(self.temp_rect)
            self.temp_rect = None

        ix1, iy1 = self.canvas_to_image(start_x, start_y)
        ix2, iy2 = self.canvas_to_image(end_x, end_y)
        if abs(ix2 - ix1) < 5 or abs(iy2 - iy1) < 5:
            return
        try:
            class_id = int(self.class_var.get())
        except ValueError:
            messagebox.showerror("Invalid class ID", "Class ID must be an integer.")
            return
        self.boxes.append(PixelBox(class_id=class_id, x1=ix1, y1=iy1, x2=ix2, y2=iy2))
        self.selected_box_index = len(self.boxes) - 1
        self.render_current_image()

    def on_right_click(self, event: tk.Event) -> None:
        if self.original_image is None:
            return
        best_index: Optional[int] = None
        best_area = None
        ix, iy = self.canvas_to_image(event.x, event.y)
        for idx, box in enumerate(self.boxes):
            x1, x2 = sorted((box.x1, box.x2))
            y1, y2 = sorted((box.y1, box.y2))
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                area = (x2 - x1) * (y2 - y1)
                if best_area is None or area < best_area:
                    best_area = area
                    best_index = idx
        self.selected_box_index = best_index
        self.render_current_image()

    def delete_selected_box(self) -> None:
        if self.selected_box_index is None:
            return
        del self.boxes[self.selected_box_index]
        self.selected_box_index = None
        self.render_current_image()

    def save_labels(self) -> None:
        if self.original_image is None or not self.image_paths:
            return
        image_path = self.image_paths[self.current_index]
        label_path = self.label_path_for_image(image_path)
        yolo_boxes = [pixel_to_yolo(box, self.original_image.width, self.original_image.height) for box in self.boxes]
        write_yolo_label_file(label_path, yolo_boxes)
        self.log(f"Saved labels: {label_path}")
        self.status_var.set(self.status_var.get() + "\nSaved.")

    def prev_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index - 1) % len(self.image_paths)
        self.load_current_image()

    def next_image(self) -> None:
        if not self.image_paths:
            return
        self.current_index = (self.current_index + 1) % len(self.image_paths)
        self.load_current_image()
