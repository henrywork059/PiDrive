from __future__ import annotations

import numpy as np
import pandas as pd


RangeTuple = tuple[float, float] | None


def _apply_range_filter(filtered: pd.DataFrame, column: str, value_range: RangeTuple) -> pd.DataFrame:
    if value_range is None or column not in filtered.columns:
        return filtered
    min_value, max_value = value_range
    numeric = pd.to_numeric(filtered[column], errors='coerce')
    mask = numeric.notna() & (numeric >= min_value) & (numeric <= max_value)
    return filtered[mask].copy()


def _legacy_filter(
    df: pd.DataFrame,
    text: str = "",
    mode: str = "",
    speed_range: RangeTuple = None,
    steering_range: RangeTuple = None,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    filtered = df.copy()

    text = text.strip().lower()
    if text:
        cols = [col for col in ["session", "frame_id", "mode", "ts"] if col in filtered.columns]
        if cols:
            mask = filtered[cols].fillna("").astype(str).apply(
                lambda row: text in " ".join(value.lower() for value in row.values), axis=1
            )
            filtered = filtered[mask].copy()

    mode = mode.strip().lower()
    if mode and "mode" in filtered.columns:
        filtered = filtered[filtered["mode"].fillna("").astype(str).str.lower() == mode].copy()

    filtered = _apply_range_filter(filtered, 'throttle', speed_range)
    filtered = _apply_range_filter(filtered, 'steering', steering_range)
    return filtered.reset_index(drop=True)


def filter_preview_dataframe(df: pd.DataFrame, text: str = "", mode: str = "",
                             speed_range: RangeTuple = None, steering_range: RangeTuple = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if not df.columns.is_unique:
        return _legacy_filter(df,text,mode,speed_range,steering_range)
    positions = None
    def restrict(mask):
        nonlocal positions
        keep = mask.to_numpy(dtype=bool, na_value=False)
        positions = np.flatnonzero(keep) if positions is None else positions[keep]
    def select(values):
        return values if positions is None else values.iloc[positions]
    text = text.strip().lower()
    if text:
        cols = [col for col in ['session','frame_id','mode','ts'] if col in df.columns]
        if cols:
            mask = select(df[cols]).fillna('').astype(str).apply(lambda row: text in ' '.join(value.lower() for value in row.values),axis=1)
            restrict(mask)
    mode = mode.strip().lower()
    if mode and 'mode' in df.columns:
        restrict(select(df['mode']).fillna('').astype(str).str.lower() == mode)
    for column, bounds in (('throttle',speed_range),('steering',steering_range)):
        if bounds is not None and column in df.columns:
            low,high = bounds
            numeric = pd.to_numeric(select(df[column]),errors='coerce')
            restrict(numeric.notna() & (numeric >= low) & (numeric <= high))
    result = df.copy() if positions is None else df.take(positions)
    result.index = pd.RangeIndex(len(result))
    return result
