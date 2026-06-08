#!/usr/bin/env python3
"""Validate PiSD AI Mode page and API/page contracts without moving motors."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.ai_correction import apply_additive_manual_correction, manual_correction_status  # noqa: E402
from pisd.services.ai_safety import apply_ai_safety  # noqa: E402
from pisd.core.settings_manager import SettingsManager  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
AI_TEMPLATE = WEB_ROOT / "templates" / "ai_mode.html"
AI_CSS = WEB_ROOT / "static" / "css" / "ai_mode.css"
AI_JS = WEB_ROOT / "static" / "js" / "ai_mode.js"
GLOBAL_SPACE_JS = WEB_ROOT / "static" / "js" / "global_space_stop.js"
RECORDING_PANEL_JS = WEB_ROOT / "static" / "js" / "recording_download_panel.js"
AI_CORRECTION_PY = PROJECT_ROOT / "pisd" / "services" / "ai_correction.py"
AI_SAFETY_PY = PROJECT_ROOT / "pisd" / "services" / "ai_safety.py"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "ai_mode_page"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": bool(self.ok), "code": self.code, "message": self.message, "details": self.details}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate PiSD AI Mode page.")
    parser.add_argument("--static-only", action="store_true", help="Skip Flask route checks.")
    parser.add_argument("--hardware", action="store_true", help="Create app in hardware mode. No motor output is sent.")
    parser.add_argument("--output", default=str(SUMMARY_PATH))
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    files = {"template": AI_TEMPLATE, "css": AI_CSS, "js": AI_JS, "global_space_js": GLOBAL_SPACE_JS, "recording_panel_js": RECORDING_PANEL_JS, "correction_helper": AI_CORRECTION_PY, "safety_helper": AI_SAFETY_PY}
    return [
        Result(
            f"ai_mode.file.{name}",
            path.exists() and path.stat().st_size > 0,
            PiSDErrorCodes.OK if path.exists() and path.stat().st_size > 0 else PiSDErrorCodes.TEST_AI_MODE_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if path.exists() and path.stat().st_size > 0 else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        )
        for name, path in files.items()
    ]


def check_source_contract() -> Result:
    try:
        template = AI_TEMPLATE.read_text(encoding="utf-8")
        css = AI_CSS.read_text(encoding="utf-8")
        js = AI_JS.read_text(encoding="utf-8")
        global_space_js = GLOBAL_SPACE_JS.read_text(encoding="utf-8")
        recording_panel_js = RECORDING_PANEL_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return Result("ai_mode.source_contract", False, PiSDErrorCodes.TEST_AI_MODE_FAILED, f"failed to read AI files: {exc}")
    required = {
        "template": [
            "PiSD AI Mode",
            "Back to Front Page",
            "aiModeInitialStatus",
            "aiModelSelect",
            "aiLoadModel",
            "aiUploadModel",
            "aiDeleteModel",
            "aiModelUploadFile",
            "aiOutputNames",
            "aiPiTrainerCompatible",
            "aiRuntimeSupport",
            "aiRuntimeHelp",
            "aiRuntimeHelpCommands",
            "aiLoadError",
            "Runtime",
            "TFLite install help",
            "Last load/error",
            "Upload model to Pi",
            "Delete selected",
            "piTrainer export",
            "steering</code> and <code>throttle",
            "aiSafetyAck",
            "aiEnableMotor",
            "aiStartPreview",
            "aiStartDrive",
            "aiSaveSnapshot",
            "aiRecordToggle",
            "aiRecordingState",
            "Start live",
            "Snapshot",
            "Record",
            "STOP AI + motors",
            "aiPreviewFrame",
            "aiDriveOverlay",
            "AI road guide",
            "Overlay: On",
            "labels.jsonl",
            "Limiter / correction / manual",
            "aiLimiterTab",
            "aiCorrectionTab",
            "aiManualDriveTab",
            "aiCorrectionPad",
            "aiManualDrivePad",
            "Full manual pad",
            "Correction %",
            "Corrected steering",
            "Manual correction",
            "aiFilesPanel",
            "aiFileKind",
            "aiDownloadZip",
            "Records & snaps",
            "Download zip",
            "global_space_stop.js",
            "recording_download_panel.js",
            "Space STOP",
            "Reverse steering",
            "Drive output",
            "Frame seq",
            'max="60"',
            "same sign",
            "manual_drive.css",
            "mdrv-panel",
            'max="1.0"',
        ],
        "css": [".ai-shell", ".ai-grid", ".ai-preview-frame", ".ai-preview-run-actions", ".ai-button-danger", "mdrv-drive-overlay", ".ai-runtime-help", "#aiFilesPanel", "@media (max-width: 980px)"],
        "js": [
            "aiModeInitialStatus",
            "/api/ai/models",
            "/api/ai/load-model",
            "/api/ai/upload-model",
            "/api/ai/delete-model",
            "uploadModel",
            "deleteSelectedModel",
            "FormData",
            "aiOutputNames",
            "aiPiTrainerCompatible",
            "aiRuntimeSupport",
            "aiRuntimeHelp",
            "aiRuntimeHelpCommands",
            "aiLoadError",
            "runtime_support",
            "last_corrected_command",
            "install_commands",
            "scripts/install_ai_runtime.py",
            "TFLite missing",
            "/api/ai/start",
            "/api/ai/stop",
            "/api/ai/config",
            "safety_ack",
            "enable_motor_output",
            "sendBeacon",
            "enforceFullScaleThrottleRanges",
            "updateAIOverlay",
            "roadGuideGeometry",
            "aiOverlayToggle",
            "reverse guide hidden",
            "roadBoundaryPath",
            "aiReverseSteeringPolicy",
            "aiDriveOutputState",
            "aiFrameSeq",
            "drive_output_enabled",
            "/api/recording/capture",
            "/api/recording/start",
            "/api/recording/stop",
            "refreshAIRecordingFiles",
            "saveAISnapshot",
            "toggleAIRecording",
            "/api/ai/manual-correction",
            "sendManualCorrection",
            "bindKeyboardShortcuts",
            "ai-correction-keyboard",
            "sendFullManualDrive",
            "ai-manual-keyboard",
            "/api/control/manual",
            "pisd:space-stop",
            "configDirtyFields",
            "scheduleConfigAutoSave",
            "aiMaxThrottle",
        ],
        "global_space_js": ["PiSDGlobalSpaceStop", "space-global-stop", "/api/control/stop", "/api/ai/stop", "stopImmediatePropagation"],
        "recording_panel_js": ["PiSDRecordingDownloadPanels", "/api/recording/items", "/api/recording/download.zip", "/api/recording/delete", "data-recording-download-panel"],
    }
    sources = {"template": template, "css": css, "js": js, "global_space_js": global_space_js, "recording_panel_js": recording_panel_js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    forbidden = {
        "template": ["Refresh frame", "Start camera + live stream", "Space centre correction"],
        "js": ["aiSnapshot"],
    }
    present_forbidden = {name: [token for token in tokens if token in sources[name]] for name, tokens in forbidden.items()}
    present_forbidden = {name: tokens for name, tokens in present_forbidden.items() if tokens}
    ok = not missing and not present_forbidden
    return Result(
        "ai_mode.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "AI Mode source contains model-loading, one Start live action, snapshot/record buttons, road-guide overlay, safety, same-sign reverse steering policy, and drive contracts" if ok else "AI Mode source contract failed",
        {"missing": missing, "forbidden_present": present_forbidden},
    )


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("ai_mode.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    checks = []
    for path, label, marker in (
        ("/ai-mode", "ai_mode.route.page", b"PiSD AI Mode"),
        ("/autopilot", "ai_mode.route.legacy_alias", b"PiSD AI Mode"),
        ("/api/ai/status", "ai_mode.api.status", b"ai"),
        ("/api/ai/models", "ai_mode.api.models", b"supported_extensions"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        checks.append(Result(label, ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, f"{path} loaded" if ok else f"{path} returned {response.status_code}", {"http_status": response.status_code}))
    upload_missing = client.post("/api/ai/upload-model", data={})
    ok = upload_missing.status_code == 400 and b"No AI model file" in upload_missing.data
    checks.append(Result("ai_mode.api.upload_requires_file", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI upload rejects missing file" if ok else "AI upload did not reject missing file", {"http_status": upload_missing.status_code, "body": upload_missing.get_data(as_text=True)[:240]}))

    correction = client.post("/api/ai/manual-correction", json={"steering": 0.25, "throttle": -0.10, "source": "test"})
    ok = correction.status_code == 200 and b"manual_correction" in correction.data
    checks.append(Result("ai_mode.api.manual_correction", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI manual correction API accepts guarded correction vector" if ok else "AI manual correction API did not accept correction vector", {"http_status": correction.status_code, "body": correction.get_data(as_text=True)[:240]}))

    config = client.post("/api/ai/config", json={"manual_correction_enabled": True, "manual_mix_percent": 75})
    ok = config.status_code == 200 and b"manual_mix_percent" in config.data and b"75" in config.data
    checks.append(Result("ai_mode.api.correction_config", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI correction percentage settings save and normalize" if ok else "AI correction percentage config did not save", {"http_status": config.status_code, "body": config.get_data(as_text=True)[:240]}))

    throttle_config = client.post("/api/ai/config", json={"max_throttle": 0.61})
    throttle_body = throttle_config.get_data(as_text=True)
    ok = throttle_config.status_code == 200 and '"max_throttle":0.61' in throttle_body.replace(' ', '')
    checks.append(Result("ai_mode.api.max_throttle_config", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI max throttle setting saves and returns from runtime settings" if ok else "AI max throttle setting did not persist through config API", {"http_status": throttle_config.status_code, "body": throttle_body[:240]}))

    start_unloaded = client.post("/api/ai/start", json={"mode": "drive", "safety_ack": True, "enable_motor_output": False})
    ok = start_unloaded.status_code in {400, 409} and b"PISD-AI-003" in start_unloaded.data
    checks.append(Result("ai_mode.api.drive_requires_model", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI drive is blocked when no model is loaded" if ok else "AI drive was not safely blocked without a model", {"http_status": start_unloaded.status_code, "body": start_unloaded.get_data(as_text=True)[:240]}))
    return checks




def check_settings_persistence() -> Result:
    """Check that AI max throttle survives SettingsManager save/load without Flask."""
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = Path(tmp) / "runtime_settings.json"
        manager = SettingsManager(settings_path, {})
        ok, settings, report = manager.save({"ai_mode": {"max_throttle": 0.61, "max_steering": 0.64}})
        reloaded = SettingsManager(settings_path, {}).get().get("ai_mode") or {}
    throttle_ok = abs(float(reloaded.get("max_throttle", -1.0)) - 0.61) < 1e-9
    steering_ok = abs(float(reloaded.get("max_steering", -1.0)) - 0.64) < 1e-9
    return Result(
        "ai_mode.settings_persistence.max_throttle",
        bool(ok and throttle_ok and steering_ok),
        PiSDErrorCodes.OK if ok and throttle_ok and steering_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "AI max throttle persists through runtime_settings.json save/load" if ok and throttle_ok and steering_ok else "AI max throttle did not persist through settings manager",
        {"saved_ok": ok, "report": getattr(report, "message", ""), "reloaded_ai_mode": reloaded},
    )

def check_correction_math() -> list[Result]:
    """Check AI correction and safety math without camera, model, Flask, or motors."""
    manual = manual_correction_status(
        {"manual_correction_enabled": True, "manual_mix_percent": 50.0, "manual_correction_timeout_s": 0.75},
        {"steering": -0.6, "throttle": 0.4, "source": "math-test", "updated_at_utc": ""},
        10.0,
        now_monotonic=10.2,
    )
    corrected = apply_additive_manual_correction(0.4, -0.2, {"manual_mix_percent": 50.0}, manual)
    steering_ok = abs(corrected.get("steering", 99.0) - 0.1) < 1e-9
    throttle_ok = abs(corrected.get("throttle", 99.0) - 0.0) < 1e-9
    gain_ok = abs(corrected.get("correction_gain", corrected.get("manual_weight", 99.0)) - 0.5) < 1e-9
    debug_ok = corrected.get("equation") == "ai + manual * correction_gain"
    first = Result(
        "ai_mode.correction_math.additive_50_percent",
        steering_ok and throttle_ok and gain_ok and debug_ok,
        PiSDErrorCodes.OK if steering_ok and throttle_ok and gain_ok and debug_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "manual correction is added as AI + manual * correction_percent" if steering_ok and throttle_ok and gain_ok and debug_ok else "manual correction did not use additive AI-base equation",
        {"corrected": corrected, "expected": {"steering": 0.1, "throttle": 0.0, "correction_gain": 0.5}},
    )

    full = apply_additive_manual_correction(0.3, 0.2, {"manual_mix_percent": 100.0}, {"active": True, "steering": 0.4, "throttle": -0.3})
    second_ok = abs(full.get("steering", 99.0) - 0.7) < 1e-9 and abs(full.get("throttle", 99.0) - (-0.1)) < 1e-9
    second = Result(
        "ai_mode.correction_math.additive_100_percent",
        second_ok,
        PiSDErrorCodes.OK if second_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "100% correction adds the full manual correction to the AI base" if second_ok else "100% correction replaced AI output instead of adding to it",
        {"corrected": full, "expected": {"steering": 0.7, "throttle": -0.1}},
    )

    clamped = apply_additive_manual_correction(0.8, 0.9, {"manual_mix_percent": 60.0}, {"active": True, "steering": 0.5, "throttle": 0.5})
    clamp_ok = abs(clamped.get("steering", 99.0) - 1.0) < 1e-9 and abs(clamped.get("throttle", 99.0) - 1.0) < 1e-9
    third = Result(
        "ai_mode.correction_math.clamps_corrected_command",
        clamp_ok,
        PiSDErrorCodes.OK if clamp_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "corrected AI command is clamped before the safety limiter" if clamp_ok else "corrected AI command was not clamped safely",
        {"corrected": clamped, "expected": {"steering": 1.0, "throttle": 1.0}},
    )

    fixed = apply_ai_safety(
        0.4,
        -0.8,
        {"output_mode": "steering_only", "fixed_throttle": 0.16, "max_steering": 1.0, "max_throttle": 1.0, "steering_smoothing": 0.0, "throttle_smoothing": 0.0},
        {"steering": 0.0, "throttle": 0.0},
    )
    fixed_ok = abs(fixed.get("steering", 99.0) - 0.4) < 1e-9 and abs(fixed.get("throttle", 99.0) - 0.16) < 1e-9
    fourth = Result(
        "ai_mode.safety_math.fixed_throttle_after_correction",
        fixed_ok,
        PiSDErrorCodes.OK if fixed_ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "fixed-throttle mode still forces throttle after correction" if fixed_ok else "fixed-throttle safety output changed unexpectedly",
        {"safe": fixed, "expected": {"steering": 0.4, "throttle": 0.16}},
    )
    return [first, second, third, fourth]

def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.append(check_source_contract())
    results.append(check_settings_persistence())
    results.extend(check_correction_math())
    if not args.static_only:
        results.extend(check_routes(args.hardware))
    for result in results:
        emit(result)
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
