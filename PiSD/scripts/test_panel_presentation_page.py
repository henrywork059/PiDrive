#!/usr/bin/env python3
"""Validate the PiSD panel presentation settings page.

This checks the browser-local panel presentation settings page and the shared
CSS/JS that applies saved panel style/size choices across other PiSD pages.
It never starts camera output or moves motors.
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
TEMPLATE = WEB_ROOT / "templates" / "panel_presentation.html"
CSS = WEB_ROOT / "static" / "css" / "panel_presentation.css"
JS = WEB_ROOT / "static" / "js" / "panel_presentation.js"
GLOBAL_CSS = WEB_ROOT / "static" / "css" / "panel_presentation_global.css"
GLOBAL_JS = WEB_ROOT / "static" / "js" / "panel_presentation_global.js"
FRONT_TEMPLATE = WEB_ROOT / "templates" / "front_page.html"
SETTINGS_TEMPLATE = WEB_ROOT / "templates" / "settings_tab.html"
TESTING_TEMPLATE = WEB_ROOT / "templates" / "testing_server.html"
DASHBOARD_TEMPLATE = WEB_ROOT / "templates" / "main_dashboard.html"
MANUAL_TEMPLATE = WEB_ROOT / "templates" / "manual_drive.html"
PANEL_TESTING_TEMPLATE = WEB_ROOT / "templates" / "panel_testing.html"
OUTPUT_DIR = PROJECT_ROOT / "test_outputs" / "panel_presentation"
SUMMARY_PATH = OUTPUT_DIR / "summary.json"

REQUIRED_CONTROLS = [
    "ppTheme",
    "ppLayoutMode",
    "ppDensity",
    "ppFontScale",
    "ppPanelGap",
    "ppPanelRadius",
    "ppBorderStrength",
    "ppShadowStrength",
    "ppMinPanelWidth",
    "ppPreviewAspect",
    "ppPreviewFit",
    "ppPanelPadding",
    "ppPanelHeaderMode",
    "ppButtonScale",
    "ppConsoleHeight",
    "ppCardAccent",
    "ppAdaptivePanels",
    "ppStatusPanelHWeight",
    "ppStatusPanelVWeight",
    "ppPreviewPanelHWeight",
    "ppPreviewPanelVWeight",
    "ppControlPanelHWeight",
    "ppControlPanelVWeight",
    "ppSettingsPanelHWeight",
    "ppSettingsPanelVWeight",
    "ppLogPanelHWeight",
    "ppLogPanelVWeight",
    "ppAutoSave",
    "ppApply",
    "ppSave",
    "ppReset",
    "ppExport",
    "ppImportButton",
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
    parser = argparse.ArgumentParser(description="Validate PiSD panel presentation settings page.")
    parser.add_argument("--hardware", action="store_true", help="Create app in hardware mode. No movement commands are sent.")
    parser.add_argument("--static-only", action="store_true", help="Only check files/source contracts; skip Flask route checks.")
    parser.add_argument("--output", default=str(SUMMARY_PATH), help="Summary JSON output path.")
    return parser.parse_args()


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def check_files() -> list[Result]:
    results: list[Result] = []
    for name, path in {
        "template": TEMPLATE,
        "css": CSS,
        "js": JS,
        "global_css": GLOBAL_CSS,
        "global_js": GLOBAL_JS,
    }.items():
        ok = path.exists() and path.stat().st_size > 0
        results.append(
            Result(
                f"panel_presentation.file.{name}",
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
                f"{path.relative_to(PROJECT_ROOT)} exists" if ok else f"{path.relative_to(PROJECT_ROOT)} missing or empty",
                {"path": str(path.relative_to(PROJECT_ROOT)), "bytes": path.stat().st_size if path.exists() else 0},
            )
        )
    return results


def check_source_contract() -> list[Result]:
    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        css = CSS.read_text(encoding="utf-8")
        js = JS.read_text(encoding="utf-8")
        global_css = GLOBAL_CSS.read_text(encoding="utf-8")
        global_js = GLOBAL_JS.read_text(encoding="utf-8")
    except Exception as exc:
        return [Result("panel_presentation.source_contract", False, PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED, f"failed to read files: {exc}")]

    required_template = [
        "PiSD Panel Presentation Settings",
        "Back to Front Page",
        "panelPresentationControls",
        "panelPresentationPreview",
        "panelPresentationOutput",
        "panelPresentationInitialStatus",
        *REQUIRED_CONTROLS,
    ]
    required_css = [".pp-shell", ".pp-control-grid", ".pp-panel-grid", ".pp-preview-surface", "@media (max-width: 980px)"]
    required_js = ["PiSDPanelPresentation", "/api/settings", "ppSave", "ppApply", "ppReset", "ppExport", "autoSaveEnabled", "PISD-TEST-018"]
    required_global_css = ["--pisd-ui-gap", "--pisd-ui-radius", "--pisd-ui-panel-min-width", "--pisd-ui-button-scale", "--pisd-ui-console-height", "--pisd-preview-h-span", "data-pisd-adaptive-panels", "body[data-pisd-density", ".fp-mode-grid", ".mdrv-shell"]
    required_global_js = ["STORAGE_KEY", "pisd.panelPresentation.v1", "PiSDPanelPresentation", "loadFromBackend", "applyPanelWeights", "statusPanelHWeight", "previewPanelVWeight"]

    missing = {
        "template": [token for token in required_template if token not in template],
        "css": [token for token in required_css if token not in css],
        "js": [token for token in required_js if token not in js],
        "global_css": [token for token in required_global_css if token not in global_css],
        "global_js": [token for token in required_global_js if token not in global_js],
    }
    missing = {key: value for key, value in missing.items() if value}
    ok = not missing
    results = [
        Result(
            "panel_presentation.source_contract",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
            "panel presentation page includes controls, save/apply/export/import, and global style application" if ok else "panel presentation source contract failed",
            {"missing": missing},
        )
    ]

    page_sources = {
        "front_page": FRONT_TEMPLATE,
        "settings_tab": SETTINGS_TEMPLATE,
        "testing_tab": TESTING_TEMPLATE,
        "dashboard": DASHBOARD_TEMPLATE,
        "manual_drive": MANUAL_TEMPLATE,
        "panel_testing": PANEL_TESTING_TEMPLATE,
    }
    missing_includes = []
    for name, path in page_sources.items():
        text = path.read_text(encoding="utf-8")
        if "panel_presentation_global.css" not in text or "panel_presentation_global.js" not in text:
            missing_includes.append(name)
    ok = not missing_includes
    results.append(
        Result(
            "panel_presentation.global_includes",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
            "shared panel presentation CSS/JS is included on all GUI pages" if ok else "some pages do not include global presentation CSS/JS",
            {"missing_includes": missing_includes},
        )
    )
    return results


def check_routes(hardware: bool) -> list[Result]:
    try:
        app = create_app(hardware_enabled=hardware)
    except RuntimeError as exc:
        return [Result("panel_presentation.create_app", False, PiSDErrorCodes.APP_DEPENDENCY_MISSING, f"Flask app could not be created: {exc}")]

    client = app.test_client()
    results: list[Result] = []
    for path, label, marker in (
        ("/panel-presentation", "panel_presentation.route.page", b"Panel style and size settings"),
        ("/api/panel-presentation/manifest", "panel_presentation.route.manifest", b"pisd.panelPresentation.v1"),
        ("/testing/static/css/panel_presentation.css", "panel_presentation.static.css", b".pp-shell"),
        ("/testing/static/js/panel_presentation.js", "panel_presentation.static.js", b"ppSave"),
        ("/testing/static/css/panel_presentation_global.css", "panel_presentation.static.global_css", b"--pisd-ui-gap"),
        ("/testing/static/js/panel_presentation_global.js", "panel_presentation.static.global_js", b"PiSDPanelPresentation"),
    ):
        response = client.get(path)
        ok = response.status_code == 200 and marker in response.data
        results.append(
            Result(
                label,
                ok,
                PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
                f"{path} loaded" if ok else f"{path} returned HTTP {response.status_code} or missing marker",
                {"http_status": response.status_code, "bytes": len(response.data)},
            )
        )

    # Confirm panel-testing remains its own route and was not renamed/replaced.
    response = client.get("/panel-testing")
    ok = response.status_code == 200 and b"PiSD Panel Testing Lab" in response.data
    results.append(
        Result(
            "panel_presentation.panel_testing_preserved",
            ok,
            PiSDErrorCodes.OK if ok else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED,
            "/panel-testing remains preserved" if ok else "/panel-testing was not available as expected",
            {"http_status": response.status_code, "bytes": len(response.data)},
        )
    )
    return results


def main() -> int:
    args = parse_args()
    results: list[Result] = []
    results.extend(check_files())
    results.extend(check_source_contract())
    if not args.static_only:
        results.extend(check_routes(args.hardware))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps({"code": PiSDErrorCodes.OK if all(r.ok for r in results) else PiSDErrorCodes.TEST_PANEL_PRESENTATION_FAILED, "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")

    for result in results:
        emit(result)
    failed = [result for result in results if not result.ok]
    print(json.dumps({"summary": str(args.output), "ok": not failed, "failed": len(failed)}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
