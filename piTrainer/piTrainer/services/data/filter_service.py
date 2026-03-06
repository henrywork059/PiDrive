from __future__ import annotations

import pandas as pd


def filter_preview_dataframe(df: pd.DataFrame, text: str = "", mode: str = "") -> pd.DataFrame:
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

    return filtered.reset_index(drop=True)
