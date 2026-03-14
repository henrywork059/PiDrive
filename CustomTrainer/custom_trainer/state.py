from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class DatasetSummary:
    image_count: int = 0
    label_count: int = 0
    missing_labels: int = 0
    extra_labels: int = 0
    class_histogram: dict[int, int] = field(default_factory=dict)


@dataclass
class AppState:
    project_root: Optional[Path] = None
    images_dir: Optional[Path] = None
    labels_dir: Optional[Path] = None
    dataset_yaml: Optional[Path] = None
    classes: List[str] = field(default_factory=lambda: ["he3", "mineral", "radiation", "he3_zone"])
    model_path: str = "yolov8n.pt"
    runs_dir: Optional[Path] = None
    last_summary: DatasetSummary = field(default_factory=DatasetSummary)
