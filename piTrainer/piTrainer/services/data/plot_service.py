from __future__ import annotations

from typing import Any

import pandas as pd


def plot_sessions_for_combo(df: pd.DataFrame) -> list[str]:
    if df.empty or 'session' not in df.columns:
        return []
    return sorted(df['session'].dropna().astype(str).unique().tolist())


def filter_plot_dataframe(df: pd.DataFrame, session_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if session_name and session_name != 'All loaded sessions' and 'session' in df.columns:
        filtered = df[df['session'].astype(str) == session_name].copy()
        return filtered.reset_index(drop=True)
    return df.reset_index(drop=True).copy()


def build_plot_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            'rows': 0,
            'sessions': 0,
            'steering_min': 0.0,
            'steering_max': 0.0,
            'steering_mean': 0.0,
            'throttle_min': 0.0,
            'throttle_max': 0.0,
            'throttle_mean': 0.0,
        }

    steering = pd.to_numeric(df.get('steering', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    throttle = pd.to_numeric(df.get('throttle', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    sessions = int(df['session'].nunique()) if 'session' in df.columns else 0
    return {
        'rows': int(len(df)),
        'sessions': sessions,
        'steering_min': float(steering.min()),
        'steering_max': float(steering.max()),
        'steering_mean': float(steering.mean()),
        'throttle_min': float(throttle.min()),
        'throttle_max': float(throttle.max()),
        'throttle_mean': float(throttle.mean()),
    }
