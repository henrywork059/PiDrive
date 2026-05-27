#!/usr/bin/env python3
"""Validate AI Drive service model listing and safety limits without hardware."""

from __future__ import annotations

import io
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

    uploaded = service.upload_model("piTrainer export.keras", io.BytesIO(b"fake keras bytes"))
    uploaded_id = ((uploaded.get("model") or {}).get("id") or "")
    upload_ok = uploaded.get("ok") and uploaded_id.endswith(".keras") and "/" not in uploaded_id
    results.append(Result("ai_service.upload_model", upload_ok, PiSDErrorCodes.OK if upload_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "uploaded piTrainer-style model file is saved with a safe id" if upload_ok else "model upload failed", {"response": uploaded}))

    deleted = service.delete_model(uploaded_id)
    delete_ok = deleted.get("ok") and deleted.get("deleted_model_id") == uploaded_id and not (models / uploaded_id).exists()
    results.append(Result("ai_service.delete_model", delete_ok, PiSDErrorCodes.OK if delete_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "selected model can be deleted from PiSD/models" if delete_ok else "model delete failed", {"response": deleted}))

    dict_steering, dict_throttle = service._commands_from_prediction_output({"steering": [[0.42]], "throttle": [[0.18]]})
    list_steering, list_throttle = service._commands_from_prediction_output([[[0.31]], [[0.27]]], ["serving_default_steering:0", "serving_default_throttle:0"])
    array_steering, array_throttle = service._commands_from_prediction_output([[0.25, 0.35]])
    parser_ok = (
        abs(dict_steering - 0.42) < 1e-6 and abs(dict_throttle - 0.18) < 1e-6
        and abs(list_steering - 0.31) < 1e-6 and abs(list_throttle - 0.27) < 1e-6
        and abs(array_steering - 0.25) < 1e-6 and abs(array_throttle - 0.35) < 1e-6
    )
    results.append(Result("ai_service.pitrainer_output_parser", parser_ok, PiSDErrorCodes.OK if parser_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "piTrainer dict/list/two-value model outputs map to steering/throttle" if parser_ok else "piTrainer model output parser failed", {"dict": [dict_steering, dict_throttle], "list": [list_steering, list_throttle], "array": [array_steering, array_throttle]}))

    unsafe = service.load_model("../bad.tflite")
    unsafe_ok = unsafe.get("code") == PiSDErrorCodes.AI_MODEL_NOT_FOUND
    results.append(Result("ai_service.reject_unsafe_model_id", unsafe_ok, PiSDErrorCodes.OK if unsafe_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "unsafe model id rejected" if unsafe_ok else "unsafe model id was not rejected", {"response": unsafe}))

    safe = service.apply_safety(1.2, 0.9)
    safety_ok = abs(safe["steering"] - 0.6) < 1e-6 and abs(safe["throttle"] - 0.2) < 1e-6
    results.append(Result("ai_service.safety_clamps", safety_ok, PiSDErrorCodes.OK if safety_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI raw output is clamped before motor output" if safety_ok else "AI safety clamp failed", {"safe": safe}))

    full_scale_service = AIDriveService(OUTPUT_ROOT, {"max_throttle": 1.0, "fixed_throttle": 1.0, "max_steering": 1.0, "steering_smoothing": 0.0, "throttle_smoothing": 0.0})
    full_safe = full_scale_service.apply_safety(0.4, 1.2)
    full_scale_ok = abs(full_safe["throttle"] - 1.0) < 1e-6 and abs((full_scale_service.status().get("settings") or {}).get("max_throttle", 0.0) - 1.0) < 1e-6
    results.append(Result("ai_service.full_scale_throttle", full_scale_ok, PiSDErrorCodes.OK if full_scale_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI max/fixed throttle settings allow full-scale 1.00" if full_scale_ok else "AI throttle settings were still clamped below 1.00", {"safe": full_safe, "settings": full_scale_service.status().get("settings")}))

    reverse_service = AIDriveService(OUTPUT_ROOT, {"max_throttle": 1.0, "max_steering": 1.0, "steering_smoothing": 0.0, "throttle_smoothing": 0.0})
    reverse_safe = reverse_service.apply_safety(0.45, -0.6)
    reverse_ok = abs(reverse_safe["steering"] - 0.45) < 1e-6 and abs(reverse_safe["throttle"] + 0.6) < 1e-6
    results.append(Result("ai_service.reverse_steering_same_sign", reverse_ok, PiSDErrorCodes.OK if reverse_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "reverse throttle keeps the same steering sign before motor output" if reverse_ok else "reverse throttle unexpectedly inverted steering", {"safe": reverse_safe}))

    steering_only_service = AIDriveService(OUTPUT_ROOT, {"output_mode": "steering_only", "fixed_throttle": 0.33, "max_throttle": 1.0, "steering_smoothing": 0.0, "throttle_smoothing": 0.0})
    straight_safe = steering_only_service.apply_safety(0.0, 0.0)
    steering_only_ok = abs(straight_safe["throttle"] - 0.33) < 1e-6
    results.append(Result("ai_service.steering_only_keeps_fixed_throttle", steering_only_ok, PiSDErrorCodes.OK if steering_only_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "steering-only mode keeps fixed throttle even when predicted steering is straight" if steering_only_ok else "steering-only mode stopped on straight steering", {"safe": straight_safe}))

    unloaded_status = service.status()
    safety_layer = unloaded_status.get("safety_layer") or {}
    layer_ok = bool(safety_layer.get("between_ai_and_motors")) and safety_layer.get("reverse_steering_policy") == "same_sign" and not unloaded_status.get("model_ready")
    results.append(Result("ai_service.status_safety_layer", layer_ok, PiSDErrorCodes.OK if layer_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "status exposes AI safety layer, model readiness, and same-sign reverse steering policy" if layer_ok else "AI safety status failed", {"status": unloaded_status}))

    for result in results:
        emit(result)
    SUMMARY_PATH.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
