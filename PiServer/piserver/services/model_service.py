from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

InterpreterType = None
try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore
    InterpreterType = _Interpreter
except Exception:
    try:
        from tensorflow.lite.python.interpreter import Interpreter as _Interpreter  # type: ignore
        InterpreterType = _Interpreter
    except Exception:
        InterpreterType = None

MODEL_INPUT_WIDTH = 200
MODEL_INPUT_HEIGHT = 112


class ModelService:
    def __init__(self, root: str | Path, max_infer_hz: float = 15.0):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_name = "none"
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self._lock = threading.Lock()
        self._last_frame_seq = -1
        self._last_predict_ts = 0.0
        self._last_prediction: Optional[Tuple[float, float]] = None
        self.min_infer_interval = 1.0 / max(1.0, float(max_infer_hz))

    def list_models(self) -> list[str]:
        return sorted([p.name for p in self.root.glob("*.tflite")])

    def save_uploaded_model(self, file_storage) -> tuple[bool, str]:
        filename = (getattr(file_storage, "filename", "") or "").strip()
        if not filename.lower().endswith(".tflite"):
            return False, "Only .tflite files are supported."
        target = self.root / Path(filename).name
        try:
            file_storage.save(target)
            return True, target.name
        except Exception as exc:
            return False, f"Failed to save model: {exc}"

    def load_model(self, filename: str) -> tuple[bool, str]:
        if InterpreterType is None:
            return False, "No TFLite interpreter is available on this system."
        path = self.root / Path(filename).name
        if not path.exists():
            return False, "Model file does not exist."
        try:
            interpreter = InterpreterType(model_path=str(path))
            interpreter.allocate_tensors()
            with self._lock:
                self.interpreter = interpreter
                self.input_details = interpreter.get_input_details()[0]
                self.output_details = interpreter.get_output_details()[0]
                self.active_name = path.name
                self._last_frame_seq = -1
                self._last_predict_ts = 0.0
                self._last_prediction = None
            return True, self.active_name
        except Exception as exc:
            return False, f"Failed to load model: {exc}"

    def get_active_name(self) -> str:
        return self.active_name

    def _prepare_input(self, frame_bgr):
        if np is None or cv2 is None or frame_bgr is None:
            return None
        try:
            img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT), interpolation=cv2.INTER_AREA)
            img = img.astype(np.float32, copy=False) / 255.0
            img = np.expand_dims(img, axis=0)
            return img
        except Exception:
            return None

    def _quantize_if_needed(self, x, input_details):
        if np is None:
            return x
        dtype = input_details.get("dtype", None)
        if dtype is None or dtype == np.float32:
            return x.astype(np.float32, copy=False)
        scale, zero_point = input_details.get("quantization", (0.0, 0))
        if scale and scale > 0.0:
            q = x / scale + zero_point
        else:
            q = x
        if dtype == np.int8:
            q = np.clip(q, -128, 127)
        elif dtype == np.uint8:
            q = np.clip(q, 0, 255)
        return q.astype(dtype, copy=False)

    def _dequantize_output(self, y, output_details):
        if np is None:
            return y
        dtype = output_details.get("dtype", None)
        if dtype is None or dtype == np.float32:
            return y.astype(np.float32, copy=False)
        scale, zero_point = output_details.get("quantization", (0.0, 0))
        y = y.astype(np.float32, copy=False)
        if scale and scale > 0.0:
            y = scale * (y - float(zero_point))
        return y

    def predict_uv_from_frame(self, frame_bgr, frame_seq: int | None = None) -> Optional[Tuple[float, float]]:
        if np is None or cv2 is None or frame_bgr is None:
            return None
        with self._lock:
            interpreter = self.interpreter
            input_details = self.input_details
            output_details = self.output_details
            last_prediction = self._last_prediction
            now = time.perf_counter()
            if interpreter is None or input_details is None or output_details is None:
                return None
            if frame_seq is not None and frame_seq == self._last_frame_seq and last_prediction is not None:
                return last_prediction
            if (now - self._last_predict_ts) < self.min_infer_interval and last_prediction is not None:
                return last_prediction

        x = self._prepare_input(frame_bgr)
        if x is None:
            return None
        try:
            x = self._quantize_if_needed(x, input_details)
            with self._lock:
                if self.interpreter is None or self.input_details is None or self.output_details is None:
                    return None
                interpreter = self.interpreter
                input_details = self.input_details
                output_details = self.output_details
                interpreter.set_tensor(input_details["index"], x)
                interpreter.invoke()
                y = interpreter.get_tensor(output_details["index"])
                self._last_predict_ts = time.perf_counter()
            y = self._dequantize_output(y, output_details)
            y = y.reshape(-1)
            if y.size < 2:
                return None
            steer = max(-1.0, min(1.0, float(y[0])))
            throttle = max(0.0, min(1.0, float(y[1])))
            result = (steer, throttle)
            with self._lock:
                self._last_frame_seq = int(frame_seq) if frame_seq is not None else self._last_frame_seq + 1
                self._last_prediction = result
            return result
        except Exception:
            return None
