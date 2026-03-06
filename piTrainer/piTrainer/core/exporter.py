from __future__ import annotations
from pathlib import Path

def save_keras(model, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(out_path)

def export_tflite(model, out_path: Path, quantize: bool, representative_ds=None):
    import tensorflow as tf

    out_path.parent.mkdir(parents=True, exist_ok=True)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if quantize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        if representative_ds is not None:
            def rep():
                for batch in representative_ds.take(100):
                    x, _y = batch
                    yield [x]
            converter.representative_dataset = rep
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS_INT8,
            tf.lite.OpsSet.TFLITE_BUILTINS,
        ]

    tflite_model = converter.convert()
    out_path.write_bytes(tflite_model)
