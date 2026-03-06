from __future__ import annotations

import pandas as pd



def dataframe_preview_rows(df: pd.DataFrame, limit: int = 50) -> list[dict]:
    if df.empty:
        return []
    rows = []
    keep_columns = [
        col
        for col in ["session", "frame_id", "mode", "steering", "throttle", "ts", "cam_w", "cam_h", "format"]
        if col in df.columns
    ]
    sample = df.head(limit)
    for _, row in sample.iterrows():
        rows.append({col: row.get(col, "") for col in keep_columns})
    return rows



def preview_columns(rows: list[dict]) -> list[str]:
    if not rows:
        return []
    ordered = []
    for row in rows:
        for key in row.keys():
            if key not in ordered:
                ordered.append(key)
    return ordered
