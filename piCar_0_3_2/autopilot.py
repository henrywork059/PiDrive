# autopilot.py
"""Run TFLite model on the latest camera frame and map outputs to steering/throttle.

This module keeps inference logic separate from:
- control_api.py (which manages state/motor/record),
- model_manager.py (which manages loading/listing models).

It assumes the TFLite model was trained with outputs:
    u <- steering
    v <- throttle

and that both are in roughly:
    steering in [-1.0, +1.0]
    throttle in [0.0, 1.0]
"""

from __future__ import annotations

from typing import Optional, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover - runtime safety
    np = None  # type: ignore

try:
    import cv2
except Exception:  # pragma: no cover - runtime safety
    cv2 = None  # type: ignore

from model_manager import get_interpreter, MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT


def _prepare_input(frame_bgr) -> Optional["np.ndarray"]:
    """Convert a BGR frame into a TFLite input tensor.

    - Converts BGR -> RGB
    - Resizes to (H, W) as required by the model
    - Normalizes to [0, 1]
    - Expands to shape [1, H, W, 3]
    """
    if np is None or cv2 is None:
        return None
    if frame_bgr is None:
        return None

    try:
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT))
        img = img.astype("float32") / 255.0
        img = np.expand_dims(img, axis=0)  # [1, H, W, 3]
        return img
    except Exception:
        return None


def _quantize_if_needed(x, input_details):
    """Match the interpreter's expected dtype.

    For dynamically-quantized models this will usually be float32 input,
    but we handle int8/uint8 just in case.
    """
    if np is None:
        return None

    dtype = input_details.get("dtype", None)
    if dtype is None:
        return x

    if dtype == np.float32:
        return x.astype(np.float32)

    # Handle int8/uint8 quantization if scale is provided
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


def _dequantize_output(y, output_details):
    """Convert quantized output back to float, if necessary."""
    if np is None:
        return y

    dtype = output_details.get("dtype", None)
    if dtype is None or dtype == np.float32:
        return y.astype("float32")

    scale, zero_point = output_details.get("quantization", (0.0, 0))
    y = y.astype("float32")
    if scale and scale > 0.0:
        y = scale * (y - float(zero_point))
    return y


def predict_uv_from_camera(camera) -> Optional[Tuple[float, float]]:
    """Run the active TFLite model on the latest camera frame.

    Returns (u, v) as floats, or None if:
    - no interpreter is active,
    - numpy/cv2 are unavailable,
    - no frame is ready,
    - or inference fails.
    """
    interpreter = get_interpreter()
    if interpreter is None:
        return None
    if np is None or cv2 is None:
        return None
    if not hasattr(camera, "get_latest_frame"):
        return None

    frame = camera.get_latest_frame()
    if frame is None:
        return None

    x = _prepare_input(frame)
    if x is None:
        return None

    try:
        input_details = interpreter.get_input_details()[0]
        x = _quantize_if_needed(x, input_details)
        if x is None:
            return None

        interpreter.set_tensor(input_details["index"], x)
        interpreter.invoke()

        output_details = interpreter.get_output_details()[0]
        y = interpreter.get_tensor(output_details["index"])
        y = _dequantize_output(y, output_details)

        # Expect shape [1, 2]; fall back to first two entries otherwise
        y = y.reshape(-1)
        if y.size < 2:
            return None

        u = float(y[0])
        v = float(y[1])

        # Basic safety clipping
        u = max(-1.0, min(1.0, u))
        v = max(0.0, min(1.0, v))

        return u, v
    except Exception:
        return None
