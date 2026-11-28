"""Explicit frozen qualification; normal application version gate runs first."""
from __future__ import annotations
import hashlib
import json
import math
import sys
import time
import traceback
from pathlib import Path

def run_probe(app, output, gate_source):
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    report = {"complete": False, "frozen": bool(getattr(sys, "frozen", False)),
              "exe_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
              "version": app.applicationVersion(), "platform": app.platformName(),
              "gate_source": gate_source, "deployment_authorized": False}
    def save():
        (root / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    save()
    worker = None
    window = None
    try:
        if not report["frozen"] or report["platform"] != "windows" or report["version"] != "1.0.0":
            raise RuntimeError("Expected frozen native Windows 1.0.0 executable")
        from .main_window import MainWindow
        window = MainWindow()
        window.show()
        app.processEvents()
        if not window.isVisible() or not window.grab().save(str(root / "native-window.png")):
            raise RuntimeError("Native main window not captured")
        import numpy as np
        import pandas as pd
        from PIL import Image
        import tensorflow as tf
        from .app_state import TrainConfig, ExportConfig
        from .services.train.worker import TrainingWorker
        from .services.train.dataset_service import make_tf_dataset
        from .services.export.export_service import export_model_artifacts
        from .utils.model_manifest import inspect_manifest
        report["tensorflow"] = tf.__version__
        rng = np.random.default_rng(42)
        rows = []
        for i in range(16):
            path = root / ("frame-%02d.jpg" % i)
            Image.fromarray(rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)).save(path)
            rows.append({"abs_image": str(path), "frame_id": str(i), "session": "train" if i < 12 else "validation",
                         "steering": (i - 8) / 16, "throttle": .2 + i / 40})
        train, val = pd.DataFrame(rows[:12]), pd.DataFrame(rows[12:])
        cfg = TrainConfig(img_w=64, img_h=64, batch_size=4, epochs=2, shuffle=False,
                          augment=False, bounded_input=True, compute_device="CPU only",
                          early_stopping=False, reduce_lr_on_plateau=False)
        result, errors, logs = [], [], []
        worker = TrainingWorker(train, val, cfg)
        worker.training_finished.connect(lambda model, history: result.append((model, history)))
        worker.error_message.connect(errors.append)
        worker.training_cancelled.connect(lambda _: errors.append("cancelled"))
        worker.log_message.connect(logs.append)
        worker.start()
        deadline = time.monotonic() + 180
        while worker.isRunning() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(.02)
        if worker.isRunning():
            worker.request_stop()
            deadline = time.monotonic() + 30
            while worker.isRunning() and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.02)
            if worker.isRunning():
                report["error"] = "Training timeout; worker failed to retire in isolated qualification process"
                save()
                import os
                os._exit(1)
            raise RuntimeError("Training deadline exceeded")
        app.processEvents()
        report["logs"] = logs
        if errors or len(result) != 1:
            raise RuntimeError("Training failed: " + repr(errors))
        model, history = result[0]
        history = {k: [float(v) for v in vs] for k, vs in history.items()}
        if len(history.get("loss", [])) != 2 or not all(math.isfinite(v) for vs in history.values() for v in vs):
            raise RuntimeError("Training did not produce two finite epochs")
        report["history"] = history
        report["train_rows"], report["validation_rows"] = len(train), len(val)
        save()
        export = ExportConfig(out_dir=str(root / "exports"), base_name="qualification")
        artifacts = export_model_artifacts(model, export, train, cfg)
        paths = {a.kind: Path(a.path) for a in artifacts}
        if set(paths) != {".keras", ".tflite"}:
            raise RuntimeError("Missing model output")
        report["artifacts"] = []
        for p in paths.values():
            metadata, _ = inspect_manifest(p, expected_kind="steering_control", input_size=(64, 64))
            if not metadata:
                raise RuntimeError("Manifest verification failed")
            report["artifacts"].append({"path": p.relative_to(root).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                        "manifest_sha256": hashlib.sha256(Path(str(p)+".manifest.json").read_bytes()).hexdigest()})
        loaded = tf.keras.models.load_model(paths[".keras"])
        interpreter = tf.lite.Interpreter(model_path=str(paths[".tflite"]))
        interpreter.allocate_tensors()
        inp, = interpreter.get_input_details()
        out, = interpreter.get_output_details()
        ds = make_tf_dataset(val, 64, 64, 1, False, False, bounded_input=True)
        predictions = []
        for i, (image, _) in enumerate(ds):
            pred = loaded(image, training=False)
            ref = [float(pred[k].numpy().ravel()[0]) for k in ("steering", "throttle")]
            interpreter.set_tensor(inp["index"], image.numpy())
            interpreter.invoke()
            actual = interpreter.get_tensor(out["index"]).reshape(-1).tolist()
            if len(actual) != 2 or not all(math.isfinite(x) for x in ref + actual):
                raise RuntimeError("Invalid inference output")
            predictions.append({"frame_id": str(val.iloc[i]["frame_id"]), "keras": ref, "tflite": actual})
        if len(predictions) != len(val):
            raise RuntimeError("Validation row mismatch")
        report["predictions"] = predictions
        report["max_abs_difference"] = [max(abs(p["keras"][i]-p["tflite"][i]) for p in predictions) for i in range(2)]
        report["complete"] = True
        save()
        return 0
    except Exception:
        report["error"] = traceback.format_exc()
        save()
        return 1
    finally:
        if window is not None:
            window.close()
