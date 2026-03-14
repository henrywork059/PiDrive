from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

try:
    from tflite_runtime.interpreter import Interpreter
except Exception:
    from tensorflow.lite import Interpreter  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--runs", type=int, default=100)
    args = parser.parse_args()

    interpreter = Interpreter(model_path=str(Path(args.model)))
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()[0]
    shape = input_details["shape"]
    sample = np.zeros(shape, dtype=input_details["dtype"])

    for _ in range(args.warmup):
        interpreter.set_tensor(input_details["index"], sample)
        interpreter.invoke()

    t0 = time.perf_counter()
    for _ in range(args.runs):
        interpreter.set_tensor(input_details["index"], sample)
        interpreter.invoke()
    total = time.perf_counter() - t0
    avg_ms = (total / max(args.runs, 1)) * 1000.0
    fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0
    print(f"Average inference: {avg_ms:.2f} ms")
    print(f"Approx FPS: {fps:.2f}")


if __name__ == "__main__":
    main()
