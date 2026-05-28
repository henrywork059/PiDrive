#!/usr/bin/env python3
"""Install a PiSD AI inference runtime into the current Python environment.

Run from PiSD root on the Raspberry Pi:

    python3 scripts/install_ai_runtime.py --runtime tflite-runtime

The script intentionally installs only the inference runtime. It does not change
PiSD settings, does not load models, and does not move motors.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys

RUNTIMES = {
    "tflite-runtime": {
        "package": "tflite-runtime",
        "import": "tflite_runtime.interpreter",
        "note": "Small TensorFlow Lite runtime. Best first choice on Raspberry Pi OS when a matching wheel exists.",
    },
    "ai-edge-litert": {
        "package": "ai-edge-litert",
        "import": "ai_edge_litert.interpreter",
        "note": "Newer Google AI Edge LiteRT package. Useful fallback on 64-bit Pi OS if tflite-runtime is unavailable.",
    },
    "tensorflow": {
        "package": "tensorflow",
        "import": "tensorflow",
        "note": "Full TensorFlow. Heavier than TFLite runtimes and usually not the first choice for Pi driving.",
    },
}


def module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.call(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install a PiSD AI inference runtime.")
    parser.add_argument("--runtime", choices=sorted(RUNTIMES), default="tflite-runtime")
    parser.add_argument("--no-break-system-packages", action="store_true", help="Do not pass --break-system-packages to pip.")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade the selected package if already installed.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = RUNTIMES[args.runtime]
    package = spec["package"]
    import_name = spec["import"]
    print(f"PiSD AI runtime installer")
    print(f"Python: {sys.executable}")
    print(f"Runtime: {args.runtime}")
    print(spec["note"])
    if module_available(import_name) and not args.upgrade:
        print(f"OK: {import_name} is already importable. Nothing to install.")
        return 0
    cmd = [sys.executable, "-m", "pip", "install"]
    if not args.no_break_system_packages:
        cmd.append("--break-system-packages")
    if args.upgrade:
        cmd.append("--upgrade")
    cmd.append(package)
    code = run(cmd)
    if code != 0:
        print("\nInstall failed.")
        if args.runtime == "tflite-runtime":
            print("Try the newer fallback runtime on 64-bit Pi OS:")
            print("  python3 scripts/install_ai_runtime.py --runtime ai-edge-litert")
        return code
    if module_available(import_name):
        print(f"\nOK: {import_name} is now importable.")
        print("Restart PiSD, then open AI Mode and click Load model again.")
        return 0
    print(f"\nPackage installed, but {import_name} is still not importable by {sys.executable}.")
    print("Check that PiSD is started with the same python3 command/environment used here.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
