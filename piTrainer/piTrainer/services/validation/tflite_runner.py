from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ...utils.tf_log_utils import quiet_tensorflow_output
from .validation_inputs import _prepare_inputs
from .validation_result import _build_validation_result


def _load_tflite_interpreter(tflite_path: str):
    chosen = Path(tflite_path).expanduser()
    if not chosen.exists():
        raise FileNotFoundError(f'TFLite model file not found: {chosen}')
    try:
        with quiet_tensorflow_output():
            import tensorflow as tf

            return tf.lite.Interpreter(model_path=str(chosen)), 'tensorflow.lite.Interpreter'
    except Exception as tf_exc:
        try:
            with quiet_tensorflow_output():
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
        with quiet_tensorflow_output():
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
    with quiet_tensorflow_output():
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

