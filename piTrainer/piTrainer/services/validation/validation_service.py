from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ...ui.theme import theme_color
from ..data.augmentation_service import boolean_series, normalize_horizontal_flip_labels


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
    rows = normalize_horizontal_flip_labels(dataset_df.copy())
    rows['source_row_number'] = rows.index.astype(int) + 1
    rows = rows[rows['abs_image'].astype(str).map(lambda p: Path(p).exists())].reset_index(drop=True)
    if max_rows and max_rows > 0:
        rows = rows.head(max_rows).reset_index(drop=True)
    if rows.empty:
        raise ValueError('No usable validation rows remain after filtering for existing image files.')

    from PIL import Image

    flip_flags = boolean_series(rows['aug_flip_lr'], default=False).tolist() if 'aug_flip_lr' in rows.columns else [False] * len(rows)
    flip_left_right = getattr(getattr(Image, 'Transpose', Image), 'FLIP_LEFT_RIGHT')

    images = []
    for index, path in enumerate(rows['abs_image'].astype(str)):
        with Image.open(path) as image:
            image = image.convert('RGB')
            if flip_flags[index]:
                image = image.transpose(flip_left_right)
            image = image.resize((img_w, img_h))
            arr = np.asarray(image, dtype=np.float32) / 255.0
            images.append(arr)
    x = np.stack(images, axis=0)
    steering_true = rows['steering'].astype(float).to_numpy(np.float32)
    throttle_true = rows['throttle'].astype(float).to_numpy(np.float32)
    return rows, x, steering_true, throttle_true


def _prediction_arrays(predictions) -> tuple[np.ndarray, np.ndarray]:
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
    return steering_pred.astype(np.float32), throttle_pred.astype(np.float32)


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
    steering_pred, throttle_pred = _prediction_arrays(predictions)
    return _build_validation_result(
        rows=rows,
        steering_true=steering_true,
        throttle_true=throttle_true,
        steering_pred=steering_pred,
        throttle_pred=throttle_pred,
        dataset_name='validation',
        model_kind=model_source,
        model_path=model_path,
        prediction_backend='Keras model.predict',
    )


def _load_tflite_interpreter(tflite_path: str):
    chosen = Path(tflite_path).expanduser()
    if not chosen.exists():
        raise FileNotFoundError(f'TFLite model file not found: {chosen}')
    try:
        import tensorflow as tf

        return tf.lite.Interpreter(model_path=str(chosen)), 'tensorflow.lite.Interpreter'
    except Exception as tf_exc:
        try:
            from tflite_runtime.interpreter import Interpreter

            return Interpreter(model_path=str(chosen)), 'tflite_runtime.Interpreter'
        except Exception as rt_exc:
            raise RuntimeError(
                'Could not load a TFLite interpreter. Install TensorFlow or tflite-runtime. '
                f'TensorFlow error: {tf_exc}; tflite-runtime error: {rt_exc}'
            ) from rt_exc


def _quantize_input(sample: np.ndarray, input_detail: dict) -> np.ndarray:
    dtype = input_detail.get('dtype', np.float32)
    sample = np.asarray(sample, dtype=np.float32)
    if np.issubdtype(dtype, np.floating):
        return sample.astype(dtype)

    scale, zero_point = input_detail.get('quantization', (0.0, 0))
    scale = float(scale or 0.0)
    zero_point = int(zero_point or 0)
    if scale <= 0.0:
        raise ValueError('TFLite model has integer input but no valid quantization scale.')
    quantized = np.rint(sample / scale + zero_point)
    info = np.iinfo(dtype)
    return np.clip(quantized, info.min, info.max).astype(dtype)


def _dequantize_output(output: np.ndarray, output_detail: dict) -> np.ndarray:
    dtype = output_detail.get('dtype', output.dtype)
    output = np.asarray(output)
    if np.issubdtype(dtype, np.floating):
        return output.astype(np.float32)

    scale, zero_point = output_detail.get('quantization', (0.0, 0))
    scale = float(scale or 0.0)
    zero_point = int(zero_point or 0)
    if scale <= 0.0:
        return output.astype(np.float32)
    return (output.astype(np.float32) - float(zero_point)) * scale


def _looks_like_output(name: str, needle: str) -> bool:
    text = str(name or '').lower()
    return needle in text


def _first_column(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    if arr.ndim == 0:
        return arr.reshape(1)
    if arr.ndim == 1:
        return arr.reshape(-1)
    return arr.reshape((arr.shape[0], -1))[:, 0].reshape(-1)


def _mapping_error(
    steering_candidate: np.ndarray,
    throttle_candidate: np.ndarray,
    steering_true: np.ndarray | None,
    throttle_true: np.ndarray | None,
) -> float | None:
    if steering_true is None or throttle_true is None:
        return None
    steering_candidate = np.asarray(steering_candidate, dtype=np.float32).reshape(-1)
    throttle_candidate = np.asarray(throttle_candidate, dtype=np.float32).reshape(-1)
    steering_true = np.asarray(steering_true, dtype=np.float32).reshape(-1)
    throttle_true = np.asarray(throttle_true, dtype=np.float32).reshape(-1)
    total = min(len(steering_candidate), len(throttle_candidate), len(steering_true), len(throttle_true))
    if total <= 0:
        return None
    return float(
        np.mean(np.abs(steering_candidate[:total] - steering_true[:total]))
        + np.mean(np.abs(throttle_candidate[:total] - throttle_true[:total]))
    )


def _choose_tflite_output_mapping(
    flat_outputs: list[np.ndarray],
    output_details: list[dict],
    steering_true: np.ndarray | None,
    throttle_true: np.ndarray | None,
) -> tuple[int, int, list[str]]:
    notes: list[str] = []
    steering_index = None
    throttle_index = None
    for index, detail in enumerate(output_details):
        name = str(detail.get('name', ''))
        if steering_index is None and _looks_like_output(name, 'steering'):
            steering_index = index
        if throttle_index is None and (_looks_like_output(name, 'throttle') or _looks_like_output(name, 'speed')):
            throttle_index = index

    if steering_index is not None and throttle_index is not None and steering_index != throttle_index:
        notes.append(f'TFLite output mapping from tensor names: steering=output[{steering_index}], speed=output[{throttle_index}].')
        return steering_index, throttle_index, notes

    best: tuple[float, int, int] | None = None
    for steer_idx in range(len(flat_outputs)):
        for speed_idx in range(len(flat_outputs)):
            if steer_idx == speed_idx:
                continue
            error = _mapping_error(
                _first_column(flat_outputs[steer_idx]),
                _first_column(flat_outputs[speed_idx]),
                steering_true,
                throttle_true,
            )
            if error is None:
                continue
            if best is None or error < best[0]:
                best = (error, steer_idx, speed_idx)

    if best is not None:
        _error, steering_index, throttle_index = best
        if (steering_index, throttle_index) != (0, 1):
            notes.append(
                'Auto-mapped unnamed TFLite outputs using validation labels: '
                f'steering=output[{steering_index}], speed=output[{throttle_index}]. '
                'This usually means an older multi-output TFLite export has tensor order different from the car-side assumption; re-export the model with this patch.'
            )
        else:
            notes.append(
                'Auto-mapped unnamed TFLite outputs using validation labels: steering=output[0], speed=output[1].'
            )
        return steering_index, throttle_index, notes

    if len(flat_outputs) < 2:
        raise ValueError('Could not map TFLite output tensors to steering and speed.')
    names = ', '.join(str(detail.get('name', f'output_{idx}')) for idx, detail in enumerate(output_details[:2]))
    notes.append(
        'TFLite output tensor names did not clearly identify steering/throttle and validation-label auto mapping was unavailable; '
        f'used fallback output order [steering, speed] from: {names}'
    )
    return 0, 1, notes


def _split_tflite_outputs(
    outputs: list[np.ndarray],
    output_details: list[dict],
    steering_true: np.ndarray | None = None,
    throttle_true: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    notes: list[str] = []
    if not outputs:
        raise ValueError('The TFLite model produced no output tensors.')

    flat_outputs = [np.asarray(output, dtype=np.float32).reshape((np.asarray(output).shape[0], -1)) for output in outputs]
    if len(flat_outputs) == 1:
        pred = flat_outputs[0]
        if pred.shape[1] < 2:
            raise ValueError(f'TFLite single-output tensor must have at least 2 values per row, got shape {pred.shape}.')
        notes.append('TFLite output is a single ordered tensor; using value[0]=steering and value[1]=speed.')
        return pred[:, 0].reshape(-1), pred[:, 1].reshape(-1), notes

    steering_index, throttle_index, mapping_notes = _choose_tflite_output_mapping(
        flat_outputs, output_details, steering_true, throttle_true
    )
    notes.extend(mapping_notes)
    if steering_index >= len(flat_outputs) or throttle_index >= len(flat_outputs):
        raise ValueError('Could not map TFLite output tensors to steering and speed.')
    return _first_column(flat_outputs[steering_index]), _first_column(flat_outputs[throttle_index]), notes


def _resize_tflite_input_if_needed(interpreter, input_detail: dict, sample_shape: tuple[int, ...]) -> None:
    index = int(input_detail['index'])
    current_shape = tuple(int(value) for value in input_detail.get('shape', []))
    if current_shape == sample_shape:
        return
    signature = tuple(int(value) for value in input_detail.get('shape_signature', []))
    batch_is_dynamic = bool(signature and signature[0] == -1)
    if not batch_is_dynamic and len(current_shape) == len(sample_shape) and current_shape[1:] == sample_shape[1:] and current_shape[0] == sample_shape[0]:
        return
    try:
        interpreter.resize_tensor_input(index, sample_shape, strict=False)
        interpreter.allocate_tensors()
    except Exception as exc:
        raise ValueError(
            f'TFLite input shape {current_shape} could not be resized to {sample_shape}. '
            'Check that the exported model image size matches the trainer image size.'
        ) from exc


def _run_tflite_predictions(
    interpreter,
    x: np.ndarray,
    steering_true: np.ndarray,
    throttle_true: np.ndarray,
    requested_batch_size: int,
) -> tuple[np.ndarray, np.ndarray, list[str], str]:
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    if len(input_details) != 1:
        raise ValueError(f'Expected a single image input tensor, found {len(input_details)} input tensors.')

    input_detail = input_details[0]
    input_shape = tuple(int(value) for value in input_detail.get('shape', []))
    if len(input_shape) != 4:
        raise ValueError(f'Expected TFLite image input shape [batch, height, width, channels], got {input_shape}.')
    if tuple(input_shape[1:]) != tuple(x.shape[1:]):
        raise ValueError(
            f'TFLite input image size {input_shape[1:]} does not match prepared validation images {tuple(x.shape[1:])}. '
            'Check the Train image width/height used before export.'
        )

    shape_signature = tuple(int(value) for value in input_detail.get('shape_signature', []))
    dynamic_batch = bool(shape_signature and shape_signature[0] == -1)
    fixed_batch = max(1, int(input_shape[0] or 1))
    if dynamic_batch:
        chunk_size = max(1, int(requested_batch_size or 1))
    else:
        chunk_size = 1 if fixed_batch == 1 else fixed_batch

    backend_notes = [
        f"Input tensor: name={input_detail.get('name', '')}, shape={tuple(input_shape)}, dtype={getattr(input_detail.get('dtype', ''), '__name__', input_detail.get('dtype', ''))}",
        'Dynamic batch enabled for TFLite validation.' if dynamic_batch else 'Fixed-shape TFLite input; validated with safe fixed-batch execution.',
    ]
    output_summaries = []
    for idx, detail in enumerate(output_details):
        output_summaries.append(
            f"output[{idx}] name={detail.get('name', '')}, shape={tuple(int(v) for v in detail.get('shape', []))}, dtype={getattr(detail.get('dtype', ''), '__name__', detail.get('dtype', ''))}"
        )
    if output_summaries:
        backend_notes.append('Output tensors: ' + '; '.join(output_summaries))

    output_chunks: list[list[np.ndarray]] | None = None
    latest_output_details = output_details
    for start in range(0, len(x), chunk_size):
        chunk = x[start:start + chunk_size]
        real_count = len(chunk)
        if not dynamic_batch and fixed_batch > 1 and real_count < fixed_batch:
            pad_count = fixed_batch - real_count
            chunk = np.concatenate([chunk, np.repeat(chunk[-1:], pad_count, axis=0)], axis=0)

        _resize_tflite_input_if_needed(interpreter, input_detail, tuple(chunk.shape))
        input_detail = interpreter.get_input_details()[0]
        latest_output_details = interpreter.get_output_details()
        interpreter.set_tensor(int(input_detail['index']), _quantize_input(chunk, input_detail))
        interpreter.invoke()
        outputs = [_dequantize_output(interpreter.get_tensor(int(detail['index'])), detail) for detail in latest_output_details]
        if output_chunks is None:
            output_chunks = [[] for _ in outputs]
        if len(outputs) != len(output_chunks):
            raise ValueError('TFLite output tensor count changed during validation.')
        for index, output in enumerate(outputs):
            output_chunks[index].append(np.asarray(output)[:real_count])

    if output_chunks is None:
        raise ValueError('No TFLite prediction chunks were produced.')
    combined_outputs = [np.concatenate(chunks, axis=0) for chunks in output_chunks]
    steering_pred, throttle_pred, mapping_notes = _split_tflite_outputs(
        combined_outputs, latest_output_details, steering_true=steering_true, throttle_true=throttle_true
    )
    backend_notes.extend(dict.fromkeys(mapping_notes))
    return steering_pred, throttle_pred, backend_notes, 'TFLite Interpreter'


def run_tflite_validation(
    dataset_df: pd.DataFrame,
    train_config,
    tflite_path: str,
    batch_size: int,
    max_rows: int,
) -> dict:
    interpreter, backend_name = _load_tflite_interpreter(tflite_path)
    rows, x, steering_true, throttle_true = _prepare_inputs(
        dataset_df,
        img_h=int(getattr(train_config, 'img_h', 120)),
        img_w=int(getattr(train_config, 'img_w', 160)),
        max_rows=int(max_rows),
    )
    steering_pred, throttle_pred, backend_notes, prediction_backend = _run_tflite_predictions(
        interpreter,
        x,
        steering_true=steering_true,
        throttle_true=throttle_true,
        requested_batch_size=max(1, int(batch_size)),
    )
    backend_notes.insert(0, f'Interpreter backend: {backend_name}')
    return _build_validation_result(
        rows=rows,
        steering_true=steering_true,
        throttle_true=throttle_true,
        steering_pred=steering_pred,
        throttle_pred=throttle_pred,
        dataset_name='export_validation',
        model_kind='Exported TFLite model',
        model_path=str(Path(tflite_path).expanduser()),
        prediction_backend=prediction_backend,
        backend_notes=backend_notes,
    )


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


def render_validation_plot(ax, result: dict, plot_type: str) -> None:
    steering_true = np.asarray(result['steering_true'])
    throttle_true = np.asarray(result['throttle_true'])
    steering_pred = np.asarray(result['steering_pred'])
    throttle_pred = np.asarray(result['throttle_pred'])
    steering_error = np.asarray(result['steering_error'])
    throttle_error = np.asarray(result['throttle_error'])

    ax.set_facecolor(theme_color('plot_axis'))
    ax.tick_params(colors=theme_color('text_secondary'))
    for spine in ax.spines.values():
        spine.set_color(theme_color('border'))

    label_color = theme_color('text_secondary')
    title_color = theme_color('text_primary')
    ax.xaxis.label.set_color(label_color)
    ax.yaxis.label.set_color(label_color)
    ax.title.set_color(title_color)
    ax.grid(True, color=theme_color('plot_grid'), alpha=0.35)

    def _style_legend() -> None:
        legend = ax.legend(loc='best')
        if legend is None:
            return
        legend.get_frame().set_facecolor(theme_color('plot_bg'))
        legend.get_frame().set_edgecolor(theme_color('border'))
        for text in legend.get_texts():
            text.set_color(theme_color('text_secondary'))

    if plot_type == 'Prediction vs Ground Truth':
        ax.scatter(steering_true, steering_pred, alpha=0.72, label='Steering', color=theme_color('plot_steering'))
        ax.scatter(throttle_true, throttle_pred, alpha=0.72, label='Speed', color=theme_color('plot_speed'))
        combined = np.concatenate([steering_true, throttle_true, steering_pred, throttle_pred])
        lo, hi = float(np.min(combined)), float(np.max(combined))
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        ax.plot([lo, hi], [lo, hi], linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Ground Truth')
        ax.set_ylabel('Prediction')
        ax.set_title('Prediction vs Ground Truth')
        _style_legend()
        return

    if plot_type == 'Prediction Error Histogram':
        ax.hist(steering_error, bins=30, alpha=0.72, label='Steering Error', color=theme_color('plot_steering'), edgecolor=theme_color('bg_panel'))
        ax.hist(throttle_error, bins=30, alpha=0.72, label='Speed Error', color=theme_color('plot_error'), edgecolor=theme_color('bg_panel'))
        ax.axvline(0.0, linestyle='--', linewidth=1.2, color=theme_color('plot_reference'))
        ax.set_xlabel('Prediction Error')
        ax.set_ylabel('Count')
        ax.set_title('Prediction Error Histogram')
        _style_legend()
        return

    sample_count = min(120, len(steering_true))
    x = np.arange(sample_count)
    ax.plot(x, steering_true[:sample_count], label='Steering GT', color=theme_color('plot_steering'), linewidth=1.8)
    ax.plot(x, steering_pred[:sample_count], label='Steering Pred', color=theme_color('primary_hover'), linewidth=1.5)
    ax.plot(x, throttle_true[:sample_count], label='Speed GT', color=theme_color('plot_speed'), linewidth=1.8)
    ax.plot(x, throttle_pred[:sample_count], label='Speed Pred', color=theme_color('warning_hover'), linewidth=1.5)
    ax.set_xlabel('Sample Index')
    ax.set_ylabel('Value')
    ax.set_title('Sample Prediction Trace')
    _style_legend()
