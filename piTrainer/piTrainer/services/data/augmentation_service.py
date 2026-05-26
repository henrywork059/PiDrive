from __future__ import annotations

import math
from typing import Any

import pandas as pd

TRUE_TEXT = {'1', 'true', 't', 'yes', 'y', 'on'}
FALSE_TEXT = {'0', 'false', 'f', 'no', 'n', 'off', 'none', 'nan', ''}


def truthy_value(value: Any, default: bool = False) -> bool:
    """Parse bool-like values safely, including values loaded from CSV/JSONL."""
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    try:
        if isinstance(value, float) and math.isnan(value):
            return bool(default)
    except TypeError:
        pass
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUE_TEXT:
        return True
    if text in FALSE_TEXT:
        return False
    return bool(default)


def boolean_series(series: pd.Series, default: bool = False) -> pd.Series:
    """Return a boolean Series without treating the string 'False' as truthy."""
    if series is None:
        return pd.Series(dtype=bool)
    return series.map(lambda value: truthy_value(value, default=default)).astype(bool)


def normalize_horizontal_flip_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Keep horizontal-flip rows label-safe.

    The image loader flips rows marked with ``aug_flip_lr``. Their steering label
    must point in the opposite direction to the source row, while throttle/speed
    values must remain unchanged. When ``source_steering`` is present, use it as
    the source of truth and correct the synthetic row's ``steering`` label.
    """
    if df is None or df.empty or 'aug_flip_lr' not in df.columns:
        return df.copy() if df is not None else pd.DataFrame()

    result = df.copy()
    flip_mask = boolean_series(result['aug_flip_lr'], default=False)
    if not flip_mask.any() or 'source_steering' not in result.columns:
        return result

    source_steering = pd.to_numeric(result['source_steering'], errors='coerce')
    valid_mask = flip_mask & source_steering.notna()
    if valid_mask.any():
        result.loc[valid_mask, 'steering'] = (-source_steering[valid_mask]).clip(-1.0, 1.0)
        result.loc[valid_mask, 'flip_steering_inverted'] = True
    return result
