from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MANUAL_MODES = {'manual', 'user', 'train'}
COLOR_PRESETS = [
    {'aug_brightness_delta': 0.06, 'aug_contrast_factor': 1.08, 'aug_saturation_factor': 1.08, 'aug_hue_delta': 0.01},
    {'aug_brightness_delta': -0.05, 'aug_contrast_factor': 0.94, 'aug_saturation_factor': 0.92, 'aug_hue_delta': -0.01},
    {'aug_brightness_delta': 0.03, 'aug_contrast_factor': 1.12, 'aug_saturation_factor': 0.90, 'aug_hue_delta': 0.015},
    {'aug_brightness_delta': -0.02, 'aug_contrast_factor': 0.88, 'aug_saturation_factor': 1.12, 'aug_hue_delta': -0.015},
]
AUGMENT_DEFAULTS = {
    'aug_flip_lr': False,
    'aug_brightness_delta': 0.0,
    'aug_contrast_factor': 1.0,
    'aug_saturation_factor': 1.0,
    'aug_hue_delta': 0.0,
    'aug_variant': 'original',
}


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


def _deterministic_take(index_values: pd.Index, keep_count: int) -> pd.Index:
    keep_count = max(0, min(int(keep_count), len(index_values)))
    if keep_count >= len(index_values):
        return index_values
    if keep_count <= 0:
        return pd.Index([])
    positions = np.linspace(0, len(index_values) - 1, keep_count, dtype=int)
    return index_values[positions]


def _apply_straight_balance(df: pd.DataFrame, recipe: dict[str, object]) -> tuple[pd.DataFrame, dict[str, int | float]]:
    if df.empty or 'steering' not in df.columns or not bool(recipe.get('balance_straight', False)):
        return df, {
            'straight_rows_before_balance': int(len(df)),
            'straight_rows_after_balance': int(len(df)),
            'straight_rows_removed': 0,
            'straight_threshold': float(recipe.get('straight_threshold', 0.05) or 0.05),
            'straight_keep_ratio': float(recipe.get('straight_keep_ratio', 0.35) or 0.35),
        }

    threshold = abs(float(recipe.get('straight_threshold', 0.05) or 0.05))
    keep_ratio = float(recipe.get('straight_keep_ratio', 0.35) or 0.35)
    keep_ratio = max(0.01, min(1.0, keep_ratio))

    steering = pd.to_numeric(df['steering'], errors='coerce').fillna(0.0)
    straight_mask = steering.abs() <= threshold
    straight_index = df.index[straight_mask]
    turn_index = df.index[~straight_mask]
    keep_count = int(np.ceil(len(straight_index) * keep_ratio))
    kept_straight = _deterministic_take(straight_index, keep_count)
    kept_index = kept_straight.append(turn_index).sort_values()
    balanced = df.loc[kept_index].copy().reset_index(drop=True)
    return balanced, {
        'straight_rows_before_balance': int(len(straight_index)),
        'straight_rows_after_balance': int(len(kept_straight)),
        'straight_rows_removed': int(len(straight_index) - len(kept_straight)),
        'straight_threshold': threshold,
        'straight_keep_ratio': keep_ratio,
    }


def _with_default_aug_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column, default_value in AUGMENT_DEFAULTS.items():
        if column not in result.columns:
            result[column] = default_value
        else:
            result[column] = result[column].fillna(default_value)
    return result


def _build_augmented_dataset(filtered: pd.DataFrame, recipe: dict[str, object]) -> tuple[pd.DataFrame, dict[str, int]]:
    base = _with_default_aug_columns(filtered).reset_index(drop=True)
    if base.empty:
        return base, {
            'original_rows_after_filter': 0,
            'mirror_rows_added': 0,
            'color_rows_added': 0,
            'generated_rows': 0,
        }

    mirror_enabled = bool(recipe.get('mirror_enabled', False))
    color_variants = int(recipe.get('color_variants', 0) or 0)
    pieces = [base]
    mirror_rows_added = 0
    color_rows_added = 0

    if mirror_enabled:
        mirror_df = base.copy()
        if 'steering' in mirror_df.columns:
            mirror_df['steering'] = -pd.to_numeric(mirror_df['steering'], errors='coerce').fillna(0.0)
        mirror_df['aug_flip_lr'] = True
        mirror_df['aug_variant'] = 'mirror'
        pieces.append(mirror_df)
        mirror_rows_added = int(len(mirror_df))

    color_variants = max(0, min(color_variants, len(COLOR_PRESETS)))
    for variant_index in range(color_variants):
        params = COLOR_PRESETS[variant_index]
        color_df = base.copy()
        for column, value in params.items():
            color_df[column] = value
        color_df['aug_variant'] = f'color_{variant_index + 1}'
        pieces.append(color_df)
        color_rows_added += int(len(color_df))

    expanded = pd.concat(pieces, ignore_index=True)
    return expanded, {
        'original_rows_after_filter': int(len(base)),
        'mirror_rows_added': mirror_rows_added,
        'color_rows_added': color_rows_added,
        'generated_rows': mirror_rows_added + color_rows_added,
    }


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
            'original_rows_after_filter': 0,
            'mirror_rows_added': 0,
            'color_rows_added': 0,
            'generated_rows': 0,
            'straight_rows_before_balance': 0,
            'straight_rows_after_balance': 0,
            'straight_rows_removed': 0,
            'straight_threshold': float(recipe.get('straight_threshold', 0.05) or 0.05),
            'straight_keep_ratio': float(recipe.get('straight_keep_ratio', 0.35) or 0.35),
        }

    filtered = df.copy()
    mask = _mode_mask(filtered, str(recipe.get('mode_filter', 'Any mode')))
    mask &= _range_mask(filtered, 'steering', recipe.get('steering_range'))
    mask &= _range_mask(filtered, 'throttle', recipe.get('speed_range'))
    mask &= _image_mask(filtered, bool(recipe.get('require_images', True)))
    filtered = filtered[mask].copy().reset_index(drop=True)

    balanced, balance_counts = _apply_straight_balance(filtered, recipe)
    expanded, aug_counts = _build_augmented_dataset(balanced, recipe)
    return expanded, build_summary_dict(df, expanded, aug_counts=aug_counts, balance_counts=balance_counts)


def build_summary_dict(
    source_df: pd.DataFrame,
    filtered_df: pd.DataFrame,
    aug_counts: dict[str, int] | None = None,
    balance_counts: dict[str, int | float] | None = None,
) -> dict[str, float | int | str]:
    steering = pd.to_numeric(filtered_df.get('steering', pd.Series(dtype=float)), errors='coerce')
    throttle = pd.to_numeric(filtered_df.get('throttle', pd.Series(dtype=float)), errors='coerce')
    aug_counts = aug_counts or {
        'original_rows_after_filter': int(len(filtered_df)),
        'mirror_rows_added': 0,
        'color_rows_added': 0,
        'generated_rows': 0,
    }
    balance_counts = balance_counts or {
        'straight_rows_before_balance': int(len(filtered_df)),
        'straight_rows_after_balance': int(len(filtered_df)),
        'straight_rows_removed': 0,
        'straight_threshold': 0.05,
        'straight_keep_ratio': 0.35,
    }
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
        'original_rows_after_filter': int(aug_counts.get('original_rows_after_filter', len(filtered_df))),
        'mirror_rows_added': int(aug_counts.get('mirror_rows_added', 0)),
        'color_rows_added': int(aug_counts.get('color_rows_added', 0)),
        'generated_rows': int(aug_counts.get('generated_rows', 0)),
        'straight_rows_before_balance': int(balance_counts.get('straight_rows_before_balance', len(filtered_df))),
        'straight_rows_after_balance': int(balance_counts.get('straight_rows_after_balance', len(filtered_df))),
        'straight_rows_removed': int(balance_counts.get('straight_rows_removed', 0)),
        'straight_threshold': float(balance_counts.get('straight_threshold', 0.05)),
        'straight_keep_ratio': float(balance_counts.get('straight_keep_ratio', 0.35)),
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
        f"Rows after filter/balance: {summary['original_rows_after_filter']}",
        f"Straight rows kept: {summary['straight_rows_after_balance']} / {summary['straight_rows_before_balance']}",
        f"Straight rows removed: {summary['straight_rows_removed']}",
        f"Generated rows: {summary['generated_rows']}",
        f"Active rows after augmentation: {summary['rows_after']}",
        f"Source sessions: {summary['sessions_before']}",
        f"Remaining sessions: {summary['sessions_after']}",
        f"Mode filter: {recipe.get('mode_filter', 'Any mode')}",
        f"Require existing images: {'Yes' if recipe.get('require_images', True) else 'No'}",
        f"Steering range: {recipe.get('steering_range') or 'Disabled'}",
        f"Speed range: {recipe.get('speed_range') or 'Disabled'}",
        (
            'Balance near-zero steering rows: '
            f"{'Enabled' if recipe.get('balance_straight', False) else 'Disabled'}"
        ),
        f"Straight threshold: {float(recipe.get('straight_threshold', 0.05) or 0.05):.3f}",
        f"Straight keep ratio: {float(recipe.get('straight_keep_ratio', 0.35) or 0.35):.2f}",
        f"Mirror copies: {'Enabled' if recipe.get('mirror_enabled', False) else 'Disabled'}",
        f"Color variants per row: {int(recipe.get('color_variants', 0) or 0)}",
        f"Added mirrored rows: {summary['mirror_rows_added']}",
        f"Added color rows: {summary['color_rows_added']}",
        f"Output image size: {recipe.get('image_width')}x{recipe.get('image_height')}",
        '',
        (
            'Active steering min/max/mean: '
            f"{summary['steering_min']:.3f} / {summary['steering_max']:.3f} / {summary['steering_mean']:.3f}"
        ),
        (
            'Active speed min/max/mean: '
            f"{summary['throttle_min']:.3f} / {summary['throttle_max']:.3f} / {summary['throttle_mean']:.3f}"
        ),
    ]
    return '\n'.join(lines)
