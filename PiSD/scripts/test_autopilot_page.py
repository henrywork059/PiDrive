#!/usr/bin/env python3
"""Validate the PiSD Autopilot page source contract.

Static checks do not start camera output or move motors. Optional Flask route
checks only load pages/API status in simulation mode.
"""

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
TEMPLATE = WEB_ROOT / "templates" / "autopilot.html"
CSS = WEB_ROOT / "static" / "css" / "autopilot.css"
JS = WEB_ROOT / "static" / "js" / "autopilot.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "autopilot_page"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": bool(self.ok), "code": self.code, "message": self.message, "details": dict(self.details)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate PiSD Autopilot page.")
    parser.add_argument("--static-only", action="store_true", help="Skip Flask route/API checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": TEMPLATE, "css": CSS, "js": JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(Result(
            f"autopilot.file.{name}",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED,
            f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
            {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
        ))
    return results


def check_source_contract() -> Result:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
    except Exception as exc:
        return Result("autopilot.source_contract", False, PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, f"failed to read source: {exc}")
    expected = {
        "template": [
            "PiSD Autopilot", "Back to Front Page", "autopilotInitialStatus", "autopilotControlPanel",
            "apSafetyAck", "apEnableMotorOutput", "apStart", "apStop", "STOP AUTOPILOT + MOTORS",
            "autopilotPreviewPanel", "apStartCamera", "apLiveCamera", "apStopCamera",
        ],
        "css": [".ap-shell", ".ap-grid", ".ap-preview-frame", ".ap-big-stop", "data-autopilot-running"],
        "js": [
            "autopilotInitialStatus", "/api/autopilot/status", "/api/autopilot/config", "/api/autopilot/start",
            "/api/autopilot/stop", "/api/camera/start", "/video_feed", "sendBeacon", "failSafeStop",
        ],
    }
    sources = {"template": template, "css": css, "js": js}
    missing = {name: [token for token in tokens if token not in sources[name]] for name, tokens in expected.items()}
    missing = {name: tokens for name, tokens in missing.items() if tokens}
    return Result(
        "autopilot.source_contract",
        not missing,
        PiSDErrorCodes.OK if not missing else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED,
        "autopilot page source contract passed" if not missing else "autopilot page source contract missing tokens",
        {"missing": missing},
    )


def check_routes() -> list[Result]:
    try:
        app = create_app(hardware_enabled=False)
    except RuntimeError as exc:
        return [Result("autopilot.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]
    client = app.test_client()
    results: list[Result] = []
    for path, label, marker in (
        ("/autopilot", "autopilot.route.page", b"PiSD Autopilot"),
        ("/testing/static/css/autopilot.css", "autopilot.static.css", b".ap-shell"),
        ("/testing/static/js/autopilot.js", "autopilot.static.js", b"/api/autopilot/start"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(Result(label, ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, f"{path} loaded" if ok else f"{path} failed", {"http_status": response.status_code}))
    response = client.get("/api/autopilot/status")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("ok") is True and isinstance(payload.get("autopilot"), dict)
    results.append(Result("autopilot.route.status_api", ok, PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "status API loaded" if ok else "status API failed", {"http_status": response.status_code, "code": payload.get("code")}))
    return results


def main() -> int:
    args = parse_args()
    results = check_files()
    results.append(check_source_contract())
    if not args.static_only:
        results.extend(check_routes())
    for result in results:
        emit(result)
    ok = all(r.ok for r in results)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": ok, "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    print(json.dumps({"summary": str(output), "code": PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_AUTOPILOT_CONTRACT_FAILED, "failed": sum(1 for r in results if not r.ok)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
