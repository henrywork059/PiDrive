#!/usr/bin/env python3
"""Validate the PiSD panel testing page.

This script checks the new flexible panel lab used before the final GUI is built.
It is safe by default and never moves motors.
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
from pisd.core.panel_contracts import get_panel_contracts  # noqa: E402

WEB_ROOT = PROJECT_ROOT / "pisd" / "web"
WEB_TEMPLATE = WEB_ROOT / "templates" / "panel_testing.html"
WEB_CSS = WEB_ROOT / "static" / "css" / "panel_testing.css"
WEB_JS = WEB_ROOT / "static" / "js" / "panel_testing.js"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "panel_testing_gui"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

REQUIRED_PANELS = [
    "system-status-panel",
    "camera-preview-panel",
    "camera-settings-panel",
    "motor-settings-panel",
    "motor-channel-panel",
    "manual-drive-panel",
    "safety-stop-panel",
    "error-monitor-panel",
    "api-inspector-panel",
    "validation-panel",
    "recording-panel",
    "model-runtime-panel",
]

REQUIRED_STYLE_CONTROLS = [
    "ptTheme",
    "ptLayoutMode",
    "ptViewportPreset",
    "ptPanelSizePreset",
    "ptDensity",
    "ptFontScale",
    "ptPanelGap",
    "ptPanelRadius",
    "ptBorderStrength",
    "ptShadowStrength",
    "ptMinPanelWidth",
    "ptPreviewAspect",
]


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": bool(self.ok),
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the PiSD panel testing lab page.")
    parser.add_argument("--hardware", action="store_true", help="Create the Flask app with hardware mode requested. Motors are never armed by this script.")
    parser.add_argument("--static-only", action="store_true", help="Only check template/CSS/JS files; skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {"template": WEB_TEMPLATE, "css": WEB_CSS, "js": WEB_JS}.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"panel_gui.file.{name}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> Result:
    try:
        template = WEB_TEMPLATE.read_text(encoding="utf-8")
        css = WEB_CSS.read_text(encoding="utf-8")
        js = WEB_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return Result("panel_gui.source_contract", False, PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED, f"failed to read files: {exc}")

    required_template = [
        "PiSD Panel Testing Lab",
        "Back to Front Page",
        "Flexible GUI panel stress page",
        "ptPanelGrid",
        "ptPanelReport",
        "panelInitialStatusJson",
        "panelManifestJson",
        *REQUIRED_STYLE_CONTROLS,
    ]
    required_css = [
        "--pt-min-panel-width",
        "--pt-preview-aspect",
        ".pt-panel-grid",
        ".pt-panel[data-size=\"compact\"]",
        "@media (max-width: 850px)",
        "container-type: inline-size",
    ]
    required_js = [
        "PANEL_BLUEPRINTS",
        "runAllPanelChecks",
        "runAllPanelApiChecks",
        "runPanelApiTest",
        "showContract",
        "showLastResponse",
        "showExpected",
        "applyPanelSizePreset",
        "collectSettings",
        "savePreset",
        "loadPreset",
        "exportPreset",
        "importPresetFile",
        "PISD-TEST-012",
        "PISD-TEST-013",
        "PISD-TEST-014",
    ]
    missing = {
        "template": [token for token in required_template if token not in template],
        "css": [token for token in required_css if token not in css],
        "js": [token for token in required_js if token not in js],
    }
    missing = {key: value for key, value in missing.items() if value}
    ok = not missing
    return Result(
        "panel_gui.source_contract",
        ok,
        PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
        "panel lab source includes registry loading, style controls, size controls, presets, and API contract actions" if ok else "panel lab source contract failed",
        {"missing": missing},
    )


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("panel_gui.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]

    client = app.test_client()
    results: list[Result] = []

    response = client.get("/panel-testing")
    ok = response.status_code == 200 and b"PiSD Panel Testing Lab" in response.data and b"ptPanelGrid" in response.data
    results.append(
        Result(
            "panel_gui.route.page",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
            "/panel-testing loaded" if ok else f"/panel-testing returned HTTP {response.status_code} or missing content",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )

    for path, label, marker in (
        ("/testing/static/css/panel_testing.css", "panel_gui.static.css", b".pt-panel-grid"),
        ("/testing/static/js/panel_testing.js", "panel_gui.static.js", b"PANEL_BLUEPRINTS"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    response = client.get("/api/panel-testing/manifest")
    payload = response.get_json(silent=True) or {}
    panels_payload = payload.get("panels") or []
    panels = {str(item.get("id")) for item in panels_payload if isinstance(item, dict)}
    controls = set(payload.get("style_controls") or [])
    required_control_names = {"theme", "layout_mode", "viewport_preset", "panel_size_preset", "density", "font_scale", "panel_gap", "corner_radius", "minimum_panel_width", "preview_aspect"}
    contracts_ok = all(isinstance(item.get("safe_test"), dict) and isinstance(item.get("endpoints"), list) for item in panels_payload if isinstance(item, dict))
    ok = (
        response.status_code == 200
        and payload.get("code") == PiSDErrorCodes.OK
        and set(REQUIRED_PANELS).issubset(panels)
        and required_control_names.issubset(controls)
        and payload.get("panel_count", 0) >= len(REQUIRED_PANELS)
        and contracts_ok
    )
    results.append(
        Result(
            "panel_gui.manifest_contract",
            ok,
            payload.get("code") or PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
            "panel manifest lists planned final panels, style controls, and API contracts" if ok else "panel manifest contract failed",
            {"http_status": response.status_code, "missing_panels": sorted(set(REQUIRED_PANELS) - panels), "missing_controls": sorted(required_control_names - controls), "contracts_ok": contracts_ok},
        )
    )

    response = client.get("/api/panel-testing/contracts")
    payload = response.get_json(silent=True) or {}
    ok = response.status_code == 200 and payload.get("code") == PiSDErrorCodes.OK and len(payload.get("panels") or []) >= len(REQUIRED_PANELS)
    results.append(
        Result(
            "panel_gui.contracts_route",
            ok,
            payload.get("code") or PiSDErrorCodes.TEST_PANEL_API_CONTRACT_FAILED,
            "panel contracts route loaded" if ok else f"panel contracts route returned HTTP {response.status_code}",
            {"http_status": response.status_code, "panel_count": len(payload.get("panels") or [])},
        )
    )
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    for result in check_files():
        emit(result)
        results.append(result)
    result = check_source_contract()
    emit(result)
    results.append(result)
    if not args.static_only:
        for result in check_routes(args.hardware):
            emit(result)
            results.append(result)

    failed = [item for item in results if not item.ok]
    summary = {
        "ok": not failed,
        "code": PiSDErrorCodes.OK if not failed else PiSDErrorCodes.TEST_PANEL_GUI_CONTRACT_FAILED,
        "failed": len(failed),
        "passed": len(results) - len(failed),
        "results": [item.as_dict() for item in results],
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("-" * 72)
    print(f"{'OK' if not failed else 'FAIL':<4} {summary['code']:<13} summary - passed={summary['passed']} failed={summary['failed']} output={output_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
