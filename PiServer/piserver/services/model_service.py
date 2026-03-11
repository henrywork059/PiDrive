from __future__ import annotations

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
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_name = "none"
        self.interpreter = None

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
            self.interpreter = interpreter
            self.active_name = path.name
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
            img = cv2.resize(img, (MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT))
            img = img.astype("float32") / 255.0
            img = np.expand_dims(img, axis=0)
            return img
        except Exception:
            return None

    def _quantize_if_needed(self, x, input_details):
        if np is None:
            return x
        dtype = input_details.get("dtype", None)
        if dtype is None or dtype == np.float32:
            return x.astype(np.float32)
        scale, zero_point = input_details.get("quantization", (0.0, 0))
        if scale and scale > 0.0:
            q = x / scale + zero_point
        else:
            q = x
        if dtype == np.int8:
            q = np.clip(q, -128, 127)
        elif dtype == np.uint8:
            q = np.clip(q, 0, 255)
        return q.astype(dtype)

    def _dequantize_output(self, y, output_details):
        if np is None:
            return y
        dtype = output_details.get("dtype", None)
        if dtype is None or dtype == np.float32:
            return y.astype(np.float32)
        scale, zero_point = output_details.get("quantization", (0.0, 0))
        y = y.astype("float32")
        if scale and scale > 0.0:
            y = scale * (y - float(zero_point))
        return y

    def predict_uv_from_frame(self, frame_bgr) -> Optional[Tuple[float, float]]:
        if self.interpreter is None or np is None or cv2 is None:
            return None
        x = self._prepare_input(frame_bgr)
        if x is None:
            return None
        try:
            input_details = self.interpreter.get_input_details()[0]
            output_details = self.interpreter.get_output_details()[0]
            x = self._quantize_if_needed(x, input_details)
            self.interpreter.set_tensor(input_details["index"], x)
            self.interpreter.invoke()
            y = self.interpreter.get_tensor(output_details["index"])
            y = self._dequantize_output(y, output_details)
            y = y.reshape(-1)
            if y.size < 2:
                return None
            steer = max(-1.0, min(1.0, float(y[0])))
            throttle = max(0.0, min(1.0, float(y[1])))
            return steer, throttle
        except Exception:
            return None
