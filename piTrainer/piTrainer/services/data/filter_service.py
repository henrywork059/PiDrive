from __future__ import annotations

import pandas as pd


RangeTuple = tuple[float, float] | None


def _apply_range_filter(filtered: pd.DataFrame, column: str, value_range: RangeTuple) -> pd.DataFrame:
    if value_range is None or column not in filtered.columns:
        return filtered
    min_value, max_value = value_range
    numeric = pd.to_numeric(filtered[column], errors='coerce')
    mask = numeric.notna() & (numeric >= min_value) & (numeric <= max_value)
    return filtered[mask].copy()


def filter_preview_dataframe(
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
