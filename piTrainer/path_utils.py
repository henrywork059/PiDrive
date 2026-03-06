from __future__ import annotations

import pandas as pd



def calculate_basic_stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "rows": 0,
            "sessions": 0,
            "steering_mean": 0.0,
            "steering_std": 0.0,
            "throttle_mean": 0.0,
            "throttle_std": 0.0,
        }
    return {
        "rows": int(len(df)),
        "sessions": int(df["session"].nunique()) if "session" in df.columns else 0,
        "steering_mean": float(df["steering"].mean()),
        "steering_std": float(df["steering"].std() if len(df) > 1 else 0.0),
        "throttle_mean": float(df["throttle"].mean()),
        "throttle_std": float(df["throttle"].std() if len(df) > 1 else 0.0),
    }
