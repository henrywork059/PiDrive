from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _load_model(in_memory_model, model_source: str, model_path: str):
    if model_source == 'Current trained model':
        if in_memory_model is None:
            raise ValueError('No in-memory trained model is available. Train a model first or load a saved model file.')
        return in_memory_model

    chosen = Path(model_path).expanduser()
    if not chosen.exists():
        raise FileNotFoundError(f'Model file not found: {chosen}')

    import tensorflow as tf

    return tf.keras.models.load_model(chosen)


def _prepare_inputs(dataset_df: pd.DataFrame, img_h: int, img_w: int, max_rows: int):
    rows = dataset_df.copy()
    rows['source_row_number'] = rows.index.astype(int) + 1
    rows = rows[rows['abs_image'].astype(str).map(lambda p: Path(p).exists())].reset_index(drop=True)
    if max_rows and max_rows > 0:
        rows = rows.head(max_rows).reset_index(drop=True)
    if rows.empty:
        raise ValueError('No usable validation rows remain after filtering for existing image files.')

    from PIL import Image

    images = []
    for path in rows['abs_image'].astype(str):
        with Image.open(path) as image:
            image = image.convert('RGB').resize((img_w, img_h))
            arr = np.asarray(image, dtype=np.float32) / 255.0
            images.append(arr)
    x = np.stack(images, axis=0)
    steering_true = rows['steering'].astype(float).to_numpy(np.float32)
    throttle_true = rows['throttle'].astype(float).to_numpy(np.float32)
    return rows, x, steering_true, throttle_true


def run_validation(
    dataset_df: pd.DataFrame,
    train_config,
    in_memory_model,
    model_source: str,
    model_path: str,
    batch_size: int,
    max_rows: int,
) -> dict:
    model = _load_model(in_memory_model, model_source, model_path)
    rows, x, steering_true, throttle_true = _prepare_inputs(
        dataset_df,
        img_h=int(getattr(train_config, 'img_h', 120)),
        img_w=int(getattr(train_config, 'img_w', 160)),
        max_rows=int(max_rows),
    )

    predictions = model.predict(x, batch_size=max(1, int(batch_size)), verbose=0)
    if isinstance(predictions, dict):
        steering_pred = np.asarray(predictions.get('steering')).reshape(-1)
        throttle_pred = np.asarray(predictions.get('throttle')).reshape(-1)
    elif isinstance(predictions, (list, tuple)) and len(predictions) >= 2:
        steering_pred = np.asarray(predictions[0]).reshape(-1)
        throttle_pred = np.asarray(predictions[1]).reshape(-1)
    else:
        pred = np.asarray(predictions)
        if pred.ndim == 2 and pred.shape[1] >= 2:
            steering_pred = pred[:, 0].reshape(-1)
            throttle_pred = pred[:, 1].reshape(-1)
        else:
            raise ValueError('Unsupported model prediction output shape for validation.')

    steering_error = steering_pred - steering_true
    throttle_error = throttle_pred - throttle_true
    combined_error = np.abs(steering_error) + np.abs(throttle_error)

    return {
        'rows_used': int(len(rows)),
        'dataset_name': 'validation',
        'frame_ids': rows.get('frame_id', pd.Series(range(len(rows)))).astype(str).tolist(),
        'frame_numbers': rows.get('frame_number', rows.get('frame_no', rows.get('source_row_number', pd.Series(range(1, len(rows) + 1))))).astype(str).tolist(),
        'sessions': rows.get('session', pd.Series([''] * len(rows))).astype(str).tolist(),
        'modes': rows.get('mode', pd.Series([''] * len(rows))).astype(str).tolist(),
        'timestamps': rows.get('ts', pd.Series([''] * len(rows))).astype(str).tolist(),
        'abs_images': rows.get('abs_image', pd.Series([''] * len(rows))).astype(str).tolist(),
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


def build_validation_summary_text(result: dict) -> str:
    return (
        f"Rows used: {result['rows_used']}\n"
        f"Steering MAE / RMSE / Bias: {result['steering_mae']:.4f} / {result['steering_rmse']:.4f} / {result['steering_bias']:.4f}\n"
        f"Speed MAE / RMSE / Bias: {result['throttle_mae']:.4f} / {result['throttle_rmse']:.4f} / {result['throttle_bias']:.4f}\n"
        'Use the plot panel and frame-review panel to inspect prediction agreement, bad frames, and overlay differences.'
    )


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
                'target_steering': float(steering_true[idx]) if idx < len(steering_true) else 0.0,
                'pred_steering': float(steering_pred[idx]) if idx < len(steering_pred) else 0.0,
                'target_speed': float(throttle_true[idx]) if idx < len(throttle_true) else 0.0,
                'pred_speed': float(throttle_pred[idx]) if idx < len(throttle_pred) else 0.0,
                'combined_error': float(combined_error[idx]) if idx < len(combined_error) else 0.0,
            }
        )
    return rows


def render_validation_plot(ax, result: dict, plot_type: str) -> None:
    steering_true = np.asarray(result['steering_true'])
    throttle_true = np.asarray(result['throttle_true'])
    steering_pred = np.asarray(result['steering_pred'])
    throttle_pred = np.asarray(result['throttle_pred'])
    steering_error = np.asarray(result['steering_error'])
    throttle_error = np.asarray(result['throttle_error'])

    ax.set_facecolor('#171c26')
    ax.tick_params(colors='#dce3f0')
    for spine in ax.spines.values():
        spine.set_color('#687387')

    if plot_type == 'Prediction vs Ground Truth':
        ax.scatter(steering_true, steering_pred, alpha=0.6, label='Steering')
        ax.scatter(throttle_true, throttle_pred, alpha=0.6, label='Speed')
        combined = np.concatenate([steering_true, throttle_true, steering_pred, throttle_pred])
        lo, hi = float(np.min(combined)), float(np.max(combined))
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        ax.plot([lo, hi], [lo, hi], linestyle='--', linewidth=1.0)
        ax.set_xlabel('Ground Truth')
        ax.set_ylabel('Prediction')
        ax.set_title('Prediction vs Ground Truth')
        ax.legend()
        return

    if plot_type == 'Prediction Error Histogram':
        ax.hist(steering_error, bins=30, alpha=0.65, label='Steering Error')
        ax.hist(throttle_error, bins=30, alpha=0.65, label='Speed Error')
        ax.axvline(0.0, linestyle='--', linewidth=1.0)
        ax.set_xlabel('Prediction Error')
        ax.set_ylabel('Count')
        ax.set_title('Prediction Error Histogram')
        ax.legend()
        return

    sample_count = min(120, len(steering_true))
    x = np.arange(sample_count)
    ax.plot(x, steering_true[:sample_count], label='Steering GT')
    ax.plot(x, steering_pred[:sample_count], label='Steering Pred')
    ax.plot(x, throttle_true[:sample_count], label='Speed GT')
    ax.plot(x, throttle_pred[:sample_count], label='Speed Pred')
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Value')
    ax.set_title('Sample Prediction Trace')
    ax.legend(loc='best')
