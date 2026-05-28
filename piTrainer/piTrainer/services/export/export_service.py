from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
import io
import os
from pathlib import Path
import warnings

from ...app_state import ExportConfig, TrainConfig
from ...utils.path_utils import ensure_dir, safe_filename
from ..train.dataset_service import make_tf_dataset


@dataclass(frozen=True)
class ExportArtifact:
    """Summary returned to the UI after an export finishes."""

    path: str
    kind: str
    size_bytes: int
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def size_label(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024.0 or unit == "GB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0


@dataclass
class _CapturedExportOutput:
    stdout: str = ""
    stderr: str = ""
    warnings: list[str] = field(default_factory=list)


@contextmanager
def _quiet_tensorflow_export() -> _CapturedExportOutput:
    """Capture TensorFlow/Keras converter chatter so the app log stays readable.

    TensorFlow Lite conversion may print temporary SavedModel endpoints and low-level
    converter warnings even when export succeeds. Those messages are useful for
    debugging but confusing in normal classroom/runtime export use, so piTrainer
    captures them and returns a short summary instead of dumping them to the console.
    """

    captured = _CapturedExportOutput()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    old_tf_level = os.environ.get("TF_CPP_MIN_LOG_LEVEL")
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always")
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            yield captured
        captured.warnings = [str(item.message) for item in warning_records]
    captured.stdout = stdout_buffer.getvalue().strip()
    captured.stderr = stderr_buffer.getvalue().strip()
    if old_tf_level is None:
        os.environ.pop("TF_CPP_MIN_LOG_LEVEL", None)
    else:
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = old_tf_level


def _configure_tensorflow_export_logging(tf) -> None:
    try:
        tf.get_logger().setLevel("ERROR")
    except Exception:
        pass
    try:
        from absl import logging as absl_logging

        absl_logging.set_verbosity(absl_logging.ERROR)
    except Exception:
        pass


def _summarize_capture(captured: _CapturedExportOutput) -> tuple[str, ...]:
    notes: list[str] = []
    combined = "\n".join(part for part in (captured.stdout, captured.stderr) if part)
    warning_text = "\n".join(captured.warnings)
    if combined:
        if "Saved artifact at" in combined or "Endpoint 'serve'" in combined:
            notes.append("Suppressed TensorFlow temporary SavedModel endpoint details from the console.")
        if "Ignored output_format" in combined or "Ignored drop_control_dependency" in combined:
            notes.append("Suppressed low-level TFLite converter compatibility messages.")
        if "fully_quantize" in combined:
            notes.append("TFLite converter completed quantization diagnostics.")
    if warning_text:
        if "Statistics for quantized inputs were expected" in warning_text:
            notes.append("TFLite keeps float32 input/output for PiDrive compatibility while applying size optimisation internally.")
        else:
            notes.append("Suppressed non-fatal TensorFlow export warning(s); export file was still written.")
    return tuple(dict.fromkeys(notes))


def save_keras_model(model, out_path: Path) -> ExportArtifact:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with _quiet_tensorflow_export() as captured:
        model.save(out_path)
    notes = _summarize_capture(captured)
    return ExportArtifact(str(out_path), ".keras", out_path.stat().st_size, notes)


def _model_output_by_name(model, names: tuple[str, ...]):
    outputs = getattr(model, 'output', None)
    if isinstance(outputs, dict):
        for name in names:
            if name in outputs:
                return outputs[name]

    output_names = list(getattr(model, 'output_names', []) or [])
    output_tensors = list(getattr(model, 'outputs', []) or [])
    for wanted in names:
        for index, output_name in enumerate(output_names):
            if wanted.lower() in str(output_name).lower() and index < len(output_tensors):
                return output_tensors[index]

    for tensor in output_tensors:
        tensor_name = str(getattr(tensor, 'name', '') or '').lower()
        if any(wanted.lower() in tensor_name for wanted in names):
            return tensor
    return None


def _ordered_tflite_export_model(model):
    """Return a TFLite export wrapper with one stable [steering, throttle] output.

    Keras dict-output models can become unnamed multi-output tensors after TFLite
    conversion, and the tensor order is not safe to assume in the car runtime.
    The wrapper keeps the trained network unchanged but joins the two regression
    heads into one explicit 2-value tensor so output[0] is steering and output[1]
    is throttle/speed for every new TFLite export.
    """

    import tensorflow as tf

    steering = _model_output_by_name(model, ('steering', 'steer'))
    throttle = _model_output_by_name(model, ('throttle', 'speed'))
    if steering is None or throttle is None:
        output_tensors = list(getattr(model, 'outputs', []) or [])
        if len(output_tensors) >= 2:
            steering = steering or output_tensors[0]
            throttle = throttle or output_tensors[1]
    if steering is None or throttle is None:
        raise ValueError(
            'Could not identify steering and throttle outputs for ordered TFLite export. '
            'Expected model outputs named steering/throttle or at least two output tensors.'
        )

    steering = tf.keras.layers.Reshape((1,), name='ordered_steering_scalar')(steering)
    throttle = tf.keras.layers.Reshape((1,), name='ordered_throttle_scalar')(throttle)
    ordered_output = tf.keras.layers.Concatenate(name='steering_throttle')([steering, throttle])
    return tf.keras.Model(inputs=model.inputs, outputs=ordered_output, name=f'{model.name}_ordered_tflite')


def export_tflite_model(model, out_path: Path, quantize: bool, representative_ds=None) -> ExportArtifact:
    import tensorflow as tf

    _configure_tensorflow_export_logging(tf)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with _quiet_tensorflow_export() as captured:
        tflite_model = _ordered_tflite_export_model(model)
        converter = tf.lite.TFLiteConverter.from_keras_model(tflite_model)
        if quantize:
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            if representative_ds is not None:
                def rep_data():
                    for batch in representative_ds.take(100):
                        images, _targets = batch
                        yield [images]
                converter.representative_dataset = rep_data
            converter.target_spec.supported_ops = [
                tf.lite.OpsSet.TFLITE_BUILTINS_INT8,
                tf.lite.OpsSet.TFLITE_BUILTINS,
            ]
        tflite_bytes = converter.convert()
    out_path.write_bytes(tflite_bytes)
    notes = list(_summarize_capture(captured))
    notes.append('TFLite output is forced to one ordered tensor: [steering, throttle/speed].')
    if quantize:
        notes.append("Created size-optimised TFLite file; model input/output remain float32 for the current PiDrive runtime.")
    else:
        notes.append("Created float32 TFLite file.")
    return ExportArtifact(str(out_path), ".tflite", out_path.stat().st_size, tuple(dict.fromkeys(notes)))


def build_representative_dataset(train_df, train_config: TrainConfig):
    if train_df is None or train_df.empty:
        return None
    return make_tf_dataset(
        train_df,
        img_h=train_config.img_h,
        img_w=train_config.img_w,
        batch_size=1,
        shuffle=False,
        augment=False,
    )


def export_model_artifacts(model, export_config: ExportConfig, train_df, train_config: TrainConfig) -> list[ExportArtifact]:
    out_dir = ensure_dir(Path(export_config.out_dir).expanduser().resolve())
    base_name = safe_filename(export_config.base_name or "picar_model")
    created: list[ExportArtifact] = []

    if export_config.export_keras:
        keras_path = out_dir / f"{base_name}.keras"
        created.append(save_keras_model(model, keras_path))

    if export_config.export_tflite:
        rep_ds = build_representative_dataset(train_df, train_config) if export_config.quantize_int8 else None
        suffix = "_int8" if export_config.quantize_int8 else ""
        tflite_path = out_dir / f"{base_name}{suffix}.tflite"
        created.append(export_tflite_model(model, tflite_path, export_config.quantize_int8, rep_ds))

    if not created:
        raise RuntimeError("No export target selected.")
    return created
