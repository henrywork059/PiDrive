from __future__ import annotations

from pathlib import Path

from ...app_state import ExportConfig, TrainConfig
from ...utils.path_utils import ensure_dir, safe_filename
from ..train.dataset_service import make_tf_dataset



def save_keras_model(model, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(out_path)



def export_tflite_model(model, out_path: Path, quantize: bool, representative_ds=None) -> None:
    import tensorflow as tf

    out_path.parent.mkdir(parents=True, exist_ok=True)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
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



def export_model_artifacts(model, export_config: ExportConfig, train_df, train_config: TrainConfig) -> list[str]:
    out_dir = ensure_dir(Path(export_config.out_dir).expanduser().resolve())
    base_name = safe_filename(export_config.base_name or "picar_model")
    created: list[str] = []

    if export_config.export_keras:
        keras_path = out_dir / f"{base_name}.keras"
        save_keras_model(model, keras_path)
        created.append(str(keras_path))

    if export_config.export_tflite:
        rep_ds = build_representative_dataset(train_df, train_config) if export_config.quantize_int8 else None
        suffix = "_int8" if export_config.quantize_int8 else ""
        tflite_path = out_dir / f"{base_name}{suffix}.tflite"
        export_tflite_model(model, tflite_path, export_config.quantize_int8, rep_ds)
        created.append(str(tflite_path))

    if not created:
        raise RuntimeError("No export target selected.")
    return created
