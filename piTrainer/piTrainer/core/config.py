from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppConfig:
    records_root: Path
    out_dir: Path

@dataclass
class TrainConfig:
    img_h: int = 120
    img_w: int = 160
    batch: int = 32
    epochs: int = 10
    lr: float = 1e-3
    val_ratio: float = 0.2
    only_manual: bool = True
    augment: bool = True
    session_split: bool = True  # avoid leakage by splitting per session
