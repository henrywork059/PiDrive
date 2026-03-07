from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class TrainConfig:
    img_h: int = 120
    img_w: int = 160
    batch_size: int = 32
    epochs: int = 10
    learning_rate: float = 1e-3
    val_ratio: float = 0.2
    only_manual: bool = True
    augment: bool = True
    session_split: bool = True
    shuffle: bool = True
    model_size: str = 'Small CNN'
    seed: int = 42
    early_stopping: bool = True
    early_stopping_patience: int = 4
    reduce_lr_on_plateau: bool = True
    reduce_lr_patience: int = 2
    reduce_lr_factor: float = 0.5


@dataclass
class ExportConfig:
    out_dir: str = str(Path("trainer_out").resolve())
    base_name: str = "picar_model"
    export_keras: bool = True
    export_tflite: bool = True
    quantize_int8: bool = False


@dataclass
class AppState:
    records_root: str = str(Path("data/records").resolve())
    available_sessions: list[str] = field(default_factory=list)
    selected_sessions: list[str] = field(default_factory=list)
    dataset_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    filtered_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    train_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    val_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    train_config: TrainConfig = field(default_factory=TrainConfig)
    export_config: ExportConfig = field(default_factory=ExportConfig)
    model: Any = None
    history: dict[str, list[float]] = field(default_factory=dict)
    last_error: str = ""

    @property
    def records_root_path(self) -> Path:
        return Path(self.records_root).expanduser().resolve()

    @property
    def out_dir_path(self) -> Path:
        return Path(self.export_config.out_dir).expanduser().resolve()
