from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.augmentation_service import boolean_series


def _series_text(rows: pd.DataFrame, column: str, default='') -> list[str]:
    if column not in rows.columns:
        return [str(default)] * len(rows)
    series = rows[column].astype(object).where(rows[column].notna(), default)
    return series.astype(str).tolist()

def _prediction_range(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {'min': 0.0, 'max': 0.0, 'mean': 0.0}
    return {
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'mean': float(np.mean(values)),
    }

def _build_validation_result(
    *,
    rows: pd.DataFrame,
    steering_true: np.ndarray,
    throttle_true: np.ndarray,
    steering_pred: np.ndarray,
    throttle_pred: np.ndarray,
    dataset_name: str,
    model_kind: str,
    model_path: str = '',
    prediction_backend: str = '',
    backend_notes: list[str] | tuple[str, ...] = (),
) -> dict:
    steering_pred = np.asarray(steering_pred, dtype=np.float32).reshape(-1)
    throttle_pred = np.asarray(throttle_pred, dtype=np.float32).reshape(-1)
    steering_true = np.asarray(steering_true, dtype=np.float32).reshape(-1)
    throttle_true = np.asarray(throttle_true, dtype=np.float32).reshape(-1)
    total = min(len(rows), len(steering_true), len(throttle_true), len(steering_pred), len(throttle_pred))
    if total <= 0:
        raise ValueError('No predictions were produced for validation.')

    rows = rows.head(total).reset_index(drop=True)
    steering_true = steering_true[:total]
    throttle_true = throttle_true[:total]
    steering_pred = steering_pred[:total]
    throttle_pred = throttle_pred[:total]

    steering_error = steering_pred - steering_true
    throttle_error = throttle_pred - throttle_true
    combined_error = np.abs(steering_error) + np.abs(throttle_error)

    frame_number_series = rows.get(
        'frame_number',
        rows.get('frame_no', rows.get('source_row_number', pd.Series(range(1, len(rows) + 1)))),
    )
    synthetic_series = rows.get('synthetic_variant', rows.get('aug_variant', pd.Series([''] * len(rows))))

    return {
        'rows_used': int(len(rows)),
        'dataset_name': dataset_name,
        'model_kind': model_kind,
        'model_path': str(model_path or ''),
        'prediction_backend': str(prediction_backend or ''),
        'backend_notes': list(dict.fromkeys(str(note) for note in backend_notes if str(note).strip())),
        'prediction_ranges': {
            'steering': _prediction_range(steering_pred),
            'speed': _prediction_range(throttle_pred),
        },
        'frame_ids': _series_text(rows, 'frame_id'),
        'frame_numbers': frame_number_series.astype(object).where(frame_number_series.notna(), '').astype(str).tolist(),
        'sessions': _series_text(rows, 'session'),
        'modes': _series_text(rows, 'mode'),
        'timestamps': _series_text(rows, 'ts'),
        'abs_images': _series_text(rows, 'abs_image'),
        'aug_flip_lr': boolean_series(rows['aug_flip_lr'], default=False).tolist() if 'aug_flip_lr' in rows.columns else [False] * len(rows),
        'source_frame_ids': _series_text(rows, 'source_frame_id'),
        'synthetic_variants': synthetic_series.astype(object).where(synthetic_series.notna(), '').astype(str).tolist(),
        'flip_label_sources': _series_text(rows, 'flip_label_source'),
        'flip_label_warnings': _series_text(rows, 'flip_label_warning'),
        'overlay_settings': rows.get('overlay_settings', pd.Series([{} for _ in range(len(rows))])).tolist(),
        'overlay_schema_versions': _series_text(rows, 'overlay_schema_version'),
        'steering_true': steering_true,
        'throttle_true': throttle_true,
        'steering_pred': steering_pred,
        'throttle_pred': throttle_pred,
        'steering_error': steering_error,
        'throttle_error': throttle_error,
        'combined_error': combined_error,
        'steering_mae': float(np.mean(np.abs(steering_error))),
        'throttle_mae': float(np.mean(np.abs(throttle_error))),
        'steering_rmse': float(np.sqrt(np.mean(np.square(steering_error)))),
        'throttle_rmse': float(np.sqrt(np.mean(np.square(throttle_error)))),
        'steering_bias': float(np.mean(steering_error)),
        'throttle_bias': float(np.mean(throttle_error)),
    }

def _range_text(values: dict[str, float]) -> str:
    return f"min={values.get('min', 0.0):.4f}, max={values.get('max', 0.0):.4f}, mean={values.get('mean', 0.0):.4f}"

def build_validation_summary_text(result: dict) -> str:
    lines = []
    model_kind = str(result.get('model_kind', '')).strip()
    model_path = str(result.get('model_path', '')).strip()
    prediction_backend = str(result.get('prediction_backend', '')).strip()
    if model_kind or model_path:
        path_suffix = f" — {model_path}" if model_path else ''
        lines.append(f"Model source: {model_kind}{path_suffix}")
    if prediction_backend:
        lines.append(f"Prediction backend: {prediction_backend}")
    lines.extend([
        f"Rows used: {result['rows_used']}",
        f"Steering MAE / RMSE / Bias: {result['steering_mae']:.4f} / {result['steering_rmse']:.4f} / {result['steering_bias']:.4f}",
        f"Speed MAE / RMSE / Bias: {result['throttle_mae']:.4f} / {result['throttle_rmse']:.4f} / {result['throttle_bias']:.4f}",
    ])
    ranges = result.get('prediction_ranges', {}) if isinstance(result.get('prediction_ranges', {}), dict) else {}
    if ranges:
        lines.append(f"Prediction range — steering: {_range_text(ranges.get('steering', {}))} | speed: {_range_text(ranges.get('speed', {}))}")
    notes = result.get('backend_notes', []) or []
    if notes:
        lines.append('Backend notes:')
        lines.extend(f"- {note}" for note in notes[:5])
    lines.append('Use the plot panel and frame-review panel to inspect prediction agreement, bad frames, and overlay differences.')
    return '\n'.join(lines)

def validation_preview_rows(result: dict | None) -> list[dict]:
    if not result:
        return []
    rows = []
    total = int(result.get('rows_used', 0) or 0)
    frame_ids = list(result.get('frame_ids', []))
    frame_numbers = list(result.get('frame_numbers', []))
    sessions = list(result.get('sessions', []))
    modes = list(result.get('modes', []))
    timestamps = list(result.get('timestamps', []))
    abs_images = list(result.get('abs_images', []))
    aug_flip_lr = list(result.get('aug_flip_lr', []))
    source_frame_ids = list(result.get('source_frame_ids', []))
    synthetic_variants = list(result.get('synthetic_variants', []))
    flip_label_sources = list(result.get('flip_label_sources', []))
    flip_label_warnings = list(result.get('flip_label_warnings', []))
    overlay_settings = list(result.get('overlay_settings', []))
    overlay_schema_versions = list(result.get('overlay_schema_versions', []))
    steering_true = np.asarray(result.get('steering_true', []))
    throttle_true = np.asarray(result.get('throttle_true', []))
    steering_pred = np.asarray(result.get('steering_pred', []))
    throttle_pred = np.asarray(result.get('throttle_pred', []))
    combined_error = np.asarray(result.get('combined_error', []))
    for idx in range(total):
        rows.append(
            {
                'result_index': int(idx),
                'row_number': int(idx + 1),
                'session': str(sessions[idx]) if idx < len(sessions) else '',
                'mode': str(modes[idx]) if idx < len(modes) else '',
                'frame_id': str(frame_ids[idx]) if idx < len(frame_ids) else '',
                'frame_number': str(frame_numbers[idx]) if idx < len(frame_numbers) else '',
                'ts': str(timestamps[idx]) if idx < len(timestamps) else '',
                'abs_image': str(abs_images[idx]) if idx < len(abs_images) else '',
                'aug_flip_lr': bool(aug_flip_lr[idx]) if idx < len(aug_flip_lr) else False,
                'source_frame_id': str(source_frame_ids[idx]) if idx < len(source_frame_ids) else '',
                'synthetic_variant': str(synthetic_variants[idx]) if idx < len(synthetic_variants) else '',
                'flip_label_source': str(flip_label_sources[idx]) if idx < len(flip_label_sources) else '',
                'flip_label_warning': str(flip_label_warnings[idx]) if idx < len(flip_label_warnings) else '',
                'overlay_settings': overlay_settings[idx] if idx < len(overlay_settings) and isinstance(overlay_settings[idx], dict) else {},
                'overlay_schema_version': str(overlay_schema_versions[idx]) if idx < len(overlay_schema_versions) else '',
                'target_steering': float(steering_true[idx]) if idx < len(steering_true) else 0.0,
                'pred_steering': float(steering_pred[idx]) if idx < len(steering_pred) else 0.0,
                'target_speed': float(throttle_true[idx]) if idx < len(throttle_true) else 0.0,
                'pred_speed': float(throttle_pred[idx]) if idx < len(throttle_pred) else 0.0,
                'combined_error': float(combined_error[idx]) if idx < len(combined_error) else 0.0,
            }
        )
    return rows

