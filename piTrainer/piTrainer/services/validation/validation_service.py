from __future__ import annotations

from .tflite_runner import (
    _choose_tflite_output_mapping,
    _dequantize_output,
    _first_column,
    _load_tflite_interpreter,
    _looks_like_output,
    _mapping_error,
    _quantize_input,
    _resize_tflite_input_if_needed,
    _run_tflite_predictions,
    _split_tflite_outputs,
    run_tflite_validation,
)
from .validation_inputs import _load_model, _prediction_arrays, _prepare_inputs
from .validation_plot import render_validation_plot
from .validation_result import (
    _build_validation_result,
    _prediction_range,
    _range_text,
    _series_text,
    build_validation_summary_text,
    validation_preview_rows,
)


def run_validation(
    dataset_df,
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


__all__ = [
    'build_validation_summary_text',
    'render_validation_plot',
    'run_tflite_validation',
    'run_validation',
    'validation_preview_rows',
]
