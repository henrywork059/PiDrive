from __future__ import annotations

from pathlib import Path

import pandas as pd

MANUAL_MODES = {'manual', 'user', 'train'}


def _mode_mask(df: pd.DataFrame, mode_filter: str) -> pd.Series:
    if 'mode' not in df.columns:
        return pd.Series([True] * len(df), index=df.index)
    modes = df['mode'].fillna('').astype(str).str.lower()
    if mode_filter == 'Manual only':
        return modes.isin(MANUAL_MODES)
    if mode_filter == 'Exclude manual':
        return ~modes.isin(MANUAL_MODES)
    return pd.Series([True] * len(df), index=df.index)


def _range_mask(df: pd.DataFrame, column: str, value_range: tuple[float, float] | None) -> pd.Series:
    if value_range is None or column not in df.columns:
        return pd.Series([True] * len(df), index=df.index)
    low, high = value_range
    numeric = pd.to_numeric(df[column], errors='coerce')
    return numeric.notna() & (numeric >= low) & (numeric <= high)


def _image_mask(df: pd.DataFrame, require_images: bool) -> pd.Series:
    if not require_images or 'abs_image' not in df.columns:
        return pd.Series([True] * len(df), index=df.index)
    image_series = df['abs_image'].fillna('').astype(str)
    return image_series.str.len().gt(0) & image_series.apply(lambda value: Path(value).exists())


def apply_preprocessing_recipe(df: pd.DataFrame, recipe: dict[str, object]) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    if df.empty:
        empty = pd.DataFrame(columns=df.columns)
        return empty, {
            'rows_before': 0,
            'rows_after': 0,
            'sessions_before': 0,
            'sessions_after': 0,
            'steering_min': 0.0,
            'steering_max': 0.0,
            'steering_mean': 0.0,
            'throttle_min': 0.0,
            'throttle_max': 0.0,
            'throttle_mean': 0.0,
        }

    filtered = df.copy()
    mask = _mode_mask(filtered, str(recipe.get('mode_filter', 'Any mode')))
    mask &= _range_mask(filtered, 'steering', recipe.get('steering_range'))
    mask &= _range_mask(filtered, 'throttle', recipe.get('speed_range'))
    mask &= _image_mask(filtered, bool(recipe.get('require_images', True)))
    filtered = filtered[mask].copy().reset_index(drop=True)
    return filtered, build_summary_dict(df, filtered)


def build_summary_dict(source_df: pd.DataFrame, filtered_df: pd.DataFrame) -> dict[str, float | int | str]:
    steering = pd.to_numeric(filtered_df.get('steering', pd.Series(dtype=float)), errors='coerce')
    throttle = pd.to_numeric(filtered_df.get('throttle', pd.Series(dtype=float)), errors='coerce')
    return {
        'rows_before': int(len(source_df)),
        'rows_after': int(len(filtered_df)),
        'sessions_before': int(len(set(source_df.get('session', [])))) if not source_df.empty else 0,
        'sessions_after': int(len(set(filtered_df.get('session', [])))) if not filtered_df.empty else 0,
        'steering_min': float(steering.min()) if not filtered_df.empty and steering.notna().any() else 0.0,
        'steering_max': float(steering.max()) if not filtered_df.empty and steering.notna().any() else 0.0,
        'steering_mean': float(steering.mean()) if not filtered_df.empty and steering.notna().any() else 0.0,
        'throttle_min': float(throttle.min()) if not filtered_df.empty and throttle.notna().any() else 0.0,
        'throttle_max': float(throttle.max()) if not filtered_df.empty and throttle.notna().any() else 0.0,
        'throttle_mean': float(throttle.mean()) if not filtered_df.empty and throttle.notna().any() else 0.0,
    }


def build_preprocess_summary(df: pd.DataFrame, selected_sessions: list[str], title: str) -> str:
    if df.empty:
        return f'{title}\n\nNo rows available.'
    summary = build_summary_dict(df, df)
    return (
        f'{title}\n\n'
        f"Selected sessions: {len(selected_sessions)}\n"
        f"Rows: {summary['rows_after']}\n"
        f"Sessions represented: {summary['sessions_after']}\n"
        f"Steering min/max/mean: {summary['steering_min']:.3f} / {summary['steering_max']:.3f} / {summary['steering_mean']:.3f}\n"
        f"Speed min/max/mean: {summary['throttle_min']:.3f} / {summary['throttle_max']:.3f} / {summary['throttle_mean']:.3f}"
    )


def format_preprocess_preview(
    summary: dict[str, float | int | str], recipe: dict[str, object], applied: bool = False
) -> str:
    title = 'Applied preprocessing recipe' if applied else 'Preprocessing recipe preview'
    lines = [
        title,
        '',
        f"Source rows: {summary['rows_before']}",
        f"Remaining rows: {summary['rows_after']}",
        f"Source sessions: {summary['sessions_before']}",
        f"Remaining sessions: {summary['sessions_after']}",
        f"Mode filter: {recipe.get('mode_filter', 'Any mode')}",
        f"Require existing images: {'Yes' if recipe.get('require_images', True) else 'No'}",
        f"Steering range: {recipe.get('steering_range') or 'Disabled'}",
        f"Speed range: {recipe.get('speed_range') or 'Disabled'}",
        f"Output image size: {recipe.get('image_width')}x{recipe.get('image_height')}",
        '',
        (
            'Remaining steering min/max/mean: '
            f"{summary['steering_min']:.3f} / {summary['steering_max']:.3f} / {summary['steering_mean']:.3f}"
        ),
        (
            'Remaining speed min/max/mean: '
            f"{summary['throttle_min']:.3f} / {summary['throttle_max']:.3f} / {summary['throttle_mean']:.3f}"
        ),
    ]
    return '\n'.join(lines)
