#!/usr/bin/env python3
"""Validate PiSD AI Mode page and API/page contracts without moving motors."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.app import create_app  # noqa: E402
from pisd.core.errors import PiSDErrorCodes  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
AI_TEMPLATE = WEB_ROOT / "templates" / "ai_mode.html"
AI_CSS = WEB_ROOT / "static" / "css" / "ai_mode.css"
AI_JS = WEB_ROOT / "static" / "js" / "ai_mode.js"
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
    files = {"template": AI_TEMPLATE, "css": AI_CSS, "js": AI_JS}
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
    except Exception as exc:
        return Result("ai_mode.source_contract", False, PiSDErrorCodes.TEST_AI_MODE_FAILED, f"failed to read AI files: {exc}")
    required = {
        "template": [
            "PiSD AI Mode",
            "Back to Front Page",
            "aiModeInitialStatus",
            "aiModelSelect",
            "aiLoadModel",
            "aiSafetyAck",
            "aiEnableMotor",
            "aiStartPreview",
            "aiStartDrive",
            "STOP AI + motors",
            "aiPreviewFrame",
            "aiDriveOverlay",
            "AI road guide",
            "Overlay: On",
            "labels.jsonl",
            "AI → safety limiter → motors",
            "Reverse steering",
            "same sign",
            "manual_drive.css",
            "mdrv-panel",
            'max="1.0"',
        ],
        "css": [".ai-shell", ".ai-grid", ".ai-preview-frame", ".ai-button-danger", "mdrv-drive-overlay", "@media (max-width: 980px)"],
        "js": [
            "aiModeInitialStatus",
            "/api/ai/models",
            "/api/ai/load-model",
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
        ],
    }
    sources = {"template": template, "css": css, "js": js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in required.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    ok = not missing
    return Result(
        "ai_mode.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED,
        "AI Mode source contains model-loading, Manual Drive-style road-guide overlay, safety, same-sign reverse steering policy, and drive contracts" if ok else "AI Mode source contract failed",
        {"missing": missing},
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
    start_unloaded = client.post("/api/ai/start", json={"mode": "drive", "safety_ack": True, "enable_motor_output": False})
    ok = start_unloaded.status_code in {400, 409} and b"PISD-AI-003" in start_unloaded.data
    checks.append(Result("ai_mode.api.drive_requires_model", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AI_MODE_FAILED, "AI drive is blocked when no model is loaded" if ok else "AI drive was not safely blocked without a model", {"http_status": start_unloaded.status_code, "body": start_unloaded.get_data(as_text=True)[:240]}))
    return checks


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.append(check_source_contract())
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
