# model_manager.py
"""Simple TFLite model manager for Pi-Car.

- Stores all models under the local "models" directory.
- Validates input shape to match (batch, 112, 200, 3).
- Keeps track of the currently active model name and interpreter.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

# Hard-coded expected input size (from training GUI + TFLite metadata)
MODEL_INPUT_WIDTH = 200
MODEL_INPUT_HEIGHT = 112

# Directory where all .tflite models are stored
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Try to import a TFLite Interpreter implementation
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
        # This will be printed on the Pi console so the user understands
        # why auto_steer/autopilot are not moving the car.
        print("[WARN] No TFLite interpreter backend found. Install 'tflite-runtime' or TensorFlow Lite on the Pi to enable auto_steer/autopilot.")  # NO_TFLITE_BACKEND

try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore
    InterpreterType = _Interpreter
except Exception:
    try:
        from tensorflow.lite.python.interpreter import Interpreter as _Interpreter  # type: ignore
        InterpreterType = _Interpreter
    except Exception:
        InterpreterType = None

_active_model_name: Optional[str] = None
_active_interpreter = None


def list_models() -> List[str]:
    """Return a sorted list of available .tflite model filenames in MODELS_DIR."""
    if not MODELS_DIR.exists():
        return []
    return sorted(
        f.name for f in MODELS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".tflite"
    )


def get_model_name() -> str:
    """Return the currently active model name (or 'none')."""
    return _active_model_name or "none"


def get_interpreter():
    """Return the currently active TFLite interpreter (or None)."""
    return _active_interpreter


def _validate_model_shape(model_path: Path) -> Tuple[bool, str]:
    """Check that the uploaded model has the expected input shape.

    Returns (ok, message).
    """
    if InterpreterType is None:
        # We cannot validate without an interpreter; accept but warn.
        return True, "Interpreter backend not available; shape not validated."

    try:
        interpreter = InterpreterType(model_path=str(model_path))
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()[0]
        shape = input_details.get("shape", None)
        if shape is None or len(shape) != 4:
            return False, f"Unexpected input rank: {shape!r}"

        # Typical TFLite shape: [1, height, width, channels]
        batch, h, w, c = int(shape[0]), int(shape[1]), int(shape[2]), int(shape[3])
        if h != MODEL_INPUT_HEIGHT or w != MODEL_INPUT_WIDTH or c not in (1, 3):
            return False, f"Model input must be [1, {MODEL_INPUT_HEIGHT}, {MODEL_INPUT_WIDTH}, 3], got {shape!r}"

        return True, "OK"
    except Exception as e:
        return False, f"Failed to inspect model: {e}"


def save_uploaded_model(file_storage) -> Tuple[bool, str]:
    """Save an uploaded file (Flask FileStorage) into MODELS_DIR after validation.

    Returns (ok, message_or_filename).
    """
    filename = os.path.basename(file_storage.filename or "").strip()
    if not filename:
        return False, "Missing filename."
    if not filename.lower().endswith(".tflite"):
        return False, "Only .tflite files are supported."

    dest = MODELS_DIR / filename
    # Save to disk first
    file_storage.save(str(dest))

    ok, msg = _validate_model_shape(dest)
    if not ok:
        # Remove invalid file
        try:
            dest.unlink()
        except OSError:
            pass
        return False, msg

    return True, filename


def load_model(filename: str) -> Tuple[bool, str]:
    """Load a model by filename from MODELS_DIR and make it active.

    Returns (ok, message or model_name).
    """
    global _active_model_name, _active_interpreter

    filename = os.path.basename(filename.strip())
    if not filename:
        return False, "Filename is required."

    model_path = MODELS_DIR / filename
    if not model_path.is_file():
        return False, f"Model not found: {filename}"

    if InterpreterType is None:
        # We can't actually create an interpreter; remember the name anyway.
        _active_model_name = filename
        _active_interpreter = None
        return True, filename

    try:
        interpreter = InterpreterType(model_path=str(model_path))
        interpreter.allocate_tensors()

        input_details = interpreter.get_input_details()[0]
        shape = input_details.get("shape", None)
        if shape is None or len(shape) != 4:
            return False, f"Unexpected input rank: {shape!r}"

        batch, h, w, c = int(shape[0]), int(shape[1]), int(shape[2]), int(shape[3])
        if h != MODEL_INPUT_HEIGHT or w != MODEL_INPUT_WIDTH or c not in (1, 3):
            return False, f"Model input must be [1, {MODEL_INPUT_HEIGHT}, {MODEL_INPUT_WIDTH}, 3], got {shape!r}"

        _active_interpreter = interpreter
        _active_model_name = filename
        return True, filename
    except Exception as e:
        return False, f"Failed to load model: {e}"
