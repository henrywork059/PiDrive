#!/usr/bin/env python3
"""Check whether PiSD can import an AI inference runtime.

This script is safe to run on any PiSD install. It does not load a model or move
motors. It only checks imports in the same Python environment used to run PiSD.
"""

from __future__ import annotations

import importlib
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RuntimeCheck:
    name: str
    import_name: str
    ok: bool
    detail: str


def check_module(name: str, import_name: str) -> RuntimeCheck:
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", "")
        detail = f"imported {import_name}"
        if version:
            detail += f" version {version}"
        return RuntimeCheck(name=name, import_name=import_name, ok=True, detail=detail)
    except Exception as exc:
        return RuntimeCheck(name=name, import_name=import_name, ok=False, detail=f"{type(exc).__name__}: {exc}")


def main() -> int:
    checks = [
        check_module("tflite_runtime", "tflite_runtime.interpreter"),
        check_module("ai_edge_litert", "ai_edge_litert.interpreter"),
        check_module("tensorflow", "tensorflow"),
    ]
    tflite_ok = any(c.ok for c in checks)
    payload: dict[str, Any] = {
        "python": sys.executable,
        "version": sys.version.split()[0],
        "tflite_ok": tflite_ok,
        "checks": [asdict(c) for c in checks],
    }
    print(json.dumps(payload, indent=2))
    if tflite_ok:
        print("\nOK: PiSD can load .tflite models with this Python environment.")
        return 0
    print("\nFAIL: PiSD cannot import a TFLite runtime in this Python environment.")
    print("Try:")
    print("  cd ~/PiDrive/PiSD")
    print("  python3 scripts/install_ai_runtime.py --runtime tflite-runtime")
    print("  python3 scripts/check_ai_runtime.py")
    print("If tflite-runtime is unavailable on this Pi, try:")
    print("  python3 scripts/install_ai_runtime.py --runtime ai-edge-litert")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
