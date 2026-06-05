from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ..validation.validation_service import run_tflite_validation, run_validation, validation_preview_rows


MODEL_SOURCE_CURRENT = 'Current trained model'
MODEL_SOURCE_SAVED = 'Load .keras / .h5 model'
MODEL_SOURCE_TFLITE = 'Load .tflite model'


def _normalise_model_source(model_source: str, model_path: str) -> str:
    source = str(model_source or '').strip()
    path = str(model_path or '').strip().lower()
    if source == MODEL_SOURCE_TFLITE or path.endswith('.tflite'):
        return MODEL_SOURCE_TFLITE
    if source == MODEL_SOURCE_SAVED:
        return MODEL_SOURCE_SAVED
    return MODEL_SOURCE_CURRENT


def run_model_deploy(
    dataset_df: pd.DataFrame,
    train_config: Any,
    in_memory_model: Any,
    *,
    model_source: str,
    model_path: str,
    batch_size: int,
    max_rows: int = 0,
) -> dict[str, Any]:
    """Run the selected model over Data-page rows and return prediction rows.

    This deliberately reuses the Validate/TFLite Check prediction paths so Data
    deploy uses the same image resize, flip handling, Keras output parsing, and
    TFLite output mapping as the existing validation pages.
    """
    if dataset_df is None or dataset_df.empty:
        raise ValueError('No frames are visible. Load a session or loosen the filter first.')

    source = _normalise_model_source(model_source, model_path)
    if source == MODEL_SOURCE_TFLITE:
        result = run_tflite_validation(
            dataset_df,
            train_config,
            tflite_path=str(model_path or ''),
            batch_size=max(1, int(batch_size)),
            max_rows=max(0, int(max_rows or 0)),
        )
    else:
        validation_source = MODEL_SOURCE_CURRENT if source == MODEL_SOURCE_CURRENT else MODEL_SOURCE_SAVED
        result = run_validation(
            dataset_df,
            train_config,
            in_memory_model,
            validation_source,
            str(model_path or ''),
            batch_size=max(1, int(batch_size)),
            max_rows=max(0, int(max_rows or 0)),
        )

    rows = validation_preview_rows(result)
    for row in rows:
        steering_true = float(row.get('target_steering', 0.0) or 0.0)
        speed_true = float(row.get('target_speed', 0.0) or 0.0)
        steering_pred = float(row.get('pred_steering', 0.0) or 0.0)
        speed_pred = float(row.get('pred_speed', 0.0) or 0.0)
        row['pred_throttle'] = speed_pred
        row['steering_diff'] = abs(steering_pred - steering_true)
        row['speed_diff'] = abs(speed_pred - speed_true)

    result['model_source'] = source
    result['deploy_rows'] = rows
    return result


def latest_model_path(out_dir: str, *, include_tflite: bool = False) -> str:
    root = Path(out_dir or '.').expanduser()
    patterns = ('*.tflite',) if include_tflite else ('*.keras', '*.h5')
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path for path in root.glob(pattern) if path.is_file())
    if not matches:
        return ''
    matches.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0.0)
    return str(matches[-1])
