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

    Rows marked with ``aug_flip_lr`` are rendered/flown into TensorFlow as
    left-right flipped images. Their steering label must therefore point in the
    opposite direction to the source frame, while speed/throttle must remain the
    same. This helper is intentionally shared by preprocessing, training,
    validation, and review paths so the same safety rule is applied everywhere.

    Preferred source of truth is ``source_steering`` stored on synthetic rows.
    For older/pre-safety datasets, the helper also tries to recover the source
    steering from an unflipped row with a matching ``source_frame_id``/``frame_id``.
    Rows that cannot be proven safe are left unchanged but marked with a warning
    column so they can be inspected instead of being silently double-inverted.
    """
    if df is None:
        return pd.DataFrame()
    if df.empty or 'aug_flip_lr' not in df.columns:
        return df.copy()

    result = df.copy()
    flip_mask = boolean_series(result['aug_flip_lr'], default=False)
    if not flip_mask.any():
        return result

    index = result.index
    source_steering = pd.Series(float('nan'), index=index, dtype='float64')
    steering_source = pd.Series('', index=index, dtype='object')

    if 'source_steering' in result.columns:
        explicit_source = pd.to_numeric(result['source_steering'], errors='coerce')
        explicit_mask = flip_mask & explicit_source.notna()
        source_steering.loc[explicit_mask] = explicit_source.loc[explicit_mask]
        steering_source.loc[explicit_mask] = 'source_steering'

    # Compatibility guard for older saved datasets: when a flipped row has a
    # source_frame_id but no source_steering, recover the label from the matching
    # unflipped source row in the same dataframe. This avoids trusting a flipped
    # row's current steering value, which may already be inverted.
    unresolved = flip_mask & source_steering.isna()
    if unresolved.any() and {'source_frame_id', 'frame_id', 'steering'}.issubset(result.columns):
        unflipped = result.loc[~flip_mask, ['frame_id', 'steering']].copy()
        unflipped['_frame_key'] = unflipped['frame_id'].fillna('').astype(str).str.strip()
        unflipped['_source_value'] = pd.to_numeric(unflipped['steering'], errors='coerce')
        lookup = (
            unflipped[unflipped['_frame_key'].str.len().gt(0) & unflipped['_source_value'].notna()]
            .drop_duplicates('_frame_key', keep='first')
            .set_index('_frame_key')['_source_value']
        )
        source_ids = result['source_frame_id'].fillna('').astype(str).str.strip()
        recovered = source_ids.map(lookup)
        recovered_mask = unresolved & recovered.notna()
        if recovered_mask.any():
            source_steering.loc[recovered_mask] = recovered.loc[recovered_mask]
            steering_source.loc[recovered_mask] = 'matched_source_frame_id'

    valid_mask = flip_mask & source_steering.notna()
    if valid_mask.any():
        clipped_source = source_steering.loc[valid_mask].clip(-1.0, 1.0)
        result.loc[valid_mask, 'source_steering'] = clipped_source
        result.loc[valid_mask, 'steering'] = (-clipped_source).clip(-1.0, 1.0)
        result.loc[valid_mask, 'flip_steering_inverted'] = True
        result.loc[valid_mask, 'flip_label_source'] = steering_source.loc[valid_mask].replace('', 'source_steering')
        result.loc[valid_mask, 'flip_label_warning'] = ''

        # Speed/throttle should not change for a left-right flip. If source
        # values were stored, re-apply them defensively so training and
        # validation do not learn accidental speed edits from the synthetic row.
        if 'source_throttle' in result.columns and 'throttle' in result.columns:
            source_throttle = pd.to_numeric(result['source_throttle'], errors='coerce')
            throttle_mask = valid_mask & source_throttle.notna()
            if throttle_mask.any():
                result.loc[throttle_mask, 'throttle'] = source_throttle.loc[throttle_mask]
        if 'source_speed' in result.columns and 'speed' in result.columns:
            source_speed = pd.to_numeric(result['source_speed'], errors='coerce')
            speed_mask = valid_mask & source_speed.notna()
            if speed_mask.any():
                result.loc[speed_mask, 'speed'] = source_speed.loc[speed_mask]

    unresolved = flip_mask & source_steering.isna()
    if unresolved.any():
        existing = boolean_series(result.get('flip_steering_inverted', pd.Series([False] * len(result), index=index)), default=False)
        unsafe_mask = unresolved & ~existing
        if unsafe_mask.any():
            result.loc[unsafe_mask, 'flip_label_warning'] = 'missing_source_steering_label_not_auto_inverted'
        trusted_mask = unresolved & existing
        if trusted_mask.any():
            result.loc[trusted_mask, 'flip_label_warning'] = 'trusted_existing_inverted_label_no_source_steering'

    return result
