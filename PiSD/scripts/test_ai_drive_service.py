#!/usr/bin/env python3
"""Validate AI Drive service model listing and safety limits without hardware."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.ai_drive_service import AIDriveService  # noqa: E402

OUTPUT_ROOT = PROJECT_ROOT / "test_outputs" / "ai_drive_service"
SUMMARY_PATH = OUTPUT_ROOT / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": bool(self.ok), "code": self.code, "message": self.message, "details": self.details}


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    models = OUTPUT_ROOT / "models"
    models.mkdir(parents=True, exist_ok=True)
    (models / "dummy.tflite").write_bytes(b"not a real model")
    service = AIDriveService(OUTPUT_ROOT, {"max_throttle": 0.2, "max_steering": 0.6, "steering_smoothing": 0.0, "throttle_smoothing": 0.0})
    results: list[Result] = []

    listed = service.list_models()
    list_ok = listed.get("code") == PiSDErrorCodes.OK and any(item.get("id") == "dummy.tflite" for item in listed.get("models", []))
    results.append(Result("ai_service.list_models", list_ok, PiSDErrorCodes.OK if list_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "models folder lists supported model files" if list_ok else "model listing failed", {"listed": listed}))

    unsafe = service.load_model("../bad.tflite")
    unsafe_ok = unsafe.get("code") == PiSDErrorCodes.AI_MODEL_NOT_FOUND
    results.append(Result("ai_service.reject_unsafe_model_id", unsafe_ok, PiSDErrorCodes.OK if unsafe_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "unsafe model id rejected" if unsafe_ok else "unsafe model id was not rejected", {"response": unsafe}))

    safe = service.apply_safety(1.2, 0.9)
    safety_ok = abs(safe["steering"] - 0.6) < 1e-6 and abs(safe["throttle"] - 0.2) < 1e-6
    results.append(Result("ai_service.safety_clamps", safety_ok, PiSDErrorCodes.OK if safety_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI raw output is clamped before motor output" if safety_ok else "AI safety clamp failed", {"safe": safe}))

    unloaded_status = service.status()
    layer_ok = bool((unloaded_status.get("safety_layer") or {}).get("between_ai_and_motors")) and not unloaded_status.get("model_ready")
    results.append(Result("ai_service.status_safety_layer", layer_ok, PiSDErrorCodes.OK if layer_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "status exposes AI safety layer and model readiness" if layer_ok else "AI safety status failed", {"status": unloaded_status}))

    for result in results:
        emit(result)
    SUMMARY_PATH.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
