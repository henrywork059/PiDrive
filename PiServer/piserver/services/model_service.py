from __future__ import annotations

import math
import os
import threading
import uuid
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

MAX_INPUT_PIXELS = 4096 * 4096


class ModelService:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_name = "none"
        self.interpreter = None
        self._input_details = None
        self._output_details = None
        self._input_size = None
        self._lock = threading.RLock()

    def list_models(self) -> list[str]:
        return sorted([p.name for p in self.root.glob("*.tflite")])

    def save_uploaded_model(self, file_storage) -> tuple[bool, str]:
        filename = (getattr(file_storage, "filename", "") or "").strip()
        safe_name = Path(filename).name
        if not safe_name or not safe_name.lower().endswith(".tflite"):
            return False, "Only .tflite files are supported."
        target = self.root / safe_name
        tmp_target = self.root / f".{safe_name}.{uuid.uuid4().hex}.upload"
        try:
            file_storage.save(tmp_target)
            os.replace(tmp_target, target)
            return True, target.name
        except Exception as exc:
            try:
                if tmp_target.exists():
                    tmp_target.unlink()
            except Exception:
                pass
            return False, f"Failed to save model: {exc}"

    @staticmethod
    def _validate_model_signature(interpreter):
        """Require one fixed NHWC RGB input and an ordered [steering, throttle] output."""
        if np is None:
            raise ValueError("NumPy is required for TFLite model validation.")
        inputs = interpreter.get_input_details()
        outputs = interpreter.get_output_details()
        if len(inputs) != 1 or len(outputs) != 1:
            raise ValueError("Expected one image input and one [steering, throttle] output tensor.")
        input_info, output_info = inputs[0], outputs[0]
        shape = tuple(int(x) for x in input_info.get("shape", ()))
        if len(shape) != 4 or shape[0] != 1 or shape[3] != 3 or shape[1] <= 0 or shape[2] <= 0:
            raise ValueError(f"Unsupported input shape {shape}; expected [1, height, width, 3].")
        if shape[1] * shape[2] > MAX_INPUT_PIXELS:
            raise ValueError(f"Input image {shape[2]}x{shape[1]} is too large.")

        output_shape = tuple(int(x) for x in output_info.get("shape", ()))
        if not output_shape or any(v <= 0 for v in output_shape) or math.prod(output_shape) != 2:
            raise ValueError(f"Unsupported output shape {output_shape}; expected two ordered values [steering, throttle].")
        for name, detail in (("input", input_info), ("output", output_info)):
            try:
                dtype = np.dtype(detail["dtype"])
            except (KeyError, TypeError) as exc:
                raise ValueError(f"Unsupported {name} tensor dtype.") from exc
            if dtype not in (np.dtype("float32"), np.dtype("int8"), np.dtype("uint8")):
                raise ValueError(f"Unsupported {name} tensor dtype {dtype}; expected float32, int8 or uint8.")
            if dtype != np.dtype("float32"):
                scale, _zero_point = detail.get("quantization", (0.0, 0))
                if not math.isfinite(float(scale)) or float(scale) <= 0:
                    raise ValueError(f"Invalid {name} quantization scale; expected a positive finite value.")
        return input_info, output_info, (shape[2], shape[1])

    def load_model(self, filename: str) -> tuple[bool, str]:
        if InterpreterType is None:
            return False, "No TFLite interpreter is available on this system."
        if np is None or cv2 is None:
            return False, "NumPy and OpenCV are required to run TFLite camera models."
        path = self.root / Path(str(filename or "")).name
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".tflite":
            return False, "Model file does not exist or is not .tflite."
        try:
            # Load and preflight a replacement separately; never clear a working
            # interpreter when the new model has an incompatible tensor contract.
            interpreter = InterpreterType(model_path=str(path))
            interpreter.allocate_tensors()
            input_info, output_info, input_size = self._validate_model_signature(interpreter)
            preflight_input = np.zeros((1, input_size[1], input_size[0], 3), dtype=np.float32)
            preflight_input = self._quantize_if_needed(preflight_input, input_info)
            interpreter.set_tensor(int(input_info["index"]), preflight_input)
            interpreter.invoke()
            preflight_output = interpreter.get_tensor(int(output_info["index"]))
            if self._read_output(preflight_output, output_info) is None:
                raise ValueError("Preflight returned missing or non-finite steering/throttle values.")
        except Exception as exc:
            return False, f"Model preflight failed: {exc}"
        with self._lock:
            self.interpreter = interpreter
            self._input_details = input_info
            self._output_details = output_info
            self._input_size = input_size
            self.active_name = path.name
        return True, self.active_name

    def get_active_name(self) -> str:
        with self._lock:
            return self.active_name

    def delete_model(self, filename: str) -> tuple[bool, str]:
        path = self.root / Path(str(filename or "")).name
        if not path.exists() or not path.is_file() or path.suffix.lower() != ".tflite":
            return False, "Model file does not exist."
        with self._lock:
            is_active = path.name == self.active_name
            if is_active:
                self.interpreter = None
                self._input_details = None
                self._output_details = None
                self._input_size = None
                self.active_name = "none"
        try:
            path.unlink()
        except Exception as exc:
            return False, f"Failed to delete model: {exc}"
        message = f"Deleted model: {path.name}"
        if is_active:
            message += ". Active model cleared."
        return True, message

    def get_input_spec(self) -> dict | None:
        """Expose resolved model dimensions for API diagnostics without changing config."""
        with self._lock:
            if self._input_size is None or self._input_details is None:
                return None
            width, height = self._input_size
            return {"width": width, "height": height, "channels": 3,
                    "dtype": str(np.dtype(self._input_details["dtype"]))}

    def _prepare_input(self, frame_bgr, input_size):
        if np is None or cv2 is None or frame_bgr is None or input_size is None:
            return None
        try:
            img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, input_size)
            img = img.astype(np.float32) / 255.0
            return np.expand_dims(img, axis=0)
        except (TypeError, ValueError, cv2.error):
            return None

    def _quantize_if_needed(self, x, input_details):
        if np is None:
            return x
        dtype = input_details.get("dtype", None)
        if dtype is None or dtype == np.float32:
            return x.astype(np.float32)
        scale, zero_point = input_details.get("quantization", (0.0, 0))
        if scale and scale > 0.0:
            q = np.rint(x / scale + zero_point)
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

    def _read_output(self, tensor, output_details) -> Optional[Tuple[float, float]]:
        if np is None:
            return None
        try:
            output = self._dequantize_output(np.asarray(tensor), output_details).reshape(-1)
            if output.size != 2 or not np.all(np.isfinite(output)):
                return None
            steer = float(np.clip(output[0], -1.0, 1.0))
            throttle = float(np.clip(output[1], 0.0, 1.0))
            return steer, throttle
        except (TypeError, ValueError, OverflowError):
            return None

    def predict_uv_from_frame(self, frame_bgr) -> Optional[Tuple[float, float]]:
        if np is None or cv2 is None:
            return None
        with self._lock:
            interpreter = self.interpreter
            input_info = self._input_details
            output_info = self._output_details
            input_size = self._input_size
            if interpreter is None or input_info is None or output_info is None:
                return None
            # Hold the lock through preprocessing/invoke so a concurrent model
            # load cannot swap an interpreter between shape selection and infer.
            x = self._prepare_input(frame_bgr, input_size)
            if x is None:
                return None
            try:
                x = self._quantize_if_needed(x, input_info)
                interpreter.set_tensor(int(input_info["index"]), x)
                interpreter.invoke()
                y = interpreter.get_tensor(int(output_info["index"]))
                return self._read_output(y, output_info)
            except Exception:
                return None
