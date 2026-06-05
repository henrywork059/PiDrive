from __future__ import annotations

import pandas as pd

# Keep Record Preview deliberately small and stable.
# The table is a review/navigation tool, not the full metadata editor.
# `frame_id` must remain first so the user always sees the frame identity first.
PREVIEW_COLUMN_ORDER = [
    "frame_id",
    "session",
    "steering",
    "throttle",
    "pred_steering",
    "pred_throttle",
    "steering_diff",
    "speed_diff",
    "mode",
    "ts",
]


def dataframe_preview_rows(df: pd.DataFrame, limit: int | None = None) -> list[dict]:
    if df.empty:
        return []
    columns = [col for col in PREVIEW_COLUMN_ORDER if col in df.columns]
    sample = df if limit is None else df.head(limit)
    rows: list[dict] = []
    for _, row in sample.iterrows():
        rows.append({col: row.get(col, "") for col in columns})
    return rows


def preview_columns(rows: list[dict]) -> list[str]:
    if not rows:
        return []
    present = set()
    for row in rows:
        present.update(row.keys())
    ordered = [col for col in PREVIEW_COLUMN_ORDER if col in present]
    # Safety fallback: append any unexpected keys after the stable columns.
    for row in rows:
        for key in row.keys():
            if key not in ordered:
                ordered.append(key)
    return ordered
